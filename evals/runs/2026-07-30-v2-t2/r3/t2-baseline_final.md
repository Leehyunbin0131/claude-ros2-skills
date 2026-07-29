# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.1463694
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-EhsI

## Final message

The working directory is empty — there's no repo, config, or logs here for me to inspect. So I can't pull your actual EKF/IMU setup automatically; I need either your config files or live data from the robot. Rather than guess at your stack, here's a protocol that turns "I think it's the IMU mount" into a number you can point at.

**Three tests, each falsifies or confirms a specific mounting failure mode:**

**1. Gravity vector test** (catches tilt or mislabeled axes)
Robot stationary, level ground. Echo raw IMU acceleration (`/imu/data_raw` or equivalent) for a few seconds, average `ax, ay, az`.
- Expect: `|az| ≈ 9.8`, `ax ≈ ay ≈ 0` (within ~0.2 m/s² noise).
- If `ax` or `ay` is significantly nonzero, the IMU is physically tilted or its axes are mislabeled in the driver. Compute the tilt angle directly: `atan2(sqrt(ax²+ay²), az)`. That's a number, not a hunch.

**2. Yaw sign/axis test** (catches inverted or swapped axes — the classic cause of "spins on the spot")
Pick the robot up or free-wheel it, rotate the chassis by hand exactly 90° CCW as viewed from above, no translation.
- Watch `angular_velocity.z` during the motion — should stay positive throughout (REP-103: CCW+ about Z), and `angular_velocity.x/y` should stay near zero.
- Separately, drive+turn on the ground and compare the sign of wheel-odometry heading change against IMU yaw change for the same physical turn.
- If the IMU's sign is opposite the wheel-encoder-implied sign, or x/y angular velocity spike during a pure yaw motion, that's direct proof of an axis swap/inversion in the mount or the driver's frame convention.

**3. Lever-arm / centripetal coupling test** (catches an off-center mount — explains drift *and* spin together)
Command pure in-place rotation (angular.z only, linear.x = 0) for ~5s. Confirm on wheel encoders that net translation is ~0.
- Log `linear_acceleration.x/y` from the IMU during this — nonzero radial/tangential acceleration here means the IMU sits off the rotation center by some radius `r` (centripetal = ω²r).
- Then check `/odometry/filtered` (or your EKF's output) position during the same window. If position drifts away from origin during a confirmed-zero-translation rotation, the EKF is absorbing that false acceleration into velocity/position — this is usually what causes both symptoms: drift accumulates from the false accel, and the spin comes from the EKF's heading estimate reacting to it (or a controller trying to correct a phantom lateral error).

**Fastest path if you can share files instead:** paste your `ekf.yaml` (or equivalent EKF node config, especially the `imuX_config` fusion flags) and the static transform / URDF joint for `base_link → imu_link`. A wrong sign or swapped axis in that transform, or linear acceleration being fused directly into position (very common misconfiguration, independent of mounting), is visible by inspection in seconds — no hardware run needed.

Tell me which stack you're on (ROS1/ROS2, `robot_localization` or custom EKF) and paste whatever config/topic-echo output you have, and I'll pin down the exact failure from the numbers.
