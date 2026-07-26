# Evals — measure the skills instead of trusting them

Reproducible A/B tasks: run each prompt in a **fresh Claude Code session**
twice — once in a project *without* these skills, once *with* them installed —
and grade both transcripts against the checklist. No results are published
here until they come from a real run; PRs attaching graded transcripts are
welcome.

## Protocol

1. `mkdir baseline && cd baseline` → run the task prompt headlessly, capturing cost:
   ```bash
   claude -p "<task prompt>" --output-format json > result.json
   ```
   The result object carries token usage and `total_cost_usd` alongside the reply.
   Use `--output-format stream-json` when you also need the tool calls (which docs
   the agent actually fetched) rather than only the final message.
2. `mkdir with-skills`, install the skills + `CLAUDE.md` there
   (see [Quickstart](../README.md#quickstart)), run the same prompt the same way.
3. Grade both with the task's checklist. Every symbol (class, method, message
   field, parameter) the agent wrote must be verified against
   `/opt/ros/jazzy/` (`ros2 interface show`, `python3 -c "import ..."`) or the
   linked Jazzy docs — a symbol that doesn't exist there counts as a
   hallucination regardless of how plausible it looks.

Score per task:

| Metric | Why it's here |
| :--- | :--- |
| hallucinated symbols (count) | the failure the skills exist to prevent |
| checklist items met (n/N) | output quality |
| verified before writing (yes/no) | process, not luck |
| **tokens in / out, `total_cost_usd`** | a skill that buys +2% quality for +5k tokens is a bad trade — without this number, "should this content stay?" is opinion |

**Cost is a first-class result.** Report it in both conditions even when quality
ties: the with-skills run paying for doc fetches is the honest price of
verification, and a change that grows it without moving the other columns should
be reverted.

## Running a pair with the harness

Tasks 1–3 are automated. [`harness/run_ab.sh`](./harness/run_ab.sh) brings up the
live scenario the task needs, runs both cells with identical flags in fresh
directories, and reduces each transcript with
[`harness/summarize_run.py`](./harness/summarize_run.py) so the tool calls each
cell actually made are counted rather than recalled:

```bash
# needs a sourced ROS 2 Jazzy install; ros-jazzy-ros-base is enough for 1-3
MODEL=haiku ./evals/harness/run_ab.sh 1 evals/runs/$(date +%F)-native
```

The scenario differs per task, and the same one is up for **both** cells:

| Task | Live scenario | Why |
| :--- | :--- | :--- |
| 1 | [`fake_scan_pub.py`](./harness/fake_scan_pub.py) — `/scan` at 5 Hz, BEST_EFFORT, with `inf`, `nan`, a below-`range_min` and an above-`range_max` reading | a default RELIABLE subscriber must fail to receive, and only bounds filtering finds the true minimum (0.45 m) |
| 2 | `map→odom→base_link` only | writing the sensor transform is the agent's job; grade its output by publishing it and running `check_tf_tree.py` |
| 3 | [`task3_scenario.sh`](./harness/task3_scenario.sh) — BEST_EFFORT camera at 30 Hz plus a default-RELIABLE subscriber | reproduces the premise exactly: `ros2 topic hz` shows 30 Hz while the subscriber receives 0 |

Grade Task 1 by **running both generated nodes** against the publisher, not by
reading them: the QoS defect is invisible in review and unmissable at runtime.

## Running a pair in a Jazzy container

Tasks that verify against `/opt/ros/jazzy/` need ROS actually installed. The
`ros:jazzy` image is the reference environment:

```bash
docker run --rm -it -v "$PWD":/repo ros:jazzy bash
# inside the container, install the Claude Code CLI, then:
mkdir -p /tmp/ev/{baseline,with-skills/.claude/skills}
cp -r /repo/skills/* /tmp/ev/with-skills/.claude/skills/
cp /repo/CLAUDE.md /tmp/ev/with-skills/

P="Set up Nav2 with the MPPI controller for a differential-drive robot on Jazzy. Give me the controller server YAML."

cd /tmp/ev/baseline && claude -p "$P" --model haiku --output-format json \
  --permission-mode acceptEdits \
  --allowedTools WebFetch WebSearch Read Glob Grep Write Bash > result.json

cd /tmp/ev/with-skills && claude -p "$P" --model haiku --output-format stream-json --verbose \
  --permission-mode acceptEdits \
  --allowedTools WebFetch WebSearch Read Glob Grep Write Bash > result.jsonl
```

Grade against `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml`, and
record from the run metadata: cost, token counts, and **which files the agent
actually opened** (the `stream-json` tool calls answer whether it reached the
shipped defaults or fell back to `references/`).

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

## Task 5 — build wiring, end to end (`ros2-package`)

The only task here with a **binary, runtime** outcome. Run it inside a container
that has Jazzy installed (`ros:jazzy`), so the agent can actually build and run.

> In this workspace, create a ROS 2 Jazzy Python package `demo_pkg` with a node
> that publishes `std_msgs/msg/String` on `/greeting` at 1 Hz, plus a launch file
> that starts it. Build it and show me the output of `ros2 topic echo /greeting`.

| Check | Verify with |
| :--- | :--- |
| **`ros2 topic echo /greeting` prints messages** — the whole task in one bit | run it |
| `ros2 run demo_pkg <node>` works (console_scripts wired) | run it |
| `ros2 launch demo_pkg <file>` works (launch file installed, not just written) | run it |
| Agent rebuilt and re-sourced before declaring success | transcript |

Unlike Tasks 1–4, nothing here depends on a grader's judgement: either the topic
carries data or it doesn't.
