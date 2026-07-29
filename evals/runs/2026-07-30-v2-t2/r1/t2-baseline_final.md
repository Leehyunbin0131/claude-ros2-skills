# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 14
- total_cost_usd: 0.7533214
- tool calls: **13**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-y6pt/
2. `Bash` — echo "--- home ---"; ls -la ~ 2>/dev/null | head -30
echo "--- looking for ros workspaces ---"; find / -maxdepth 4 -iname "*catkin_ws*" -o -maxdepth 4 -iname "*
3. `Bash` — echo "--- .ros dir ---"; find ~/.ros -maxdepth 3 2>/dev/null
echo "--- .gz dir ---"; find ~/.gz -maxdepth 3 2>/dev/null
echo "--- home/home subfolder ---"; find
4. `Read` — /home/hyunlee/.claude/projects/-tmp-eval-t2-baseline-y6pt/e7b1c603-48f4-4115-93cb-e7dd5047097b/tool-results/ba57326x6.txt
5. `Bash` — echo "=== running processes ==="
ps aux | grep -iE "ros2|gz|ekf|robot_localization|sim" | grep -v grep
echo "=== workspace layout (excluding .git) ==="
find /ho
6. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== nodes ==="; timeout 8 ros2 node list
echo "=== topics ==="; timeout 8 ros2 topic list -t

7. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== static tf tree ==="
timeout 6 ros2 topic echo /tf_static --once 2>/dev/null

8. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== tf_static info ==="
timeout 6 ros2 topic info /tf_static -v 2>/dev/null
echo "=== robot_description imu s
9. `Bash` — wc -l /tmp/robot_desc.txt; head -5 /tmp/robot_desc.txt
echo "---"
grep -n -iE "imu|<link|<joint" /tmp/robot_desc.txt | head -60
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
python3 - <<'EOF'
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Grab(Node):
    d
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== find ekf yaml / config files in /tmp ==="
find /tmp -maxdepth 3 -iname "*ekf*" -o -iname "*.yaml" 2>/dev/
12. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== 3 more imu samples (stationary) to confirm gravity axis is stable ==="
timeout 5 ros2 topic echo /imu/dat
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 3 ros2 topic pub /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped \
  "{twist: {angular: {z: 0

## Final message

Confirmed. The rotation test didn't couple (this IMU feed is a synthetic fixture, not physically tied to the sim's motion — noise floor stayed flat regardless of commanded spin), but the static test is airtight and doesn't need motion to be conclusive. Here's the evidence:

**The smoking gun — gravity is on the wrong axis**

With the robot level and stationary, `/imu/data` should show ~9.81 m/s² almost entirely on **Z** (vertical, per REP-103: X-forward, Y-left, Z-up) and near-zero on X/Y. Five consecutive samples show the opposite:

| sample | x | y | z |
|---|---|---|---|
| 1 | 9.819 | -0.008 | -0.046 |
| 2 | 9.827 | -0.086 | 0.108 |
| 3 | 9.740 | -0.002 | 0.032 |
| 4 | 9.868 | -0.001 | 0.077 |
| 5 | 9.809 | -0.052 | -0.046 |

Gravity is sitting on **X**, not Z, every single time, with Y/Z at noise level (±0.1 m/s²). That's not sensor bias or calibration drift — a bias would still leave the bulk of the 9.81 m/s² on the vertical axis. This pattern only happens when the physical sensor package is rotated ~90° from its assumed orientation (e.g., mounted on its side), so what the driver reports as "X" is actually pointing straight up.

**Why this produces exactly your two symptoms**

- **Drift**: the EKF expects gravity on Z and (depending on config) either subtracts it or ignores accel-Z for gravity. Here it's getting a spurious ~9.8 m/s² on what it thinks is the forward/lateral axis. If that's fed into the filter at all (even indirectly via covariance-weighted correction), it looks like constant real-world acceleration — double-integrate that and you get runaway position drift with no corresponding wheel motion.
- **Spin on the spot**: the EKF fuses gyro-Z as yaw rate, trusting that Z is the vertical/yaw axis. Since the true vertical axis on this sensor is X (not Z), actual yaw motion doesn't show up where the filter is looking, while whatever noise/cross-coupling lands on the sensor's real Z axis gets fused *as if* it were yaw. The filter reports rotation that isn't happening — textbook "spins in place while driving straight."

**A second, structural piece of evidence**: I pulled the full URDF from `/robot_description` — it defines only `base_link`, `lw`, `rw`. There is **no `imu_link` and no static transform for the IMU at all** (confirmed via `/tf_static`, which is empty). So even if someone wanted to compensate for a rotated mount via `tf`, there's no joint in the model to carry that rotation — robot_localization has zero information about the sensor's physical pose to correct for. The mounting error isn't just present, it's structurally unfixable at the config level until an `imu_link` frame is added.

**Fix**
1. Physically correct: remount so the sensor's native Z axis points up (or note the actual rotation and keep it).
2. If remounting isn't possible: add an `imu_link` to the URDF with a `<joint>` `origin rpy` capturing the true rotation (this looks like a 90° rotation about Y or X — pitch/roll the sensor's X onto vertical), publish it as `frame_id: imu_link` (already done) with that static transform in place, and let `robot_localization` (which does apply `tf` to rotate sensor data into `base_link` before fusion) do the correction automatically. Don't try to hack it with sign flips in the EKF yaml — that only fixes yaw and leaves the accel channel wrong.
