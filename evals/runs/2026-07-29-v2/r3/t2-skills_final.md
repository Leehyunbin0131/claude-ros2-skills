# Run summary — `t2-skills_result.jsonl`

- model: `claude-sonnet-5`
- turns: 17
- total_cost_usd: 0.43648889999999996
- tool calls: **14**

## Tool calls, in order

1. `Skill` — ros2-troubleshooting
2. `Skill` — ros2-core
3. `Bash` — ls /tmp/eval-t2-skills-qBtX/.claude/skills/ros2-troubleshooting/scripts/ 2>&1; echo "---"; source /opt/ros/jazzy/setup.bash 2>&1 && echo "ROS sourced OK" || ech
4. `Bash` — source /opt/ros/jazzy/setup.bash && timeout 8 ros2 topic list -t 2>&1
5. `Bash` — source /opt/ros/jazzy/setup.bash && python3 /tmp/eval-t2-skills-qBtX/.claude/skills/ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data 2>&1
6. `Bash` — source /opt/ros/jazzy/setup.bash && python3 /tmp/eval-t2-skills-qBtX/.claude/skills/ros2-troubleshooting/scripts/check_tf_tree.py --sensors imu_link 2>&1
7. `Bash` — source /opt/ros/jazzy/setup.bash && timeout 5 ros2 topic echo /robot_description --once 2>&1 | grep -o '<link name="imu[^"]*"[^/]*/>\|imu' | head -5
echo "---fu
8. `Bash` — wc -l /tmp/robot_desc.xml; head -20 /tmp/robot_desc.xml
9. `Bash` — python3 -c "
import re
with open('/tmp/robot_desc.xml') as f:
    content = f.read()
m = re.search(r'data:\s*\"(.*)\"\s*$', content, re.S)
s = m.group(1)
s = s.
10. `Bash` — source /opt/ros/jazzy/setup.bash && python3 -c "
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import sys

rclpy.init()
node = rclpy.
11. `Bash` — source /opt/ros/jazzy/setup.bash && timeout 5 ros2 topic info /robot_description -v 2>&1
12. `Bash` — source /opt/ros/jazzy/setup.bash && python3 -c "
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy

13. `Bash` — cat /tmp/robot_desc_pretty.xml
14. `Bash` — source /opt/ros/jazzy/setup.bash && timeout 4 ros2 topic echo /imu/data --once 2>&1 | head -15
echo "--- static tf frames ---"
timeout 4 ros2 run tf2_ros tf2_ec

## Final message

Confirmed — hard evidence, not a hunch. Two things, both from live system checks against this robot:

**1. Physical mounting fault (from `check_imu_gravity.py`, robot at rest):**
```
mean accel = (+9.80, +0.00, +0.00) m/s², |a| = 9.80
FAIL: Gravity is on X, not Z
```
Per REP 103, a flat, level, stationary IMU must read gravity on **Z**. Yours reads it on **X**. The sensor is physically mounted rotated ~90° (pitched) relative to the orientation its `imu_link` frame claims.

**2. There's no TF transform to correct it, at any level:**
- `ros2 topic echo /robot_description` (fetched with matching `TRANSIENT_LOCAL` QoS — default-QoS echo silently returned nothing, itself a live example of the pub/sub QoS mismatch this skill warns about) shows the URDF has **no `imu_link` at all** — just `base_link`, two wheel joints, and `ros2_control`.
- `/tf_static` is completely empty (`transforms: []`).
- `check_tf_tree.py --sensors imu_link` reports `base_link -> imu_link (LookupException)`.

So whatever publishes `/imu/data` (frame_id `imu_link`) is stamping raw, physically-rotated axes with a frame that has zero declared relationship to `base_link`. Any consumer — including `robot_localization`'s EKF — has no way to know the sensor is tilted and fuses `angular_velocity.z` as if it were true yaw rate. Because the real Z axis of the IMU is actually pointed near-horizontal, what the EKF is fusing as "yaw rate" is contaminated by roll/pitch motion (bumps, accel/decel body pitch), which explains both symptoms: slow heading **drift** (spurious rate noise integrated as yaw) and outright **spin-on-the-spot** (a burst of pitch/roll motion misread as a fast yaw rate). Nothing errors because every topic is publishing fine — this is a silent semantic mismatch, not a fault any log would catch.

Also worth noting: `orientation_covariance[0] = -1` on `/imu/data`, meaning this IMU doesn't provide absolute orientation — the EKF has nothing to correct the drifting integrated heading against, so the bad yaw-rate readings accumulate unchecked.

**Fix, in order:**
1. Remount the IMU physically level (or note the actual mounting angle precisely).
2. Add a real `imu_link` to the URDF with a joint from `base_link` whose `origin rpy` matches the *actual* physical mounting (all zeros only if truly level) — this is what's currently completely missing.
3. Re-run `check_imu_gravity.py --topic /imu/data` at rest — it must report `mean accel ≈ (0, 0, +9.81)` before trusting the EKF again.
4. Re-check `check_tf_tree.py --sensors imu_link` — `base_link -> imu_link` must resolve `OK`.

Want me to also run `check_odom_direction.py` (needs you to push the robot ~1 m by hand) to rule out a second contributing cause on the wheel-odometry side, or is the IMU finding sufficient to act on?
