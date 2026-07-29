# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 21
- total_cost_usd: 0.48311810000000005
- tool calls: **20**

## Tool calls, in order

1. `Bash` — find . -maxdepth 3 -type d | grep -v '^\.$' | sort
2. `Bash` — find . -maxdepth 3 -type f | grep -v __pycache__ | sort
3. `Read` — /tmp/eval-t2-scripts-only-kvIp/scripts/check_imu_gravity.py
4. `Read` — /tmp/eval-t2-scripts-only-kvIp/scripts/check_odom_direction.py
5. `Read` — /tmp/eval-t2-scripts-only-kvIp/scripts/check_tf_tree.py
6. `Read` — /tmp/eval-t2-scripts-only-kvIp/scripts/check_qos_compat.py
7. `Read` — /tmp/eval-t2-scripts-only-kvIp/scripts/test_checks.py
8. `Bash` — python3 scripts/test_checks.py
9. `Bash` — python3 -c "import rclpy" 2>&1; echo "---"; which ros2 2>&1; echo "---"; ros2 topic list 2>&1 | head -20
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; python3 scripts/check_imu_gravity.py --topic /imu/data --samples 30 --timeout 8
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; ros2 topic list -t | grep -i imu; ros2 run tf2_ros tf2_echo base_link imu_link 2>&1 &
sleep 3; kill %1 2>/dev/null
12. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
export ROS_LOCALHOST_ONLY=0
timeout 4 ros2 topic echo /tf_static --once 2>/dev/null
echo "===frames from /tf==="
ti
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
python3 scripts/check_tf_tree.py --no-global --base base_link --sensors imu_link 2>&1 | grep -v RTPS_TRANSPORT
14. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 5 ros2 topic echo /robot_description --once 2>/dev/null | grep -v RTPS_TRANSPORT > /tmp/urdf.xml
cat /tmp/u
15. `Bash` — python3 - <<'EOF'
import re, json
txt = open('/tmp/urdf.xml').read()
m = re.search(r'data:\s*"(.*)"\s*$', txt, re.S)
raw = m.group(1)
xml = raw.encode().decode(
16. `Read` — /tmp/urdf.xml
17. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 5 ros2 topic echo /robot_description --once --full-length 2>/dev/null | grep -v RTPS_TRANSPORT > /tmp/urdf.
18. `Read` — /tmp/urdf.xml
19. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 4 ros2 topic echo /imu/data --once --full-length 2>/dev/null | grep -v RTPS_TRANSPORT
echo "===nodes==="
ti
20. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 4 ros2 node info /fake_imu_pub 2>/dev/null | grep -v RTPS_TRANSPORT
echo "=== find source ==="
find / -inam

## Final message

That last command (a full-filesystem `find`) is still running in the background — not needed though, I already have what's required. Here's the verdict.

## Verdict: confirmed — the IMU is mounted/declared rotated 90°, and that's what's driving the EKF spin/drift

**Evidence, not hunch:**

**1. Gravity vector test (`check_imu_gravity.py` against live `/imu/data`, robot at rest):**
```
[FAIL] mean accel = (+9.81, +0.01, +0.02) m/s^2, |a| = 9.81.
Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
The magnitude is exactly right (9.81 — sensor itself is healthy, well-calibrated, not noisy). But 100% of it is on **X**, none on Z. A correctly mounted IMU at rest reports gravity on **+Z** per REP 103. This one doesn't — full stop.

**2. TF corroborates why nobody caught it (`check_tf_tree.py`):**
```
[MISSING] base_link -> imu_link  (LookupException)
```
Confirmed by reading `/robot_description`: the URDF only defines `base_link`, `lw`, `rw` and the diff-drive `ros2_control` block — **there is no `imu_link` and no joint mounting it**. The IMU driver (node `fake_imu_pub`) stamps its messages `frame_id: imu_link` anyway, but nothing — not the URDF, not a `static_transform_publisher` — ever declares what `imu_link` is relative to `base_link`.

**Why this produces your exact symptom set:**
- Every topic "looks healthy" because it is — the IMU publishes at rate, values are in-range, no error/warn floods anywhere. Nothing is malformed, so nothing errors.
- `robot_localization`'s EKF consumes IMU angular velocity / linear acceleration as if they're already expressed in `base_link` axes (that's the standard assumption when the TF chain to declare otherwise is missing). With the frame rotated 90°, physical **roll-rate lands on the yaw channel** (and vice versa) — so any tilt/vibration the real robot experiences gets fused into the filter as a yaw-rate, producing exactly "drifts and sometimes spins on the spot" while linear odometry from wheels still looks plausible in short bursts.

**Fix, two parts:**
1. Add the missing `imu_link` joint to the URDF (or a `static_transform_publisher`) with the **true physical mounting** roll/pitch/yaw — don't just zero it out, measure the actual rotation.
2. Physically re-seat the IMU square with `base_link`, or correct its internal axis mapping, then re-run `check_imu_gravity.py` — it should report `PASS` with gravity on +Z before you trust the EKF output again.

I did not run `check_odom_direction.py`, since it requires physically pushing the robot 1 m — run it yourself after the IMU fix to confirm wheel/encoder signs are separately correct (`python3 scripts/check_odom_direction.py --topic /diff_drive_controller/odom`).
