# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.1276774
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-k37Y

## Final message

The working directory here is empty — no ROS files, URDF, or bag data for me to inspect directly. So this needs to be settled with data from your actual system, and I can tell you exactly what to pull to get an unambiguous verdict rather than a guess.

**The single most decisive test (30 seconds, no math needed):**

Put the robot dead still on a flat, level surface and echo the raw IMU topic:
```
ros2 topic echo /imu/data --once      # or rostopic echo /imu/data -n1
```
Look at `linear_acceleration`. At rest, gravity (~9.81 m/s², sign depends on your convention) should appear almost entirely on whichever axis your URDF/static transform declares as "up" (Z, per REP-103). 

- If ~9.81 shows up on X or Y instead of Z → the IMU is physically rotated 90° from what the code thinks. **Proof, not inference.**
- If Z reads something like 7–8 with nonzero X/Y (e.g. X≈3, Z≈9) → it's mounted tilted, not flat. Roll/pitch = `atan2` of those components gives you the exact tilt angle.
- If Z is clean ~9.81 and X/Y ≈ 0 → mounting orientation is fine; drift/spin has a different cause (see below).

**Second test — axis mapping under rotation (rules out sign/axis swap):**

Manually rotate the robot exactly 90° CW about its vertical axis (use a printed protractor or a jig, not by eye) and watch `angular_velocity.z` during the turn and the integrated yaw in `/imu/data` or your AHRS output before/after.
- Rotation should show up almost purely on `angular_velocity.z`, near-zero on x/y.
- The yaw change should be +90° or -90° matching REP-103 (CCW positive, viewed from above) — flipped sign here is a classic "IMU mounted upside-down" signature, and it explains spin-in-place perfectly: the EKF sees yaw-rate with the wrong sign relative to wheel odometry's yaw-rate, the two sources fight, and the filter's state estimate spins even though the robot barely moves.

**Third test — cross-check the declared transform against reality:**
```
ros2 run tf2_ros tf2_echo base_link imu_link
```
Compare that RPY to how the sensor is *actually* bolted on (check the axis arrows silkscreened on the IMU board against the chassis). A mismatch here — even a small one, like 5-10° — combined with `two_d_mode: true` and `imu0_remove_gravitational_acceleration: true` in your EKF config will bleed a fake angular rate into yaw during linear acceleration, which reads exactly like "drifts and spins in place" while every topic still looks perfectly healthy.

**If all three come back clean** (gravity on Z, rotation isolated to z, tf matches physical mount), the mounting hypothesis is dead and I'd look next at: gyro bias not calibrated (log `angular_velocity.z` for 60s stationary — should average ~0, not something like 0.01-0.05 rad/s), or your `imu0_config` matrix fusing IMU absolute yaw against wheel-odometry yaw with clashing covariances.

If you paste the output of the stationary `linear_acceleration` echo, the `tf2_echo base_link imu_link` result, and your `ekf.yaml`'s `imu0_config`/`imu0_remove_gravitational_acceleration` lines, I can tell you definitively whether it's the mount or something else — happy to also review the actual files if you point me at the repo/workspace path.
