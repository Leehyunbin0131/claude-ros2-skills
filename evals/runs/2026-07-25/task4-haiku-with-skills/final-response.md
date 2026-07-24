Done. Saved `controller_server.yaml` with complete MPPI controller setup for differential-drive robots.

**Key configuration:**
- **Motion model**: DiffDrive (for differential-drive kinematics)
- **Controller**: nav2_mppi_controller::MPPIController with 56 time steps @ 0.05s per step
- **Velocity limits**: vx [−0.35, 0.5] m/s, wz max 1.9 rad/s
- **Eight critics** balanced for obstacle avoidance, path alignment, and goal reaching:
  - PathAlignCritic (weight 14.0) — keeps trajectory aligned to global path
  - GoalCritic (weight 5.0) — drives toward goal
  - PreferForwardCritic (weight 5.0) — favors forward motion over backing
  - CostCritic (weight 3.81) — collision avoidance
  - Others fine-tune angle alignment and constraint satisfaction

To use this, include it in your Nav2 launch file or merge its parameters into your full `nav2_params.yaml`. Adjust critic weights (particularly `PathAlignCritic` and `PreferForwardCritic`) if the robot oscillates or prefers reversing.
