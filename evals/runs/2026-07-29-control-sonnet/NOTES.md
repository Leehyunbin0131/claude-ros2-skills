<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-control` verified on sonnet — 2026-07-29

**70 lines to 46, and one line added** — the first skill in this project where
the pre-measurement found a place the model is *reliably wrong* rather than a
place it is already right.

| | |
| :--- | :--- |
| Method | pre-measurement, one content addition, n=4 sweep with one targeted top-up, one rewrite, confirmation |
| Probes | 6 new, 14 checks, covering 17/17 claims (16 after the rewrite merged two) |
| Spend | $7.85 sweep and top-up, $1.68 variant, $2.26 confirmation — $11.79 |
| Outcome | 70 -> 46 lines. `naked` 0.696 vs `full` 1.000; install-verified checks alone, 0.444 vs 1.000 |

## The pre-measurement found a gap, not a ceiling

Asked cold, sonnet already gives the whole of section 5: the diff-drive
calibration knobs (`left`/`right_wheel_radius_multiplier`,
`wheel_separation_multiplier`), the right order to apply them, and the
arithmetic. Section 5 was never going to measure anything.

The same pre-measurement turned up something better. Asked why an active
`diff_drive_controller` ignores `/cmd_vel`, sonnet correctly identifies a
`Twist`/`TwistStamped` mismatch — and then, **4 times out of 4**, tells the user
to set `use_stamped_vel`, a parameter that does not exist. Checked against the
install before acting on it:

- `diff_drive_controller_parameters.hpp` declares 23 parameters; no such name.
- `diff_drive_controller.hpp` has a single `Subscription<TwistStamped>` and no
  plain-`Twist` path.
- `grep -rl use_stamped_vel /opt/ros/jazzy/` returns nothing at all.

So the model has the diagnosis right and the fix confidently wrong, every time,
and the skill said nothing about it. A symptom row naming the `TwistStamped`-only
subscription and warning off the invented parameter was **added** before the
sweep — ablation can only measure lines that exist, so a gap has to be closed
first and then measured.

It measured **KEEP at q=0.050**: `naked` 0.00, `full` 1.00, `ablate` 0.30 at
n=10. The line does the job it was added for.

## Axis 1

Pooled over all 14 checks on the shipped 46-line body at n=8: **`naked` 55/79 =
0.696, `full` 112/112 = 1.000**, after a later stub-detector fix and regrade.

**`full` = 1.000 is capped by check design here.** These probes were written
from the skill, so most checks look for what it says. Split by anchor: the
install-verified checks (the `TwistStamped`-only subscription, the absent
`use_stamped_vel`) read `naked` **0.444** against `full` 1.000, while the checks
that echo the file's phrasing read `naked` 0.833 against the same `full` 1.000.
The first pair is the informative one. `protocol` is 0.500, below `naked`, the usual
artifact of a tools-off harness being told to go verify against the install.

Beyond the added row, the measurable content is navigational: `docs_url` is
1/4 naked against 4/4 full, and the calibration multipliers 1/3 against 4/4.
Everything else sat at `naked = full = ablate = 1.00`.

## The rewrite

Both code blocks — the `<ros2_control>` XML and the launch-file spawner Python —
measured at ceiling on every check they owned. Following the finding from
`ros2-testing` and `ros2-package`, they were replaced with two prose paragraphs
in a new "Wiring" section, and the `joint_state_broadcaster` symptom row folded
into the same paragraph rather than being stated twice.

Written with the compression rules this project has since collected: the
paragraphs name the *specifics* (`--controller-manager`, "`joint_state_broadcaster`
is not started automatically", the exact interface names) and keep the *reasons*
rather than only the actions — the last `ros2-troubleshooting` run failed three
rewrites by compressing causes away, and section 5 here gained back the two
causal clauses ("tire deformation under load", "separation has no effect on
straight-line driving, so fix radius first") that the original left implicit.

**Tied on all 14 checks at n=8, three of them slightly better.** 70 -> 46 lines,
adopted.

## Method note

`_c_no_use_stamped_vel` was wrong on its first draft and scored the correct
answers as failures: it searched for the string and returned False whenever it
appeared, including in answers that named the parameter *in order to warn the
reader off it* — which is exactly what the skill asks for. `full` read 0/4 while
every one of those four answers said "there is no `use_stamped_vel` parameter in
Jazzy; don't look for it".

The check now fails only when the parameter is *prescribed*, passing when every
occurrence sits inside a negating context, and was tested against four hand-
written cases before being trusted. Fixed by `runner.py regrade` against the
stored answers — 18 of 583 results changed, no re-run, no spend. Pattern versus
meaning, which is already written up in `PROCEDURE.md` and still took seeing a
0/4 to notice.
