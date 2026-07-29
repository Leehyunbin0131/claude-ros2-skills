# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.1065594
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-kXqo/ 2>&1

## Final message

There's nothing in this working directory to inspect — no repo, no configs, no bag files. To "settle it with evidence" I need actual data from your system, not code I can read locally. Here's the fastest path to a smoking gun, plus what to send me.

## The three checks that actually distinguish "IMU mounted wrong" from other causes

**1. Static gravity vector test (kills or confirms the mounting theory in 10 seconds)**

With the robot sitting still on a level surface:

```
ros2 topic echo /imu/data --once      # or rostopic echo -n1 for ROS1
```

Look at `linear_acceleration`. If the IMU's declared frame (per your URDF) has Z-up, X-forward, you should see approximately `(0, 0, ±9.81)`. 

- If instead you see meaningful acceleration on X or Y (e.g. `ax ≈ 9.8, az ≈ 0`), the physical mount is rotated ~90° from what the URDF/static transform claims — classic axis-swap wiring/mounting bug. This alone explains spin-in-place, because the EKF is now trying to reconcile a yaw rate that's actually pitch or roll rate.

**2. Yaw-rate sign/axis check while manually rotating the robot**

Physically yaw the robot (turn it by hand) around its true vertical axis and watch `angular_velocity.z` in the same echo. It should move cleanly and *only* z should respond. If yawing the robot moves `angular_velocity.x` or `.y` instead (or z barely moves while x/y spike), that's hard confirmation of a rotated mount — independent of check 1.

**3. Compare wheel-odom yaw vs IMU yaw vs EKF output yaw during a straight-line drive**

```
ros2 topic echo /wheel_odom      # yaw component
ros2 topic echo /imu/data        # orientation quaternion → yaw
ros2 topic echo /odometry/filtered   # EKF output
```

Drive straight for a few meters. If wheel odom yaw stays ~flat but IMU yaw drifts/ramps, and EKF output follows the IMU's drift, that confirms the EKF is trusting a bad IMU yaw signal over correct wheel data — which is the actual mechanism of "spins on the spot" (the EKF fuses a phantom rotation rate as if it were real, since covariances all look "healthy," nothing errors).

## What to send me
- Output of the static echo (check 1) and the hand-rotation echo (check 2)
- The `imu_link` joint/transform from your URDF (or the static_transform_publisher args)
- Your `ekf.yaml` (robot_localization config) — specifically the imu0_config bitmask and imu0_remove_gravitational_acceleration setting
- If you have a rosbag from a stationary period, that's ideal — I can check it directly

If you can copy/paste the static-test output and the URDF IMU joint now, that alone will likely confirm or rule out the mounting theory.
