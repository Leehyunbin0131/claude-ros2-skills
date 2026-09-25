# Harness

The tool reference: what is in this directory and why each piece works the way
it does. The *method* — how a ladder is designed so it cannot be tuned into
agreeing with you — is [`../LADDER.md`](../LADDER.md). The *result* is
[`../CAPABILITIES.md`](../CAPABILITIES.md).

## What runs a round

| File | What it does |
| :--- | :--- |
| [`run_ab.sh`](./run_ab.sh) | One task: holds every task's **frozen prompt**, refuses to start unless preflight passes, and for each condition brings up the task's live scenario, runs the cell in a fresh directory under `isolate_cell.sh`, runs the task's `*_check.sh`, and tears the scenario down. |
| [`isolate_cell.sh`](./isolate_cell.sh) + [`isolation.py`](./isolation.py) | Unprivileged mount namespace in which every copy of this repository and the host's own Claude instructions are masked with empty bind mounts, then a nested user namespace so the agent runs as your uid and cannot unmount them. `--check` verifies all of that without running anything. |
| [`scenario_ready.py`](./scenario_ready.py) | Bounded, read-only probes require the promised topics, service and TF before a model call; missing readiness aborts and preserves the scenario log. |
| [`procscope.py`](./procscope.py) + [`procscope.sh`](./procscope.sh) | Which processes belong to this run: everything it starts carries `EVAL_RUN_TAG`, and only tagged processes are ever killed. Sets localhost ROS discovery and rejects vendor overrides; not a network sandbox. |
| [`grade_v2.py`](./grade_v2.py) | Turns each cell into a dict of check → pass/fail/ungradable. Real-outcome tasks read the JSON verdict the shell checker wrote at cell time, while the cell's workspace still existed. |
| [`analyze_v2.py`](./analyze_v2.py) | Grades every cell in a round directory, tallies per check per cell type, runs the fixed comparisons, corrects across the round, and reports isolation, set-aside, ungradable and contaminated cells. |
| [`summarize_run.py`](./summarize_run.py) | Reduces a `stream-json` log to the final message plus the tool calls actually invoked. Diagnosis only — never a grading input. |
| [`test_harness.py`](./test_harness.py) | Regression tests for all of the above. No model call, no ROS. Run it before trusting a change here. |

```bash
python3 test_harness.py                       # the harness itself
MODEL=sonnet ./run_ab.sh --preflight          # every refusal check; no scenario, no model call
# A ladder rung is ten reps, one directory each (the layout of ../runs/):
for i in $(seq 1 10); do
  MODEL=sonnet CELLS=baseline ./run_ab.sh dev3 ../runs/$(date +%F)-sweep/dev3/r$i
done
python3 analyze_v2.py ../runs/$(date +%F)-sweep
```

Existing task/cell artifacts are never overwritten. Duplicate or unsupported
conditions are refused, as are `qos2`/`qos3`, whose prompts are frozen but have no
grader. A readiness failure starts no paid model call. `t2` now publishes the
identity `base_link -> imu_link` transform as well as the deliberately incorrect
gravity vector; this fixture correction applies to future runs only.

`MODEL` has no default and must be named; every committed sweep ran `sonnet`
(each transcript's init event records the model id, and `analyze_v2.py` prints
it). Needs Ubuntu 24.04 (util-linux ≥ 2.38 for `unshare --map-user`),
unprivileged user namespaces, and `/opt/ros/jazzy`.

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
  invisible to a checker on a different domain. `adopt_domain_from()`
  (`procscope.sh`) reads the domain out of `/proc/<pid>/environ` of a process
  the cell's own bringup started — **only this run's processes**. The unscoped
  `pgrep -f ros2_control_node | head -1` it replaced could adopt the domain of
  someone else's live controller, and `ctl2`'s probe then publishes position
  commands there.
- Never `pkill -f <name>`: it kills every matching process on the host, a live
  robot's `controller_server` or `robot_state_publisher` included. Every
  checker used to. Use `kill_owned <pattern>` (`procscope.sh`), which only
  touches processes carrying this run's `EVAL_RUN_TAG`.
- `pkill -f "$BDIR"` matches the checker's own command line. Walk `$$`/`$PPID`
  to build an exclusion set first (`procscope.py` always excludes the caller
  and its ancestors).
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
it `False`, indistinguishable from the model being wrong. `grade_v2.py` treats
as ungradable — never graded, listed by `analyze_v2.py`, to be retried — a
transcript with no closing `result` event (cut off mid-cell), one whose result
says `is_error` or a non-`success` subtype, a short answer that is only a
harness error, and a real-outcome task whose checker left no parseable verdict.
The same goes for an install fact this host lacks: without Nav2, "is this a
registered Nav2 plugin?" is ungradable, not False.

**`--bare` / `CLAUDE_CODE_SIMPLE=1` must not be used.** Bare mode reads
Anthropic auth only from `ANTHROPIC_API_KEY`, so on an OAuth machine every cell
returns "Not logged in" and records as a silent failure. `run_ab.sh` passes
`--setting-sources project,local --strict-mcp-config` instead: the host's user
settings, enabled plugins, hooks and MCP servers stay out of every condition,
while the project scope — where a treatment's `CLAUDE.md` and `.claude/skills`
live — still loads. `--settings '{"autoMemoryEnabled":false}'` disables auto
memory explicitly; `--no-session-persistence` alone does not do that. (`--safe-mode` is not usable: it would also disable the
treatment.) The committed 2026-07/08 rounds ran without these flags; their init
events show no plugin and no pack skill loaded, which `analyze_v2.py` checks on
every cell. That these flags leave OAuth login working was **not** re-verified
when they were added (no model call was made); a cell that cannot log in is
recorded ungradable, not scored.

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

What a cell must not see, and what hides it (`isolation.py` has the full list):

| Threat | Handled by |
| :--- | :--- |
| This checkout, and every other git worktree of it | masked (`git worktree list`) |
| Another clone, a plugin cache, an earlier `skills` cell's `CLAUDE.md` / skills / scripts under `/tmp` | masked, if a bounded scan of `$HOME` (depth 6) and `/tmp` (depth 5) recognises it |
| Anything the scan cannot recognise — e.g. a directory of transcripts that quote this repository | **you** list it in `EVAL_MASK_PATHS` (colon-separated); a listed path that does not exist is refused |
| The host's `~/.claude/CLAUDE.md`, `rules/`, `skills/`, `agents/`, `commands/`, `output-styles/`, `plugins/` | masked; user settings, enabled plugins, hooks and MCP also excluded by `run_ab.sh`'s flags |
| `CLAUDE.md` / `CLAUDE.local.md` / `AGENTS.md` / `.claude/` in an ancestor of the cell directory (Claude Code loads those) | masked |
| Managed policy (`/etc/claude-code`), which cannot be excluded | **refused** unless `EVAL_ALLOW_MANAGED_POLICY=1` |
| The agent unmounting a mask | agent runs as your uid in a nested user namespace; `--check` tries the unmount and fails if it works |
| Accidental discovery of a robot on the LAN | Force `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, clear static peers, reject vendor discovery/profile overrides, use a dedicated `ROS_DOMAIN_ID` per run |
| A robot stack on the same host | `run_ab.sh` **refuses** while ROS processes it did not start are running (`EVAL_ALLOW_FOREIGN_ROS=1` overrides) |
| Two rounds for the same OS user sharing a DDS domain | user lock; the second run is refused |

**Not handled, and not claimed.** This is not a sandbox. The agent keeps the
network — the repository is public, and a `WebFetch` can read it — the process
table, and every file outside the masks. The masks are only as complete as the
scan plus `EVAL_MASK_PATHS`. The foreign-process scan is heuristic, not proof that no robot is present.
Nothing stops a cell changing its discovery configuration or choosing the same
`ROS_DOMAIN_ID` as another process. Run evaluations on a development host
separated from operational robots.

`analyze_v2.py` separates an **attempt** from a **breach**. Naming the
repository path in a tool call is not a breach on its own — `ps` and
`/proc/<pid>/cmdline` expose the harness's own invocation, which contains the
path, and the bind mount leaves the directory empty for anything that reads it.
Content markers in tool results are flagged for review, not automatically
classified as breaches: a treatment legitimately reads its own `CLAUDE.md`,
and a generic command can occur independently. No marker match is not proof
of isolation. Confirm provenance before excluding a cell or citing a result. Separately, a cell in a condition
that must not have this pack (`baseline`, `scripts-only`, `claude-md-only`)
whose init event lists one of its skills or its plugin is **contaminated**:
listed and excluded, never tallied.

**Set-aside cells.** A directory whose name contains `-DISCARDED-` or
`-SUPERSEDED-` holds cells a round threw away. `analyze_v2.py` lists and
excludes it; it used to pool it, which turned `mvt1` into 12/12 in a 40-cell
round that reported "50 cells graded".

## Archived

The first-generation per-line ablation tooling (`claims.py`, `probes.py`,
`runner.py`, `analyze.py`, `evals/variants/`) was deleted along with the rounds
it produced. `isolate_guardrail.sh` followed later: it read
`skills/ros2-perception/SKILL.md` out of `HEAD` after that skill was deleted, so
it could no longer start, and it ran its cells without `isolate_cell.sh`. It answered "does this shipped line earn its place?", which can
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
