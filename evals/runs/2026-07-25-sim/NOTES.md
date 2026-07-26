<!-- Detailed write-up for this run. The summary that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Simulation run — 2026-07-25 (Gazebo Harmonic, headless)

The last gap: "0 invented keys" proves the YAML is *spelled* correctly, not
that a robot obeys it. So both Task 4 outputs from the container run were
loaded into a live simulation. Environment: `osrf/ros:jazzy-desktop` container
+ `ros-jazzy-nav2-bringup`, `ros-jazzy-nav2-minimal-tb3-sim`, `ros_gz`
(Gazebo Sim 8.11), `gz sim` server-only (no GUI, software rendering).
Each YAML was spliced verbatim into the shipped `nav2_params.yaml` — the
`controller_server:` section replaced wholesale — and launched with
`nav2_bringup tb3_simulation_launch.py headless:=True`. Artifacts (params
files, launch logs) in [`runs/2026-07-25-sim/`](./).

## A/B: do the two YAMLs actually drive a robot?

| | Baseline YAML | With-skills YAML |
| :--- | :--- | :--- |
| Controller plugin load | **`[FATAL] Failed to create controller … class mppi_generic::ControllerServer … does not exist`** — Nav2 aborts bringup; nothing ever moves | `Created controller : FollowPath of type nav2_mppi_controller::MPPIController`, all **8 critics loaded** |
| `NavigateToPose` (−2.0, −0.5) → (0.5, 0.5) | unreachable — no controller server | **`Goal finished with status: SUCCEEDED`**; final AMCL pose (0.15, 0.53), inside the goal checker's tolerance |
| Sensor pipeline during the run | — | `/scan` 5 Hz, `/odom` 28 Hz through `ros_gz_bridge`, MPPI consuming both |

One incident during with-skills bringup, honestly noted: `global_costmap`
activation timed out on its first attempt because the operator (this session)
published the AMCL initial pose *after* the 60 s activation window — a launch
sequencing issue, not a parameter issue. After publishing the pose and
re-activating the remaining lifecycle nodes, the same params file ran to
`SUCCEEDED` with no further intervention. The baseline failure, by contrast,
is unrecoverable: the plugin class it names does not exist in the registry.

## Verification scripts against live data — first time

Until now `skills/ros2-troubleshooting/scripts/` had only pure-logic unit
tests. Run against the live simulation:

| Script | Result | What it means |
| :--- | :--- | :--- |
| `check_tf_tree.py --sensors base_scan` | **[OK]** — resolved `map → odom → base_link`, printed the real TB3 mount (x −0.064 m, z +0.122 m, level) | works on a live tree |
| `check_tf_tree.py --sensors rear_lidar` (Task 2 scenario: static TF published with roll 180°, yaw 180°) | **flagged both**: "declared UPSIDE-DOWN … declared FACING BACKWARD … If the sensor is NOT physically mounted that way, this TF is the bug" | the Task 2 diagnostic works end to end |
| `check_qos_compat.py --topic /scan` | **[PASS] × 4** endpoint pairs (`ros_gz_bridge` → amcl, collision_monitor, both costmaps) | live endpoint introspection works |
| `check_odom_direction.py` while driving forward | **[PASS]** "+1.64 m along the initial heading" over a 14 s non-interactive window — sign and magnitude match the commanded forward motion ([`odom_check2.log`](./odom_check2.log)) | direction logic confirmed against real motion |
| `check_imu_gravity.py --topic /imu` | **[FAIL]** `|a| = 0.01` — and that verdict is *correct*: the sim's IMU publishes gravity-free acceleration, which violates the REP 103/145 expectation the script tests (gravity must appear as ~+9.81 m/s² on +Z at rest) | the check catches a genuinely non-physical sensor config, which is its job |

**Defect found and fixed.** `check_odom_direction.py` blocked on `input()` and
died with `EOFError` when run without a terminal — unusable headless/CI. Fixed
in the same commit: `--wait-secs N` for non-interactive use, and a closed-stdin
fallback that waits instead of crashing. Re-verified in the sim ([PASS],
`odom_check2.log`) and the pure-logic unit tests still pass (7 groups).

## What the simulation run establishes

1. **The chain is now closed end to end**: skill → gate questions → read the
   installed defaults → 0 invented keys → plugin loads → **robot reaches the
   goal**. Every link measured, none assumed.
2. **The baseline's ~16 invented keys were never the whole story** — its single
   wrong plugin string alone kills the entire Nav2 stack at bringup, before any
   other key is even parsed.
3. **The verification scripts survived first contact with live data**, caught a
   real non-physical sensor config, and the one defect the exercise exposed was
   in *our* tooling — found because we ran it, fixed, and re-verified.

---
