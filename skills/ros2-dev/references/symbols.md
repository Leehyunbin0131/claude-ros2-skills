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

### MPPI (`nav2_mppi_controller::MPPIController`)

**The eight critics in the Jazzy defaults** — this exact list, no more, no less:

```yaml
critics: ["ConstraintCritic", "CostCritic", "GoalCritic",
          "GoalAngleCritic", "PathAlignCritic", "PathFollowCritic",
          "PathAngleCritic", "PreferForwardCritic"]
```

`ObstaclesCritic` exists in the source but is **not** in the shipped defaults —
Jazzy uses `CostCritic` instead. `KeepOutCritic` does not exist at all. Critic
blocks take `enabled` / `cost_power` / `cost_weight` (+ critic-specific keys);
they have **no `type:` field**.

**Parameter names are terse and easy to get wrong.** The real keys:

| Concept | Real key | Common wrong guess |
| :--- | :--- | :--- |
| max/min forward vel | `vx_max` / `vx_min` | `max_velocity_x`, `max_vel_x` |
| lateral / angular vel | `vy_max` / `wz_max` | `max_velocity_y`, `max_velocity_theta` |
| accelerations | `ax_max`, `ax_min`, `ay_max`, `ay_min`, `az_max` | `max_accel_x`, `max_decel_x` |
| sampling noise | `vx_std`, `vy_std`, `wz_std` | `noise_sigma_x` |
| drive kinematics | `motion_model` (`DiffDrive`/`Ackermann`/`Omni`) | `motion_model_type` |
| trajectory drawing | `visualize` | `visualize_trajectories` |
| turning radius | `AckermannConstraints.min_turning_r` | `min_turning_radius` |

Other real top-level keys: `time_steps`, `model_dt`, `batch_size`,
`iteration_count`, `prune_distance`, `transform_tolerance`, `temperature`,
`gamma`, `regenerate_noises`, `TrajectoryVisualizer`.

Velocity/acceleration limits belong **inside** the `FollowPath` block, not at
`controller_server` level.

### Other controllers
DWB, Regulated Pure Pursuit, Rotation Shim.

### Progress / goal checkers
`nav2_controller::SimpleProgressChecker`, `nav2_controller::SimpleGoalChecker`,
`nav2_controller::StoppedGoalChecker` — note the `nav2_controller::` namespace,
**not** `nav2_core::`. Keys are plural (`progress_checker_plugins`,
`goal_checker_plugins`) since Iron; singular `progress_checker_plugin` is a
pre-Iron leftover.

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
