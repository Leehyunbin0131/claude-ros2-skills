#!/usr/bin/env python3
"""Aggregate a v2 round: grade every cell, tally per check, test per TASKS.md.

Usage:
    python3 analyze_v2.py evals/runs/<round-dir>

Comparisons and the significance handling are fixed in TASKS.md and are not
chosen here after seeing the numbers:
  * t1, t3, t4  -> skills vs baseline
  * t2          -> skills vs scripts-only (what the TEXT buys)
                   and scripts-only vs baseline (what the FILES buy)
  * Fisher exact, two-sided; Benjamini-Hochberg across every test in the round.
  * t4 must be null. If any t4 check is significant, the round is void.
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("round_dir")
    ap.add_argument("--only", help="comma-separated task ids to include")
    a = ap.parse_args()
    root = Path(a.round_dir)
    only = set(a.only.split(",")) if a.only else None

    # tally[(task, check, cell)] = [passed, gradable]
    tally: dict[tuple[str, str, str], list[int]] = collections.defaultdict(lambda: [0, 0])
    tools: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
    leaks: list[tuple[str, str, int]] = []
    cells = 0

    files = sorted(root.rglob("*_result.jsonl")) + sorted(root.rglob("*_result.jsonl.gz"))
    if not files:
        print(f"no transcripts under {root}", file=sys.stderr)
        return 2
    for f in files:
        stem = f.name.split("_result.jsonl")[0]
        task, _, cell = stem.partition("-")
        if task not in COMPARISONS or (only and task not in only):
            continue
        c = grade_v2.Cell(f)
        fn = getattr(grade_v2, task)
        if task == "t1":
            grade = fn(c, live=False)
        elif task == "t4":
            grade = fn(c, workdir=str(f.parent))
        elif task in ("t5", "t6", "t7", "g1", "g2", "g3"):
            # Real-outcome verdicts were written next to the transcript by
            # t5_check.sh at cell time, while the workspace still existed.
            grade = fn(c, check=f.parent / f"{stem}_check.json")
        else:
            grade = fn(c)
        cells += 1
        lk = grade_v2.leaked(c)
        if lk:
            leaks.append((f.parent.name, f.name, len(lk)))
        for tn in c.tool_names():
            tools[(task, cell)][tn] += 1
        for check, v in grade.items():
            if v is None:
                continue
            t = tally[(task, check, cell)]
            t[1] += 1
            t[0] += 1 if v else 0

    print(f"# v2 round — `{root.name}`\n")
    print(f"{cells} cells graded\n")

    # --- per-check table ---------------------------------------------------
    print("## Pass rate per check\n")
    order = [x for x in ("t4", "t1", "t2", "t3", "t5", "t6", "t7", "g1", "g2", "g3") if not only or x in only]
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
    print("Comparisons and alpha fixed in TASKS.md before the round. "
          "`q` is Benjamini-Hochberg across every test here.\n")
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
    print("## Control gate\n")
    if only and "t4" not in only:
        print("t4 was not run in this round. The gate was cleared in the round "
              "that established the harness; a narrow follow-up inherits that "
              "rather than re-paying for it.\n")
    elif t4sig:
        print("**ROUND VOID.** The t4 null control moved:")
        for r in t4sig:
            print(f"- {r['check']}: {r['ph']}/{r['nh']} vs {r['pl']}/{r['nl']}, q={r['q']:.3f}")
        print("\nFind the bias before reading anything above.")
    else:
        print("t4 shows no significant difference between cells — the harness is "
              "not tilted toward the skills condition, so the other tasks can be read.")
    print()

    print("## Isolation\n")
    if leaks:
        print(f"**{len(leaks)} of {cells} cells reached the repository** — these "
              f"have seen the eval design and/or a scenario source, which names "
              f"the planted answer. Reported, not averaged away:\n")
        for rep, name, n in leaks:
            print(f"- `{rep}/{name}` — {n} tool call(s)")
        print("\nRun through `isolate_cell.sh` to close this.\n")
    else:
        print("No cell reached the repository. Isolation held.\n")

    print("## Tool use per cell\n")
    print("| Task | Cell | Tools seen (cells using each) |")
    print("| :--- | :--- | :--- |")
    for (task, cell), cnt in sorted(tools.items()):
        print(f"| `{task}` | {cell} | " +
              ", ".join(f"{k} ({v})" for k, v in sorted(cnt.items())) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
