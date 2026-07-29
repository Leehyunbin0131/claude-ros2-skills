# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 18
- total_cost_usd: 0.45115760000000005
- tool calls: **17**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-scripts-only-QItx/ 2>&1 | head -50
2. `Bash` — find /tmp/eval-t2-scripts-only-QItx/scripts -type f | head -200
3. `Read` — /tmp/eval-t2-scripts-only-QItx/scripts/check_imu_gravity.py
4. `Read` — /tmp/eval-t2-scripts-only-QItx/scripts/check_odom_direction.py
5. `Read` — /tmp/eval-t2-scripts-only-QItx/scripts/check_tf_tree.py
6. `Read` — /tmp/eval-t2-scripts-only-QItx/scripts/check_qos_compat.py
7. `Read` — /tmp/eval-t2-scripts-only-QItx/scripts/test_checks.py
8. `Bash` — cd /tmp/eval-t2-scripts-only-QItx/scripts && python3 test_checks.py
9. `Bash` — python3 -c "import rclpy" 2>&1; echo "---"; which ros2 2>&1; echo "---"; env | grep -i ros 2>&1
10. `Bash` — timeout 8 ros2 topic list 2>&1
11. `Bash` — timeout 15 python3 check_imu_gravity.py --topic /imu/data 2>&1
12. `Bash` — timeout 15 python3 check_tf_tree.py --no-global --base base_link --sensors imu_link 2>&1
13. `Bash` — timeout 6 ros2 topic echo /imu/data --once 2>&1 | grep -A2 "frame_id"; echo "---frames---"; timeout 8 ros2 run tf2_tools view_frames 2>&1 | tail -5; echo "---tf
14. `Bash` — timeout 6 ros2 param get /robot_state_publisher robot_description 2>&1 | tr '>' '>\n' | grep -i -B2 -A15 "imu_link" | head -80
15. `Bash` — timeout 6 ros2 param dump /robot_state_publisher 2>&1 > /tmp/rsp_dump.yaml; wc -l /tmp/rsp_dump.yaml; grep -n -i "imu" /tmp/rsp_dump.yaml
16. `Read` — /tmp/rsp_dump.yaml
17. `Bash` — timeout 6 ros2 node list 2>&1; echo "---"; timeout 6 ros2 node list 2>&1 | grep -i -E "ekf|localiz|robot_loc"

## Final message

Confirmed — this is a mounting error, not a hunch. Here's the evidence chain:

**1. Direct physical proof (the smoking gun):**
```
check_imu_gravity.py --topic /imu/data
[FAIL] mean accel = (+9.81, -0.00, -0.01) m/s^2, |a| = 9.81.
Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
With the robot at rest, gravity must read ~+9.81 on **+Z** per REP 103. It's reading on **+X** instead, at full magnitude. That's not noise or bias — it's a full 90° axis swap. The IMU's physical "up" is your declared frame's "forward."

**2. Why nothing catches it downstream:**
- `check_tf_tree.py --sensors imu_link` → `[MISSING] base_link -> imu_link (LookupException)`
- Confirmed by dumping `robot_state_publisher`'s URDF directly: it only defines `base_link`, `lw`, `rw` — **no `imu_link` joint exists at all**, and `/tf_static` is empty.

So the driver publishes `frame_id: imu_link` on `/imu/data`, but there is no transform anywhere (URDF or static publisher) that tells the EKF how that frame relates to `base_link`. Nothing corrects the rotation before it reaches the filter — which is exactly why every topic "looks healthy": messages flow, QoS matches, TF *chains that exist* resolve fine. The bug is a missing/wrong link, not a missing message.

**Why this produces your exact symptoms:**
- **Drift**: gravity (~9.81 m/s²) is landing on what the filter treats as a horizontal (forward/back) acceleration axis → interpreted as constant real acceleration → integrated velocity/position runs away.
- **Spins on the spot**: gyro axes are rotated the same 90° as the accelerometer. Real roll/pitch motion (floor unevenness, accel/decel body pitch) lands on the axis the EKF treats as yaw-rate → spurious yaw injected → the filter spins the pose estimate even when the wheels aren't.

**Fix, in order:**
1. Physically remount the IMU so its declared X/Y/Z match REP 103 body axes, **or**
2. If remount isn't possible, add a correct `imu_link` joint/static transform (with the real rpy offset) so `robot_localization` can auto-correct via TF — then re-run `check_imu_gravity.py`; it must report `[PASS] ... Gravity on +Z`.
3. After either fix, re-run `check_tf_tree.py --sensors imu_link` to confirm the chain resolves.
