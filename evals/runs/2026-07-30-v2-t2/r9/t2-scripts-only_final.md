# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 16
- total_cost_usd: 0.4216996
- tool calls: **15**

## Tool calls, in order

1. `Bash` — find /tmp/eval-t2-scripts-only-ostU -maxdepth 4 -not -path '*/.git*' | head -200
2. `Read` — /tmp/eval-t2-scripts-only-ostU/scripts/check_imu_gravity.py
3. `Read` — /tmp/eval-t2-scripts-only-ostU/scripts/check_odom_direction.py
4. `Read` — /tmp/eval-t2-scripts-only-ostU/scripts/check_tf_tree.py
5. `Read` — /tmp/eval-t2-scripts-only-ostU/scripts/check_qos_compat.py
6. `Read` — /tmp/eval-t2-scripts-only-ostU/scripts/test_checks.py
7. `Bash` — cd /tmp/eval-t2-scripts-only-ostU/scripts && python3 test_checks.py
8. `Bash` — python3 -c "import rclpy" 2>&1; echo "---"; which ros2 2>&1; echo "---"; ros2 topic list 2>&1 | head -30
9. `Bash` — echo "=== nodes ==="; ros2 node list 2>&1
echo "=== imu topic info ==="; ros2 topic info /imu/data --verbose 2>&1
echo "=== one imu msg ==="; timeout 5 ros2 top
10. `Bash` — python3 check_imu_gravity.py --topic /imu/data --samples 30 --timeout 8 2>&1
11. `Bash` — timeout 8 python3 /tmp/eval-t2-scripts-only-ostU/scripts/check_tf_tree.py --no-global --base base_link --sensors imu_link 2>&1
12. `Bash` — ros2 param get /robot_state_publisher use_sim_time 2>&1 | head -5
echo "=== robot_description imu joint ==="
timeout 8 ros2 topic echo /robot_description --once
13. `Bash` — timeout 5 ros2 topic echo /tf_static --once 2>&1 | grep -v RTPS_TRANSPORT
echo "=== frames ==="
timeout 5 python3 -c "
import subprocess
" 
timeout 5 ros2 topic
14. `Bash` — cat /tmp/urdf_dump.txt
echo "=== try again without --once timing race ==="
timeout 8 ros2 topic echo /robot_description --once 2>/dev/null | head -c 3000
15. `Bash` — python3 check_qos_compat.py --topic /imu/data 2>&1 | grep -v RTPS_TRANSPORT
echo "===="
python3 check_qos_compat.py --topic /diff_drive_controller/odom 2>&1 | g

## Final message

Settled. Here's the evidence trail.

**1. Raw sensor data (`ros2 topic echo /imu/data --once`), robot at rest:**
```
linear_acceleration: x: 9.908  y: -0.055  z: 0.067
```

**2. Formal check (`check_imu_gravity.py`, 30-sample average):**
```
[FAIL] mean accel = (+9.82, +0.01, +0.01) m/s^2, |a| = 9.82.
Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
Two independent samples agree: magnitude is correct (9.82 ≈ g, so it's not a scale/units bug), but gravity is loading almost entirely onto the X axis with Y/Z near zero. Per REP 103, a stationary, level IMU must report gravity on **+Z**. It doesn't.

**3. Ruled out the "declared correctly, mount matches, something else is broken" alternative:**
- `check_tf_tree.py --sensors imu_link` → `[MISSING] base_link -> imu_link (LookupException)` — no TF entry for `imu_link` exists at all.
- `/robot_description` URDF only defines `base_link`, `lw`, `rw` and the wheel joints — no `imu_link`, no IMU joint anywhere.
- So `imu_link` in the IMU message header is a name with zero backing transform. Any consumer (robot_localization) that can't look up `base_link → imu_link` falls back to treating the data as identity-aligned with `base_link`.

**4. Ruled out QoS/discovery as a confound:**
- `check_qos_compat.py` on `/imu/data` and the odom topic: no active subscribers right now, so this isn't a "publisher/subscriber can't match" masking issue — the numbers themselves are wrong at the source.

**Diagnosis:** The IMU board is physically mounted rotated ~90° (its local X axis is pointed along what should be the up axis) relative to the orientation `imu_link` is assumed to have. There's no TF or URDF correction for this rotation, so nothing downstream compensates. Fed straight into an EKF, this looks like a constant ~9.8 m/s² acceleration along the robot's body X — a phantom forward-acceleration bias that the filter integrates into velocity and position (drift), and since gyro axes on a rigid board are misaligned the same way, angular-rate readings leak across axes into the yaw estimate (spin-on-the-spot). This matches both symptoms exactly, and every topic still "looks healthy" because rates, message counts, and covariances are all fine — only the axis content is wrong.

**Fix, in order of preference:**
1. Physically re-seat the IMU so its silkscreen X/Y/Z matches the robot body axes (X-fwd, Y-left, Z-up), then re-run `check_imu_gravity.py` to confirm PASS.
2. If remounting isn't possible, add the true rotation as a `static_transform_publisher`/URDF joint origin for `imu_link` (not just a cosmetic TF — robot_localization uses that transform to actually rotate the incoming accel/gyro vectors into `base_link` before fusing), then confirm `check_tf_tree.py --sensors imu_link` resolves and shows the expected rpy.
