# v2 tasks

Four tasks. Three target one category each from
[`DESIGN.md`](./DESIGN.md) §2; the fourth is a null control that must come back
with no difference, or the harness is biased and nothing else here can be
trusted.

Every cell: tools on (`Read Glob Grep Bash Write WebSearch WebFetch`),
multi-turn, live Jazzy install, fresh working directory. The **only** difference
between conditions is what is installed in that directory.

## Conditions

| Cell | `CLAUDE.md` | `skills/*/SKILL.md` | `skills/*/scripts/` |
| :--- | :---: | :---: | :---: |
| `baseline` | no | no | no |
| `skills` | yes | yes | yes |
| `scripts-only` | no | no | **yes** | 

`scripts-only` exists for T2 only, and it is the cell that makes T2 a real test
rather than a tautology — see the note there.

n = 5 per cell per task.

---

## T1 — category 1: version-specific breakage

**Prompt**

> I have a diff-drive robot running `ros2_control` on ROS 2 Jazzy with
> `diff_drive_controller` active and its interfaces claimed. Publishing to
> `/cmd_vel` does nothing — the wheels never turn and nothing errors. Find out
> why and give me a command that actually moves it.

**Why this task.** The pre-check in `DESIGN.md` §2 found the agent gets this
right *when told to search*. What is untested is whether it searches when nobody
tells it to. If it does, the skill line is dead weight; if it answers from
memory and invents `use_stamped_vel`, the line earns its place.

**Graders — all mechanical**

| id | Rule | Anchor |
| :--- | :--- | :--- |
| `t1_correct_type` | the final message names `TwistStamped` as what the controller subscribes to | install: `diff_drive_controller.hpp` declares `Subscription<TwistStamped>` and no plain-`Twist` path |
| `t1_no_invented_param` | does not *prescribe* `use_stamped_vel`; naming it to warn the reader off passes | install: `diff_drive_controller_parameters.hpp` declares 23 parameters, none is that |
| `t1_searched_or_read` | transcript contains a `WebSearch`/`WebFetch` call, **or** a `Read`/`Grep`/`Bash` touching `/opt/ros/jazzy` | transcript |
| `t1_command_runs` | the command given, run verbatim against a live `diff_drive_controller`, produces non-zero wheel velocity | **real outcome** |

`t1_command_runs` needs a live controller. Scenario script brings up
`ros2_control_node` with the `diff_drive_controller` demo config, then the graded
command is executed and `/joint_states` velocity is sampled. If that proves
unreliable to stand up, `t1_command_runs` is dropped and recorded as dropped —
not quietly replaced by a regex.

---

## T2 — category 2: content that exists nowhere else

**Prompt**

> My robot's EKF odometry drifts and sometimes spins on the spot. Every topic
> looks healthy and nothing errors. I think the IMU is mounted wrong but I want
> evidence, not a hunch. Settle it.

**Why three cells.** With `skills/` installed, `check_imu_gravity.py` is sitting
in the working directory — an agent that globs will find it whether or not any
`SKILL.md` mentions it. Comparing `baseline` against `skills` would therefore
measure *shipping the script*, not *the skill text*. The `scripts-only` cell
isolates that: same files, no `SKILL.md`, no `CLAUDE.md`.

- `skills` vs `scripts-only` → what the **text** buys
- `scripts-only` vs `baseline` → what **shipping the scripts** buys

**Graders**

| id | Rule | Anchor |
| :--- | :--- | :--- |
| `t2_ran_script` | transcript shows a `Bash` call executing `check_imu_gravity.py` | **real outcome** — the script ran |
| `t2_exit_code_read` | the final message reports the script's verdict (pass/fail/no-data), not just that it exists | transcript + the script's own exit code |
| `t2_no_ros2_run` | does not invent `ros2 run <package> check_imu_gravity.py`; the scripts are plain files | install: no such package exists |
| `t2_evidence_not_guess` | final message cites a measured number (an acceleration value, an axis) rather than only prose | transcript |

Scenario: `fake_imu_pub.py` publishing a **deliberately wrong** mount — gravity
on `+X` instead of `+Z`. The right answer is discoverable only by sampling the
topic. Needs writing; `fake_scan_pub.py` is the template.

---

## T3 — category 3: known but not done

**Prompt**

> Set up Nav2 on my ROS 2 Jazzy robot and tune it so it navigates well. Go
> ahead.

Deliberately underspecified. Footprint, drive type, and who publishes
`map -> odom` are all unstated and all decide the config.

**Graders**

| id | Rule | Anchor |
| :--- | :--- | :--- |
| `t3_asked_before_writing` | the first `Write`/`Edit` of a `.yaml` occurs **after** an assistant turn containing a question, or no such write happens | transcript, ordered by event index |
| `t3_asked_footprint` | a question mentions footprint / inscribed radius / robot radius | transcript |
| `t3_asked_drive_type` | a question mentions differential / omni / ackermann | transcript |
| `t3_read_shipped_defaults` | a `Read`/`Grep`/`Bash` touches `nav2_bringup/params/nav2_params.yaml` before writing config | transcript, ordered |
| `t3_plugins_real` | every `pkg::Class` string written to a `.yaml` is in the 233-class pluginlib index | **install index** |

`t3_asked_before_writing` is the whole point and is fully mechanical: compare the
event index of the first config write against the index of the first assistant
question mark. No judgement.

---

## T4 — null control

**Prompt**

> Write a Python node for ROS 2 Jazzy that subscribes to `/scan`
> (`sensor_msgs/msg/LaserScan`) and logs the minimum range once per second.

**Why.** Every skill in this pack claims to help; a harness that shows the
`skills` cell ahead on a task the model handles cold is measuring the harness.
This task is that check.

**Graders**

| id | Rule | Anchor |
| :--- | :--- | :--- |
| `t4_node_runs` | the generated file runs against the live `/scan` publisher and logs at least one finite minimum | **real outcome** |
| `t4_guards_range` | the emitted code filters non-finite readings or clamps to `[range_min, range_max]` | code inspection against `sensor_msgs/msg/LaserScan` |

**Expected: no significant difference between cells.** If `skills` wins here,
stop and find the bias before reading T1-T3.

---

## What is decided in advance

Written down now so it cannot be adjusted after seeing numbers:

- **n = 5 per cell per task.** Fisher exact, two-sided, `skills` vs the
  comparison cell named per task. Benjamini-Hochberg across all graders in a
  round.
- **A line ships only if a grader anchored to a real outcome or the install
  moves.** A difference visible only in transcript-behaviour graders counts for
  category 3 and nothing else.
- **T4 must be null.** If it is not, the round is void.
- **No top-up to cross a threshold.** If something lands at q=0.06, it is
  recorded as unresolved. Sampling until a number crosses is manufacturing.
- **Predicted outcome:** T1 comes back null (the agent searches and gets it
  right unprompted), T2 shows `scripts-only` ≈ `skills` (the script matters, the
  text does not), T3 shows the largest effect of the three. If T1 or T2 shows a
  large skill effect, this prediction was wrong and that is the finding.

## Still to build

1. `fake_imu_pub.py` — wrong-mount IMU publisher for T2.
2. A `ros2_control` bring-up for T1's `t1_command_runs`, or a recorded decision
   to drop that grader.
3. `grade_v2.py` — reads a `stream-json` transcript and emits the table above.
   Nothing is graded by reading.
4. `scripts-only` cell support in `run_ab.sh` (currently baseline/skills only).
