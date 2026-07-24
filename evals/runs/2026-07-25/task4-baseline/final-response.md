Saved as `controller_server.yaml`. Key points for this diff-drive setup:

- **`motion_model: "DiffDrive"`** — constrains MPPI rollouts to forward/backward + rotation only (no strafing), matching your kinematics.
- **`vy_std: 0.0` / `vy_max: 0.0` / `ay_max: 0.0`** — lateral velocity/acceleration disabled since diff-drive robots can't move sideways.
- **`vx_min: -0.35`** — allows limited reverse motion; set to `0.0` if your robot/behavior tree shouldn't drive backward.
- **`AckermannConstraints`** is present but unused unless you switch `motion_model` to `"Ackermann"` — harmless to leave in.
- Critics include `PreferForwardCritic` (penalizes reversing) and `PathAngleCritic`/`PathAlignCritic` for smooth path tracking — common choices for diff-drive.
- `TwirlingCritic` is commented out — enable it if you see the robot oscillating/spinning in place unnecessarily.

Tune `vx_max`, `wz_max`, `ax_max`, `az_max` to your robot's actual max linear/angular velocity and acceleration limits — these values are reasonable defaults for a small-to-mid indoor robot but not universal. Also make sure `controller_frequency` here matches (or divides evenly into) your BT navigator/costmap update rates.
