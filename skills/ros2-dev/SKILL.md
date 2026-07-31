---
name: ros2-dev
description: "Nav2 & SLAM: AMCL, costmaps, MPPI/DWB/Smac plugins, behavior trees, SLAM Toolbox, RTAB-Map, Isaac ROS, docking. Establish the robot-specific facts no doc can supply, then diff every value against the shipped defaults."
---

# Nav2 & SLAM

## Establish first (Nav2-specific)

Nav2 config is only correct relative to a specific robot. Ask if unstated:

- **Footprint / inscribed radius** — `inflation_radius` and every "won't fit
  through the door" complaint depend on it. A default copied from a tutorial
  robot is the most common root cause of bad navigation.
- **Drive type** — diff / omni / ackermann. Sets `motion_model` and rules out
  planners (car-like needs `SmacPlannerHybrid`).
- **Who publishes `map -> odom`** — AMCL, SLAM Toolbox, or RTAB-Map. Exactly
  one may. Two is a silent conflict, not an error.
- **Modifying an existing `nav2_params.yaml` or starting fresh?** A wholesale
  replacement silently drops values already tuned into it.

## Verify against the install, not memory

Baseline for every value you write is the shipped file, never recollection:
`/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml`. Change one value
at a time from it. Before trusting a plugin string, a critic name, or a
parameter key, diff it against that file or `references/symbols.md`.

Prove Nav2 works by outcome, not by the YAML looking right: every lifecycle
server `active` (`ros2 lifecycle get /controller_server`), a goal accepted,
the robot actually moving. Bad odometry cannot be fixed by tuning — verify it
physically first with `ros2-troubleshooting`'s `check_odom_direction.py` /
`check_tf_tree.py`.

## The one trap that kills a server at startup silently

Plugin strings are fully namespaced. Dropping the package prefix loads
nothing and the controller server simply doesn't come up:

```yaml
plugin: "nav2_mppi_controller::MPPIController"   # correct
plugin: "mppi_controller::MPPIController"        # loads nothing
```

## References (load only when you need them)

- **`references/symbols.md`** — plugin/critic/planner/BT node names, costmap
  layers, SLAM packages, doc entry points. Read before naming anything.
- **`references/tuning.md`** — AMCL, costmap, MPPI and slam_toolbox baselines
  with tune-in-this-direction guidance. Read when the robot moves but behaves
  badly.

## Rules

1. Never mix ROS 1 `move_base` or Foxy parameter names into Jazzy config.
2. Exactly one node publishes `map -> odom`. Verify which before adding
   another localization source.
3. Never tune Nav2 in simulation alone — it uses ideal kinematics; re-verify
   on hardware.
