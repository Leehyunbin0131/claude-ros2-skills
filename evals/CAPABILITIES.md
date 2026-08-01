# What the baseline agent reaches unaided, and where it stops

The list this project exists to produce. One row per tested mechanism, filled in
only from a real-outcome check that actually ran — never from an impression of a
transcript.

**How to read it.** Every number is *cells passing / cells run*, `baseline` only:
no skills, no `CLAUDE.md`, model knowledge + web search + a live ROS 2 Jazzy
install. **A rung fails at ≤ 7/10.** Method and anti-manufacturing rules:
[`LADDER.md`](./LADDER.md).

**Status legend.** `reached` = the model does this on its own, so a skill saying
it buys nothing. `GAP` = it does not, and that is content worth writing.
`pending` = the rung has not run.

---

## Reached unaided — no skill content licensed

| Area | Mechanism tested | Result |
| :--- | :--- | ---: |
| Packaging | `ament_python` + `ament_cmake` interface pkg, launch file, params file | **60/60** |
| Packaging | + C++ node pkg, `.srv` used from both C++ and Python, launch including another package's launch | **70/70** |
| Packaging | + message field typed by another package's message, `rclcpp_components` composable node in a container, a `colcon test` that passes | **60/60** |
| Gazebo | SDF world, physics system, diff-drive robot with joints, headless `gz sim -s -r` | **40/40** |
| Gazebo | + `ros_gz_bridge` direction characters, `gpu_lidar` needing `gz-sim-sensors-system`, `/clock` bridged | **40/40** |
| Gazebo | + URDF on `/robot_description` spawned with `ros_gz_sim`, IMU system, sensor `frame_id` matching the URDF link, `use_sim_time` following sim time | **28/30** |
| Executors | 1 s service called from a timer callback | **30/30** |
| Executors | + call moved into a subscription callback, 10 Hz heartbeat must not drop | **40/40** |
| Executors | + five concurrent calls, batch under 3 s | **40/40** |
| Messages | `TwistStamped` vs `Twist` on a Jazzy `diff_drive_controller` | **10/10** |

Two skills (`ros2-package`, `gazebo-sim`) and one section were deleted on these
numbers.

---

## Confirmed gaps

| Gap | Baseline | What closes it | After |
| :--- | ---: | :--- | ---: |
| Verifies against the install instead of answering from memory | **2/10** | `CLAUDE.md`'s verify paragraph | **10/10** (q=0.002) |
| Produces an exit-coded pass/fail verdict, not "looks right" | **0/10** | a bundled runnable script | **10/10** (q<0.001) |
| Runs the QoS code it writes instead of shipping it untested | **5/10** | `CLAUDE.md`'s "Done means it ran" | **9/10** (q=0.141, **underpowered — not significant**) |

Prose describing the bundled script moved **+0.00 on every check**. Ten skills
stacked on top of `CLAUDE.md` moved **nothing** (10/10 vs 10/10, 6/10 vs 6/10).
**No `SKILL.md` prose in this pack has ever shown a measured effect.**

---

## 2026-07-31 coverage sweep — L1, L2 and L3 complete

Four skills that had never been tested at all. Prompts frozen before any cell
ran; graders validated against deliberately broken references first.

**Every L1 and L2 rung passed.** 254 of 270 real-outcome checks. By rule 4 all
four ladders climb to L3.

The only failures anywhere are the QoS trap: one `per1` cell and one `per2`
cell subscribed with rclpy's default RELIABLE QoS to a BEST_EFFORT camera,
received nothing, and timed out. Everything else the model reached unaided.

Six checker defects surfaced during L2 and every one of them was mine, not a
cell's — five cells scored as total failures came back perfect when re-graded.
They are listed in [`LADDER.md`](./LADDER.md); the short version is that a
grader sampling a live distributed system kept assuming its own conditions were
the only ones, and three of the defects punished *good* practice (isolating a
DDS domain, guarding a bringup against double-launch).

| Rung | Mechanisms added | Checks | Result |
| :--- | :--- | :--- | ---: |
| `ctl1` | URDF `<ros2_control>`, `mock_components/GenericSystem`, controller_manager params, `joint_state_broadcaster` spawned | cm_running, jsb_active, joint_states | **30/30 reached** |
| `ctl2` | + a second controller claiming interfaces, commands reaching mocked state | both_active, **command_lands** | **20/20 reached** |
| `ctl3` | + a custom C++ `SystemInterface` pluginlib plugin | builds, **custom_plugin**, component_active, joint_states | **40/40 reached** |
| `tst1` | a pytest registered with the build that `colcon test` actually runs | builds, test_ran, no_failures | **30/30 reached** |
| `tst2` | + `launch_testing` against a live node | builds, test_ran, no_failures, **launch_testing** | **40/40 reached** |
| `tst3` | + rosbag2 recorded programmatically and read back | builds, test_ran, no_failures, **bag_written** | **40/40 reached** (re-graded; the first pass measured a grader defect) |
| `per1` | `cv_bridge` round trip, BEST_EFFORT camera, republish | frames, publishes, no_hang, exits_clean | **36/40 reached** (1 cell lost to the QoS trap) |
| `per2` | + `CameraInfo` intrinsics, 3D→pixel projection, `vision_msgs` | pixel_correct, detection_published, **detection_correct**, exits_clean | **38/40 reached** (1 cell lost to the QoS trap) |
| `per3` | + 16UC1 depth → `PointCloud2` in metres | clouds, fields_ok, **metres**, **drops_invalid** | **32/40 reached** (2 cells lost to the QoS trap) |
| `mvt1` | self-authored URDF+SRDF, `move_group` reaching a usable state | move_group_up, plan_service, group_known | **30/30 reached** (re-run; see LADDER.md) |
| `mvt2` | + a real `GetMotionPlan` returning a trajectory | move_group_up, plan_runs, **points** | **30/30 reached** |
| `mvt3` | + a collision object applied to and respected by the scene | move_group_up, plan_runs, points, **objects** | **reached, clean** |

### `ros2-core` and `ros2-dev`

Prompts frozen 2026-07-31 with the rest of the sweep; graders being built as
the L3 round runs.

| Rung | Mechanisms added | Checks | Result |
| :--- | :--- | :--- | ---: |
| `cor1` | static TF broadcast + lookup, values driven by ROS parameters | tf_logged, tf_correct, **params_used**, exits_clean | **40/40 reached** |
| `cor2` | + a dynamic transform, lookup at a stamp, extrapolation handled not crashed | tf_lines, motion, **extrap**, exits_clean | **40/40 reached** |
| `cor3` | + a lifecycle node whose publication is gated on the active state | lifecycle_node, **silent_when_inactive**, publishes_when_active | **30/30 reached** |
| `dev1` | a Nav2 param file the servers accept as-is | yaml_valid, **servers_load**, mppi, footprint | queued |
| `dev2` | + the stack driven through lifecycle to active | servers_up, **controller_active**, planner_active | queued (prompt amended pre-run; see LADDER.md) |
| `dev3` | + a costmap that ingests live scan data and marks an obstacle | controller_active, costmap_published, **obstacle_marked** | queued |

`cor1`'s `params_used` re-runs the node with `-p tx:=0.7`: a node that
hardcodes the translation prints the right default and ignores the override.
`dev1`'s `servers_load` drives the lifecycle to `configure` rather than
checking `ros2 node list`, because a Nav2 server starts `unconfigured` and does
not resolve its plugin strings until then — a controller plugin missing its
package namespace comes up looking identical either way.

`ros2-microros` is out of scope: no MCU on this machine, and a standing
instruction not to verify it.

---

## Silent-failure facts found while building the fixtures

Not model gaps — properties of Jazzy that cost a debugging cycle each, recorded
because every one of them fails without an error.

- `controller_manager` reads `robot_description` from the **topic**, not a
  parameter. Passed as a parameter it waits forever logging
  `Waiting for data on 'robot_description' topic`.
- `--params-file` without `--ros-args` is **ignored**, surfacing much later as
  `The 'type' param was not defined for 'joint_state_broadcaster'`.
- `ros2 topic echo` **auto-negotiates QoS** and therefore cannot detect a
  reliability mismatch — it shows data from a BEST_EFFORT publisher either way.
  A default rclpy subscriber on the same topic receives 0 and logs
  `offering incompatible QoS ... Last incompatible policy: RELIABILITY`.
- Missing `<export><build_type>ament_cmake</build_type></export>` makes colcon
  treat the package as catkin: build exits 0, `ros2 run` cannot find it.
- `colcon test` **exits 0 with zero tests registered**. The exit code cannot
  distinguish "all tests passed" from "no tests ran".
- `ogre2` segfaults headless on this WSL2 machine, inside
  `Ogre::Hlms::createDatablock`.
- `set -u` + `source /opt/ros/jazzy/setup.bash` aborts on
  `AMENT_TRACE_SETUP_FILES: unbound variable`.
- `ros2 topic echo` prints float arrays as YAML block sequences, not inline
  `[a, b, c]` — a naive parser reads 0 elements from a real lidar scan.
- A URDF with **no acceleration limits** makes MoveIt's
  `AddTimeOptimalParameterization` response adapter fail, and the whole plan is
  reported `FAILURE` (99999) **even though the geometric path was computed and
  returned**. Limits go in `joint_limits.yaml` under
  `robot_description_planning`, or in the URDF. With them: `CODE 1`, 14 points.
  Without: `CODE 99999`, 6 points — a result that looks partly right and is
  labelled a total failure.
- MoveIt planning-pipeline parameters are namespaced under the pipeline name
  (`ompl.planning_plugins`, not `planning_plugins`), and `joint_limits.yaml`
  under `robot_description_planning`. Both confirmed by reading
  `moveit_configs_builder.py` on this install rather than by guessing.
