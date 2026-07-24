---
name: ros2-dev
description: "Nav2 & SLAM: AMCL, costmaps, MPPI/DWB/Smac plugins, behavior trees, SLAM Toolbox, RTAB-Map, Isaac ROS VSLAM, docking."
---

# Nav2 & SLAM Development Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Core Principles & Distro Awareness
- **Target OS & ROS Distro**: **Ubuntu 24.04 LTS & ROS 2 Jazzy Jalisco** (Primary target; verify active `$ROS_DISTRO` in shell).
- **Zero-Hallucination Policy**: Never speculate about Nav2 parameter names, YAML structures, Behavior Tree XML tags, or C++ plugin class names. Always reference official Nav2 documentation links or local `/opt/ros/$ROS_DISTRO/share/` package files.

## 2. Dedicated Nav2 Component Reference Catalogs
Fetch these exact documentation pages when configuring or developing Nav2:

### A. Master Navigation Portals
- **Official Nav2 User & Configuration Guide**: `https://docs.nav2.org/`
- **Nav2 Configuration Master Index**: `https://docs.nav2.org/configuration/index.html`
- **First-Time Robot Setup Guide**: `https://docs.nav2.org/setup_guides/index.html`
- **General Nav2 Tutorials Index**: `https://docs.nav2.org/tutorials/index.html`

### B. SLAM & Visual SLAM (2D LiDAR SLAM & VSLAM)
Refer to these pages when performing simultaneous localization and mapping with LiDAR or Cameras:
- **Nav2 with SLAM Master Tutorial**: `https://docs.nav2.org/tutorials/docs/navigation2_with_slam.html`
  - *Description*: Launching online async SLAM (`slam_toolbox`) concurrently with Nav2, dynamic map building, and Rviz visualization.
- **SLAM Toolbox Configuration (Default 2D LiDAR SLAM)**: `https://github.com/SteveMacenski/slam_toolbox`
  - *Description*: Lifecycled SLAM node (`async` / `sync` mode), solver parameters (`ceres_solver`), loop closure detection, graph optimization, `.posegraph` serialization/saving, dynamic map expansion.
- **Visual SLAM (NVIDIA Isaac ROS Visual SLAM - Stereo/VIO)**: `https://nvidia-isaac-ros.github.io/concepts/visual_slam/index.html`
  - *Description*: Hardware-accelerated stereo camera VIO/VSLAM for ROS 2, publishing high-accuracy `odom` -> `base_link` visual odometry and landmark points.
- **RTAB-Map (RGB-D / Stereo / 3D LiDAR Graph-Based SLAM)**: `https://introlab.github.io/rtabmap/`
  - *Description*: Graph-based visual & 3D LiDAR SLAM (`rtabmap_slam`), memory management, loop closure detection, publishing 2D occupancy grids (`/map`) for Nav2 costmaps.
- **Map Server & Saver Configuration**: `https://docs.nav2.org/configuration/packages/configuring-map-server.html`
  - *Description*: Serving 2D grid maps (`.yaml`/`.pgm`), saving generated maps via `ros2 run nav2_map_server map_saver_cli -f my_map`.

### C. Localization & AMCL
- **AMCL Configuration Guide**: `https://docs.nav2.org/configuration/packages/configuring-amcl.html`
  - *Description*: Particle filter parameters, initial pose, scan matching, particle count (`min_particles`, `max_particles`), laser model (`likelihood_field` / `beam`).

### D. Environmental Representation (Costmap 2D)
- **Costmap 2D Configuration Guide**: `https://docs.nav2.org/configuration/packages/configuring-costmaps.html`
  - *Description*: Global and Local costmaps, resolution, update/publish frequency, footprint, inflation layer (`inflation_radius`, `cost_scaling_factor`), obstacle layer, voxel layer, static layer, and costmap filters.

### E. Controller Server & Path Following Plugins
- **Controller Server Main Guide**: `https://docs.nav2.org/configuration/packages/configuring-controller-server.html`
  - *Description*: Controller server parameters, progress checkers (`SimpleProgressChecker`), goal checkers (`StoppedGoalChecker`, `SimpleGoalChecker`).
- **MPPI Controller Plugin**: `https://docs.nav2.org/configuration/packages/configuring-mppic.html`
  - *Description*: Model Predictive Path Integral controller, critics (`GoalCritic`, `PathAlignCritic`, `ObstaclesCritic`, `PreferForwardCritic`), model types (`DiffDrive`, `Ackermann`, `Omni`).
- **DWB Local Planner Plugin**: `https://docs.nav2.org/configuration/packages/configuring-dwb-controller.html`
- **Regulated Pure Pursuit Plugin**: `https://docs.nav2.org/configuration/packages/configuring-regulated-pp.html`
- **Rotation Shim Controller Plugin**: `https://docs.nav2.org/configuration/packages/configuring-rotation-shim-controller.html`

### F. Planner Server & Global Path Planning Plugins
- **Planner Server Main Guide**: `https://docs.nav2.org/configuration/packages/configuring-planner-server.html`
- **Smac Planner (2D A*, Hybrid-A*, State Lattice)**: `https://docs.nav2.org/configuration/packages/configuring-smac-planner.html`
  - *Description*: SmacPlanner2D, SmacPlannerHybrid (for ackermann/cars), SmacPlannerLattice.
- **NavFn Planner Plugin**: `https://docs.nav2.org/configuration/packages/configuring-navfn.html`
- **Theta Star Planner Plugin**: `https://docs.nav2.org/configuration/packages/configuring-thetastar.html`

### G. Behavior Trees & BT Navigator
- **BT Navigator Configuration**: `https://docs.nav2.org/configuration/packages/configuring-bt-navigator.html`
  - *Description*: `nav2_bt_navigator` node parameters, default behavior tree XML paths, plugin libraries.
- **Behavior Tree XML Nodes Guide**: `https://docs.nav2.org/configuration/packages/configuring-bt-xml.html`
  - *Description*: Action nodes (`ComputePathToPose`, `FollowPath`, `Spin`, `BackUp`, `Wait`), Condition nodes (`IsStuck`, `GoalReached`), Control nodes (`PipelineSequence`, `RecoveryNode`), Decorator nodes (`RateController`, `DistanceController`).

### H. Collision Monitor & Velocity Smoother
- **Collision Monitor Configuration**: `https://docs.nav2.org/configuration/packages/configuring-collision-monitor.html`
- **Velocity Smoother Configuration**: `https://docs.nav2.org/configuration/packages/configuring-velocity-smoother.html`

### I. Docking & Waypoint Following
- **Docking Server Configuration**: `https://docs.nav2.org/configuration/packages/configuring-docking-server.html`
  - *Description*: Pre-dock pose, docking plugins, perception alignment, charging contact validation.
- **Waypoint Follower Configuration**: `https://docs.nav2.org/configuration/packages/configuring-waypoint-follower.html`

### J. C++ Doxygen API Reference (For Low-Level C++ Code)
- **Nav2 C++ API Reference**: `https://api.nav2.org/nav2-jazzy/html/`

## 3. Local Ground Truth Verification
Check local installed package definitions under `/opt/ros/$ROS_DISTRO/share/`:
- **Default Nav2 YAML Params**: `/opt/ros/$ROS_DISTRO/share/nav2_bringup/params/nav2_params.yaml`
- **Default BT XML Files**: `/opt/ros/$ROS_DISTRO/share/nav2_bt_navigator/behavior_trees/`

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Action goals return `Goal rejected` / freeze while topics look fine | Lifecycle servers stuck `unconfigured`/`inactive` | `ros2 lifecycle get /controller_server` etc.; check `nav2_lifecycle_manager` `node_names` covers all servers |
| `Timed out waiting for transform` / extrapolation errors | `use_sim_time` inconsistent across nodes, or `map->odom` publisher missing | Verify every node's `use_sim_time`; confirm exactly ONE of AMCL/SLAM publishes `map->odom` |
| Costmap empty even though `/map` is published | QoS mismatch: map_server publishes `transient_local`, subscriber uses volatile durability | Set subscriber durability to `transient_local`; check `ros2 topic info /map -v` |
| Obstacles appear but never clear from costmap | `raytrace_max_range` <= `obstacle_max_range` in obstacle layer | Set raytrace range slightly larger than obstacle range |
| "No valid trajectory" / robot refuses to move near obstacles | Inflation too large for footprint, or velocity limits effectively zero | Compare `inflation_radius` + `footprint` vs corridor width; check `min_vel_x`/`max_vel_x` actually nonzero |
| AMCL pose diverges while driving | Odometry noise params unrealistic, or initial pose never set | Set initial pose; sanity-check odom quality first (`scripts/check_odom_direction.py`), then tune `alpha1-4` |
| MPPI oscillates / prefers reversing | Critic weights: `PreferForwardCritic` too weak vs `PathAlignCritic` | Raise `PreferForwardCritic.cost_weight`; verify with default `nav2_params.yaml` as baseline |
| Path planned through walls | Static layer not enabled in global costmap, or wrong `map_topic` | Check global costmap `plugins` list includes static layer and its `map_topic` |

## 5. Tuning Baselines (start here, then adjust in the stated direction)

Baseline = shipped defaults in `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml` — always diff against that file, not memory.

### A. AMCL
| Param | Baseline | Symptom -> direction |
| :--- | :--- | :--- |
| `alpha1`..`alpha4` (odom noise) | 0.2 each | Pose lags/overtrusts bad odom -> raise toward 0.4. Good wheel odom but pose jitters -> lower toward 0.1. Fix odometry first (`scripts/check_odom_direction.py`) — alphas cannot repair inverted/scaled odom. |
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
3. Before tuning Nav2, verify odometry and TF physically: `python3 scripts/check_odom_direction.py`, `python3 scripts/check_tf_tree.py --sensors laser_frame` (see `ros2-troubleshooting`).
