#!/usr/bin/env python3
"""Turn cells.jsonl into per-claim verdicts.

For every (claim, check) pair the runner produced, three numbers decide the
claim's fate:

    P(naked)   how often the model satisfies the check with no skill at all
    P(full)    how often it does with the whole body in context
    P(ablate)  how often it does with the body minus exactly that claim

    Δ = P(full) − P(ablate)      the claim's own contribution

The verdict grid, and the reason for each:

    P(naked) high, Δ≈0   CUT        true but free; the model already does it
    P(naked) low,  Δ>0   KEEP       the payload
    P(naked) low,  Δ≈0   INERT      in context and doing nothing — reword or move
    P(full) < P(naked)   HARMFUL    the body makes the model worse than silence

Significance is Fisher's exact test, computed exactly — at n=8 a 6/8 vs 4/8
difference is noise, and calling it an effect is how the retraction in this
repo's history happened.

    python3 analyze.py <run-dir> [--alpha 0.05]
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probes import PROBES  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """p-value for the 2x2 table [[a,b],[c,d]]; no scipy on the eval machine."""
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1, row2, col1 = a + b, c + d, a + c

    def prob(x: int) -> float:
        return (math.comb(row1, x) * math.comb(row2, col1 - x)) / math.comb(n, col1)

    observed = prob(a)
    lo = max(0, col1 - row2)
    hi = min(col1, row1)
    # sum every table at least as extreme as the observed one
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= observed * (1 + 1e-9)))


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


class Tally:
    __slots__ = ("passed", "graded", "ungraded")

    def __init__(self) -> None:
        self.passed = self.graded = self.ungraded = 0

    def add(self, value) -> None:
        if value is None:
            self.ungraded += 1
        else:
            self.graded += 1
            self.passed += bool(value)

    @property
    def rate(self) -> float | None:
        return self.passed / self.graded if self.graded else None


def load(run_dir: Path):
    """-> {(probe, condition, check): Tally}, plus cost and error counts."""
    tallies: dict[tuple[str, str, str], Tally] = defaultdict(Tally)
    cost = 0.0
    errors = 0
    cells = 0
    # Committed runs keep the cell log gzipped — it is ~10x smaller and nothing
    # else reads it — so a re-grade should not need a manual gunzip first.
    plain, packed = run_dir / "cells.jsonl", run_dir / "cells.jsonl.gz"
    if plain.exists():
        fh = plain.open(encoding="utf-8")
    elif packed.exists():
        fh = gzip.open(packed, "rt", encoding="utf-8")
    else:
        raise SystemExit(f"no cells.jsonl or cells.jsonl.gz in {run_dir}")
    for line in fh:
        rec = json.loads(line)
        # `error` is ours; `is_error` / missing cost mean the CLI answered with
        # an error message (usage limit, auth) that older runs recorded as data.
        if rec.get("error") or rec.get("is_error") or not rec.get("cost_usd"):
            errors += 1
            continue
        cells += 1
        cost += rec.get("cost_usd") or 0
        for check, value in (rec.get("grade") or {}).items():
            tallies[(rec["probe"], rec["condition"], check)].add(value)
    return tallies, cost, errors, cells


def verdict(p_naked, p_full, p_abl, sig_effect: bool, sig_harm: bool) -> str:
    if p_full is None or p_abl is None:
        return "no-data"
    if sig_harm:
        return "HARMFUL"
    if sig_effect and p_full > p_abl:
        return "KEEP"
    if p_naked is not None and p_naked >= 0.8:
        return "CUT"
    if p_naked is not None and p_naked <= 0.5:
        return "INERT"
    return "unclear"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = REPO / "evals" / "runs" / args.run_dir
    tallies, cost, errors, cells = load(run_dir)
    probes = {p.id: p for p in PROBES}

    print(f"# Per-claim analysis — `{run_dir.name}`\n")
    print(f"{cells} cells, {errors} errored, ${cost:.2f} spent\n")

    # --- baseline table ------------------------------------------------------
    print("## Baselines per check\n")
    print("| Probe | Check | P(naked) | P(protocol) | P(full) | P(shipped) |")
    print("| :--- | :--- | ---: | ---: | ---: | ---: |")
    for pid, probe in probes.items():
        for check in probe.checks:
            def r(cond: str) -> str:
                t = tallies.get((pid, cond, check))
                if not t or not t.graded:
                    return "—"
                return f"{t.passed}/{t.graded}"
            row = [r("naked"), r("protocol"), r("full"), r("shipped")]
            if all(v == "—" for v in row):
                continue
            print(f"| `{pid}` | {check} | {row[0]} | {row[1]} | {row[2]} | {row[3]} |")

    # --- per-claim verdicts --------------------------------------------------
    print("\n## Claim verdicts\n")
    print("Δ is P(full) − P(ablate) on the check the claim is supposed to drive. "
          "`p` is Fisher exact, two-sided, full vs ablate.\n")
    print("| Claim | Check | P(naked) | P(full) | P(ablate) | Δ | p | Verdict |")
    print("| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |")

    rows = []
    for pid, probe in probes.items():
        for check_name, check in probe.checks.items():
            for cid in check.claims:
                t_naked = tallies.get((pid, "naked", check_name))
                t_full = tallies.get((pid, "full", check_name))
                t_abl = tallies.get((pid, f"ablate:{cid}", check_name))
                if not t_full or not t_abl or not t_full.graded or not t_abl.graded:
                    continue
                p_naked = t_naked.rate if t_naked else None
                p_full, p_abl = t_full.rate, t_abl.rate

                p_val = fisher_exact_two_sided(
                    t_full.passed, t_full.graded - t_full.passed,
                    t_abl.passed, t_abl.graded - t_abl.passed)
                sig_effect = p_val < args.alpha

                sig_harm = False
                if t_naked and t_naked.graded and p_naked is not None and p_full < p_naked:
                    p_harm = fisher_exact_two_sided(
                        t_full.passed, t_full.graded - t_full.passed,
                        t_naked.passed, t_naked.graded - t_naked.passed)
                    sig_harm = p_harm < args.alpha

                v = verdict(p_naked, p_full, p_abl, sig_effect, sig_harm)
                rows.append((v, cid, check_name, p_naked, p_full, p_abl, p_val))

    order = {"HARMFUL": 0, "KEEP": 1, "INERT": 2, "CUT": 3, "unclear": 4, "no-data": 5}
    for v, cid, check_name, p_naked, p_full, p_abl, p_val in sorted(
            rows, key=lambda r: (order.get(r[0], 9), r[1])):
        n = "—" if p_naked is None else f"{p_naked:.2f}"
        print(f"| `{cid.split(':',1)[1]}` | {check_name} | {n} | {p_full:.2f} | "
              f"{p_abl:.2f} | {p_full - p_abl:+.2f} | {p_val:.3f} | **{v}** |")

    # --- redundancy groups ---------------------------------------------------
    # The single-ablation table cannot tell "this line does nothing" from "this
    # line is one of two that each suffice". Only removing the whole group can.
    groups = [(p, g) for p in probes.values() for g in p.joint]
    if groups:
        print("\n## Redundancy groups — removing the whole group\n")
        print("Every member of these groups measured Δ≈0 alone. That is the signature of "
              "redundancy, not of uselessness: cutting them all is only safe if the joint "
              "ablation also shows no effect.\n")
        print("| Group | Check | P(full) | P(drop all) | Δ | p | Reading |")
        print("| :--- | :--- | ---: | ---: | ---: | ---: | :--- |")
        for probe, g in groups:
            cond = f"ablate:{'+'.join(g)}"
            for check_name, check in probe.checks.items():
                if not any(cid in check.claims for cid in g):
                    continue
                t_full = tallies.get((probe.id, "full", check_name))
                t_j = tallies.get((probe.id, cond, check_name))
                if not t_full or not t_j or not t_full.graded or not t_j.graded:
                    continue
                p_val = fisher_exact_two_sided(
                    t_full.passed, t_full.graded - t_full.passed,
                    t_j.passed, t_j.graded - t_j.passed)
                delta = t_full.rate - t_j.rate
                if p_val < args.alpha and delta > 0:
                    reading = "**the group is load-bearing** — keep at least one member"
                else:
                    reading = "no joint effect — the whole group is a cut candidate"
                short = ", ".join(c.split(":")[-2][:22] + ":" + c.split(":")[-1] for c in g)
                print(f"| {short} | {check_name} | {t_full.passed}/{t_full.graded} | "
                      f"{t_j.passed}/{t_j.graded} | {delta:+.2f} | {p_val:.3f} | {reading} |")

    # --- rewrite variants ----------------------------------------------------
    # Deletion can only find lines that do nothing. It cannot ask whether three
    # lines would work better as one, whether a table beats prose, or whether
    # the sections are split in the right places -- those need an authored
    # alternative measured against the current body on the same checks.
    variants = sorted({cond for (_pid, cond, _c) in tallies if cond.startswith("variant:")})
    if variants:
        print("\n## Rewrite variants — an authored alternative vs the current body\n")
        print("`full` is the body as it stands; each variant is a rewrite of it. A variant "
              "that ties on every check and costs fewer tokens is an improvement — on a tie "
              "the smaller body wins, which is the efficiency axis applied to wording rather "
              "than to deletion.\n")
        print("| Variant | Probe | Check | P(full) | P(variant) | Δ | p | Reading |")
        print("| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |")
        for cond in variants:
            for pid, probe in probes.items():
                for check_name in probe.checks:
                    t_full = tallies.get((pid, "full", check_name))
                    t_var = tallies.get((pid, cond, check_name))
                    if not t_full or not t_var or not t_full.graded or not t_var.graded:
                        continue
                    p_val = fisher_exact_two_sided(
                        t_full.passed, t_full.graded - t_full.passed,
                        t_var.passed, t_var.graded - t_var.passed)
                    delta = t_var.rate - t_full.rate
                    if p_val < args.alpha and delta < 0:
                        reading = "**variant is worse** — reject the rewrite"
                    elif p_val < args.alpha and delta > 0:
                        reading = "**variant is better** — adopt it"
                    else:
                        reading = "indistinguishable — adopt only if it is smaller"
                    print(f"| `{cond.split(':',1)[1]}` | `{pid}` | {check_name} | "
                          f"{t_full.passed}/{t_full.graded} | {t_var.passed}/{t_var.graded} | "
                          f"{delta:+.2f} | {p_val:.3f} | {reading} |")

    # --- interference --------------------------------------------------------
    print("\n## Interference — ablations that moved a check they do not own\n")
    print("A claim's removal should not disturb an unrelated check. Where it does, "
          "'the effect of line X' is not well defined.\n")
    hits = 0
    for pid, probe in probes.items():
        for check_name, check in probe.checks.items():
            t_full = tallies.get((pid, "full", check_name))
            if not t_full or not t_full.graded:
                continue
            for cid in probe.claim_ids:
                if cid in check.claims:
                    continue
                t_abl = tallies.get((pid, f"ablate:{cid}", check_name))
                if not t_abl or not t_abl.graded:
                    continue
                p_val = fisher_exact_two_sided(
                    t_full.passed, t_full.graded - t_full.passed,
                    t_abl.passed, t_abl.graded - t_abl.passed)
                if p_val < args.alpha:
                    hits += 1
                    print(f"- removing `{cid.split(':',1)[1]}` moved **{check_name}** "
                          f"({t_full.passed}/{t_full.graded} → {t_abl.passed}/{t_abl.graded}, "
                          f"p={p_val:.3f}) — that check does not depend on it")
    if not hits:
        print("_none — every ablation left the checks it does not own alone._")

    # --- ungradable ----------------------------------------------------------
    ung = sum(t.ungraded for t in tallies.values())
    tot = sum(t.ungraded + t.graded for t in tallies.values())
    print(f"\n## Grading coverage\n\n{tot - ung}/{tot} check results were gradable "
          f"({ung} ungradable, never counted as failures).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
