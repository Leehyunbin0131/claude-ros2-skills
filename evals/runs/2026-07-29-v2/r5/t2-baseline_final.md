# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.12019640000000001
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-cyiG/

## Final message

Your working directory is empty — no repo, config, bag files, or logs I can inspect. I can't verify a mounting fault from thin air, so let's get you a set of tests that will produce hard evidence, not more guessing. This assumes `robot_localization`'s `ekf_node`/`ekf_localization_node` (say if it's something else and I'll adjust).

**The signature to look for:** "drifts + spins in place with everything nominal" almost always means the EKF is fusing a *bad yaw rate*, not a bad position. Two very different root causes produce that symptom, and these tests separate them:

**1. Sign/axis test (proves or kills the mounting theory directly)**
With the robot free to rotate, physically turn it by hand slowly **counter-clockwise viewed from above**, and watch:
```
ros2 topic echo /imu/data --field angular_velocity   # or rostopic echo for ROS1
```
Per REP-103, `angular_velocity.z` must read **positive** during a CCW turn, and X/Y should stay near zero if the IMU's Z axis is truly vertical. If it reads negative, or if a CCW yaw shows up as motion on X/Y instead of Z, the IMU frame is rotated relative to `base_link` — that's your smoking gun, no interpretation needed.

**2. Static gravity test**
Robot stationary, level ground:
```
ros2 topic echo /imu/data --field linear_acceleration
```
Expect ~9.81 on Z only. If gravity leaks onto X or Y, the IMU is tilted or the axes are swapped from what the URDF/static transform claims.

**3. Cross-check the claimed mounting vs the physical mounting**
```
ros2 run tf2_ros tf2_echo base_link imu_link
```
or read the `<joint>` origin `rpy` for `imu_link` in the URDF. Compare that declared rotation against how the sensor is actually bolted on (check silkscreen axis labels on the board). A mismatch here is the mechanism — tests 1/2 are how you catch it even if you can't see the board.

**4. Isolate which source is causing the spin**
Log wheel-only odom yaw, IMU-only yaw, and fused EKF yaw side by side while the robot is commanded to sit still or drive straight. If wheel odom stays sane and only the fused yaw races/spins, that indicts the IMU input (or its covariance/config in `ekf.yaml`) rather than the wheels — narrowing "drift" vs "mounting" vs "fusion config" before you touch hardware.

If you can share the `ekf.yaml` fusion config, the static transform/URDF snippet for `imu_link`, and a short `ros2 topic echo` capture from tests 1–2, I'll read them directly and tell you definitively whether it's mounting, axis convention in software, or a fusion-config issue (e.g., two absolute yaw sources fighting) — rather than you having to interpret the numbers yourself.
