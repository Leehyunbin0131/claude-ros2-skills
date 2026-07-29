# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 20
- total_cost_usd: 0.505723
- tool calls: **19**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-scripts-only-uDuX/
2. `Bash` — find /tmp/eval-t2-scripts-only-uDuX/scripts -type f | head -200
3. `Read` — /tmp/eval-t2-scripts-only-uDuX/scripts/check_imu_gravity.py
4. `Read` — /tmp/eval-t2-scripts-only-uDuX/scripts/check_odom_direction.py
5. `Read` — /tmp/eval-t2-scripts-only-uDuX/scripts/check_tf_tree.py
6. `Read` — /tmp/eval-t2-scripts-only-uDuX/scripts/check_qos_compat.py
7. `Read` — /tmp/eval-t2-scripts-only-uDuX/scripts/test_checks.py
8. `Bash` — cd /tmp/eval-t2-scripts-only-uDuX/scripts && python3 test_checks.py; echo "---"; python3 -c "import rclpy" 2>&1 | head -5; echo "---"; ros2 topic list 2>&1 | he
9. `Bash` — ros2 topic list 2>&1
10. `Bash` — ros2 node list 2>&1; echo "---frames---"; timeout 5 ros2 run tf2_tools view_frames 2>&1 | tail -20 || true; echo "---imu echo---"; timeout 3 ros2 topic echo /im
11. `Bash` — python3 check_imu_gravity.py --topic /imu/data --samples 50 --timeout 10 2>&1
12. `Bash` — python3 check_tf_tree.py --no-global --base base_link --sensors imu_link --timeout 5 2>&1
13. `Bash` — timeout 3 ros2 topic echo /tf_static --once 2>&1
14. `Bash` — timeout 3 ros2 topic echo /robot_description --once 2>&1 | head -100
15. `Bash` — timeout 3 ros2 topic echo /robot_description --once --full-length 2>&1 | python3 -c "
import sys, yaml
data = sys.stdin.read()
d = yaml.safe_load(data)
print(d[
16. `Bash` — python3 - <<'EOF'
import rclpy
from std_msgs.msg import String
rclpy.init()
node = rclpy.create_node('dump_urdf')
box = []
sub = node.create_subscription(String
17. `Bash` — python3 - <<'EOF'
import rclpy
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, HistoryPolicy
rclpy.init()
18. `Bash` — timeout 3 ros2 topic echo /tf --once 2>&1; echo "---odom---"; timeout 3 ros2 topic echo /diff_drive_controller/odom --once 2>&1 | head -30
19. `Bash` — timeout 3 ros2 topic echo /diagnostics --once 2>&1 | head -40

## Final message

Ran the diagnostic scripts against the live ROS 2 graph (not simulated — this sandbox has real topics: `/imu/data`, `/diff_drive_controller/odom`, `/tf`, `/tf_static`, `/robot_description`). Found two compounding, verifiable bugs — not a hunch.

**Evidence 1 — gravity vector check (`check_imu_gravity.py`, 50 samples, robot at rest):**
```
[FAIL] mean accel = (+9.81, -0.01, -0.00) m/s^2, |a| = 9.81. Gravity is on X, not Z:
IMU is mounted rotated 90 deg relative to its declared TF frame.
```
Full 9.81 m/s² is landing on X with Z at ~0.00. At rest, gravity must be on +Z per REP 103. It isn't — that's not noise or bias, it's a 90° axis swap.

**Evidence 2 — TF audit (`check_tf_tree.py --sensors imu_link`):**
```
[MISSING] base_link -> imu_link  (LookupException)
```
I confirmed why: `/tf_static` is publishing an empty transform list, and I pulled the actual URDF off `/robot_description` — it defines `base_link`, `lw`, `rw` and the two wheel joints, but **no `imu_link` link or joint at all**. The IMU message's `frame_id: imu_link` refers to a frame that doesn't exist anywhere in the TF tree.

**Why everything "looks healthy":** `/imu/data` publishes at full rate with valid, in-range values (that's why topic tools show nothing wrong), and nothing in ROS treats a missing static transform as fatal — there's no crash, no QoS mismatch, no dropped connection, and `/diagnostics` stays silent. But `robot_localization`/your EKF needs `base_link -> imu_link` to rotate the accelerometer/gyro readings into `base_link` before fusing them. With that transform absent, the filter either silently drops IMU input or (more likely, given your symptoms) treats the IMU frame as coincident with `base_link` and fuses the raw, 90°-rotated readings directly — so a stationary robot's "gravity" reads as huge acceleration/rotation signal on the wrong axis, which the EKF interprets as motion → drift and unprompted yaw spin.

**Fix, in order:**
1. Add an `imu_link` and a fixed joint to the URDF, with `origin rpy` set to match how the sensor is *actually* physically bolted on — verify against the real board, don't guess.
2. Correct the rotation so gravity lands on +Z: physically remount the board, or if that's not possible, encode the true mounting rotation in that joint's `rpy` (this is a TF/URDF fix, not an EKF sign-flip hack).
3. Re-run both checks to confirm:
   - `python3 check_imu_gravity.py --topic /imu/data` → should report `[PASS] ... Gravity on +Z`
   - `python3 check_tf_tree.py --no-global --sensors imu_link` → should report `[OK] base_link -> imu_link`

That combination (URDF dump + live gravity sampling + TF lookup) is the evidence: the IMU is both physically mis-oriented (gravity on X) and structurally invisible to TF (no `imu_link` ever declared), which is why the EKF drifts and spins while every topic still looks fine.
