# What the baseline agent reaches unaided, and where it stops

The list this project exists to produce. One row per tested mechanism, filled in
only from a real-outcome check that actually ran — never from an impression of a
transcript.

**How to read it.** Every number is *checks passing / checks run*, `baseline`
only: no skills, no `CLAUDE.md`, model knowledge + web search + a live ROS 2
Jazzy install. Ten cells per rung. **A rung fails at ≤ 7/10 cells.** Method and
anti-manufacturing rules: [`LADDER.md`](./LADDER.md).

---

## The short answer

Across **eight ladders and 24 rungs — every scenario this project set out to
test — the model reached every mechanism it was asked for** except one recurring
trap, and **not a single failure was closed by supplying information**.

Four failure modes were found. All four are behavioural:

| What the model does not do unaided | Baseline | What closes it | After |
| :--- | ---: | :--- | ---: |
| Verify against the install instead of answering from memory | **2/10** | one paragraph of `CLAUDE.md` | **10/10** (q=0.002) |
| Produce an exit-coded pass/fail verdict rather than "looks right" | **0/10** | a bundled runnable script | **10/10** (q<0.001) |
| Run the QoS code it writes before shipping it | **5/10** | `CLAUDE.md`'s "Done means it ran" | **9/10** (q=0.141, underpowered) |
| Run the Nav2 config it writes before shipping it | **0/10** | a task that requires reaching `active` | **30/30** |

The last row is the cleanest evidence here, and it is set out in full below:
same model, same wrong belief, **zero difference in information**, 0/10 versus
30/30.

**No `SKILL.md` prose has ever moved a check.** The two things that did are a
paragraph telling the agent to verify, and an executable file.

---

## Reached unaided

Every mechanism below was produced by a baseline cell with no skill installed.

### Packaging and build — `ros2-package`, ladder exhausted, **skill deleted**

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | `ament_python` + `ament_cmake` interface package, launch file, params file | **60/60** |
| L2 | + C++ node package, `.srv` consumed from both C++ and Python, launch including another package's launch | **70/70** |
| L3 | + a message field typed by another package's message, an `rclcpp_components` composable node loaded into a container, a `colcon test` that passes | **60/60** |

### Simulation — `gazebo-sim`, ladder exhausted, **skill deleted**

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | SDF world, physics system, diff-drive robot with joints, headless `gz sim -s -r` | **40/40** |
| L2 | + `ros_gz_bridge` direction characters, `gpu_lidar` needing `gz-sim-sensors-system`, `/clock` bridged | **40/40** |
| L3 | + URDF on `/robot_description` spawned with `ros_gz_sim`, IMU system, sensor `frame_id` matching the URDF link, `use_sim_time` following sim time | **28/30** |

### Executors and services — `ros2-troubleshooting` §3C, exhausted, **section cut**

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | a 1 s service called from a timer callback | **30/30** |
| L2 | + the call moved into a subscription callback, a 10 Hz heartbeat that must not drop | **40/40** |
| L3 | + five concurrent calls, batch under 3 s | **40/40** |

### `ros2-control`

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | URDF `<ros2_control>`, `mock_components/GenericSystem`, controller_manager params, `joint_state_broadcaster` spawned | **30/30** |
| L2 | + a second controller claiming interfaces, a command reaching the mocked state | **20/20** |
| L3 | + a **custom C++ `SystemInterface` pluginlib plugin**, built and active | **40/40** |

### `ros2-testing`

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | a pytest registered with the build that `colcon test` actually runs | **30/30** |
| L2 | + `launch_testing` against a live node | **40/40** |
| L3 | + rosbag2 recorded programmatically and read back | **40/40** |

### `ros2-moveit`

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | a self-authored URDF + SRDF that `move_group` loads and reports | **30/30** |
| L2 | + a real `GetMotionPlan` returning a trajectory | **30/30** |
| L3 | + a collision object applied to and reported back by the planning scene | **clean** |

### `ros2-core`

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | static TF broadcast and lookup, values driven by ROS parameters | **40/40** |
| L2 | + a dynamic transform, lookup at a stamp, `ExtrapolationException` handled not fatal | **40/40** |
| L3 | + a lifecycle node that publishes **nothing** until externally activated | **30/30** |

### `ros2-perception`

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | `cv_bridge` round trip against a BEST_EFFORT camera, republish | **36/40** |
| L2 | + `CameraInfo` intrinsics, 3D→pixel projection, `vision_msgs` output | **38/40** |
| L3 | + 16UC1 depth → `PointCloud2` in metres, invalid pixels dropped | **32/40** |

The four missing cells are all the same QoS trap, below.

### `ros2-dev`

| Rung | Mechanisms | Result |
| :--- | :--- | ---: |
| L1 | a Nav2 parameter file the servers accept as-is | **0/10 on the load check** — see below |
| L2 | + the stack driven through lifecycle to `active` | **30/30** |
| L3 | + a costmap ingesting live scan data and marking obstacles | **20/20** |

---

## The one recurring trap: QoS reliability

Four rounds, four appearances, always identical: an rclpy subscriber left at the
default RELIABLE against a BEST_EFFORT sensor publisher. The callback never
fires and the node sits until it times out.

| Round | Cells lost |
| :--- | ---: |
| `qos1` (a plain `/sensor` subscriber) | 5/10 |
| `per1` (camera image) | 1/10 |
| `per2` (image + camera_info) | 1/10 |
| `per3` (depth image + camera_info) | 2/10 |

It is **not silent**. Jazzy logs it explicitly:

```
New publisher discovered on topic '/sensor', offering incompatible QoS.
No messages will be received from it. Last incompatible policy: RELIABILITY
```

And the `qos1` diagnosis showed the split is not about QoS knowledge:

| Cell behaviour | Outcome |
| :--- | :--- |
| ran its own node before finishing | **all passed** |
| wrote the file and stopped | **all failed** |

One passing cell never looked up the publisher's QoS at all — it ran the node,
read the warning, and fixed it.

---

## `dev1` vs `dev2`: the same wrong belief, opposite outcomes

`dev1` asks for a Nav2 parameter file "loadable by the Nav2 servers as-is".
**Ten of ten cells** wrote a file that is valid YAML, names
`nav2_mppi_controller::MPPIController` correctly, puts `robot_radius: 0.3` in
exactly the right place — and set

    controller_server.FollowPath.CostCritic.consider_footprint: true

on which Nav2's own `controller_server` refuses to configure:

```
Original error: Considering footprint in collision checking but
no robot footprint provided in the costmap.
```

Cause isolated by controlled experiment, not inferred: flipping **only** that
boolean on an otherwise working file reproduces the failure exactly
(`unconfigured [1]`, identical error). A circular footprint declared through
`robot_radius` provides no polygon, and the cost critic requires one.

`dev2` adds one thing: the stack must reach `active`. **Every dev2 cell hit the
identical error** — it appears 1 to 6 times per transcript, with
`consider_footprint` discussed 8 to 12 times — diagnosed it, set the flag to
`false`, and passed.

This was briefly recorded as the project's first domain-knowledge gap. **That
was wrong**, and `dev2` is the control that settles it: given a reason to
execute, the model finds and fixes this in one sitting. The information content
of the two prompts is the same; only the demand to run differs.

---

## Silent-failure facts about Jazzy found while building the fixtures

Not model gaps — several of these caught *me*, the fixture author, and the cells
cleared them. Recorded because each fails without an error.

- `controller_manager` reads `robot_description` from the **topic**, not a
  parameter; as a parameter it waits forever logging
  `Waiting for data on 'robot_description' topic`. (Cells: 30/30.)
- `--params-file` without `--ros-args` is **ignored**, surfacing much later as
  `The 'type' param was not defined for 'joint_state_broadcaster'`. (Cells: 30/30.)
- `hardware_interface::SystemInterface` derives from `HardwareComponentInterface`
  on this install, and `on_init(const HardwareInfo&)` is **deprecated** in favour
  of `on_init(const HardwareComponentInterfaceParams&)`. (Cells: 40/40.)
- MoveIt planning-pipeline parameters are namespaced under the pipeline name
  (`ompl.planning_plugins`), and `joint_limits.yaml` under
  `robot_description_planning`. (Cells: 30/30.)
- A URDF with **no acceleration limits** makes MoveIt's
  `AddTimeOptimalParameterization` adapter fail, so a computed geometric path is
  returned and labelled `FAILURE` (99999).
- **Nav2 costmaps refuse to ACTIVATE without a TF chain** — the lifecycle manager
  reports `Failed to change state` after 60 s with no other explanation.
- Nav2 lifecycle nodes do not resolve plugin strings until `configure`, so a
  controller plugin missing its package namespace starts up looking healthy.
- `ros2 topic echo` **auto-negotiates QoS** and therefore cannot detect a
  reliability mismatch; a real rclpy subscriber is required.
- `colcon test` **exits 0 with zero tests registered**, and discovers no tests at
  all in an `ament_python` package whose `setup.py` omits `tests_require`.
- Missing `<export><build_type>ament_cmake</build_type></export>` makes colcon
  treat the package as catkin: build exits 0, `ros2 run` cannot find it.
- `rclpy.spin()` in a thread grabs the **global** default executor, so a later
  `spin_once()` raises `Executor is already spinning`.
- `ogre2` segfaults headless on this WSL2 machine, inside
  `Ogre::Hlms::createDatablock`.
- `set -u` + `source /opt/ros/jazzy/setup.bash` aborts on
  `AMENT_TRACE_SETUP_FILES: unbound variable`.
- `ros2 topic echo` prints float arrays as YAML block sequences, not inline
  `[a, b, c]`.

---

## What this measures about the graders, not the model

Ten grader defects surfaced during these rounds. **Every one was mine.** Cells
scored as total failures came back perfect when re-graded, and four of the
defects punished *good* engineering: isolating a DDS domain, guarding a bringup
against double-launch, cleaning up a temp directory, parameterising a value.

The tenth was the last to be caught, in the final rung: `dev3` also scored
`controller_active`, which the frozen prompt never asks for. Two cells reached
the costmap through a standalone `nav2_costmap_2d` node instead of a
controller_server — marking 12 and 325 lethal cells — and were failed for it.
The check was removed and the rung is 20/20.

They are listed in [`LADDER.md`](./LADDER.md). The reason they matter here: had
they been counted rather than opened, this pack would have gained paragraphs
about `launch_testing`, DDS domains, QoS probes, bag persistence, bringup
idempotence and Nav2 server topology — content for gaps the model does not have.
Opening every failing cell before counting it is the only reason that did not
happen.
