#!/usr/bin/env python3
"""Aggregate a v2 round: grade every cell, tally per check, run the fixed tests.

Usage:
    python3 analyze_v2.py evals/runs/<round-dir> [--only t1,t2] [--include-superseded]

Comparisons and the significance handling are the COMPARISONS table below and
are not chosen here after seeing the numbers (the TASKS.md that pre-registered
them is not in this repository):
  * t1, t3, t4  -> skills vs baseline
  * t2          -> skills vs scripts-only (what the TEXT buys)
                   and scripts-only vs baseline (what the FILES buy)
  * Fisher exact, two-sided; Benjamini-Hochberg across every test in the round.
  * t4 must be null. If any t4 check is significant, the round is void. A round
    with no t4 cells has NOT passed that gate -- it was never evaluated.

Directories whose name contains `-DISCARDED-` or `-SUPERSEDED-` hold cells a
round threw away (a harness edit mid-round, a grader race). They are excluded
and listed, never pooled; `--include-superseded` exists only to audit them.
Cells that are ungradable (no result event, a CLI error, no verdict file) or
contaminated (a baseline-type cell whose session loaded this pack's skills or
plugin) are counted and listed, never tallied.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import grade_v2  # noqa: E402

ALPHA = 0.05
# A round may restrict itself to a subset. Correction is applied across the
# tests actually run, which is why a narrow round is not the same as cherry-
# picking from a wide one: the comparisons are fixed before the cells exist.
COMPARISONS = {
    # `claude-md-only vs baseline` is round 4: it separates CLAUDE.md's
    # "verify, do not answer from memory" paragraph from the skill prose, which
    # the `skills` cell ships together. A pair with no cells in the round is
    # skipped, so listing it here does not affect earlier rounds.
    "t1": [("skills", "baseline"), ("claude-md-only", "baseline"),
           ("skills", "claude-md-only")],
    "t2": [("skills", "scripts-only"), ("scripts-only", "baseline")],
    "t3": [("skills", "baseline")],
    "t4": [("skills", "baseline")],
    "t5": [("skills", "baseline")],
    # Ladder rungs (evals/LADDER.md) run `baseline` only in phase 1 -- the
    # question is whether the model reaches it at all, and a real-outcome
    # grader answers that without a comparison cell. `patch` is phase 2: the
    # candidate line and nothing else, tested one line at a time.
    "t6": [("patch", "baseline")],
    "t7": [("patch", "baseline")],
    "g1": [("patch", "baseline")],
    "g2": [("patch", "baseline")],
    "g3": [("patch", "baseline")],
    "tr1": [("patch", "baseline")],
    "tr2": [("patch", "baseline")],
    "tr3": [("patch", "baseline")],
    "qos1": [("patch", "baseline")],
    # 2026-07-31 coverage sweep. Rungs run baseline-only (LADDER.md rung
    # mechanics), so there is no within-round comparison to register: the pass
    # rate per real-outcome check IS the result, and the ≤7/10 threshold is the
    # verdict.
    "ctl1": [],
    "ctl2": [],
    "ctl3": [],
    "tst1": [],
    "tst2": [],
    "tst3": [],
    "per1": [],
    "per2": [],
    "per3": [],
    "mvt1": [],
    "mvt2": [],
    "mvt3": [],
    "dev3": [],
    "dev2": [],
    "dev1": [],
    "cor3": [],
    "cor2": [],
    "cor1": [],
}


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 Fisher exact, two-sided. Same implementation as analyze.py used."""
    def logf(n: int) -> float:
        return math.lgamma(n + 1)

    n = a + b + c + d
    if n == 0:
        return 1.0
    r1, r2 = a + b, c + d
    c1, c2 = a + c, b + d

    def p_table(x: int) -> float:
        y, z, w = c1 - x, r1 - x, r2 - c1 + x
        if min(y, z, w) < 0:
            return 0.0
        return math.exp(logf(r1) + logf(r2) + logf(c1) + logf(c2) - logf(n)
                        - logf(x) - logf(z) - logf(y) - logf(w))

    obs = p_table(a)
    total = 0.0
    for x in range(max(0, c1 - r2), min(c1, r1) + 1):
        p = p_table(x)
        if p <= obs * (1 + 1e-9):
            total += p
    return min(1.0, total)


def bh_qvalues(pvals: list[float]) -> list[float]:
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        k = m - rank + 1
        prev = min(prev, pvals[i] * m / k)
        q[i] = prev
    return q


SET_ASIDE_MARKERS = ("-DISCARDED-", "-SUPERSEDED-")
# Conditions that must not have this pack loaded. `skills` and `patch` may.
NO_PACK_CONDITIONS = {"baseline", "scripts-only", "claude-md-only"}


def set_aside(path: Path, root: Path) -> str | None:
    """The discarded/superseded directory `path` sits under, if any."""
    for part in path.relative_to(root).parts[:-1]:
        if any(m in part for m in SET_ASIDE_MARKERS):
            return part
    return None


def cell_workdir(f: Path, stem: str) -> str:
    """Where run_ab.sh copied this cell's files: its own `<stem>_files/` since
    that directory exists, else (older rounds) the transcript's directory."""
    own = f.parent / f"{stem}_files"
    return str(own if own.is_dir() else f.parent)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("round_dir")
    ap.add_argument("--only", help="comma-separated task ids to include")
    ap.add_argument("--include-superseded", action="store_true",
                    help="also grade -DISCARDED-/-SUPERSEDED- directories (audit only)")
    a = ap.parse_args()
    root = Path(a.round_dir)
    only = set(a.only.split(",")) if a.only else None

    # tally[(task, check, cell)] = [passed, gradable]
    tally: dict[tuple[str, str, str], list[int]] = collections.defaultdict(lambda: [0, 0])
    tools: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
    leaks: list[tuple[str, str, int]] = []
    breaches: list[tuple[str, str, int]] = []
    excluded: collections.Counter = collections.Counter()
    ungradable: list[str] = []
    contaminated: list[tuple[str, list[str]]] = []
    models: collections.Counter = collections.Counter()
    tasks_seen: set[str] = set()
    cells = 0

    files = sorted(root.rglob("*_result.jsonl")) + sorted(root.rglob("*_result.jsonl.gz"))
    if not files:
        print(f"no transcripts under {root}", file=sys.stderr)
        return 2
    duplicates = [f for f in files if f.suffix == '.gz' and f.with_suffix('').exists()]
    if duplicates:
        print("both compressed and plain transcripts exist; choose one copy per cell: "
              + ", ".join(str(f) for f in duplicates), file=sys.stderr)
        return 2
    for f in files:
        stem = f.name.split("_result.jsonl")[0]
        task, _, cell = stem.partition("-")
        if task not in COMPARISONS or (only and task not in only):
            continue
        aside = set_aside(f, root)
        if aside and not a.include_superseded:
            excluded[aside] += 1
            continue
        c = grade_v2.Cell(f)
        rel = str(f.relative_to(root))
        cells += 1
        tasks_seen.add(task)
        models[c.model or "(no init event)"] += 1
        # Audit even cells excluded from performance tallies.
        lk = grade_v2.leaked(c)
        if lk:
            leaks.append((f.parent.name, f.name, len(lk)))
        cf = grade_v2.leak_confirmed(c)
        if cf:
            breaches.append((f.parent.name, f.name, len(cf)))
        loaded = c.pack_components_loaded()
        if loaded and cell in NO_PACK_CONDITIONS:
            contaminated.append((rel, loaded))
            continue
        grade = grade_v2.grade_cell(task, f, workdir=cell_workdir(f, stem), cell=c)
        if all(v is None for v in grade.values()):
            ungradable.append(rel)
        for tn in c.tool_names():
            tools[(task, cell)][tn] += 1
        for check, v in grade.items():
            if v is None:
                continue
            t = tally[(task, check, cell)]
            t[1] += 1
            t[0] += 1 if v else 0

    print(f"# v2 round — `{root.name}`\n")
    print(f"{cells} cells read; {len(ungradable)} ungradable, "
          f"{len(contaminated)} contaminated, "
          f"{cells - len(ungradable) - len(contaminated)} graded\n")
    print("Models (from each transcript's init event): " +
          ", ".join(f"`{m}` ×{n}" for m, n in sorted(models.items())) + "\n")
    if excluded:
        print("**Set aside, not pooled** (`-DISCARDED-` / `-SUPERSEDED-`; "
              "`--include-superseded` to audit):\n")
        for d, n in sorted(excluded.items()):
            print(f"- `{d}` — {n} transcript(s)")
        print()
    if ungradable:
        print("**Ungradable** — no result event, a CLI error, or no checker "
              "verdict. Not counted as failures:\n")
        for u in ungradable:
            print(f"- `{u}`")
        print()
    if contaminated:
        print("**CONTAMINATED — excluded.** These sessions started with this "
              "pack loaded in a condition that must not have it:\n")
        for rel, names in contaminated:
            print(f"- `{rel}` — {', '.join(names)}")
        print()

    # --- per-check table ---------------------------------------------------
    print("## Pass rate per check\n")
    order = [x for x in ("t4", "t1", "t2", "t3", "t5", "t6", "t7", "g1", "g2", "g3", "tr1", "tr2", "tr3", "qos1",
                 "ctl1", "ctl2", "tst1", "tst2", "per1", "per2", "per3", "mvt1", "mvt2", "mvt3",
                 "ctl3", "tst3",
                 "cor1", "cor2", "cor3", "dev1", "dev2", "dev3")
                 if not only or x in only]
    cellnames = [c for c in ("baseline", "scripts-only", "claude-md-only",
                             "patch", "skills")
                 if any(cl == c for (_, _, cl) in tally)]
    print("| Task | Check | " + " | ".join(cellnames) + " |")
    print("| :--- | :--- | " + " | ".join("---:" for _ in cellnames) + " |")
    checks_seen = []
    for task in order:
        names = sorted({ch for (t, ch, _) in tally if t == task})
        for ch in names:
            checks_seen.append((task, ch))
            row = []
            for cell in cellnames:
                p, n = tally.get((task, ch, cell), [0, 0])
                row.append(f"{p}/{n}" if n else "—")
            print(f"| `{task}` | {ch} | " + " | ".join(row) + " |")
    print()

    # --- tests -------------------------------------------------------------
    pending = []
    for task, ch in checks_seen:
        for hi, lo in COMPARISONS[task]:
            ph, nh = tally.get((task, ch, hi), [0, 0])
            pl, nl = tally.get((task, ch, lo), [0, 0])
            if not nh or not nl:
                continue
            p = fisher_exact_two_sided(ph, nh - ph, pl, nl - pl)
            delta = (ph / nh) - (pl / nl)
            pending.append({"task": task, "check": ch, "hi": hi, "lo": lo,
                            "ph": ph, "nh": nh, "pl": pl, "nl": nl,
                            "delta": delta, "p": p})
    qs = bh_qvalues([r["p"] for r in pending])
    for r, q in zip(pending, qs):
        r["q"] = q

    print("## Tests\n")
    print("Comparisons and alpha are fixed in `COMPARISONS` / `ALPHA` in "
          "analyze_v2.py. `q` is Benjamini-Hochberg across every test here.\n")
    if not pending:
        print("No comparison in this round has cells on both sides, so there is "
              "nothing to test. Ladder rungs run `baseline` only: the pass rate "
              "per check above is the result.\n")
    else:
        print("| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |")
        print("| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |")
    for r in sorted(pending, key=lambda x: (x["q"], -abs(x["delta"]))):
        if r["q"] < ALPHA:
            v = "**SIGNIFICANT**"
        elif abs(r["delta"]) >= 0.25:
            v = "UNDERPOWERED"
        else:
            v = "null"
        print(f"| `{r['task']}` | {r['check']} | {r['hi']} vs {r['lo']} "
              f"| {r['ph']}/{r['nh']} | {r['pl']}/{r['nl']} "
              f"| {r['delta']:+.2f} | {r['p']:.3f} | {r['q']:.3f} | {v} |")
    print()

    # --- control gate ------------------------------------------------------
    t4sig = [r for r in pending if r["task"] == "t4" and r["q"] < ALPHA]
    t4tests = [r for r in pending if r["task"] == "t4"]
    print("## Control gate\n")
    if "t4" not in tasks_seen or not t4tests:
        # Not a pass. Nothing in this directory can show the harness is untilted,
        # and the round that once cleared the gate is not in the repository.
        print("**NOT EVALUATED.** This round has no t4 null-control comparison, so "
              "nothing here tests whether the harness is tilted toward one "
              "condition. Do not read the absence of a failure as a pass.\n")
    elif t4sig:
        print("**ROUND VOID.** The t4 null control moved:")
        for r in t4sig:
            print(f"- {r['check']}: {r['ph']}/{r['nh']} vs {r['pl']}/{r['nl']}, q={r['q']:.3f}")
        print("\nFind the bias before reading anything above.")
    else:
        print("t4 shows no statistically significant difference. This does not "
              "prove equivalence or the absence of bias; consider the sample size.")
    print()

    print("## Isolation\n")
    if breaches:
        print(f"**REVIEW REQUIRED — {len(breaches)} of {cells} cells returned "
              "known content markers.** Check their provenance before using "
              "the results: a treatment reading its own CLAUDE.md is expected; "
              "reading the answer key is a breach. Marker matching alone does "
              "not distinguish these cases or automatically exclude them:\n")
        for rep, name, n in breaches:
            print(f"- `{rep}/{name}` — {n} result(s)")
        print("\nKeep confirmed breaches out of a reported comparison; preserve "
              "the original transcripts when setting them aside.\n")
    elif leaks:
        print("No known content markers detected; this is a limited audit, "
              "not proof of isolation.\n")
        print(f"{len(leaks)} of {cells} cells *named* the repository path in a "
              f"tool call. That is not a breach on its own — `ps` and "
              f"`/proc/<pid>/cmdline` expose the harness's own invocation, "
              f"which contains the path, and the bind mount leaves the "
              f"directory empty for anything that tries to read it:\n")
        for rep, name, n in leaks:
            print(f"- `{rep}/{name}` — {n} tool call(s)")
        print()
    else:
        print("No known repository-path or content markers detected. This "
              "limited audit does not prove isolation.\n")

    print("## Tool use per cell\n")
    print("| Task | Cell | Tools seen (cells using each) |")
    print("| :--- | :--- | :--- |")
    for (task, cell), cnt in sorted(tools.items()):
        print(f"| `{task}` | {cell} | " +
              ", ".join(f"{k} ({v})" for k, v in sorted(cnt.items())) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
