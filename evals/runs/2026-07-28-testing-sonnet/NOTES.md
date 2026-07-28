<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-testing` re-checked on sonnet, then rewritten — 2026-07-28

An earlier pass graded on haiku had cut this skill from 78 lines to 76 (those
runs have since been deleted — see [`../../RESULTS.md`](../../RESULTS.md) for
why haiku verdicts were not kept). This pass re-ran it on sonnet, the model
that actually ships, and the result was not another two-line trim: **76 lines
to 42**, and the change that got there was a rewrite, not a deletion.

| | |
| :--- | :--- |
| Method | full sweep at n=4 (`naked`/`protocol`/`full`/`shipped`, every claim ablated singly, every claim `only:`, plus `reorder:4,1,2,3`), targeted top-ups, then an authored `variant:` rewrite measured against the current body |
| Probes | 4, covering all 12 claims: `colcon-trust`, `rosbag2-write`, `launch-testing-node`, `testing-diagnose` |
| Spend | 184-cell sweep $4.94, top-ups $0.78, variant comparison $1.85, confirmation $1.15 — $8.72 total |
| Outcome | 76 -> 42 lines, `naked` 0.762 vs `full` 1.000 on the shipped body |

## Axis 1 first: this skill has the strongest effect of any measured

Pooled over all 13 checks on the shipped 42-line body at n=8:
**`naked` 77/101 = 0.762, `full` 104/104 = 1.000.** Perfect score with the file,
three-quarters without it. That matters because it is the opposite of the
ceiling case, where `naked` is already at 1.000 and there is no room for a file
to add anything. Here there is room, and the file fills all of it.

Two checks carry most of the gap and are worth naming, because they are what a
skill is *for*:

- `writer_create_topic` — **0/8 naked, 8/8 full.** Unaided, sonnet reaches for
  the templated `writer.write(msg, topic, time)` overload and never registers
  the topic. It is not a wrong API, but the bag's topic metadata is then written
  implicitly, and the explicit `create_topic({0, "chatter", type, "cdr", {}, ""})`
  form is what the skill shows. Zero out of eight is as clean a signal as this
  project has produced.
- `simtime_cause` — 4/8 naked, 8/8 full. Half the time, unaided answers do not
  connect "rosbag playback produces no callbacks" to `use_sim_time`/`--clock`.

## Axis 2: the ablation sweep said "cut", and it was wrong to stop there

At n=4 the sweep returned CUT on 12 of 16 claim-check pairs, two UNDERPOWERED
(`writer_create_topic` and `simtime_cause`, both Δ=+1.00 with q=0.229 — the
sample was too small, not the effect too weak), and two redundancy groups that
were declared before the run and came back clean on joint ablation:

| Group | Joint ablation |
| :--- | :--- |
| colcon code block + prose + symptom rows :01/:02 (4 claims) | Δ=0 on all three `colcon-trust` checks |
| launch_testing code block + `ReadyToTest()` prose (2 claims) | Δ=0 on all three `launch-testing-node` checks |

Reading that as "delete six claims" would have been wrong, and the top-ups
proved it: at n=8 `writer_create_topic` is 0/8 naked. **A group can be jointly
ablatable and still be load-bearing** — what the joint result actually says is
that those lines are saying the same thing more than once, which is an argument
for *merging* them, not for dropping them.

## The rewrite

So the redundancy groups were merged by hand rather than cut. Four claims about
`colcon test` became one sentence; the 23-line `launch_testing` example plus its
`ReadyToTest()` explanation became one sentence. Everything else was left alone.
Saved as [`../../variants/ros2-testing/compressed.md`](../../variants/ros2-testing/compressed.md)
and run against the live body at n=8:

**Tied on all 13 checks, 8/8 versus 8/8, p=1.000 everywhere.** By the adoption
rule (on a tie the smaller body wins) 42 lines beats 76, so it shipped.

### The prose version produced better code than the code block

This was not expected and is the most useful thing in the run. Asked to write a
`launch_testing` file, the variant's answers — working from one sentence of
description instead of a worked example — included things the deleted example
never showed:

- `@pytest.mark.launch_test` on `generate_test_description()`
- `proc_info.assertWaitForStartup(process=..., timeout=10)`
- `proc_output.assertWaitFor('Publishing:', process=...)`
- `add_launch_test()` in `CMakeLists.txt`

All four verified present in the local Jazzy install
(`launch_testing/pytest/hooks.py` registers the `launch_test` marker,
`launch_testing_ament_cmake/cmake/add_launch_test.cmake`,
`proc_info_handler.py:143`, `asserts/assert_exit_codes.py:38`). The checks score
these answers identically to the example-driven ones, so the *measurement* is a
tie — but read whole, the shorter body is better. A worked example seems to act
as a ceiling: the model reproduces it and stops. Naming the concept and leaving
the code to the model got more correct API surface, not less.

## What did not move

`reorder:4,1,2,3` (symptom table moved ahead of the doc pointers) was a clean
null again, matching the haiku pass. Section order does not measurably change
output for a body this size. No interference: no ablation moved a check it does
not own.

## Method notes for next time

Two process errors here, both self-inflicted, both worth not repeating.

**Top-ups were run at probe granularity, not claim granularity.** Two checks came
back UNDERPOWERED; the fix should have been
`--conditions naked,full,ablate:<the-one-claim>`, roughly a dozen cells. Instead
the whole probe was re-run at `--repeats 8` — 28 cells for `rosbag2-write`, 36
for `testing-diagnose` — to resolve one check each. The data is not wrong, just
mostly unnecessary. `PROCEDURE.md` step 3 now says this explicitly.

**Claim IDs shifted twice in one day.** The 78->76 cut renumbered the symptom
table once; the 76->42 rewrite collapsed four claims into two and renumbered it
again. `C_T_SYM05`/`C_T_SYM06` are the stable *names* for the QoS and
`use_sim_time` rows and now hold ids `:01`/`:02` — the low numbers — which looks
like a mistake and is not. The comment block in `probes.py` spells this out.
Validate ids before every sweep; this project has now been bitten three times.
