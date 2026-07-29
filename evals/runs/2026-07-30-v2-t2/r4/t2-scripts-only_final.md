# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 16
- total_cost_usd: 0.43683
- tool calls: **15**

## Tool calls, in order

1. `Bash` — find /tmp/eval-t2-scripts-only-j8m7 -maxdepth 4 | head -200
2. `Read` — /tmp/eval-t2-scripts-only-j8m7/scripts/check_imu_gravity.py
3. `Read` — /tmp/eval-t2-scripts-only-j8m7/scripts/check_odom_direction.py
4. `Read` — /tmp/eval-t2-scripts-only-j8m7/scripts/check_tf_tree.py
5. `Read` — /tmp/eval-t2-scripts-only-j8m7/scripts/check_qos_compat.py
6. `Read` — /tmp/eval-t2-scripts-only-j8m7/scripts/test_checks.py
7. `Bash` — cd /tmp/eval-t2-scripts-only-j8m7/scripts && python3 test_checks.py && echo "---" && python3 -c "import rclpy" 2>&1 | head -5
8. `Bash` — python3 -c "import rclpy; print('rclpy OK', rclpy.__file__)" 2>&1
9. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; timeout 5 ros2 topic list 2>&1; echo "---nodes---"; timeout 5 ros2 node list 2>&1
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "--- imu frame_id ---"
timeout 4 ros2 topic echo /imu/data --once 2>&1 | head -30
echo "--- odom frame ---"
ti
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
cd /tmp/eval-t2-scripts-only-j8m7/scripts
python3 check_imu_gravity.py --topic /imu/data --samples 40 --timeout 8
e
12. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
cd /tmp/eval-t2-scripts-only-j8m7/scripts
python3 check_tf_tree.py --no-global --base base_link --sensors imu_link 
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 5 ros2 topic echo /robot_description --once 2>/dev/null | grep -n -A3 -B10 -i "imu" 
14. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 5 ros2 topic echo /robot_description --once 2>/dev/null > /tmp/robot_desc.txt
wc -l /tmp/robot_desc.txt
gre
15. `Read` — /tmp/robot_desc.txt

## Final message

Settled — here's the hard evidence, gathered against your **live** robot graph (not a guess):

## 1. Gravity-vector test (physics, can't be faked by config)
Robot at rest, sampled 40 live messages from `/imu/data`:

```
mean accel = (+9.80, +0.02, -0.00) m/s^2, |a| = 9.80
[FAIL] Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```

Magnitude is correct (9.80 ≈ g), so the sensor itself is fine and it's genuinely at rest — but full gravity is landing on **X**, not **Z**. Per REP-103, a level, correctly-mounted IMU reports gravity almost entirely on +Z. This is unambiguous: the physical mounting is rotated ~90° from what the `imu_link` frame claims.

## 2. TF confirms nothing is correcting for it
```
[MISSING] base_link -> imu_link  (LookupException)
```
And pulling `/robot_description` shows the URDF only declares `base_link`, `lw`, `rw` — **no `imu_link` joint at all**. So there's no static transform anywhere compensating for the real mount orientation. Any consumer (including the EKF) is treating IMU data as if it's already aligned with `base_link`, when it's actually rotated 90°.

## Why this produces exactly your symptoms
- **Drift**: linear acceleration axes are swapped, so what the filter fuses as forward/lateral accel is actually vertical-vs-horizontal accel — integrated velocity/position walks away from reality.
- **Spin on the spot**: the gyro axes are swapped the same way, so ordinary roll/pitch motion (bumps, tilt) gets read into what the filter treats as yaw rate, and the EKF integrates that as heading change with no matching physical rotation.
- **Nothing errors**: topics publish at full rate with plausible-looking numbers (9.8 m/s² magnitude, small gyro noise) — `ros2 topic hz`/`echo` show nothing wrong, which is exactly why this bug hides from normal health checks.

This isn't a hunch anymore — it's a reproducible FAIL from live sensor data plus a missing TF link to explain why nothing compensates for it.

**Fix path**: add a `base_link → imu_link` joint/static transform with the correct rotation (or physically remount the IMU), then rerun `check_imu_gravity.py` and `check_tf_tree.py` — PASS should show gravity on +Z and the TF chain resolving with rpy matching the real mount. Want me to add that transform to the URDF now?
