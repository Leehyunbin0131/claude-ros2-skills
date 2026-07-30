# v1 harness — superseded, kept for the record

**Do not run these to verify a skill.** The current method is
[`../../LADDER.md`](../../LADDER.md); the current tools are `run_ab.sh`,
`grade_v2.py`, `analyze_v2.py`, `isolate_cell.sh` and the `t*_check.sh` scripts
one directory up.

These four files implement **per-claim ablation**: take one line out of a
`SKILL.md`, re-run, see whether the outcome moves.

| File | What it did |
| :--- | :--- |
| `claims.py` | split each `SKILL.md` into individually addressable claims |
| `probes.py` | one prompt, several mechanical checks, each tied to the claims it tests |
| `runner.py` | ran per-claim cells in parallel, resumably |
| `analyze.py` | turned `cells.jsonl` into per-claim KEEP/CUT verdicts |

## Why they are here and not in use

Per-claim ablation only works with **tools disabled**. An agent that can read
files opens the real `SKILL.md`, so removing a line from its context proves
nothing. That constraint is legitimate for the technique — and letting it define
the project was the error that cost 5,156 cells and $122 of measurement.

Nobody ships an agent that cannot look anything up. "The model does not know this
unaided" is not the same claim as "this line earns its place", and the v1
verdicts systematically overstated what the files were buying. Two lines v1
*added* after finding the model wrong 4/4 were later measured **10/10 correct**
by an agent with a shell and a web search.

The v1 data was deleted. These files were not, for two reasons: the statistics
(`analyze.py`'s Fisher/BH implementation is what `analyze_v2.py` uses) and the
lesson. They are moved out of `harness/` so that following a stale document
cannot quietly restart v1.

`../../FINDINGS.md` and `../../PROCEDURE.md` describe this method. Both carry a
banner saying so.
