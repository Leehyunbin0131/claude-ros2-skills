# Nav2 & SLAM — entry points and verified symbol names

Load this when you need to name a plugin, critic, BT node, or config key.
Diff every value against the shipped defaults before writing:
`/opt/ros/$ROS_DISTRO/share/nav2_bringup/params/nav2_params.yaml`

## Documentation entry points

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

## Controllers

- **MPPI critics**: `GoalCritic`, `PathAlignCritic`, `ObstaclesCritic`, `PreferForwardCritic`
- **`motion_model`** values: `DiffDrive`, `Ackermann`, `Omni`
- Other controllers: DWB, Regulated Pure Pursuit, Rotation Shim
- **Progress / goal checkers**: `SimpleProgressChecker`, `SimpleGoalChecker`, `StoppedGoalChecker`.
  Plural `progress_checker_plugins` since Iron — singular `progress_checker_plugin` is a pre-Iron leftover.

## Planners

`SmacPlanner2D`, `SmacPlannerHybrid` (ackermann / car-like), `SmacPlannerLattice`, NavFn, Theta\*.

## Costmaps

Layers: static, obstacle, voxel, inflation (`inflation_radius`, `cost_scaling_factor`), plus costmap filters.

## AMCL

`min_particles` / `max_particles`, laser model `likelihood_field` or `beam`, `alpha1`..`alpha4`.

## Behavior trees

- Actions: `ComputePathToPose`, `FollowPath`, `Spin`, `BackUp`, `Wait`
- Conditions: `IsStuck`, `GoalReached`
- Controls: `PipelineSequence`, `RecoveryNode`
- Decorators: `RateController`, `DistanceController`

Shipped trees: `/opt/ros/$ROS_DISTRO/share/nav2_bt_navigator/behavior_trees/`

## SLAM

- `slam_toolbox` — async/sync lifecycle node, `ceres_solver`, `.posegraph` serialization
- `rtabmap_slam` — RGB-D / stereo / 3D LiDAR graph SLAM
- Map saving: `ros2 run nav2_map_server map_saver_cli -f my_map`

## Also configurable

Collision monitor, velocity smoother, docking server, waypoint follower — all under the configuration index above.
