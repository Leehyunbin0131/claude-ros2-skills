# Run summary — `t2-skills_result.jsonl`

- model: `claude-sonnet-5`
- turns: 13
- total_cost_usd: 0.3269317
- tool calls: **10**

## Tool calls, in order

1. `Skill` — ros2-troubleshooting
2. `Skill` — ros2-core
3. `Bash` — ls /opt/ros/jazzy/ 2>&1 | head -5; echo "---"; ls /tmp/eval-t2-skills-Qilh/.claude/skills/ros2-troubleshooting/scripts/ 2>&1
4. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1; timeout 5 ros2 topic list -t 2>&1
5. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1
echo "=== IMU gravity check (robot must be stationary) ==="
python3 /tmp/eval-t2-skills-Qilh/.claude/skills/ros2-troublesh
6. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1
echo "=== TF tree check ==="
python3 /tmp/eval-t2-skills-Qilh/.claude/skills/ros2-troubleshooting/scripts/check_tf_tree.py
7. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1
echo "=== static tf topic raw ==="
timeout 3 ros2 topic echo /tf_static --once 2>&1 | grep -v RTPS_TRANSPORT
echo "=== fra
8. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1
echo "=== robot_description imu mentions ==="
timeout 3 ros2 topic echo /robot_description --once 2>&1 | grep -v RTPS_TRAN
9. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1
timeout 5 ros2 node list 2>&1 | grep -v RTPS_TRANSPORT
echo "---find urdf files---"
find /tmp/eval-t2-skills-Qilh -iname "
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>&1
timeout 3 ros2 topic echo /imu/data --once 2>&1 | grep -v RTPS_TRANSPORT

## Final message

Confirmed with hard evidence — this is not a hunch.

**Measured directly** (robot at rest, `/imu/data`, one raw sample):
```
linear_acceleration: x: 9.859   y: -0.074   z: -0.039
```
Full gravity (~9.81 m/s²) is sitting on **X**, not **Z**. `check_imu_gravity.py --topic /imu/data` independently flags this:
```
[FAIL] mean accel = (+9.81, +0.01, +0.01), |a| = 9.81. Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
Per REP 103, a stationary IMU must read gravity on +Z. This one doesn't — the sensor is physically rotated ~90° (roll or pitch) from the orientation its frame declares.

**Why nothing errors and every topic "looks healthy":** `/imu/data` publishes at full rate with well-formed floats — there's no exception to catch. On top of that, `check_tf_tree.py` shows `base_link -> imu_link` is **missing entirely** (`/tf_static` has zero transforms), so `robot_localization` isn't even being told about a mounting offset — correct or not. Nothing in the log stack has a way to know the mount is wrong.

**Why this produces exactly your symptom:** the EKF fuses this data assuming its declared axes are physical reality. With gravity leaking onto X instead of Z, the ~9.8 m/s² offset gets treated as horizontal acceleration (drift), and rotation about the true vertical axis is being read on the wrong sensor axis (spin-on-the-spot when the robot should be tracking straight, or vice versa).

One thing I could **not** verify here: Root Cause A from the troubleshooting skill (IMU `angular_velocity.z` sign vs. wheel-odometry yaw rate) requires physically rotating the robot, which this stationary rig doesn't let me do. Worth checking with `check_odom_direction.py` once the mount is fixed.

**Fix:** re-mount the IMU so +Z is up per REP 103, or if the mechanical mount can't change, publish the real `base_link -> imu_link` static transform (URDF joint origin RPY or `static_transform_publisher`) encoding the actual rotation, then re-run `check_imu_gravity.py` to confirm PASS before trusting the EKF again.
