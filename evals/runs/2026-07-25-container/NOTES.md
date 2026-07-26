<!-- Detailed write-up for this run. The summary that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Container run — 2026-07-25 (live `/opt/ros/jazzy`)

Task 4 and Task 5, executed inside
an `osrf/ros:jazzy-desktop` container with `ros-jazzy-nav2-bringup` installed,
so `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml` physically
exists and `ros2`/`colcon` actually run. CLI 2.1.220, `--model haiku` both
cells, `--output-format stream-json` (tool calls logged), WebFetch/WebSearch/
Read/Glob/Grep/Write/Bash allowed in both cells, fresh directory per cell.
Artifacts committed under [`runs/2026-07-25-container/`](./).

## Task 4 — MPPI YAML, graded against the installed file

The with-skills agent did not answer on the first turn: it asked the four
`ros2-dev` gate questions (footprint, existing vs fresh params, localization
source, velocity limits) and named the exact file it would read next. The
session was resumed once with the answers — that second turn is part of the
measured cost below. The baseline answered immediately.

| | Baseline | With skills |
| :--- | :--- | :--- |
| Cost (USD) / wall time | 0.0196 / 11 s | 0.0517 total (0.0255 + 0.0262) / 35 s |
| Verification tools used | **0** | **Read `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml`** — the live install, not a doc fetch |
| Plugin string | ❌ `mppi_generic::ControllerServer` (does not exist) | ✅ `nav2_mppi_controller::MPPIController` |
| `controller_plugins` wiring | ❌ absent — the `FollowPath` block would be ignored | ✅ |
| `critics:` list | ❌ absent entirely | ✅ all eight, correct names |
| `motion_model` | ❌ invented `motion_model_type` + `model_name` | ✅ |
| Invented/wrong keys | **~16** (`model_name`, `wz_min`, `path_tracking_cost`, `goal_cost`, `smooth_cost`, optimizer-level `collision_cost`, `near_goal_max_lin_vel`, `map_downsample_factor`, `visualize_scale`, `prune_plan`, `use_feedforward`, `allow_reversing`, a `parameters:` nesting level, a `controller_out:` node — each absence confirmed by grep over the pinned `nav2_mppi_controller` sources) | **0 — graded mechanically**: a script diffed every key in the output against the installed `controller_server` section; the extra-key set is empty |

## Task 5 — build wiring, end to end (first run of this task)

Binary outcome. All three commands were re-executed independently by the
grader in each workspace after the agent finished — the grades below are from
those re-runs, not from the agents' own claims.

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| `ros2 run demo_pkg …` | ❌ `Package 'demo_pkg' not found` | ✅ publishes at 1 Hz |
| `ros2 launch demo_pkg …` | ❌ `package 'demo_pkg' not found, searching: ['/opt/ros/jazzy']` | ✅ node starts |
| `ros2 topic echo /greeting` | ❌ topic never published | ✅ data flowing |
| Cost / turns / wall time | **0.172 USD / 36 turns / 178 s** (35 tool calls) | **0.079 USD / 18 turns / 61 s** (15 tool calls) |
| Final report accuracy | claimed "✅ Build & Test Results … functioning correctly" — none of the three commands work | claims match the independent re-run |

The transcripts explain the cost gap. The baseline nested `launch/` inside the
Python module, then added a `CMakeLists.txt` to an `ament_python` package,
rebuilt three times, fell back to `PYTHONPATH` hacks and `pkill -9 -f ros` —
and the package never registered in the ament index. The with-skills run
loaded `ros2-package`, ran `ros2 pkg create --build-type ament_python`, wired
`console_scripts` and the launch `data_files`, built once, sourced, and proved
it with `ros2 topic echo` — the sequence the skill prescribes, executed once.

## What the container run establishes

1. **The intended path is what was measured.** With `/opt/ros/jazzy` readable,
   the with-skills agent read the shipped defaults directly and produced a
   config with **zero invented keys, verified by mechanical diff**. The skill's
   first instruction is "read the installed defaults", so this — not a run on a
   machine without ROS — is the condition the design assumes.
2. **The gates fired in the wild.** Unprompted, the agent asked exactly the
   questions `ros2-dev` §1 lists before writing anything — and the second
   turn's output honored the answers (0.5 m/s and 1.9 rad/s appear in the YAML).
3. **On the only task with a binary outcome, skills were correct *and* 2.2×
   cheaper.** The baseline spent its extra $0.09 and 25 turns on corrections
   that never converged. "One correct pass beats many corrections" is now a
   number, not a slogan.
4. **The baseline reported success on a broken deliverable.** Its final message
   asserts working build-and-test results for a package `ros2 run` cannot even
   find. This — not exotic API hallucination — is the failure mode the
   "prove it ran" rule exists to catch.

---
