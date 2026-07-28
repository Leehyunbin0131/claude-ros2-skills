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
| Outcome | file unchanged at 119 lines. `naked` 0.795 vs `full` 1.000 off the scripts section, 0.050 vs 0.982 on it |

## Axis 1 — read in two halves, not pooled

| | naked | full |
| :--- | ---: | ---: |
| Shipped-scripts section (1a) | 4/80 = **0.050** | 109/111 = 0.982 |
| Everything else (42 claims) | 70/88 = **0.795** | 92/92 = 1.000 |
| Pooled | 74/168 = 0.440 | 201/203 = 0.990 |

The pooled 0.440 is an artifact of how many checks point at each half, not a
summary of the skill: about half the graded baseline cells belong to probes
asking for filenames that exist nowhere but this repository, where `naked` is
structurally near zero. The scripts section is worth a great deal; the rest is
worth roughly +0.20 over an unaided model. Quoting the pooled figure alone
overstates the file by more than a factor of two on its larger half.

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

## Axis 2, part two: everything else measured CUT, and three attempts to cut it failed

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
and keeping section 1a. **All three were rejected:**

| Rewrite | Lines | Rejected on | full vs variant | p |
| :--- | ---: | :--- | :--- | ---: |
| `compressed` | 44 | `tf2_echo` | 8/8 vs 2/6 | 0.015 |
| `compressed2` | 58 | `domain_default` | 15/16 vs 7/16 | 0.006 |
| `compressed3` | 62 | `single_thread` | 16/16 vs 9/16 | 0.007 |

### Corrected reading of those three rejections

The first version of these notes concluded that each rewrite had removed a line
which was secretly load-bearing despite a `CUT` verdict — that per-claim
ablation had simply been wrong. **Comparing the three variant runs against each
other, rather than each against `full` alone, shows that holds for one of the
three and is contradicted by the other two.**

| Check | `full` | v1 (topic absent) | v2 (terse summary added) | v3 (more added) |
| :--- | ---: | ---: | ---: | ---: |
| `tf2_echo` | 8/8 | **2/6** | 7/8 | 13/14 |
| `domain_default` | 15/16 | 8/8 | **7/16** | 16/16 |
| `single_thread` | 16/16 | 7/8 | 13/16 | **9/16** |

`tf2_echo` behaves as first described — dropped, collapsed, restored, fixed.
The other two do the opposite. `domain_default` scored **8/8 in the variant
that omitted DDS content entirely** and only broke in the next one, which still
omitted it but had gained an unrelated summary section. `single_thread` got
monotonically worse as content about it was added back.

The mechanism is in the wording. `_ts_single_thread_cause` searches for
`single[- ]?threaded`. The shipped body gives the cause — *"a single-threaded
executor cannot process service responses while executing a blocking
callback"* — and the rewrite compressed that to *"needs a
`MultiThreadedExecutor` plus a `ReentrantCallbackGroup`"*: the fix with the
cause deleted. The model followed the shorter framing and produced the fix
without the cause.

**A terse summary of a topic can be worse than both the full treatment and
saying nothing.** Omit a topic and the model answers from its own knowledge,
completely. Summarise it badly and the summary becomes the frame the answer is
built on, and what the summary dropped is dropped from the answer.

What is therefore established is **"these three rewrites failed"**, not "this
file cannot be compressed". The failures trace to how the rewrites were written
— actions kept, causes discarded — not to a property of the file. A compression
that preserves the causal explanations was never attempted. The skill ships
unchanged at 119 lines either way, so that attempt was not made rather than
spending further on a body that was not going to change.

**How the misreading happened, since it is the reusable part:** each variant was
compared only against `full`, never against the other variants. Three runs each
reported "another CUT-verdict line broke" and the repetition read as
confirmation. Two of the three numbers contradict that story and the
contradiction was sitting in data already collected — it cost nothing to find,
only the question.

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
