<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-troubleshooting` verified on sonnet — 2026-07-28

Largest skill in the repo (119 lines, 50 claims) and the first with no
pre-existing probes. **All 50 claims measured. Nothing was cut** — three
authored rewrites were built and all three were rejected on measurement.

| | |
| :--- | :--- |
| Method | probe design driven by a pre-measurement, n=4 sweep with targeted top-ups, then three rewrite attempts |
| Probes | 10 new, 35 checks, covering 50/50 claims |
| Spend | $20.68 sweep and top-ups, $14.56 across three rejected rewrites, $4.74 on a discarded first probe design — $39.98 |
| Outcome | file unchanged at 119 lines. `naked` 0.440 vs `full` 0.990 |

## Axis 1

Pooled over all 35 checks: **`naked` 74/168 = 0.440, `full` 201/203 = 0.990.**
`protocol` (CLAUDE.md alone) is 0.362, below `naked` — the familiar artifact of
telling a tools-off model to go verify against the install.

## Axis 2, part one: five KEEPs, all in the scripts section

| Claim | Check | naked | full | ablate | q |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `check_imu_gravity.py` line | imu_script | 0.00 | 1.00 | 0.00 | 0.000 |
| `check_odom_direction.py` line | odom_script | 0.00 | 1.00 | 0.00 | 0.000 |
| `check_odom_direction.py` line | names_a_script | 0.00 | 1.00 | 0.00 | 0.000 |
| `check_tf_tree.py` line | tf_script | 0.00 | 1.00 | 0.00 | 0.000 |
| `check_tf_tree.py` line | advisory_not_verdict | 1.00 | 1.00 | 0.00 | 0.000 |

`naked` is structurally 0.00 on the filename checks — these files exist nowhere
but this repository. The last row is the interesting one: `advisory_not_verdict`
scores 1.00 unaided *and* 0.00 ablated. Asked cold, the model reasons correctly
that a `VERIFY PHYSICALLY` advisory on a deliberately inverted mount is not a
verdict. Given the rest of the skill with that one line removed, it stops doing
so. The surrounding text creates the wrong expectation and only that line
corrects it.

## Axis 2, part two: everything else measured CUT, and cutting it failed anyway

The other 45 claims came back CUT or unclear, with `naked` between 0.75 and
1.00. The pre-measurement had predicted exactly this: asked cold, sonnet
diagnoses the silent-QoS case and reaches for `ros2 topic info -v` unprompted,
works the inverted-drive bug layer by layer, and gives the `ROS_DOMAIN_ID` range
as **0-232 with the 0-101 ephemeral-port caveat and the `7400 + 250*id`
arithmetic** — a superset of what this skill says. Read naked whole, the answers
are often better than the file: one added `twist_mux` re-signing as a candidate
cause and a way to confirm frame orientation from a known front-mounted sensor's
`x` sign, neither of which the skill mentions.

So three rewrites were authored, each dropping the sections that measured CUT
and keeping section 1a. **All three were rejected**, each by a different check
that single ablation had scored `naked = full = ablate = 1.00`:

| Rewrite | Lines | Rejected on | full vs variant | p |
| :--- | ---: | :--- | :--- | ---: |
| `compressed` | 44 | `tf2_echo` | 8/8 vs 2/6 | 0.015 |
| `compressed2` | 58 | `domain_default` | 15/16 vs 7/16 | 0.006 |
| `compressed3` | 62 | `single_thread` | 16/16 vs 9/16 | 0.007 |

Each rejection was repaired in the next attempt — the `tf2_echo` action line
went back, then the `ROS_DOMAIN_ID` default, then the executor explanation — and
each time a different line that had also measured CUT broke instead.

**That is the result, and it is not a failed experiment.** For this file, a
single-claim ablation verdict of CUT does not predict what happens when the
section around it goes. The content is mutually reinforcing in a way the
per-claim instrument cannot resolve: with the whole table present, any one row
is redundant; with most of the table gone, the survivors stop being enough. The
project's own rule — that the state which matters is the one that will ship —
held three times in a row here, at a cost of $14.56 to establish.

Cutting was abandoned after the third rejection rather than iterating further.
Each round buys one line back and finds another; the pattern was clear and more
runs would have been spending to confirm something already demonstrated.

## Method notes

**The first probe design was discarded.** All four original prompts contained
*"I have this repo's Claude skills installed"*, meant to make it fair to expect
the agent to find the shipped script. It did the opposite — it told the model
context existed to be hunted for, and with `--tools ""` the hunt stalls. Nine of
sixteen `naked` cells and seven of sixteen `protocol` cells stubbed, leaving the
baseline at n=1. $4.74 discarded. Rewritten as plain user questions, the naked
stub rate fell to about one in eight. A probe prompt must read like a user's
question, not like a hint that context exists to be found.

**A negative-form check passed trivially.** `_ts_no_ros2_run_for_script` is true
when the answer does not invent a ROS 2 package for the script, so an answer
that never mentioned the scripts passed it. Caught in the pre-flight stub check.
It now returns ungradable unless a script was actually named.

**`analyze.py` crashed on a stale joint group.** `perc-depth-encoding` still
declared a `joint=` pair whose members had been cut to `None` earlier the same
day. The declaration is gone and `analyze.py` now drops cut members and skips
groups with fewer than two survivors.

**220 cells came back `no-model-response` mid-sweep**, wiping three probes
entirely. Errored cells were filtered out of `cells.jsonl` and re-run at lower
concurrency, which completed cleanly. Worth knowing: the runner's resume logic
skips cells that are present-but-errored, so an interrupted sweep needs those
rows removed before it will retry them. A top-up written at `--repeats 12` was
also lost when a later `--repeats 4` invocation rewrote the file, and had to be
redone — do the wide top-ups last.
