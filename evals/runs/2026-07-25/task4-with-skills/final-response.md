Saved `controller_server.yaml`, sourced verbatim from the official `nav2_bringup` default params on the `jazzy` branch of `ros-navigation/navigation2` (verified live via GitHub raw, not memory).

Key points for your diff-drive robot:
- `motion_model: "DiffDrive"` — already correct, no `vy`/`ay` motion applied even though those fields are present (MPPI ignores lateral terms for this model).
- `vx_min: -0.35` allows reverse driving; set to `0.0` if you want forward-only.
- 8 critics enabled: `Constraint`, `Cost`, `Goal`, `GoalAngle`, `PathAlign`, `PathFollow`, `PathAngle`, `PreferForward`.
- Per the `ros2-dev` skill's tuning table: if the robot oscillates/reverses unnecessarily, raise `PreferForwardCritic.cost_weight` (currently 5.0); if it won't deviate around obstacles, lower `PathAlignCritic.cost_weight` (currently 14.0).

You'll still need `progress_checker`/`general_goal_checker` tolerances tuned to your robot's footprint, and this file only covers `controller_server` — planner, costmaps, etc. are separate.
