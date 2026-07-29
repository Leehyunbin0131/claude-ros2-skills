# Run summary — `t2-skills_result.jsonl`

- model: `claude-sonnet-5`
- turns: 20
- total_cost_usd: 0.48705830000000006
- tool calls: **17**

## Tool calls, in order

1. `Skill` — ros2-troubleshooting
2. `Skill` — ros2-core
3. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; ros2 topic list -t 2>&1 | head -50
4. `Bash` — ls ~/.claude/skills/ros2-troubleshooting/scripts/ 2>&1; echo "---"; ls /tmp/eval-t2-skills-QVHM/.claude/skills/ros2-troubleshooting/scripts/ 2>&1
5. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== IMU gravity check (robot must be stationary/flat) ==="
python3 /tmp/eval-t2-skills-QVHM/.claude/skills/ro
6. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== TF tree check ==="
python3 /tmp/eval-t2-skills-QVHM/.claude/skills/ros2-troubleshooting/scripts/check_tf_
7. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
ros2 topic echo /robot_description --once 2>&1 | grep -v RTPS_TRANSPORT > /tmp/robot_desc.txt
grep -n -i "imu" /tmp
8. `Bash` — wc -l /tmp/robot_desc.txt; head -5 /tmp/robot_desc.txt
9. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
python3 - <<'EOF'
import rclpy, re
from rclpy.node import Node
from std_msgs.msg import String

rclpy.init()
node =
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 5 ros2 topic echo /robot_description --once --full-length 2>/dev/null > /tmp/robot_desc2.txt
wc -l /tmp/rob
11. `Read` — /tmp/robot_desc_full.xml
12. `Grep` — imu
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== nodes ==="
ros2 node list 2>&1 | grep -v RTPS_TRANSPORT
echo "=== who publishes /imu/data ==="
ros2 topic
14. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
ros2 node info /fake_imu_pub 2>&1 | grep -v RTPS_TRANSPORT
echo "---"
find / -iname "*fake_imu*" 2>/dev/null | grep
15. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 5 ros2 topic echo /imu/data --once 2>/dev/null
16. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
python3 /tmp/eval-t2-skills-QVHM/.claude/skills/ros2-troubleshooting/scripts/check_qos_compat.py --topic /imu/data 
17. `Bash` — cat /tmp/claude-1000/-tmp-eval-t2-skills-QVHM/3cc6c96e-a460-4ed5-a5de-4d206ee0b601/tasks/blzhnvz0m.output 2>/dev/null | grep -v RTPS_TRANSPORT | head -30

## Final message

I have everything needed. Here's the settled diagnosis.

## Root cause: confirmed, not a hunch

Ran the ground-truth checks from `ros2-troubleshooting` against your live graph:

```
source /opt/ros/jazzy/setup.bash
python3 ~/.claude/skills/ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data
```
```
[FAIL] mean accel = (+9.81, +0.00, -0.01) m/s^2, |a| = 9.81. Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```

Raw single-message confirmation (`ros2 topic echo /imu/data --once`):
```
linear_acceleration: {x: 9.74, y: -0.04, z: 0.002}
orientation_covariance[0]: -1.0   # sensor reports no orientation — EKF must derive yaw itself
```

Per REP 103, a stationary, level IMU must read `+9.81` on **Z**. Yours reads it almost entirely on **X**. That's not noise — that's the sensor physically rotated ~90° (pitched) from how its frame is declared, feeding `robot_localization` gravity-contaminated "linear acceleration" and a fictitious accel-derived tilt.

Second, compounding fact — TF tree check:
```
python3 ~/.claude/skills/ros2-troubleshooting/scripts/check_tf_tree.py --sensors imu_link
[MISSING] base_link -> imu_link  (LookupException)
```
I pulled `/robot_description` and confirmed the URDF (published by `robot_state_publisher`) never declares an `imu_link` at all — no joint, no static transform, nothing. So even if you wanted the EKF to compensate for the real mounting angle via TF, there's no transform for it to use.

## Why this produces exactly your symptoms
- **Drift**: with gravity leaking onto X, the EKF's gravity-compensated linear acceleration is wrong on every cycle → integrates a fake constant acceleration → position drift, even standing still.
- **"Sometimes spins on the spot"**: since `orientation_covariance[0] = -1` (no orientation provided), the EKF is relying on raw `angular_velocity` for yaw. Because the whole IMU chip is rotated ~90°, any real roll/pitch rotation (bumps, vibration, even the wheel base flexing) bleeds into the axis the EKF *thinks* is yaw → spurious spin events that correlate with disturbances, not commanded turns. This matches "sometimes," not "always."

Both failures traced to the same physical fact: **the IMU chip is mounted rotated ~90° from its declared frame, and that mounting was never registered in TF/URDF.**

## Fix
1. Physically re-check/re-mount the IMU so its silkscreen `+Z` points up and `+X` points robot-forward (REP 103), or
2. If the mount is intentional/fixed, add the real `base_link -> imu_link` static transform (matching the actual rotation) to the URDF/xacro so `robot_localization`'s `imu0` config can rotate the data correctly before fusion.
3. Re-run `check_imu_gravity.py` after either fix — it must report `PASS` with gravity on `+Z` before trusting the EKF output again.

I did not touch any files — this was diagnosis only. Want me to add the static transform once you've measured the actual mounting angle?
