# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 20
- total_cost_usd: 0.4052614
- tool calls: **19**

## Tool calls, in order

1. `Bash` — find /tmp/eval-t2-scripts-only-OQuI -maxdepth 4 -not -path '*/.git*' | head -200
2. `Read` — /tmp/eval-t2-scripts-only-OQuI/scripts/check_imu_gravity.py
3. `Read` — /tmp/eval-t2-scripts-only-OQuI/scripts/check_odom_direction.py
4. `Read` — /tmp/eval-t2-scripts-only-OQuI/scripts/check_tf_tree.py
5. `Read` — /tmp/eval-t2-scripts-only-OQuI/scripts/check_qos_compat.py
6. `Read` — /tmp/eval-t2-scripts-only-OQuI/scripts/test_checks.py
7. `Bash` — cd /tmp/eval-t2-scripts-only-OQuI/scripts && python3 test_checks.py
8. `Bash` — python3 -c "import rclpy; print(rclpy.__file__)" 2>&1; echo "---"; which ros2 2>&1; echo "---"; ros2 topic list 2>&1 | head -30
9. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; ros2 topic echo --once /tf_static 2>&1 | head -60
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; ros2 topic info /imu/data --verbose 2>&1 | head -40
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; echo "=== nodes ==="; ros2 node list 2>&1; echo "=== ekf param file search ==="; find / -iname "*ekf*.yaml" -not -
12. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; timeout 15 ros2 topic hz /imu/data 2>&1 | tail -20
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; timeout 15 ros2 topic echo --once /imu/data 2>&1
14. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; cd /tmp/eval-t2-scripts-only-OQuI/scripts; python3 check_imu_gravity.py --topic /imu/data --samples 50 --timeout 1
15. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; cd /tmp/eval-t2-scripts-only-OQuI/scripts; timeout 20 python3 check_tf_tree.py --no-global --base base_link --sens
16. `Bash` — cat /tmp/claude-1000/-tmp-eval-t2-scripts-only-OQuI/b47f5ebc-6a70-4669-8118-38f1b7154fcc/tasks/bgloqrwpn.output 2>&1
17. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; timeout 15 ros2 topic echo --once /robot_description 2>&1 | grep -v RTPS_TRANSPORT | grep -A5 -i "imu_link\"" | he
18. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; timeout 15 ros2 param get /robot_state_publisher robot_description 2>&1 | grep -v RTPS_TRANSPORT > /tmp/urdf_dump.
19. `Read` — /tmp/urdf_dump.txt

## Final message

Settled — confirmed with data, not a hunch. Two independent, stackable pieces of evidence:

**1. Gravity is on the wrong axis (mounting confirmed rotated 90°)**

Ran `check_imu_gravity.py` against the live `/imu/data` topic, 50-sample average with the robot at rest:

```
[FAIL] mean accel = (+9.80, -0.00, +0.00) m/s^2, |a| = 9.80.
Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```

Magnitude is dead-on 9.80 m/s² (so it's not a scale/units bug), but 100% of it sits on X and ~0.00 on Y/Z. A REP‑103-compliant IMU at rest reports gravity on **+Z** in its own frame. This one doesn't — that's a physical or declared-frame rotation, not sensor noise (50-sample average, not a single glitchy reading).

**2. There's no TF connecting `imu_link` to `base_link` at all — so nothing corrects for it**

```
[MISSING] base_link -> imu_link  (LookupException)
```

I pulled `robot_description` to see why, and the URDF has no `imu_link` defined whatsoever:

```xml
<robot name="dd">
  <link name="base_link"/>
  <link name="lw"/><link name="rw"/>
  ... (only wheel joints, no imu_link link or joint)
```

The driver (`fake_imu_pub`) stamps messages `frame_id: imu_link`, but that frame doesn't exist in the kinematic tree — no `static_transform_publisher`, no URDF joint. Anything consuming this data either has to assume `imu_link == base_link` (which silently feeds X-axis gravity in as forward acceleration and scrambles which physical axis is yaw-rate) or drops the IMU input on TF lookup failure. Either path matches your symptoms exactly: **drift** (wheel odometry running unchecked because IMU correction is broken/absent) and **spin-on-the-spot** (an off-axis angular-velocity/acceleration component getting fused as if it were the robot's Z-axis rotation).

This is precisely the failure mode described in the diagnostic script itself: every topic publishes at a healthy rate, no error, no QoS mismatch — the data is just semantically wrong for the frame it claims to be in.

**Fix, in order:**
1. Physically re-check the IMU orientation on the robot — rotate 90° so its true +Z (marked on the chip/board) points up, matching gravity.
2. Add the missing `imu_link` to the URDF (or a `static_transform_publisher`) with a joint `origin rpy` from `base_link` that reflects the corrected physical mount — right now there's nothing to declare it against.
3. Re-run `check_imu_gravity.py` after remounting — it should report `PASS` with gravity on `+Z`.
4. Re-run `check_tf_tree.py --no-global --sensors imu_link` — it should resolve instead of `MISSING`.

Only after both PASS is it safe to trust the EKF fusing this IMU.
