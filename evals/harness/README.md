# Harness

The tool reference: what is in this directory and why each piece works the way
it does. The *method* — how a ladder is designed so it cannot be tuned into
agreeing with you — is [`../LADDER.md`](../LADDER.md). The *result* is
[`../CAPABILITIES.md`](../CAPABILITIES.md).

## What runs a round

| File | What it does |
| :--- | :--- |
| [`run_ab.sh`](./run_ab.sh) | The whole round. Holds every task's **frozen prompt**, brings up the live scenario the task needs, runs each cell in a fresh directory under `isolate_cell.sh`, and dispatches the task's `*_check.sh` when the cell finishes. |
| [`isolate_cell.sh`](./isolate_cell.sh) | Unprivileged mount namespace with an empty directory bind-mounted over the repository, so a cell cannot read the eval design or a scenario source that names the answer. |
| [`grade_v2.py`](./grade_v2.py) | Turns each cell into a dict of check → pass/fail/ungradable. Real-outcome tasks read the JSON verdict the shell checker wrote at cell time, while the cell's workspace still existed. |
| [`analyze_v2.py`](./analyze_v2.py) | Grades every cell in a round directory, tallies per check per cell type, runs the fixed comparisons, corrects across the round, and reports isolation. |
| [`summarize_run.py`](./summarize_run.py) | Reduces a `stream-json` log to the final message plus the tool calls actually invoked. Diagnosis only — never a grading input. |

```bash
# needs a sourced ROS 2 Jazzy install
MODEL=sonnet ./run_ab.sh dev3 ../runs/$(date +%F)-sweep
python3 analyze_v2.py ../runs/$(date +%F)-sweep
```

## The checkers

One `<task>_check.sh` per rung, plus the scenario publishers they need
(`dev3_scenario.sh`, `camera_publisher.py`, `qos_publishers.py`,
`fake_*_pub.py`, `tick_publisher.py`, `slow_trigger_server.py`,
`t1_diffdrive_scenario.sh`, `task3_scenario.sh`).

Every checker runs the artifact and reads its behaviour. None reads source code
and none reads transcript phrasing. Each writes a JSON verdict file next to the
transcript, because a workspace is gone by the time a round is analysed.

**Each checker's header lists the traps it is written downstream of.** Read one
before writing a new checker — they were each paid for by a wrong number:

- `cmd | grep -q X` under `set -o pipefail` turns a match into a failure.
- `grep -c` for counting prints `0` **and** exits 1. Use `awk`.
- `/active/` also matches `inactive`. Compare the first field exactly.
- A cell may set its own `ROS_DOMAIN_ID` — which is correct practice — and be
  invisible to a checker on a different domain. `adopt_domain_from()` reads the
  domain out of `/proc/<pid>/environ` of a process the cell's own bringup
  started.
- `pkill -f "$BDIR"` matches the checker's own command line. Walk `$$`/`$PPID`
  to build an exclusion set first.
- Killing node processes but leaving the `ros2 launch` wrapper alive makes a
  cell's re-entrancy guard skip its relaunch, scoring defensive code as failure.
- Every wait loop must be bounded, or the checker is killed before it writes any
  verdict at all — which reads as "no result", not as a failure.
- Sampling a controller once immediately after bringup returns catches it
  mid-spawn. Poll until settled.

## Rules that cost something to learn

**Never edit the harness while a round is running.** Registering new tasks in
`run_ab.sh` while `mvt1` cells were executing moved bash's incremental read to a
wrong byte offset and killed 8 of 10 cells mid-tool-call. The round was
discarded and re-run.

**Never hand-roll a substitute for `analyze_v2.py`.** A throwaway tally written
to avoid re-running the pipeline once keyed per-check pass rates on
`(task, check)` instead of `(task, check, cell)`, pooling one condition's
failures into another's. It reported two regressions that did not exist, and two
lines were restored on that evidence before the bug was found. The point of one
tool doing the tallying is that it only has to be right once.

**Assert nothing the frozen prompt does not require.** `dev3` scored
`controller_active`, which its prompt never asks for; two cells reached the
costmap through a standalone `nav2_costmap_2d` node — satisfying everything the
task actually asked, marking 12 and 325 lethal cells — and were failed for it.
Removing that check took the rung from a partial score to 20/20.

**Open every failing cell before counting it.** Ten grader defects surfaced
across these rounds and **every one was mine**. Four of them punished *good*
engineering: isolating a DDS domain, guarding a bringup against double-launch,
cleaning up a temp directory, parameterising a value. Counted rather than
opened, they would have produced skill content for gaps the model does not have.

**A cell that never reached the model is not a cell.** Usage limits, auth
failures and refusals come back as a normal-looking result whose text happens to
be an error message; a predicate handed `"You've hit your session limit"` scores
it `False`, indistinguishable from the model being wrong. Cells with `is_error`
or no cost are recorded as errors, never graded, and retried.

**`--bare` / `CLAUDE_CODE_SIMPLE=1` must not be used.** Bare mode reads
Anthropic auth only from `ANTHROPIC_API_KEY`, so on an OAuth machine every cell
returns "Not logged in" and records as a silent failure. Isolation comes from
`--setting-sources ""` instead.

**Validate a grader against a deliberately broken reference before its round
runs.** A grader that has only seen good answers is not validated. This caught
one design that would have passed three broken packages, because all three exit
`colcon build` with code 0. It also caught a rung that was unachievable as
written — Nav2 costmaps refuse to activate with no TF chain — while building the
reference, before any real cell had run.

## Grading

Mechanical always: does the build succeed, does the node publish, does the
lifecycle server reach `active`, does the generated cloud carry the right number
of points in the right units. A check returns pass, fail, or **ungradable**, and
ungradable is never counted as a failure. A grader that scores unparseable
output as "fail" invents effects.

## Statistics

`analyze_v2.py` runs Fisher exact two-sided and corrects with
Benjamini-Hochberg across every test in the round as one family. Two rules the
project had to learn:

- **Uncorrected p-values across one sweep overstate significance.** A sweep
  running 166 tests expects ~8 "significant" results from noise alone at
  `alpha=0.05` before a single real effect exists. Verdicts are gated on the
  corrected `q` column, not the `p` column the table still prints.
- **A large Δ that misses significance is a power problem, not a verdict.**
  Folding it in with a genuinely flat Δ≈0 is how a real effect hides.
  `UNDERPOWERED` (|Δ| ≥ 0.25, not significant) is its own bucket — top it up
  before treating it as settled. The QoS result (5/10 → 9/10, q=0.141) sits
  here and is reported that way rather than as a win.

Ladder rungs run `baseline` only, so most rounds have no within-round comparison
to correct: the pass rate per real-outcome check **is** the result, and
LADDER.md's ≤7/10 threshold is the verdict.

## Isolation

`analyze_v2.py` separates an **attempt** from a **breach**. Naming the
repository path in a tool call is not a breach on its own — `ps` and
`/proc/<pid>/cmdline` expose the harness's own invocation, which contains the
path, and the bind mount leaves the directory empty for anything that reads it.
A breach requires repository *content* to come back, matched against exact
strings that appear only in real repo files.

## Archived

The first-generation per-line ablation tooling (`claims.py`, `probes.py`,
`runner.py`, `analyze.py`, `evals/variants/`) was deleted along with the rounds
it produced. It answered "does this shipped line earn its place?", which can
only ever delete, and its findings are folded into `../LADDER.md`. Two of its
lessons still bind anything that edits a body programmatically, and are recorded
here so they are not rediscovered:

- **A single ablation reads a state that never ships.** Whenever more than one
  cut is on the table, measure the actual combined body — single-ablation of
  each candidate describes something nothing will ship.
- **Ablation must not leave a seam.** Removing the only claim under a subheading
  left the heading standing over nothing, which still names the topic, so the
  ablated body scored *higher* than one that never mentioned it — biasing toward
  cutting.
