---
name: ros2-troubleshooting
description: "Diagnose ROS 2 Jazzy runtime faults where everything logs healthy and nothing works: QoS mismatch, frame/sensor-mount errors (REP 103/105), sim clock, lifecycle state, DDS domain. Ships runnable pass/fail checks."
---

# ROS 2 troubleshooting

Most of this skill is scripts that turn a suspicion into an exit code. Run one
before reasoning about the symptom.

## Bundled checks

`scripts/` sits next to this file — resolve the path from this skill's own
directory, not the user's CWD. Under a plugin install that is
`${CLAUDE_PLUGIN_ROOT}/skills/ros2-troubleshooting/scripts/`.

They are plain scripts: invoke with `python3` and a real path. There is no
package to `ros2 run`, and inventing one is a known failure mode. Exit code
**0 = PASS, 1 = FAIL, 2 = no data**. Tell the user the command you ran.

```bash
source /opt/ros/jazzy/setup.bash
python3 <this-skill>/scripts/check_qos_compat.py --topic /scan
```

| Script | Answers |
| :--- | :--- |
| `check_qos_compat.py --topic /scan` | Why a healthy publisher delivers nothing to this subscriber |
| `check_tf_tree.py --sensors laser_frame,imu_link` | Does `map->odom->base_link` resolve, and does each sensor's mount RPY match the hardware |
| `check_imu_gravity.py [--topic /imu/data]` | Is the IMU mounted the way the URDF claims — gravity ~+9.81 on +Z at rest |
| `check_odom_direction.py [--topic /odom]` | Does odometry agree with the direction the robot physically moved |

`check_tf_tree.py` prints `VERIFY PHYSICALLY` for any ~180° roll or yaw **even
when that mounting is deliberate**. It asks for a comparison against the
hardware; it is not a verdict. Report it that way.

## References

Load the one the symptom points at.

- **`references/frames.md`** — REP 103/105 axis conventions, and the
  misalignment symptoms that follow from getting them wrong. `CLAUDE.md` treats
  this file as ground truth for any frame or TF question.
- **`references/runtime.md`** — sim clock, lifecycle state, DDS domain, and
  what a QoS mismatch actually looks like on Jazzy.
