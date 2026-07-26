#!/usr/bin/env python3
"""Run per-claim probe cells in parallel, resumably, and grade them mechanically.

The question this harness exists to answer is not "are the skills good?" but
"does *this line* change what the agent writes?" — which needs three things the
task-level A/B in run_ab.sh cannot give:

1. **Content isolated from routing.** A skill that does not load has zero effect
   no matter what it says, and 4 of 8 cells in the guardrail run loaded nothing.
   So the content experiment injects the skill body through
   `--append-system-prompt`: guaranteed in context, no router in the loop. What
   routing costs is then measured separately, by comparing against a real
   install, rather than silently mixed into every number.
2. **A true control.** The `ablate` condition is the full body minus exactly one
   claim, reassembled by claims.py so it reads as if authored that way. The
   effect of a line is `full - ablate`, not `full - nothing`.
3. **Repeats.** Every claim in RESULTS.md that later got retracted was n=1.
   Nothing here reports a single cell.

Conditions:
    naked            nothing injected — the model's own prior
    protocol         CLAUDE.md only
    full             the owning skill's whole body
    ablate:<claim>   that body minus one claim  -> effect of the claim in situ
    only:<claim>     that claim's text alone    -> does the line work by itself?
    shipped          CLAUDE.md + the whole body (what a user with 1 skill gets)

Usage:
    python3 runner.py plan  --suite core            # what would run, and cost
    python3 runner.py run   --suite core --repeats 5 --workers 12
    python3 runner.py report --suite core
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claims as claims_mod  # noqa: E402
from probes import PROBES, Probe  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RUNS = REPO / "evals" / "runs"

_write_lock = threading.Lock()
_printed = threading.Lock()


# --- context construction ----------------------------------------------------

def _skill_body(skill: str) -> str:
    """Skill body with its frontmatter stripped.

    The frontmatter is routing metadata; injecting it would put `description:`
    into a system prompt where it means nothing, and inflate the token delta
    that the cost column is supposed to measure.
    """
    text = (REPO / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        _, _, rest = text.partition("---")
        _, _, body = rest.partition("---")
        return body.strip()
    return text.strip()


def _strip_front(text: str) -> str:
    if text.startswith("---"):
        _, _, rest = text.partition("---")
        _, _, body = rest.partition("---")
        return body.strip()
    return text.strip()


def build_context(condition: str, probe: Probe, index: dict[str, claims_mod.Claim]) -> str:
    """Return the text to append to the system prompt for this condition."""
    protocol = (REPO / "CLAUDE.md").read_text(encoding="utf-8").strip()

    if condition == "naked":
        return ""
    if condition == "protocol":
        return protocol
    if condition == "full":
        return _skill_body(probe.skill)
    if condition == "shipped":
        return protocol + "\n\n" + _skill_body(probe.skill)
    if condition.startswith("ablate:"):
        # `ablate:a+b` removes both at once. Single-claim ablation cannot judge
        # redundant lines: if a and b each suffice on their own, dropping either
        # alone measures Δ=0 for both, and cutting both on that evidence breaks
        # the behaviour. Joint ablation is the only way to tell "inert" from
        # "one of a redundant pair".
        cids = condition.split(":", 1)[1].split("+")
        claims = [index[c] for c in cids]
        return _strip_front(
            claims_mod.ablate(claims[0], drop_ids=cids, all_claims=list(index.values()))
        )
    if condition.startswith("only:"):
        cid = condition.split(":", 1)[1]
        return index[cid].text
    raise ValueError(f"unknown condition: {condition}")


# --- one cell ----------------------------------------------------------------

@dataclass
class Cell:
    probe: str
    condition: str
    repeat: int
    model: str

    @property
    def key(self) -> str:
        return f"{self.probe}|{self.condition}|{self.model}|{self.repeat}"

    @property
    def slug(self) -> str:
        h = hashlib.sha256(self.key.encode()).hexdigest()[:8]
        return f"{self.probe}_{self.model}_{h}"


def run_cell(cell: Cell, probe: Probe, context: str, out_dir: Path, budget: float) -> dict:
    cmd = [
        "claude", "-p", probe.prompt,
        "--model", cell.model,
        "--output-format", "json",
        "--no-session-persistence",
        "--max-budget-usd", str(budget),
        "--setting-sources", "",
        "--tools", "",
    ]
    if context:
        cmd += ["--append-system-prompt", context]

    started = time.time()
    workdir = out_dir / "cwd"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        # No CLAUDE_CODE_SIMPLE / --bare here: bare mode reads Anthropic auth only
        # from ANTHROPIC_API_KEY, so it turns every cell into "Not logged in" on an
        # OAuth machine. Isolation comes from `--setting-sources ""` instead.
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, cwd=workdir,
        )
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except subprocess.TimeoutExpired:
        return {**cell.__dict__, "error": "timeout", "elapsed": time.time() - started}
    except json.JSONDecodeError:
        return {**cell.__dict__, "error": "unparseable", "stdout": proc.stdout[:400],
                "stderr": proc.stderr[:400], "elapsed": time.time() - started}

    answer = payload.get("result", "") or ""
    cost = payload.get("total_cost_usd")

    # A cell that never reached the model is not a cell. Usage limits, auth
    # failures and refusals all come back as a normal-looking result whose text
    # happens to be an error message — and a predicate handed that text will
    # score it False, which is indistinguishable from "the model got it wrong".
    # That is how a grader invents effects, so these are recorded as errors and
    # re-run rather than graded.
    if payload.get("is_error") or not cost:
        return {**cell.__dict__, "error": "no-model-response",
                "detail": answer[:200], "elapsed": round(time.time() - started, 2)}

    record = {
        **cell.__dict__,
        "elapsed": round(time.time() - started, 2),
        "cost_usd": cost,
        "turns": payload.get("num_turns"),
        "context_chars": len(context),
        "answer": answer,
    }
    try:
        record["grade"] = probe.predicate(answer)
    except Exception as exc:  # a broken predicate must not look like a failing cell
        record["grade"] = None
        record["predicate_error"] = repr(exc)
    return record


# --- suite orchestration -----------------------------------------------------

def load_index() -> dict[str, claims_mod.Claim]:
    return {c.id: c for c in claims_mod.inventory()}


def plan_cells(probes: list[Probe], repeats: int, models: list[str],
               conditions: list[str] | None) -> list[Cell]:
    cells = []
    for p in probes:
        conds = conditions if conditions else p.conditions()
        for cond in conds:
            for model in models:
                for r in range(1, repeats + 1):
                    cells.append(Cell(p.id, cond, r, model))
    return cells


def load_done(results_path: Path) -> set[str]:
    done = set()
    if results_path.exists():
        with results_path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("error"):
                    continue  # a failed cell is worth retrying
                done.add(f"{rec['probe']}|{rec['condition']}|{rec['model']}|{rec['repeat']}")
    return done


def cmd_run(args) -> int:
    index = load_index()
    probes = select_probes(args.suite, args.probe)
    out_dir = RUNS / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "cells.jsonl"

    cells = plan_cells(probes, args.repeats, args.models.split(","),
                       args.conditions.split(",") if args.conditions else None)
    done = load_done(results_path)
    todo = [c for c in cells if c.key not in done]

    print(f"{len(probes)} probes, {len(cells)} cells planned, {len(done)} already done, "
          f"{len(todo)} to run -> {results_path.relative_to(REPO)}")
    if args.dry_run:
        return 0

    by_id = {p.id: p for p in probes}
    fh = results_path.open("a", encoding="utf-8")
    completed = [0]
    total = len(todo)
    t0 = time.time()
    # A per-cell budget cannot stop a sweep from overrunning the account it is
    # billed to; only a running total can. Cells already in flight are allowed to
    # finish, so the cap is approached from below rather than enforced exactly.
    spent = [0.0]
    stopped = [False]

    def work(cell: Cell) -> None:
        if stopped[0]:
            return
        probe = by_id[cell.probe]
        context = build_context(cell.condition, probe, index)
        rec = run_cell(cell, probe, context, out_dir, args.budget)
        with _write_lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            spent[0] += rec.get("cost_usd") or 0
            if args.max_total_usd and spent[0] >= args.max_total_usd and not stopped[0]:
                stopped[0] = True
                print(f"\n!! budget cap ${args.max_total_usd:.2f} reached after "
                      f"${spent[0]:.2f} — stopping. Re-run to resume.", flush=True)
        with _printed:
            completed[0] += 1
            n = completed[0]
            rate = n / max(time.time() - t0, 1e-6)
            eta = (total - n) / rate if rate else 0
            g = rec.get("grade") or {}
            mark = "".join({True: "+", False: ".", None: "?"}[v] for v in g.values()) or "ERR"
            print(f"[{n:4}/{total}] {mark:8} {cell.probe:22} {cell.condition:34} "
                  f"r{cell.repeat} ${rec.get('cost_usd') or 0:.4f} eta {eta/60:.1f}m", flush=True)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))
    fh.close()

    spent = sum(json.loads(l).get("cost_usd") or 0 for l in results_path.open(encoding="utf-8"))
    print(f"\ndone in {(time.time()-t0)/60:.1f} min — suite total spend ${spent:.2f}")
    return 0


def select_probes(suite: str | None, probe_id: str | None) -> list[Probe]:
    if probe_id:
        return [p for p in PROBES if p.id in probe_id.split(",")]
    if suite and suite != "all":
        return [p for p in PROBES if p.suite == suite]
    return list(PROBES)


def cmd_plan(args) -> int:
    probes = select_probes(args.suite, args.probe)
    cells = plan_cells(probes, args.repeats, args.models.split(","),
                       args.conditions.split(",") if args.conditions else None)
    print(f"{len(probes)} probes -> {len(cells)} cells")
    print(f"estimated spend at $0.02/cell: ${len(cells)*0.02:.2f}")
    for p in probes:
        print(f"  {p.id:30} {len(p.conditions()):2} conditions  claims={','.join(p.claim_ids)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("--suite", default="all")
        sp.add_argument("--probe", default=None)
        sp.add_argument("--repeats", type=int, default=5)
        sp.add_argument("--models", default="haiku")
        sp.add_argument("--conditions", default=None)
        sp.add_argument("--workers", type=int, default=10)
        sp.add_argument("--budget", type=float, default=0.10)
        sp.add_argument("--max-total-usd", type=float, default=None,
                        help="stop the sweep once this much has been spent in this invocation")
        sp.add_argument("--out", default=f"{time.strftime('%Y-%m-%d')}-claims")
        sp.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return {"plan": cmd_plan, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
