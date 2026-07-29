# Run summary — `t2-skills_result.jsonl`

- model: `claude-sonnet-5`
- turns: 16
- total_cost_usd: 0.3734785
- tool calls: **13**

## Tool calls, in order

1. `Skill` — ros2-troubleshooting
2. `Skill` — ros2-core
3. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; ros2 topic list -t 2>&1 | head -50
4. `Bash` — ls /tmp/eval-t2-skills-vi9R/.claude/skills/ros2-troubleshooting/scripts/
5. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null; echo "--- nodes ---"; ros2 node list 2>&1; echo "--- clock topic check ---"; ros2 topic list -t 2>&1 | grep -i clo
6. `Bash` — pwd; ls -la /tmp/eval-t2-skills-vi9R/ 2>&1 | head -30
7. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== IMU gravity check ==="
python3 /tmp/eval-t2-skills-vi9R/.claude/skills/ros2-troubleshooting/scripts/check
8. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== raw imu sample ==="
timeout 3 ros2 topic echo /imu/data --once 2>&1
9. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== TF tree check ==="
python3 /tmp/eval-t2-skills-vi9R/.claude/skills/ros2-troubleshooting/scripts/check_tf_
10. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 5 ros2 run tf2_ros tf2_echo base_link imu_link 2>&1
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== /tf_static full dump ==="
timeout 3 ros2 topic echo /tf_static --once 2>&1
echo "=== node list with names
12. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 3 ros2 topic echo /robot_description --once 2>&1 | grep -A5 -i "imu" 
13. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
timeout 3 ros2 topic echo /robot_description --once 2>&1 | head -100

## Final message

Settled — hard evidence confirms the IMU mount, plus a second bug that's masking it. Two independent checks against the live `/imu/data` topic (source: `/opt/ros/jazzy`, robot at rest):

**1. Gravity is on the wrong axis**
```
python3 .claude/skills/ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data
[FAIL] mean accel = (+9.80, +0.00, +0.00) m/s^2, |a| = 9.80. Gravity is on X, not Z: IMU is mounted rotated 90 deg relative to its declared TF frame.
```
Confirmed with a raw echo of `/imu/data`: `linear_acceleration = (9.86, -0.02, -0.02)` while the robot is flat and still. Per REP 103, a stationary, correctly-mounted IMU must read ~+9.81 on **Z**. Here it's reading on **X**, so the sensor's physical "up" axis is pointed along its declared forward axis — the IMU is physically rotated ~90° (pitch) from what its frame_id (`imu_link`) claims.

**2. There's no transform to compensate for it — this is why "everything looks healthy"**
```
tf2_echo base_link imu_link → Invalid frame ID "imu_link" ... frame does not exist
/tf_static → transforms: []
/robot_description → no "imu" anywhere in the URDF
```
`imu_link` isn't declared in the URDF at all, so nothing publishes `base_link -> imu_link`. `robot_localization` typically handles a missing IMU transform with a `WARN` and falls back to treating it as identity, not an error — which is exactly why your topics look fine and nothing throws.

**Why this produces drift + spin-on-the-spot**: the EKF assumes REP 103 axes (Z up). With gravity landing on X, the filter's roll/pitch (and gravity-compensation of linear acceleration) are computed against the wrong axis, corrupting the acceleration that gets integrated into position — that's your drift. Because the whole IMU body is rotated, the physical rotation the driver reports as `angular_velocity.z` is not true yaw rate, it's a mix involving a different physical axis — feed that into an EKF expecting yaw-rate-on-Z and you get exactly "spins on the spot" when the robot isn't actually turning.

**Fix, in order:**
1. Physically remount the IMU so its Z axis points up (undo the ~90° pitch), or if the mount can't move, add the real orientation.
2. Add a `<joint>` (fixed) from `base_link` to `imu_link` in the URDF with the correct RPY so TF actually has a transform to work with — right now there's nothing to fall back on even if you fix the pose in code.
3. Re-run `check_imu_gravity.py` — it should PASS with gravity ~9.81 on Z before you trust the EKF output again.
