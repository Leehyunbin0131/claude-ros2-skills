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

`t1_command_runs` needs a live controller. `t1_diffdrive_scenario.sh` brings one
up on `mock_components/GenericSystem` and was verified to discriminate before
being trusted: a plain `Twist` produces **0.0 rad/s** at the wheels and a
`TwistStamped` produces **10.0 rad/s** (0.5 m/s over a 0.05 m radius). The
grader compares the message type the agent told the user to publish against what
the running controller actually subscribes to.

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

Scenario: `fake_imu_pub.py` publishes a **deliberately wrong** mount — gravity
on `+X` instead of `+Z` on a stationary, level robot, with identity orientation
so the driver still reports "level". The right answer is discoverable only by
sampling the topic: no URDF, log or web search says how a particular robot's IMU
is physically bolted on. Verified against the shipped script, which returns
`[FAIL] mean accel = (+9.81, -0.01, -0.00) ... Gravity is on X, not Z` and exit
code 1.

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

## Build status

All four built and self-tested. Each was verified to **discriminate** before
being trusted — a grader that has only ever seen good answers is not validated.

| Piece | State | Evidence it discriminates |
| :--- | :--- | :--- |
| `fake_imu_pub.py` | done | publishes a stationary robot with gravity on **+X**; `check_imu_gravity.py` returns `[FAIL] ... Gravity is on X, not Z`, **exit code 1** |
| `t1_diffdrive_scenario.sh` | done | brings up `diff_drive_controller` on `mock_components/GenericSystem`; **plain `Twist` -> 0.0 rad/s, `TwistStamped` -> 10.0 rad/s**, which is 0.5 m/s over a 0.05 m wheel radius, exactly right |
| `grade_v2.py` | done | `--selftest` exercises every rule in both directions and passes; 233 plugins indexed |
| `scripts-only` cell | done | `CELLS="baseline scripts-only skills" ./run_ab.sh 2 out/` |

Two things were learned standing these up, both recorded in the scripts:

- Jazzy's `controller_manager` takes `robot_description` from a **topic**, not a
  parameter. Passing it as a parameter leaves it waiting forever, which is what
  the first attempt did.
- `ros2 topic pub --once` is routinely lost before discovery completes, so the
  first version of the discrimination check reported 0.0 for *both* message
  types and looked like a scenario failure. Continuous publishing fixes it.

`t1_command_runs` therefore **survives** rather than being dropped: the scenario
discriminates, so the grader can compare what the agent told the user to publish
against what the running controller actually subscribes to.


---

## Round 2 — narrow, by design

Round 1 tested 16 things at n=5. A clean 5/5 vs 0/5 is p=0.008, which becomes
q=0.063 after correcting across 16 tests — so the one real-outcome effect in the
round landed just outside the bar. The honest reading is that **round 1 was
under-powered because it was wide, not because n was small.**

Round 2 therefore narrows instead of growing:

| | Round 1 | Round 2 |
| :--- | :--- | :--- |
| Tasks | t1, t2, t3, t4 | **t2 only** |
| Cells | baseline, scripts-only, skills | **baseline, scripts-only** |
| n | 5 | **10** |
| Tests corrected across | 16 | **4** |

**The question it answers:** is shipping the bundled scripts worth it? That is
the only place in round 1 where a grader anchored to a real outcome moved
(`t2_ran_script` and `t2_exit_code_read`, both +1.00).

**Why this is not cherry-picking.** The comparison, the cell pair, n, and the
correction were fixed before any round-2 cell existed, and round 1's own notes
name this as the follow-up. Picking the winning test *out of* round 1 and
re-reporting it without correction would be cherry-picking; running a
pre-registered narrow round is how you resolve an underpowered result without
paying for tests nobody needs.

**The control gate is inherited, not re-paid.** `t4` was 5/5 vs 5/5 in round 1,
which established that the harness is not tilted toward the skills condition.
Round 2 does not include the `skills` cell at all, so there is nothing for that
bias to act on.

**Decided in advance:** if `t2_ran_script` clears q<0.05, the scripts ship and
the finding is that category 2 content earns its place while the prose describing
it does not. If it does not clear at n=10, the result is recorded as unresolved
and the scripts stay on the same footing as everything else — not topped up
again.
