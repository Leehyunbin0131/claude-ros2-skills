<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-moveit` verified on sonnet — 2026-07-29

**60 lines unchanged in length, one row rewritten.** Five KEEP verdicts at
q<0.05 and one CUT — the highest ratio of load-bearing content measured in this
project, and the second skill running where the pre-measurement found the model
confidently wrong rather than already right.

| | |
| :--- | :--- |
| Method | pre-measurement, one content correction, n=4 sweep with the baseline topped up to n=10 |
| Probes | 5 new, 13 checks, covering 14/14 claims |
| Spend | $5.31 |
| Outcome | `naked` 39/83 = 0.470 vs `full` 130/130 = 1.000; install-verified checks alone, 0.083 vs 1.000 |

## The pre-measurement found the skill wrong, not just the model

Most of this file is at ceiling, as expected: unaided sonnet writes the Jazzy
`.hpp` include, sets `automatically_declare_parameters_from_overrides`, and
names TRAC-IK / PickIK, `kinematics.yaml` and the `moveit_controllers`
`action_ns` without help.

The servo row was different. Jazzy redesigned MoveIt Servo: `moveit_msgs` ships
`ServoCommandType.srv` (`JOINT_JOG=0`, `TWIST=1`, `POSE=2`) and there is no
Trigger-shaped servo service anywhere in the installed `moveit_msgs/srv/`. The
old `/servo_node/start_servo` (`std_srvs/srv/Trigger`) is gone.

Asked cold, sonnet prescribes `start_servo` + `std_srvs/srv/Trigger` **4 times
out of 4**. And this skill's own row said *"call the servo start trigger
service"* — the same dead Humble/Iron interface. So the file was not merely
silent on a gap, as in `ros2-control`; it was **actively repeating the model's
error**. The row was rewritten against the installed `.srv` before the sweep,
naming `/servo_node/switch_command_type`, the `ServoCommandType` type, the
integer for `TWIST`, and an explicit warning that the Trigger service no longer
exists.

Both of its checks came back **KEEP**: `no_start_servo` at `naked` 0.00 /
`full` 1.00 / `ablate` 0.00, q=0.007, and `switch_command_type` at q=0.033.

## Axis 1 and the KEEP set

**`naked` 39/83 = 0.470, `full` 130/130 = 1.000** on the shipped body at n=10,
after a later stub-detector fix and repo-wide regrade.

**Read that `full` with the caveat it deserves.** These probes were written by
reading the skill, so most checks look for what the skill says and `full` = 1.000
is closer to an identity than to a measurement. Splitting them by anchor:

| Check group | naked | full |
| :--- | ---: | ---: |
| verified in the install (servo `.srv`, the `.hpp` header) | **0.083** | 1.000 |
| echoing the file's own phrasing | 0.627 | 1.000 |

`full` is 1.000 either way; the groups differ entirely in `naked`. The
install-anchored group is the one that says something.

| Claim | Check | naked | full | ablate | q |
| :--- | :--- | ---: | ---: | ---: | ---: |
| servo row (rewritten) | no_start_servo | 0.00 | 1.00 | 0.00 | 0.007 |
| trajectory-tolerance row | joint_limits | 0.17 | 1.00 | 0.00 | 0.007 |
| servo row (rewritten) | switch_command_type | 0.00 | 1.00 | 0.25 | 0.033 |
| IK row | alt_ik | 0.57 | 1.00 | 0.25 | 0.033 |
| `MoveGroupInterface` block | hpp_header | 0.25 | 1.00 | 0.25 | 0.033 |

Five KEEPs against one CUT (`pose_target`, which unaided answers always
include). Every other check landed INERT or unclear with `naked` between 0.17
and 0.75 — real headroom, just not resolvable at this n.

`hpp_header` is worth naming. The code block's comment — *"Jazzy (MoveIt
2.10+): .hpp headers; legacy .h is deprecated"* — is doing the work: unaided,
the model writes the deprecated `.h` spelling three times in four. Both headers
are present in the install (`move_group_interface.h` and `.hpp` both ship), so
nothing errors at compile time and nothing warns; this is the same class of
silent-wrongness as the `cv_bridge` header in `ros2-perception`.

## No rewrite was attempted, deliberately

With five KEEPs and one CUT there is almost no ceiling mass to compress. After
`ros2-troubleshooting`, where three rewrites were each rejected and the cause
turned out to be how they were written rather than a property of the file, a
rewrite here would be spending to find out whether a 60-line body with one
cuttable check can be made shorter. It cannot meaningfully, so it was not tried.
The shipped body is the measured body — the sweep's `naked`/`full` at n=10 runs
against the file as it stands, so no separate confirmation run was needed
either.

## Method note

`_m_no_start_servo` was written from the start to distinguish *prescribing* the
dead service from *naming it to warn the reader off*, because the equivalent
check on `ros2-control` (`use_stamped_vel`) had scored correct answers as
failures the day before by searching for the bare string. The negation-window
approach carried over directly and needed no repair here.
