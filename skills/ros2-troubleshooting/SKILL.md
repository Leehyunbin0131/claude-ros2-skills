---
name: ros2-troubleshooting
description: "Diagnose ROS 2 Jazzy faults that reading the code cannot settle: QoS mismatch, sensor-mount and frame errors (REP 103/105), and odometry calibrated against CAD instead of the floor. Ships four runnable pass/fail checks."
---

# ROS 2 troubleshooting

Most of this skill is scripts that turn a suspicion into an exit code. Run one
before reasoning about the symptom.

## Bundled checks

`scripts/` sits next to this file — resolve the path from this skill's own
directory, not the user's CWD. Set `ROS2_SKILL_DIR` to the absolute directory
containing the loaded `SKILL.md`; this variable is not supplied by the assistant.
This works with Claude Code and Codex, for project and user installations.

They are plain scripts: invoke with `python3` and a real path. There is no
package to `ros2 run`, and inventing one is a known failure mode. Exit code
**0 = PASS, 1 = FAIL, 2 = inconclusive/invalid request**. Tell the user the command you ran.

```bash
source /opt/ros/jazzy/setup.bash
ROS2_SKILL_DIR="/absolute/path/to/ros2-troubleshooting" # Replace with the loaded skill directory.
python3 "${ROS2_SKILL_DIR}/scripts/check_qos_compat.py" --topic /scan
```

| Script | Answers |
| :--- | :--- |
| `check_qos_compat.py --topic /scan` | Why a healthy publisher delivers nothing to this subscriber |
| `check_tf_tree.py --sensors laser_frame,imu_link` | Does `map->odom->base_link` resolve? Prints sensor mount RPY for comparison with the hardware |
| `check_imu_gravity.py [--topic /imu/data]` | On a level robot, is measured gravity ~+9.81 on +Z in `--base base_link` after declared TF or with `--assume-aligned`? Requires ≥2 samples; RMS variation >1.5 m/s² (adjustable via `--max-variation`) returns inconclusive for motion, vibration or noise. Neither declared TF nor `--assume-aligned` proves physical stillness; yaw is not observable. Missing TF is inconclusive without `--assume-aligned` |
| `check_odom_direction.py [--topic /odom]` | Does odometry agree with the direction the robot physically moved |

`check_tf_tree.py` prints `VERIFY PHYSICALLY` for any ~180° roll or yaw **even
when that mounting is deliberate**. It asks for a comparison against the
hardware; it is not a verdict. Report it that way.

## References

Load the one the symptom points at.

- **`references/frames.md`** — REP 103/105 axis conventions, and the
  misalignment symptoms that follow from getting them wrong. `CLAUDE.md` treats
  this file as ground truth for any frame or TF question.
- **`references/runtime.md`** — what a QoS mismatch actually looks like on
  Jazzy, the two other policies that fail the same way, and why `ros2 topic
  echo` cannot detect any of them.
- **`references/calibration.md`** — correcting `diff_drive_controller` wheel
  radius and separation against a tape measure, in the order that works. Read
  when odometry is consistent but wrong by a ratio.
