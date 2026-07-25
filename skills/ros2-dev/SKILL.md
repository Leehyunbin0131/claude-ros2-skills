---
name: ros2-dev
description: "Nav2 & SLAM: AMCL, costmaps, MPPI/DWB/Smac plugins, behavior trees, SLAM Toolbox, RTAB-Map, Isaac ROS VSLAM, docking."
---

# Nav2 & SLAM Development Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Documentation Entry Points

Every Nav2 component page hangs off the configuration index — navigate from it instead of guessing deep URLs.

| For | Entry point |
| :--- | :--- |
| **Every Nav2 plugin/server config page** | `https://docs.nav2.org/configuration/index.html` |
| First-time robot bringup | `https://docs.nav2.org/setup_guides/index.html` |
| Tutorials (incl. SLAM + Nav2 together) | `https://docs.nav2.org/tutorials/index.html` |
| Nav2 C++ (Jazzy) Doxygen | `https://api.nav2.org/nav2-jazzy/html/` |
| SLAM Toolbox (not on docs.nav2.org) | `https://github.com/SteveMacenski/slam_toolbox` |
| RTAB-Map (RGB-D / 3D LiDAR graph SLAM) | `https://introlab.github.io/rtabmap/` |
| Isaac ROS Visual SLAM (stereo VIO) | `https://nvidia-isaac-ros.github.io/concepts/visual_slam/index.html` |

## 2. Local Ground Truth — diff against these, never against memory

- **Shipped Nav2 defaults**: `/opt/ros/$ROS_DISTRO/share/nav2_bringup/params/nav2_params.yaml`
- **Shipped BT XML**: `/opt/ros/$ROS_DISTRO/share/nav2_bt_navigator/behavior_trees/`

## 3. Symbols to Verify (never write these from memory)

**Plugin strings are fully namespaced** — the single most common startup-killing
error is dropping the package prefix (`nav2_mppi_controller::MPPIController`, not
`mppi_controller::MPPIController`). A wrong plugin string means the server loads
nothing and Nav2 dies at startup.

- **Controllers** — MPPI critics `GoalCritic`, `PathAlignCritic`, `ObstaclesCritic`, `PreferForwardCritic`; `motion_model` values `DiffDrive` / `Ackermann` / `Omni`. Also DWB, Regulated Pure Pursuit, Rotation Shim.
- **Progress / goal checkers** — `SimpleProgressChecker`, `SimpleGoalChecker`, `StoppedGoalChecker`. Plural `progress_checker_plugins` since Iron; singular `progress_checker_plugin` is a pre-Iron leftover.
- **Planners** — `SmacPlanner2D`, `SmacPlannerHybrid` (ackermann/car-like), `SmacPlannerLattice`, NavFn, Theta\*.
- **Costmap layers** — static, obstacle, voxel, inflation (`inflation_radius`, `cost_scaling_factor`); plus costmap filters.
- **AMCL** — `min_particles`/`max_particles`, laser model `likelihood_field` or `beam`, `alpha1`..`alpha4`.
- **BT nodes** — actions `ComputePathToPose`, `FollowPath`, `Spin`, `BackUp`, `Wait`; conditions `IsStuck`, `GoalReached`; controls `PipelineSequence`, `RecoveryNode`; decorators `RateController`, `DistanceController`.
- **SLAM** — `slam_toolbox` async/sync lifecycle node, `ceres_solver`, `.posegraph` serialization; `rtabmap_slam`; map saving via `ros2 run nav2_map_server map_saver_cli -f my_map`.
- **Also configurable**: collision monitor, velocity smoother, docking server, waypoint follower — all under the configuration index above.

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Action goals return `Goal rejected` / freeze while topics look fine | Lifecycle servers stuck `unconfigured`/`inactive` | `ros2 lifecycle get /controller_server` etc.; check `nav2_lifecycle_manager` `node_names` covers all servers |
| `Timed out waiting for transform` / extrapolation errors | `use_sim_time` inconsistent across nodes, or `map->odom` publisher missing | Verify every node's `use_sim_time`; confirm exactly ONE of AMCL/SLAM publishes `map->odom` |
| Costmap empty even though `/map` is published | QoS mismatch: map_server publishes `transient_local`, subscriber uses volatile durability | Set subscriber durability to `transient_local`; check `ros2 topic info /map -v` |
| Obstacles appear but never clear from costmap | `raytrace_max_range` <= `obstacle_max_range` in obstacle layer | Set raytrace range slightly larger than obstacle range |
| "No valid trajectory" / robot refuses to move near obstacles | Inflation too large for footprint, or velocity limits effectively zero | Compare `inflation_radius` + `footprint` vs corridor width; check `min_vel_x`/`max_vel_x` actually nonzero |
| AMCL pose diverges while driving | Odometry noise params unrealistic, or initial pose never set | Set initial pose; sanity-check odom quality first (`check_odom_direction.py`, bundled in `ros2-troubleshooting`), then tune `alpha1-4` |
| MPPI oscillates / prefers reversing | Critic weights: `PreferForwardCritic` too weak vs `PathAlignCritic` | Raise `PreferForwardCritic.cost_weight`; verify with default `nav2_params.yaml` as baseline |
| Path planned through walls | Static layer not enabled in global costmap, or wrong `map_topic` | Check global costmap `plugins` list includes static layer and its `map_topic` |

## 5. Tuning Baselines (start here, then adjust in the stated direction)

Baseline = shipped defaults in `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml` — always diff against that file, not memory.

### A. AMCL
| Param | Baseline | Symptom -> direction |
| :--- | :--- | :--- |
| `alpha1`..`alpha4` (odom noise) | 0.2 each | Pose lags/overtrusts bad odom -> raise toward 0.4. Good wheel odom but pose jitters -> lower toward 0.1. Fix odometry first (`check_odom_direction.py`) — alphas cannot repair inverted/scaled odom. |
| `min_particles` / `max_particles` | 500 / 2000 | Kidnapped-robot recovery poor or large map -> raise max to 5000 (CPU cost is linear). Small static map -> defaults are fine. |
| `update_min_d` / `update_min_a` | 0.25 m / 0.2 rad | Pose updates feel laggy -> lower both; CPU-bound -> raise. |
| `laser_max_beams` | 60 | Localization weak in feature-sparse corridors -> raise to 100-180; CPU-bound -> keep 60. |

### B. Costmaps
| Param | Baseline | Symptom -> direction |
| :--- | :--- | :--- |
| `resolution` | 0.05 m | Indoor default. Narrow gaps misjudged -> 0.025 (4x memory/CPU). Outdoor/large -> 0.1. |
| `inflation_radius` | 0.55 m | Must exceed robot inscribed radius + margin. Robot hugs obstacles -> raise; can't pass doorways -> lower toward inscribed radius + ~0.1 m. |
| `cost_scaling_factor` | 3.0 | Higher = cost decays faster = paths allowed closer to walls. Too timid in corridors -> raise toward 10; clipping corners -> lower. |
| local costmap size | 3 x 3 m | Faster robots need to see further: >= 2 x (max speed x controller horizon). |

### C. Controller (MPPI) & SLAM
- MPPI: tune ONE critic weight at a time from the shipped defaults; `PreferForwardCritic` up if it reverses unnecessarily, `PathAlignCritic` down if it refuses to deviate around obstacles. Re-baseline from the defaults file after any Nav2 upgrade — critic defaults shift between releases.
- slam_toolbox: `resolution: 0.05`; clamp `max_laser_range` to the LiDAR's *reliable* range (usually ~80% of datasheet); loop closure misfires in repetitive corridors -> raise `loop_match_minimum_response_fine`.

## 6. Strict Coding Rules
1. Never mix obsolete ROS 1 `move_base` or ROS 2 Foxy parameter names.
2. For SLAM, verify whether `slam_toolbox` or `rtabmap` is publishing the `map` -> `odom` transform to prevent double-transform conflicts.
3. Before tuning Nav2, verify odometry and TF physically with `check_odom_direction.py` and `check_tf_tree.py --sensors laser_frame` (bundled in `ros2-troubleshooting`).
