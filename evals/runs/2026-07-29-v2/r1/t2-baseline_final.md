# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.14881740000000002
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-gYH4/ 2>&1 | head -50

## Final message

This directory is empty, so I can't inspect your URDF, EKF config, or bag files directly — point me at them (path or repo) if you want me to check the actual numbers. In the meantime, here's how to get hard evidence rather than a hunch, and it separates "bad mount" from "just needs calibration," which is a different fix.

**Why "spins on the spot" implicates the IMU specifically:** wheel odometry can't report rotation while the wheels aren't turning. If the EKF's yaw estimate walks while stationary, the yaw channel it's fusing (gyro or IMU absolute orientation) is lying. Mounting error and uncalibrated bias look similar here, so you need tests that distinguish them.

**Test A — stationary leakage test (bias vs. axis-swap)**
Put the robot dead still on a level surface, record `imu/data` (or whatever your topic is) for ~60s.
- Mean/σ of `angular_velocity.z` only nonzero, x/y clean → gyro bias, not mounting (still needs a calibration fix, not a wrench).
- x or y showing structure/bias instead of z → axes are swapped in the driver/URDF, not just biased.

**Test B — known-rotation test (proves axis mapping + sign)**
Mark the heading, rotate the robot exactly 90° by hand (protractor or floor tape), log the same topic.
- Integrate `gyro.z` over the interval: should be ≈90° within ~5-10%. Wrong magnitude → scale/units bug. Wrong sign → yaw is inverted relative to REP-103 (CCW-positive, right-hand rule about +Z) — this alone will make wheel-odom yaw and IMU yaw fight, producing exactly the spin-in-place symptom.
- `gyro.x`/`gyro.y` should stay ~0 during a pure yaw move. If they deflect, the IMU's Z axis isn't vertical — physical tilt in the mount, not a software frame issue.

**Test C — gravity vector at rest (proves roll/pitch mount offset)**
On level ground, at rest, `linear_acceleration` should read ~(0,0,±9.81) (sign per your driver's convention) with everything else near zero.
- Any real signal on x/y at rest = the IMU is physically tilted or its axes are mislabeled vs `base_link`. This is the single cleanest piece of mounting evidence — it directly corrupts the orientation/velocity fusion and causes drift.

**Test D — declared frame vs. physical reality**
`tf2_echo base_link imu_link` (ROS2) or `tf_echo` (ROS1) to get the rpy your URDF *claims* for the mount. Then physically check it with a level/protractor against the IMU board's silkscreened X/Y/Z arrows. Any mismatch between declared and physical = confirmed mounting bug, not a calibration one.

**Reading the results together:**
- Gravity off-axis at rest (C) + off-axis deflection during pure yaw (B) + TF/physical mismatch (D) → mounting is confirmed, fix the URDF joint rpy or physically re-seat the board.
- Only `gyro.z` mean nonzero, gravity correctly on Z, TF matches physical → it's bias/covariance tuning in the EKF config, not the mount.

Want me to also check the `robot_localization` yaml (`imu0_config`, differential vs. absolute yaw fusion) once you point me at it? That's the other common source of exactly this symptom, and it's easy to rule in/out alongside the mount check.
