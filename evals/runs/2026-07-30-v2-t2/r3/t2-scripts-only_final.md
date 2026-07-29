# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 20
- total_cost_usd: 0.5196534000000002
- tool calls: **19**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-scripts-only-nyKs
2. `Bash` — find /tmp/eval-t2-scripts-only-nyKs -type f | head -200
3. `Read` — /tmp/eval-t2-scripts-only-nyKs/scripts/check_imu_gravity.py
4. `Read` — /tmp/eval-t2-scripts-only-nyKs/scripts/check_odom_direction.py
5. `Read` — /tmp/eval-t2-scripts-only-nyKs/scripts/check_tf_tree.py
6. `Read` — /tmp/eval-t2-scripts-only-nyKs/scripts/check_qos_compat.py
7. `Read` — /tmp/eval-t2-scripts-only-nyKs/scripts/test_checks.py
8. `Bash` — which ros2 2>/dev/null; echo "---"; python3 -c "import rclpy" 2>&1 | head -5; echo "---"; env | grep -i ros; echo "---"; ros2 topic list 2>&1 | head -20
9. `Bash` — cd /tmp/eval-t2-scripts-only-nyKs/scripts && python3 test_checks.py
10. `Bash` — ros2 topic list -t 2>&1 | head -30; echo "---frames---"; ros2 topic echo /tf_static --once 2>&1 | head -60
11. `Bash` — ros2 node list 2>&1; echo "---"; timeout 5 ros2 topic echo /tf_static --once 2>&1 | tail -60
12. `Bash` — ros2 node list 2>/dev/null | grep -i ekf; echo "---ekf search done---"; ros2 topic list 2>/dev/null | grep -i -E "odom|filter"; echo "---urdf grep imu---"; ros2
13. `Bash` — timeout 5 ros2 topic echo /robot_description --once 2>/dev/null > /tmp/robot_description.txt; wc -l /tmp/robot_description.txt; grep -n -i "imu" /tmp/robot_desc
14. `Bash` — cat /tmp/robot_description.txt
15. `Bash` — timeout 5 ros2 topic echo /robot_description --once --full-length 2>/dev/null | python3 -c "
import sys, re
raw = sys.stdin.read()
m = re.search(r'data: \"(.*)\
16. `Bash` — timeout 5 ros2 topic echo /imu/data --once --full-length 2>/dev/null
17. `Bash` — timeout 20 python3 check_imu_gravity.py --topic /imu/data --samples 50 --timeout 15 2>&1 | grep -v RTPS_TRANSPORT
18. `Bash` — timeout 15 python3 check_tf_tree.py --no-global --base base_link --sensors imu_link --timeout 8 2>&1 | grep -v RTPS_TRANSPORT
19. `Bash` — timeout 15 python3 check_tf_tree.py --no-global --base base_link --sensors "lw,rw,imu_link" --timeout 6 2>&1 | grep -v RTPS_TRANSPORT

## Final message

Confirmed — with hard evidence, not a hunch. Here's the chain:

**1. Robot at rest, 50 averaged samples of `/imu/data`:**
```
[FAIL] mean accel = (+9.82, -0.00, -0.00) m/s^2, |a| = 9.82
Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
The magnitude (9.82) is exactly gravity — the sensor itself is fine, no scale/bias problem. But it's landing almost 100% on X, essentially 0 on Z. On a level, stationary robot, gravity **must** read on +Z per REP 103. It doesn't.

**2. TF tree check for `base_link -> imu_link`:**
```
[MISSING] base_link -> imu_link (LookupException)
```
It doesn't resolve at all — not wrong, *absent*. I confirmed this two ways:
- Pulled the live `/robot_description` URDF: it defines `base_link`, `lw`, `rw` — **no `imu_link` anywhere**.
- `ros2 node list` shows no `static_transform_publisher` node either.

**3. Control check — wheel frames resolve fine:**
```
[OK] base_link -> lw  rpy=(+0.0, +0.0, +0.0) deg
[OK] base_link -> rw  rpy=(+0.0, +0.0, +0.0) deg
```
Same `robot_state_publisher`, same TF machinery — so this isn't a generic TF outage. It's specific to the IMU.

**Verdict:** the IMU (`/fake_imu_pub`) publishes `frame_id: imu_link` in its header, but that frame was never given a transform relative to `base_link`, and the raw accelerometer data independently proves the sensor's actual axis mapping is rotated ~90° from what's assumed. Nothing enforces or corrects this, so it's silent: messages are well-formed, topics look healthy, but whatever fuses this IMU (EKF/robot_localization) is fusing `angular_velocity.z` — nominally yaw rate — from an axis that's actually roll/pitch in reality. That's exactly the mechanism behind your two symptoms:
- **Spinning on the spot**: real roll/pitch noise (vibration, uneven ground) leaks into the fused yaw state as fake rotation.
- **Drift**: gravity doesn't cancel on Z as expected, so a constant ~9.8 m/s² bias leaks into whichever axis the filter treats as forward/lateral acceleration.

**Fix, in order:**
1. Physically correct the IMU mount so its +Z is up and +X is forward (REP 103), or fix the driver's axis remap if it's a firmware/config issue rather than physical.
2. Add the missing `base_link -> imu_link` static transform (URDF joint or `static_transform_publisher`) so the declared frame actually matches reality — right now nothing describes this sensor's mount at all.
3. Re-run `check_imu_gravity.py` after the fix — expect gravity on +Z, magnitude ~9.81, before trusting the EKF again.
