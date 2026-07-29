# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 21
- total_cost_usd: 0.5356145999999999
- tool calls: **20**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-scripts-only-62XX/
2. `Bash` — find /tmp/eval-t2-scripts-only-62XX/scripts -maxdepth 5 | head -200
3. `Read` — /tmp/eval-t2-scripts-only-62XX/scripts/check_imu_gravity.py
4. `Read` — /tmp/eval-t2-scripts-only-62XX/scripts/check_odom_direction.py
5. `Read` — /tmp/eval-t2-scripts-only-62XX/scripts/check_tf_tree.py
6. `Read` — /tmp/eval-t2-scripts-only-62XX/scripts/check_qos_compat.py
7. `Read` — /tmp/eval-t2-scripts-only-62XX/scripts/test_checks.py
8. `Bash` — cd /tmp/eval-t2-scripts-only-62XX/scripts && python3 test_checks.py
9. `Bash` — python3 -c "import rclpy" 2>&1 | head -5; echo "---"; which ros2 2>&1
10. `Bash` — python3 -c "import rclpy; print('rclpy OK')" 2>&1; echo "exit=$?"; source /opt/ros/jazzy/setup.bash 2>&1 | tail -5; ros2 topic list 2>&1 | head -20
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; ros2 topic list -t 2>&1
12. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; echo "=== tf_static frames ==="; timeout 3 ros2 topic echo /tf_static --once 2>&1 | grep -E "frame_id|child_fr
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; timeout 5 ros2 topic echo /robot_description --once 2>&1 | grep -oE '(base_link|imu[a-zA-Z_]*|link name="[a-zA
14. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; timeout 5 ros2 topic echo /robot_description --once 2>&1 > /tmp/urdf_dump.txt; wc -l /tmp/urdf_dump.txt; grep 
15. `Read` — /tmp/urdf_dump.txt
16. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; python3 -c "
import rclpy
from std_msgs.msg import String
rclpy.init()
node = rclpy.create_node('urdf_dump')
d
17. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; python3 -c "
import rclpy
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy, 
18. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; python3 -c "
import rclpy
from sensor_msgs.msg import Imu
from rclpy.qos import qos_profile_sensor_data
rclpy.
19. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; cd /tmp/eval-t2-scripts-only-62XX/scripts
echo "=== check_imu_gravity.py ==="
python3 check_imu_gravity.py --t
20. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1 >/dev/null; python3 -c "
import rclpy
from sensor_msgs.msg import Imu
from rclpy.qos import qos_profile_sensor_data
rclpy.

## Final message

Settled — hard evidence, not a hunch:

**1. Gravity vector is on the wrong axis** (`check_imu_gravity.py`, robot at rest):
```
[FAIL] mean accel = (+9.80, -0.00, +0.01) m/s^2, |a| = 9.80
Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
At rest, gravity must read ~+9.81 on **Z** per REP 103. It's reading full magnitude on **X** instead, with Z ≈ 0. That's not noise or bias — it's a 90° rotation between the physical chip and the orientation the driver claims (`imu_link`).

**2. `base_link → imu_link` has no transform at all**:
```
[MISSING] base_link -> imu_link  (LookupException)
```
There's no `imu_link` in the URDF (only `base_link`, `lw`, `rw`) and nothing publishes a static transform for it — `/imu/data` messages just claim `frame_id: imu_link` into a void. So even the EKF's TF lookup for the sensor offset can't succeed; it's silently consuming the raw IMU frame as if it were already aligned with `base_link`.

**Why this produces your exact symptoms:** the accelerometer and gyro are rigidly on the same chip, so the same 90° rotation applies to both. Whatever axis is actually measuring yaw-rate (real spin about the vertical) is being read by the EKF as the *pitch or roll* channel, and vice versa — a small roll/pitch disturbance gets fused in as spurious yaw velocity. That's the "spins on the spot" behavior. Meanwhile gravity leaking into the horizontal accel channel biases the fused linear acceleration, which integrates into position drift. Every topic still publishes at the right rate with valid-looking numbers, so nothing "errors" — the corruption is semantic, not structural.

**Fix, in order:**
1. Physically check which face of the IMU chip points up vs. which the datasheet calls +Z — you're looking for a 90° mount error (likely the board mounted on its edge/side rather than flat).
2. Add the real `base_link → imu_link` static transform (URDF joint or `static_transform_publisher`) once you know the true mount rotation — right now nothing declares it, so nothing can compensate even if the EKF wanted to.
3. Re-run `python3 scripts/check_imu_gravity.py --topic /imu/data` after the fix — expect `PASS` with gravity on +Z.
4. Sweep `check_odom_direction.py` and `check_qos_compat.py` afterward as a final pass, since they cover the other two silent-failure classes this toolkit targets.
