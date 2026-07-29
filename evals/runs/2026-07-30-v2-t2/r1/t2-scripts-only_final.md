# Run summary — `t2-scripts-only_result.jsonl`

- model: `claude-sonnet-5`
- turns: 22
- total_cost_usd: 0.5566576
- tool calls: **21**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-scripts-only-qcZ0/
2. `Bash` — find /tmp/eval-t2-scripts-only-qcZ0/scripts -type f | head -200
3. `Read` — /tmp/eval-t2-scripts-only-qcZ0/scripts/check_imu_gravity.py
4. `Read` — /tmp/eval-t2-scripts-only-qcZ0/scripts/check_odom_direction.py
5. `Read` — /tmp/eval-t2-scripts-only-qcZ0/scripts/check_tf_tree.py
6. `Read` — /tmp/eval-t2-scripts-only-qcZ0/scripts/check_qos_compat.py
7. `Read` — /tmp/eval-t2-scripts-only-qcZ0/scripts/test_checks.py
8. `Bash` — cd /tmp/eval-t2-scripts-only-qcZ0/scripts && python3 test_checks.py
9. `Bash` — which ros2 2>&1; echo "---"; python3 -c "import rclpy" 2>&1; echo "---"; env | grep -i ros; echo "---"; ls /opt/ros 2>&1
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; timeout 8 ros2 topic list 2>&1
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
cd /tmp/eval-t2-scripts-only-qcZ0/scripts
timeout 20 python3 check_imu_gravity.py --topic /imu/data --samples 50 --
12. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
cd /tmp/eval-t2-scripts-only-qcZ0/scripts
timeout 15 python3 check_tf_tree.py --no-global --base base_link --sensor
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 6 ros2 topic echo /imu/data --once 2>/dev/null | grep -A3 "frame_id\|header"
echo "---frames---"
timeout 8 
14. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 6 ros2 topic echo /robot_description --once 2>/dev/null | python3 -c "
import sys, re
data = sys.stdin.read
15. `Bash` — wc -l /tmp/urdf_dump.xml; head -c 500 /tmp/urdf_dump.xml
16. `Bash` — python3 -c "
with open('/tmp/urdf_dump.xml') as f:
    content = f.read()
content = content.replace('\\\\n', '\n').replace('\\\\\"', '\"')
with open('/tmp/urdf_
17. `Read` — /tmp/urdf_dump_clean.xml
18. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 6 ros2 topic echo /robot_description --once --full-length 2>/dev/null > /tmp/urdf_raw.txt
wc -c /tmp/urdf_r
19. `Read` — /tmp/urdf_raw.txt
20. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== nodes ==="
timeout 8 ros2 node list 2>&1 | grep -v RTPS
echo "=== qos: /imu/data ==="
cd /tmp/eval-t2-scr
21. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
cd /tmp/eval-t2-scripts-only-qcZ0/scripts
timeout 15 python3 check_imu_gravity.py --topic /imu/data --samples 80 --

## Final message

Reproducible across two independent runs (50 and 80 samples): mean accel ≈ (+9.82, 0, 0) m/s², magnitude correct (9.82 ≈ g), but 100% on **X**, not Z.

## Evidence

**1. Static gravity test** (`check_imu_gravity.py`, robot at rest, flat ground):
```
mean accel = (+9.82, +0.01, +0.00) m/s², |a| = 9.82
[FAIL] Gravity is on X, not Z: IMU is mounted rotated 90° relative to its declared TF frame.
```
This isn't noise or a scale bug — the magnitude is dead-on 9.81 m/s² and it's cleanly on one axis, not split across two (which would mean a partial tilt). It's a clean 90° axis swap.

**2. TF/URDF check** — confirms there's no innocent explanation on the transform side either:
- `base_link → imu_link` lookup: `LookupException` (no static transform published)
- The live `/robot_description` URDF has zero mention of `imu_link` — only `base_link`, `lw`, `rw` wheel joints. The IMU (published by node `/fake_imu_pub`) stamps its messages `frame_id: imu_link`, but that frame was never wired into the TF tree with a declared mounting rotation.

So this isn't "URDF says rotated 90°, physical sensor agrees" (that'd be a fine, deliberate side-mount) — there's no declared orientation at all, and the raw data itself proves the sensor's body-frame axes don't follow REP 103 (X-forward/Y-left/Z-up). Whatever axis the driver/mount calls "Z" is actually pointing at true horizontal.

**3. Ruled out as confounders:**
- QoS: no active subscribers on `/imu/data` or `/diff_drive_controller/odom` right now, so a reliability/durability mismatch isn't what's silently dropping data — the topics genuinely carry (bad) data, which is why everything "looks healthy."
- Not a units/scale issue: magnitude is exactly g.

## Why this produces exactly your symptoms
An EKF (robot_localization or similar) consuming this IMU assumes gyro Z = yaw rate, accel Z = up. If the physical mount is rotated 90°, real yaw-axis rotation shows up on what the EKF treats as roll or pitch (and vice versa) — the filter fuses spurious yaw rate during normal driving (spin-on-spot) and integrates gravity-contaminated acceleration into velocity (drift). No topic errors, no dropped messages, no NaNs — just wrong axis semantics, which is invisible to `ros2 topic hz`/`echo` unless you specifically check the gravity vector like this.

**Fix:** physically re-mount the IMU so gravity reads on +Z at rest (rotate 90° about whichever axis currently shows the reading — here it's on X, so check which physical rotation makes sense given your enclosure), or if it must stay physically as-is, add a correct `static_transform_publisher`/URDF joint for `imu_link` with the true mounting RPY and make sure the driver applies that rotation before publishing — then EKF will interpret it in the same frame it assumes.
