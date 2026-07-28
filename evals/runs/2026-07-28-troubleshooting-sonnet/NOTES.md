<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-troubleshooting`, section 1a measured on sonnet — 2026-07-28

First skill with no pre-existing probes, and the largest in the repo: 119 lines,
50 claims. **Eight of those 50 were measured. The other 42 were not**, and the
reason is the most useful thing in this run.

| | |
| :--- | :--- |
| Method | probe design driven by a pre-measurement, then an n=4 sweep with the `naked`/`full` baseline topped up to n=12 |
| Probes | 4 new: `ts-silent-topic`, `ts-imu-mount`, `ts-drive-backward`, `ts-tf-advisory` — 12 checks, all covering section 1a |
| Spend | $5.33 on the shipped design, plus $4.74 discarded on a first design whose prompts were wrong (below) |
| Outcome | no lines changed. Four KEEP verdicts at q<0.05 and one load-bearing joint group; 42 claims left unmeasured |

## The pre-measurement, and why it decided the design

Rather than write probes from the file, the file's own content was tested
against the model first. Sonnet was asked, with nothing in context, three
questions this skill answers:

| Question | Unaided result |
| :--- | :--- |
| Topic publishes at 10 Hz, subscriber never fires | Diagnoses QoS incompatibility correctly, reaches for `ros2 topic info -v` unprompted |
| `cmd_vel.linear.x = 0.2` drives the robot backward | Works it layer by layer, driver → controller → `hardware_interface::write()` |
| Valid `ROS_DOMAIN_ID` range and why | **`0-232`, plus the `0-101` ephemeral-port caveat, derived from `7400 + 250*id`** |

The third is a superset of what this skill says. Writing probes around REP 103
axes, executor deadlocks, lifecycle states or domain IDs would have measured
nothing — every one of them is at ceiling before the file is even loaded.

What the model cannot know is the part of this skill that is local to this
repository: that four scripts ship next to the `SKILL.md`, what they are called,
that they are plain files invoked with `python3 <path>` rather than a ROS 2
package, and one deliberately counter-intuitive behaviour of `check_tf_tree.py`.
All four probes target that. The scripts' actual CLIs were checked against
`--help` first to confirm the skill describes them accurately; it does.

## Result: section 1a is the strongest-measured content in the project

Pooled over all 12 checks: **`naked` 3/96 = 0.031, `full` 133/141 = 0.943.**

| Claim | Check | naked | full | ablate | q | Verdict |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `check_imu_gravity.py` line | imu_script | 0.00 | 1.00 | 0.00 | 0.004 | **KEEP** |
| `check_tf_tree.py` line | tf_script | 0.00 | 1.00 | 0.00 | 0.004 | **KEEP** |
| `check_odom_direction.py` line | odom_script | 0.00 | 0.82 | 0.00 | 0.041 | **KEEP** |
| `check_odom_direction.py` line | names_a_script | 0.00 | 0.82 | 0.00 | 0.041 | **KEEP** |

Four KEEP verdicts clearing the corrected bar, against two in the whole project
before this run. Unsurprising in hindsight — these are filenames that exist
nowhere but this repository, so `naked` is structurally 0.00 rather than
merely low.

The `python3`-not-`ros2 run` rule and its worked example ablate to Δ≈0
individually and read INERT, which is the classic redundancy signature. The
joint ablation settles it: **12/12 with the pair present, 0/4 with both
removed, p=0.001 — the group is load-bearing.** Either line alone teaches the
invocation; neither is disposable without the other. This is the case the
`joint=` declaration exists for, and it was declared before the run rather than
discovered from the Δ=0 collision afterwards.

`advisory_not_verdict` came back UNDERPOWERED (naked 0.50, full 1.00). The
`VERIFY PHYSICALLY` advisory that `check_tf_tree.py` always prints — including
for a correct intentional mount — is the one script behaviour a model might half
guess, and half is roughly what it does.

## What was not measured, and why that is not a footnote

**42 of 50 claims have no probe.** Sections 1, 2, 3A-3E, 4, 5 and 6 — the REP
103 conventions, the inverted-sensor checklist, `use_sim_time`, Nav2 lifecycle,
executor deadlocks, MoveIt collision, DDS domain IDs, the decision tree, the
anti-pattern table and the reference links — are all unmeasured.

The pre-measurement above says the model already handles that material, and the
honest reading of that is "probably cuttable, not measured". Those are different
claims and this run only supports the second. Writing probes that the model
passes unaided would produce a table of CUT verdicts that is really a table
about the probes.

**The axis-1 number is biased upward and should be read with that in mind.**
`naked` 0.031 is the lowest baseline in the project, but only because every
probe here targets the section the model structurally cannot know. It is not a
measurement of what the 119-line file is worth; it is a measurement of what
section 1a is worth. A probe set covering the rest would raise `naked`
substantially and shrink the gap.

Nothing was cut, so no confirmation run was needed: the shipped body is the
body that was measured.

## The design mistake that cost a run

The first version of all four prompts contained the sentence *"I have this
repo's Claude skills installed."* The intent was to make it fair to expect the
agent to find the script. The effect was the opposite: it told the model that
context existed to be hunted for, and with `--tools ""` the hunt stalls. Nine of
sixteen `naked` cells and seven of sixteen `protocol` cells stubbed, leaving the
baseline at **n=1** — unusable. $4.74 discarded.

Rewritten as plain user questions with no mention of skills, the naked stub rate
fell to about one in eight. **A probe prompt must read like a user's question,
not like a hint that context exists to be found**, and this is now in the probe
suite's own comment so the next person does not repeat it.

## Two harness bugs fixed here

**A negative-form check that passed trivially.** `_ts_no_ros2_run_for_script` is
true when the answer does *not* invent a ROS 2 package for the script — so an
answer that never mentions the scripts at all passed it. Caught in the
pre-flight stub check, where `naked` showed `...+`. It now returns ungradable
unless a script was actually named, verified against all three cases. This is
the exact failure mode already written up in `PROCEDURE.md`; it still took
seeing the `+` to notice.

**`analyze.py` crashed on a stale joint group.** `perc-depth-encoding` still
declared `joint=[[C_PERC_SYM_ENC, C_PERC_SYM_DEPTH]]` after both claims were cut
to `None` earlier the same day, and the redundancy section tried to join them
into a condition string. The stale declaration is removed, and `analyze.py` now
drops cut members and skips groups with fewer than two survivors rather than
failing.
