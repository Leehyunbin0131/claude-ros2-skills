# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 25
- total_cost_usd: 0.619445
- tool calls: **24**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-scripts-only-csOV/
2. `Bash` — find /tmp/eval-t2-scripts-only-csOV/scripts -maxdepth 5 | sort
3. `Read` — /tmp/eval-t2-scripts-only-csOV/scripts/check_imu_gravity.py
4. `Read` — /tmp/eval-t2-scripts-only-csOV/scripts/check_odom_direction.py
5. `Read` — /tmp/eval-t2-scripts-only-csOV/scripts/check_qos_compat.py
6. `Read` — /tmp/eval-t2-scripts-only-csOV/scripts/check_tf_tree.py
7. `Read` — /tmp/eval-t2-scripts-only-csOV/scripts/test_checks.py
8. `Bash` — cd /tmp/eval-t2-scripts-only-csOV/scripts && python3 test_checks.py
9. `Bash` — python3 -c "import rclpy" 2>&1; echo "---"; which ros2 2>&1; echo "---"; ros2 topic list 2>&1 | head -30
10. `Bash` — python3 check_imu_gravity.py --topic /imu/data --samples 50 --timeout 10
11. `Bash` — python3 check_tf_tree.py --no-global --base base_link --sensors imu_link --timeout 5
12. `Bash` — python3 check_qos_compat.py --topic /imu/data --wait 3
13. `Bash` — timeout 5 ros2 topic echo /imu/data --once 2>&1 | grep -A2 "frame_id\|orientation:\|angular_velocity:\|linear_acceleration:" | head -30
14. `Bash` — timeout 5 ros2 topic echo /tf_static --once 2>&1 | grep -B2 -A15 "child_frame_id" 
15. `Bash` — timeout 6 ros2 topic echo /tf_static 2>&1 | head -80
16. `Bash` — ros2 topic info /tf_static -v 2>&1 | head -40; echo "===URDF==="; timeout 5 ros2 topic echo /robot_description --once 2>&1 | grep -i -A3 "imu" 
17. `Bash` — timeout 5 ros2 topic echo /robot_description --once 2>&1 > /tmp/urdf_dump.txt; wc -l /tmp/urdf_dump.txt; grep -n -i "imu" /tmp/urdf_dump.txt
18. `Read` — /tmp/urdf_dump.txt
19. `Bash` — python3 -c "
import rclpy
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
rclpy.init()
node = rclpy.create
20. `Read` — /tmp/full_urdf.xml
21. `Bash` — python3 -c "
import rclpy
from tf2_msgs.msg import TFMessage
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
rclpy.init()
node = rclpy.cre
22. `Bash` — ros2 node list 2>&1 | grep -v RTPS_TRANSPORT; echo "---nodes info robot_state_publisher---"; timeout 5 ros2 node info /robot_state_publisher 2>&1 | grep -v RTPS
23. `Bash` — python3 -c "
import rclpy
from sensor_msgs.msg import Imu
from rclpy.qos import qos_profile_sensor_data
rclpy.init()
node = rclpy.create_node('imu_full_dump')
s
24. `Bash` — timeout 4 ros2 topic echo /diff_drive_controller/odom --once 2>&1 | grep -v RTPS_TRANSPORT

## Final message

Settled — hard evidence, not a hunch. Two independent, compounding faults on the IMU path:

**1. The IMU is reporting gravity on the wrong axis.**
```
python3 scripts/check_imu_gravity.py --topic /imu/data --samples 50
[FAIL] mean accel = (+9.81, -0.01, +0.01) m/s^2, |a| = 9.81. Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
Confirmed with a raw 30-sample average: `x=9.794, y=-0.003, z=-0.002`. That's the full gravity vector sitting almost perfectly on X with negligible spread — not noise, not vibration (angular velocity was ~0.001 rad/s, robot at rest), a clean 90° rotation. Per REP 103, `imu_link`'s Z axis must read +9.81 at rest; instead its declared "forward" axis is. And the orientation field the driver publishes is identity `(0,0,0,1)` — the driver has no idea it's rotated, so nothing compensates for it upstream.

**2. There is no TF connecting `imu_link` to `base_link` at all**, so nothing downstream *could* compensate even if you wanted to fix it in software:
```
python3 scripts/check_tf_tree.py --no-global --base base_link --sensors imu_link
[MISSING] base_link -> imu_link (LookupException)
```
Verified two ways: a full dump of `/tf_static` returned zero transforms, and the live `/robot_description` URDF only declares `base_link`, `lw`, `rw` — no `imu_link` joint exists anywhere in the kinematic tree.

**Ruled out as a confound:** wheel odometry (`/diff_drive_controller/odom`) is clean and exactly zero at rest — position, orientation, and covariance all zero. So the drift/spin isn't a wheel-encoder sign error; it's isolated to the IMU input.

**Why this produces exactly your symptoms:** an EKF fusing this feed sees a constant ~9.8 m/s² "acceleration" on what it thinks is the forward (or lateral) body axis, with no TF to catch and rotate it back. Depending on how the filter's covariance weights that axis vs. yaw, that bogus constant accel integrates into runaway position drift, and can also masquerade as a persistent angular correction — the spin-in-place. Every topic still publishes fine, so nothing "errors."

**Fix, in order:**
1. Correct the IMU mounting rotation at the source (fix the physical mount, or the driver's axis remap if it's a firmware/software rotation, i.e. `fake_imu_pub` in this rig) so gravity reads on +Z.
2. Add the missing `base_link -> imu_link` static transform (URDF joint or `static_transform_publisher`) matching the *true* physical mount, so the EKF has something to correct against even if a mounting offset remains.
3. Re-run `check_imu_gravity.py` — it should flip to `[PASS]` — before trusting EKF output again.
