# What the baseline agent reaches unaided, and where it stops

A historical capability report, followed by a reconciliation against the
committed evidence. **The published tables below are not all reproducible from
this checkout.** Some transcripts were deleted and some claimed re-grades were
never committed. They do not establish that every mechanism passed, that every
failure was behavioural, or that the current release improves agent performance.
Use the [reconciliation](#reconciliation-published-numbers-vs-the-committed-record)
before citing any score.

**How to read it.** The historical rung scores are *checks passing / checks run*, `baseline`
only: no skills, no `CLAUDE.md`, model knowledge + web search + a live ROS 2
Jazzy install. Ten cells per rung. **A rung fails at ≤ 7/10 cells.** Method and
anti-manufacturing rules: [`LADDER.md`](./LADDER.md).

Several rung numbers below include re-grades that are **not in the committed
record**; [Reconciliation](#reconciliation-published-numbers-vs-the-committed-record)
sets each one beside what `harness/analyze_v2.py` reproduces from `runs/`.

---

## Historical interpretation

The original report interpreted eight ladders and 24 rungs as favouring
execution and verification over additional domain prose. That is a historical
interpretation of these tasks and models, not a general result about ROS 2
agents. Four reported observations motivated the current verification tools:

| What the model does not do unaided | Baseline | What closes it | After |
| :--- | ---: | :--- | ---: |
| Verify against the install instead of answering from memory | **2/10** | one paragraph of `CLAUDE.md` | **10/10** (q=0.002) |
| Produce an exit-coded pass/fail verdict rather than "looks right" | **0/10** | a bundled runnable script | **10/10** (q<0.001) |
| Run the QoS code it writes before shipping it | **5/10** | `CLAUDE.md`'s "Done means it ran" | **9/10** (q=0.141, underpowered) |
| Run the Nav2 config it writes before shipping it | **0/10** | a task that requires reaching `active` | **30/30** |

The first three comparisons cannot be re-run from committed transcripts. The
last row compares different prompts and tasks, and its committed `dev2` verdicts
are 27/27 across nine gradable cells, with one missing verdict. It suggests a
useful execution workflow but is not a controlled estimate of a skill's effect.
These observations motivated keeping the protocol and executable checks; they
do not prove that domain prose can never help.

---

## Historically reported rung results

Scores in this section are preserved as originally published. See the reconciliation for available evidence and missing re-grades.

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

The original analysis attributed four missing cells to the QoS trap below; the committed verdicts contain additional failures and a probe race.

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

`dev2` instead requires bringing the stack to `active`. The original analysis
reported that the cells encountered and corrected this error. The committed
record has nine passing verdicts and one missing verdict; it cannot substantiate
a ten-cell perfect score.

This motivates checking lifecycle transitions during development. Because the
prompts request different deliverables, the comparison does not isolate the
causal effect of an instruction or rule, and does not settle whether other
domain knowledge would help.

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

Ten grader defects surfaced during these rounds. **Every one was mine.** The original report says cells
scored as total failures passed after re-grading, and four of the
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
idempotence and Nav2 server topology — content whose benefit would still need a valid measurement.
Opening every failing cell before counting it is the only reason that did not
happen.

---

## Reconciliation: published numbers vs the committed record

The rung numbers above were read after failing cells had been opened and, where
the grader was at fault, re-graded — mostly from workspaces preserved in `/tmp`
at the time. Those re-graded verdicts were never committed, and the workspaces
are gone. So `python3 harness/analyze_v2.py runs/<round>` on the committed
verdict files does not reproduce every number above. Both are recorded here;
neither is edited to match the other. `harness/test_harness.py` pins the
committed column.

| Rung | Published above | Committed verdicts (`analyze_v2.py`) | What the repository records about the difference |
| :--- | ---: | :--- | :--- |
| `ctl2` | 20/20 | **12/16** — r5, r6 fail both checks; r7, r8 left no verdict (ungradable) | grader defects #2 and #4 in [`LADDER.md`](./LADDER.md#the-l2-rounds-real-finding-six-grader-defects-one-root-cause); the post-fix re-grade is not committed. r7's own transcript reports parallel cells colliding on one DDS domain. |
| `tst2` | 40/40 | 39/40 — `tst2_launch_testing` 9/10 (r9) | re-grade argued in [`LADDER.md`](./LADDER.md#a-grader-defect-found-by-reading-a-failing-cell-instead-of-counting-it) (5 of 10 workspaces re-verified) |
| `tst3` | 40/40 | **33/40 — `tst3_bag_written` 3/10** (r1–r7: `n_bags 0`) | only the general note above ("cleaning up a temp directory" punished good engineering); **no per-cell record**. On the committed record alone this rung fails the ≤ 7/10 threshold. |
| `mvt2` | 30/30 | **23/30 — `mvt2_move_group_up` 7/10** (r4, r7, r9); plan/points 8/10 (r7, r9) | grader defects #5 and #6 in `LADDER.md`; #6's fix is recorded there as "queued, not yet applied", and the re-grade is not committed. At the threshold on the committed record. |
| `per2` | 38/40 | 34/40 — r8 fails all four; r10 fails `detection_published`/`_correct` | grader defect #3 (probe discovery race). The first attempt is kept, set aside, as `per2-SUPERSEDED-grader-race/`; the r10 re-grade is not committed. |
| `per3` | 32/40 | **28/40 — 7/10 on every check** (r3, r5: the QoS trap; r4) | r4 logged 20 correct `CLOUD 15360` lines and exited 0, yet the probe saw no cloud (`n_clouds_seen 0`) — the per2 probe race again. Published counts r4 as a pass; that re-grade is not committed. At the threshold on the committed record. |
| `dev2` | 30/30 | 27/27 — r4 left no verdict (ungradable) | not recorded |
| `mvt1` | 30/30 | 30/30 | matches once `mvt1-DISCARDED-mid-round-edit/` is excluded; the analyzer used to pool it and print 12/12 |
| all other committed rungs | — | match | `ctl1`, `ctl3`, `tst1`, `mvt3`, `per1`, `cor1`–`cor3`, `dev1`, `dev3` |

By domain, the committed record gives `ros2_control` 82/86, Testing 102/110,
MoveIt 93/100 and Perception 98/120, against 90/90, 110/110, 100/100 and 106/120
above.

**Not in the repository at all:** the `ros2-package` (`t5`–`t7`), `gazebo-sim`
(`g1`–`g3`), executor (`tr1`–`tr3`) and `qos1` rounds, and the rounds behind
the first three rows of *Historical interpretation* (2/10 → 10/10, 0/10 → 10/10,
5/10 → 9/10). Their transcripts were deleted; the numbers are the surviving
record, not something this repository can reproduce.

This section re-decides nothing. It does not restore a deleted skill or change a
threshold, and it makes no new measurement. It records that for `tst3`, `mvt2`
and `per3` the committed record alone sits at or below the rung-failure
threshold, and that the published passes rest on re-grades whose evidence is no
longer here. Whether those rungs should be re-run is a separate decision that
would cost a paid round.

---

## What was done about it

Six skills were deleted in full on 2026-08-01 — `ros2-core`, `ros2-dev`,
`ros2-control`, `ros2-moveit`, `ros2-perception`, `ros2-testing` — joining
`ros2-package` and `gazebo-sim`, which had gone the same way earlier. Each had
a ladder the original report considered exhausted. Several of those conclusions
now require new evidence, as the reconciliation above explains.

The current contents mix historically reported effects with retained, unverified guidance:

| Kept | Why |
| :--- | :--- |
| `ros2-development` (new after these historical rounds) | package development workflow and a colcon test-evidence check, validated on real temporary Python/CMake packages; no controlled agent performance comparison yet |
| `CLAUDE.md`, 30 lines | the verify paragraph (2/10 → 10/10) and "done means it ran" |
| `ros2-troubleshooting` scripts | 0/10 → 10/10 on producing a checked verdict |
| `references/frames.md` | physical mount vs REP 103 — no ladder can test it without hardware, and no doc contains the robot's real geometry |
| `references/calibration.md` | same category, and nearly lost: `diff_drive_controller` wheel calibration was deleted with `ros2-control`, but `ctl1`–`ctl3` never tested it. Restored to the physical-verification skill that owns the script it cites. |
| `references/runtime.md`, QoS only | the one trap that recurred in four rounds; the other four sections were cut against their ladders |
| `ros2-microros` | no ladder is possible here; kept and **labelled unverified** in its own body |

The deletions retain the project's narrow scope. They do not prove that these
domains need no guidance. New content should address an observed development
failure and demonstrate a benefit with a valid comparison; execution and
verification remain the current product's focus.

**One thing was nearly lost to that reasoning, and it is worth recording as a
warning about it.** `ros2-control` carried a `diff_drive_controller` calibration
procedure — drive a tape-measured line, correct the radius multipliers, then
five turns in place for separation, in that order because separation does not
affect straight-line driving. The `ctl` ladder never tested it and could not:
no container has a floor. Deleting the skill deleted the procedure with it,
which is a cut made on an argument rather than a number — the exact move this
project reverted a whole reduction over. It is now
`ros2-troubleshooting/references/calibration.md`.

**Check a deleted file for unmeasured residue before deleting it.** An exhausted
ladder licenses removing what the ladder tested, not everything that shares a
file with it.

The other five deleted skills were swept the same way. Their residue splits into
two piles, and only the first was restored:

| Residue | Category | Action |
| :--- | :--- | :--- |
| `diff_drive_controller` calibration | unmeasured **and unmeasurable here** — needs a floor | restored to `calibration.md` |
| `LaserScan` valid-reading rule (finite and within `[range_min, range_max]`) | measurable in a container, never put on a rung | **recorded as a gap, not restored** |
| MoveIt kinematics/OMPL tuning baselines; Nav2 AMCL/costmap/MPPI/slam_toolbox baselines | same | **recorded as a gap, not restored** |
| `ros2-dev`'s "establish footprint, drive type, who publishes `map->odom`" | already in `CLAUDE.md`'s "Establish before writing" | correctly dropped, rule 2 |

The second pile is the honest coverage limit of this sweep. Those lines were
measured under the v1 method on **haiku**, which this project already found does
not transfer (proven on `ros2-perception`), and no `sonnet` ladder rung covers
them: `per1`–`per3` are camera, projection and depth; `cor1`–`cor3` are TF and
lifecycle; `tr1`–`tr3` are executors. Restoring them on the strength of a
haiku-era number would be the reverted reduction with a better bibliography —
so they stay out, and this table is where that decision is written down instead
of being invisible.
