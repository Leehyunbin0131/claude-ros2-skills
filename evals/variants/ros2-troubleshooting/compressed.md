---
name: ros2-troubleshooting
description: "Troubleshooting: REP 103/105 ground-truth checks, TF/IMU/LiDAR misalignment, use_sim_time, lifecycle states, executor deadlocks, DDS domain conflicts."
---

# ROS 2 Troubleshooting & Physical Ground-Truth Verification Guide (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Core Principle

**Physical ground-truth over logic assumptions.** Never conclude a robot or
sensor direction is correct from code math alone. Verify the frame conventions
(REP 103 body axes: `+X` forward, `+Y` left, `+Z` up, `+Yaw` counter-clockwise;
REP 105 frame relations), the physical sensor mounting, and the TF tree.

Fix an inverted direction where it is wrong — controller config, hardware
interface, or URDF — never by negating the sign in application code.

## 2. Runnable Ground-Truth Checks

These ship **next to this SKILL.md in `scripts/`** — resolve the path from this
skill's own directory, not the user's CWD (plugin install:
`${CLAUDE_PLUGIN_ROOT}/skills/ros2-troubleshooting/scripts/`). Source ROS 2
first. Exit code 0 = PASS, 1 = FAIL, 2 = no data.

**Invoke them with `python3` and a real path. They are plain scripts, not a ROS 2
package** — there is no package to `ros2 run`, and inventing one (`ros2 run
ros2_troubleshooting_helpers …`) is a known failure mode. Tell the user the exact
command you ran, e.g.:

```bash
source /opt/ros/jazzy/setup.bash
python3 ~/.claude/skills/ros2-troubleshooting/scripts/check_qos_compat.py --topic /scan
```

Run these before manual diagnosis — they turn physical checks into pass/fail facts:
- `check_imu_gravity.py [--topic /imu/data]` — robot at rest: gravity must be ~+9.81 on +Z (REP 103). Catches flipped/rotated IMU mounts.
- `check_odom_direction.py [--topic /odom]` — push the robot forward ~1 m; odometry displacement must be positive along heading. Catches inverted motors/encoders/TF.
- `check_tf_tree.py --sensors laser_frame,imu_link` — verifies `map->odom->base_link` resolves and prints each sensor mount as RPY degrees to compare against the physical mounting. It **always** prints a `VERIFY PHYSICALLY` advisory for a ~180 deg roll or yaw, including when that mounting is intentional — the advisory is a prompt to compare against the hardware, not a verdict that the TF is wrong. Do not tell the user a correct transform will pass without flagging.
- `check_qos_compat.py --topic /scan` — checks every publisher/subscriber pair on a topic for DDS QoS incompatibility. Catches the silent "topic publishes at 30 Hz but my subscriber receives nothing" case (BEST_EFFORT pub vs RELIABLE sub, VOLATILE pub vs TRANSIENT_LOCAL sub).

## 3. Official References
- **REP 103 Standard Units & Coordinate Conventions**: `https://www.ros.org/reps/rep-0103.html`
- **REP 105 Coordinate Frames**: `https://www.ros.org/reps/rep-0105.html`
- **ROS 2 TF2 Concepts**: `https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html`
