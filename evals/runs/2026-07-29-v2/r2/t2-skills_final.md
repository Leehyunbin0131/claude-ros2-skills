# Run summary — `t2-skills_result.jsonl`

- model: `claude-sonnet-5`
- turns: 16
- total_cost_usd: 0.4313034
- tool calls: **14**

## Tool calls, in order

1. `Skill` — ros2-troubleshooting
2. `Bash` — ls /opt/ros/jazzy 2>&1 | head -5; echo "---"; ls /tmp/eval-t2-skills-EoGh/.claude/skills/ros2-troubleshooting/scripts/ 2>&1; echo "---"; source /opt/ros/jazzy/s
3. `Bash` — source /opt/ros/jazzy/setup.bash
echo "=== IMU gravity check ==="
python3 /tmp/eval-t2-skills-EoGh/.claude/skills/ros2-troubleshooting/scripts/check_imu_gravity
4. `Bash` — source /opt/ros/jazzy/setup.bash
echo "=== TF tree check ==="
python3 /tmp/eval-t2-skills-EoGh/.claude/skills/ros2-troubleshooting/scripts/check_tf_tree.py --se
5. `Bash` — source /opt/ros/jazzy/setup.bash
echo "=== IMU message frame_id ==="
timeout 3 ros2 topic echo /imu/data --once 2>&1 | head -20
echo
echo "=== tf_static echo ==
6. `Bash` — source /opt/ros/jazzy/setup.bash
echo "=== all link/joint names in URDF ==="
timeout 3 ros2 topic echo /robot_description --once 2>&1 | grep -oE '<link name="[^
7. `Bash` — wc -l /tmp/urdf_dump.txt; head -c 500 /tmp/urdf_dump.txt
8. `Bash` — python3 -c "
import re
with open('/tmp/urdf_dump.txt') as f:
    content = f.read()
# extract the data field string
m = re.search(r'data: \"(.*)\"', content, re
9. `Bash` — wc -c /tmp/urdf_dump.txt; source /opt/ros/jazzy/setup.bash; timeout 3 ros2 topic echo /robot_description --once --full-length 2>&1 > /tmp/urdf_dump2.txt; wc -c 
10. `Bash` — python3 -c "
import re
with open('/tmp/urdf_dump2.txt') as f:
    content = f.read()
m = re.search(r'data: \"(.*)\"', content, re.DOTALL)
if m:
    s = m.group(
11. `Bash` — source /opt/ros/jazzy/setup.bash
echo "=== raw IMU stream, 5 samples ==="
timeout 3 ros2 topic echo /imu/data 2>&1 | grep -A3 "linear_acceleration:" | head -30

12. `Bash` — source /opt/ros/jazzy/setup.bash
ros2 topic info /diff_drive_controller/cmd_vel 2>&1
echo "---"
ros2 interface show geometry_msgs/msg/TwistStamped 2>&1 | head -
13. `Bash` — source /opt/ros/jazzy/setup.bash
ros2 topic pub -r 10 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped \
"{header: {frame_id: 'base_link'}, twist: 
14. `Bash` — source /opt/ros/jazzy/setup.bash
echo "=== running nodes ==="
timeout 5 ros2 node list 2>&1
echo
echo "=== ekf_filter_node info if present ==="
timeout 5 ros2 n

## Final message

Settled — hard evidence, not a hunch.

**Finding 1: the IMU is physically mounted wrong.**
`check_imu_gravity.py --topic /imu/data` on the live `/imu/data` topic:
```
[FAIL] mean accel = (+9.81, +0.00, -0.00) m/s^2, |a| = 9.81. Gravity is on X, not Z.
```
I confirmed this wasn't a fluke by pulling six independent raw samples via `ros2 topic echo /imu/data`: `linear_acceleration.x` sits at ~9.8–9.9 m/s² every time, `y`/`z` sit near 0. Per REP 103, a stationary IMU must read gravity reaction on **+Z** (the up axis). Reading it on **+X** instead means the sensor's physical Z-axis is lying horizontal and its X-axis is pointing up — consistent with roughly a 90° mounting error, not sensor bias or noise.

**Finding 2: there's no TF transform to catch it.**
`check_tf_tree.py --sensors imu_link` reported `base_link -> imu_link` as `MISSING (LookupException)`, and `/tf_static` is empty — confirmed by checking the URDF served on `/robot_description`, which defines only `base_link`, `lw`, `rw` and never declares an `imu_link` at all. So even if something were fusing this sensor, nothing is correcting for its mount orientation — the wrong axes would pass straight through as if they were `base_link`'s.

**Why this produces exactly your symptoms, silently:**
- A constant ~9.8 m/s² fed into the *x*-acceleration channel looks to an EKF like the robot is perpetually accelerating forward → integrates into runaway position drift.
- True yaw rotation isn't landing on the `angular_velocity.z` field the EKF expects for heading, so turns get little/no correction while spurious cross-axis noise leaks into the yaw estimate → spin-on-the-spot.
- None of this trips an error: the topic still publishes at full rate with a valid, well-formed message, and there's no `base_link->imu_link` frame to fail a lookup on and log a warning.

I couldn't reproduce the live "spin" dynamically here — this sandbox only has a synthetic `/fake_imu_pub` node and mock `ros2_control` hardware (no physics, no `ekf_filter_node` running), so commanding a rotation via `cmd_vel` produced no angular-velocity response on any axis (noise-floor only, ~0.001–0.005 rad/s), which is expected for this rig, not additional evidence either way.

**Fix, per this project's anti-pattern rules:** correct the physical mount (or the static transform declaring it) so the IMU's real Z-axis is vertical — don't paper over it by flipping signs in application/EKF code. Separately, add the missing `base_link -> imu_link` static transform (URDF joint or `static_transform_publisher`) — right now there's no frame for robot_localization to even look up.
