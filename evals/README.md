# Evals — measure the skills instead of trusting them

Reproducible A/B tasks: run each prompt in a **fresh Claude Code session**
twice — once in a project *without* these skills, once *with* them installed —
and grade both transcripts against the checklist. No results are published
here until they come from a real run; PRs attaching graded transcripts are
welcome.

## Protocol

1. `mkdir baseline && cd baseline && claude` → paste the task prompt. Save the
   transcript.
2. `mkdir with-skills`, install the skills + `CLAUDE.md` there
   (see [Quickstart](../README.md#quickstart)), `claude` → paste the same
   prompt. Save the transcript.
3. Grade both with the task's checklist. Every symbol (class, method, message
   field, parameter) the agent wrote must be verified against
   `/opt/ros/jazzy/` (`ros2 interface show`, `python3 -c "import ..."`) or the
   linked Jazzy docs — a symbol that doesn't exist there counts as a
   hallucination regardless of how plausible it looks.

Score per task: `hallucinated symbols (count)`, `checklist items met (n/N)`,
`did the agent verify before writing (yes/no)`.

## Task 1 — sensor subscription (`ros2-core`)

> Write a Python node for ROS 2 Jazzy that subscribes to `/scan`
> (`sensor_msgs/msg/LaserScan`) and logs the minimum range once per second.

| Check | Verify with |
| :--- | :--- |
| Uses a sensor-data QoS (BEST_EFFORT), not the default depth-10 RELIABLE | `rclpy.qos.qos_profile_sensor_data` exists |
| Field names are real: `ranges`, `range_min`, `range_max` | `ros2 interface show sensor_msgs/msg/LaserScan` |
| Handles `inf`/empty `ranges` without crashing | read the code |
| No invented rclpy APIs (e.g. fake timer or logger signatures) | `python3 -c "import rclpy; ..."` |

## Task 2 — inverted sensor mount (`ros2-troubleshooting`)

> My robot's LiDAR is physically mounted upside-down on the back of the chassis,
> facing backward. Nav2 keeps colliding with obstacles behind the robot. Write
> the static TF for it and tell me how to confirm the fix.

| Check | Verify with |
| :--- | :--- |
| Asks about / states the physical mounting before writing the transform | transcript |
| RPY encodes both roll≈180° (upside-down) and yaw≈180° (backward) | `scripts/check_tf_tree.py --sensors <frame>` |
| Frame naming follows REP 105 (`base_link` parent, sensor child) | transcript |
| Recommends a physical confirmation (echo raw scan, walk around robot), not just "it launches" | transcript |

## Task 3 — silent QoS mismatch (`ros2-core` / `ros2-troubleshooting`)

> My subscriber to `/camera/image_raw` never receives messages, but
> `ros2 topic hz /camera/image_raw` shows 30 Hz. The code compiles and the node
> starts fine. What's wrong?

| Check | Verify with |
| :--- | :--- |
| Diagnoses reliability mismatch (BEST_EFFORT pub vs RELIABLE sub) as the prime suspect | transcript |
| Suggests inspecting actual endpoint QoS (`ros2 topic info -v` or `scripts/check_qos_compat.py`) instead of guessing | transcript |
| The fix uses a real QoS API, not an invented one | Jazzy docs / `rclpy.qos` |

## Task 4 — version drift (`ros2-dev`)

> Set up Nav2 with the MPPI controller for a differential-drive robot on
> Jazzy. Give me the controller server YAML.

| Check | Verify with |
| :--- | :--- |
| Every parameter name exists in Jazzy MPPI docs (critics list, `motion_model`, etc.) | https://docs.nav2.org/configuration/packages/configuring-mppic.html |
| No Humble/Iron-era leftovers or renamed params | same page |
| `motion_model` matches diff-drive (`DiffDrive`) | same page |
