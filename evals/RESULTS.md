# Eval results — 2026-07-25

First measured run of the [protocol](./README.md). All artifacts and final
responses are committed under [`runs/2026-07-25/`](./runs/2026-07-25/).

## Conditions

| | |
| :--- | :--- |
| Harness | Claude Code CLI 2.1.218, headless (`claude -p`), fresh directory per run |
| Model | `sonnet` for both conditions (identical per pair); a `haiku` pair below tests model-size sensitivity |
| Baseline | Empty directory — no skills, no `CLAUDE.md` |
| With skills | `CLAUDE.md` + `skills/` copied to `.claude/skills/` per the Quickstart |
| Tools | `acceptEdits`; WebFetch/WebSearch explicitly allowed in Task 4 runs (both conditions) |
| Grading | Every symbol verified against the `jazzy` branch of the upstream sources (`common_interfaces`, `navigation2`) — no local ROS install on the eval machine, so `/opt/ros/jazzy/` checks were substituted with the exact pinned sources |
| Sample size | **n=1 per cell.** This is one honest run each, not a statistic. |
| Independence | **None yet — disclosed conflict of interest.** The protocol was designed, the runs executed, and the outputs graded by the same agent session that maintains this repo. Mitigations: every artifact and final response is committed under `runs/`, and grading is mechanical (does the symbol exist in the pinned Jazzy sources?), so anyone can re-grade without trusting us. Independent re-grades and adversarial task PRs are the point of the protocol. |

## Task 1 — sensor subscription (`/scan` monitor)

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| Sensor-data QoS | ❌ `create_subscription(..., 10)` — default RELIABLE | ✅ `qos_profile_sensor_data` |
| Real message fields | ✅ `ranges` | ✅ `ranges`, `range_min`, `range_max` |
| Handles `inf`/empty | ⚠️ `isfinite` only, no `range_min/range_max` bounds | ✅ finite **and** in-bounds filter |
| No invented APIs | ✅ | ✅ |
| Logs once per second | ⚠️ log-throttle tied to message arrival | ✅ independent 1 Hz timer |
| Verified before writing | ❌ nothing consulted | ✅ cited the skill's QoS rule |

**The decisive defect:** against a real LiDAR driver (which publishes
BEST_EFFORT), the baseline's RELIABLE subscription matches nothing at the DDS
level — the callback **never fires**, and because its logging is
throttle-based rather than timer-based, the node is silent instead of saying
"no scan received yet". The code compiles, looks clean, and reviews well.
`scripts/check_qos_compat.py` flags exactly this. Zero hallucinated symbols
in either run — the failure skills prevented here was a *silently wrong
default*, not an invented name.

## Task 4 — Nav2 MPPI controller YAML (Jazzy)

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| All params exist in Jazzy | ✅ 0 hallucinations (verified against `optimizer.cpp`, `cost_critic.cpp`) | ✅ 0 hallucinations |
| No pre-Jazzy leftovers | ✅ | ✅ |
| `motion_model: DiffDrive` | ✅ | ✅ |
| Verified before writing | ❌ WebFetch was allowed; used **0 times** — pure recall | ✅ fetched `nav2_bringup` Jazzy defaults live, stated so |

**Honest read: output correctness tied.** Sonnet has current Nav2 MPPI
defaults memorized, so recall happened to be right *this time, on this
distro*. The measured difference is process: the with-skills run produced a
config whose every value is traceable to the pinned Jazzy source; the
baseline produced the same quality **unverifiably** — the exact behavior that
turns into version drift the day the API moves. Notably, in a first run
where WebFetch was not allowed, the with-skills agent **refused to emit
unverified parameters** and asked for verification access instead of
guessing (transcript in `runs/`); the baseline never noticed it hadn't
checked anything.

## Task 4 re-run on a smaller model (haiku)

Same prompt, same conditions, model swapped to `haiku` in both cells — testing
whether the sonnet baseline's clean recall was the model, not the task.

| Check | Baseline (haiku) | With skills (haiku) |
| :--- | :--- | :--- |
| All params exist in Jazzy | ❌ **~21 invented or wrong names** | ✅ 0 hallucinations |
| Plugin string | ❌ `mppi_controller::MPPIController` — wrong namespace, controller server fails to load the plugin at startup | ✅ `nav2_mppi_controller::MPPIController` |
| No pre-Jazzy leftovers | ❌ `progress_checker_plugin` (pre-Iron singular) | ✅ |
| `motion_model: DiffDrive` | ❌ invented `model_name: "DiffDriveROS"` | ✅ |
| Critic names | ❌ invented `CollisionCritic`, `PathFollowingCritic` | ✅ all eight real |
| Used the allowed WebFetch | ❌ 0 times | output is value-for-value identical to the pinned Jazzy `nav2_bringup` defaults (incl. `costmap_update_timeout: 0.30`, `near_collision_cost: 253`, `use_realtime_priority`) — three params the same model invented nonsense for in baseline |

The baseline's invented block (`max_velocity: [0.5, 0.0]`, `cost_weights:`,
`constraints:` …) is plausible-looking YAML that has never existed in any
`nav2_mppi_controller` release; the wrong plugin namespace alone means Nav2
dies on startup. With skills, the smaller model matched the larger model's
verified output. (Caveat: `claude -p` transcripts capture only the final
message, so haiku's retrieval isn't narrated the way sonnet's was; the
byte-level match with the pinned source is the evidence. Future runs should
use `--output-format stream-json` to log tool calls directly.)

---

# Re-run — 2026-07-25 (after the skill restructure)

The skills changed substantially (gates added to `CLAUDE.md`, `ros2-dev` split
into a decision body + `references/`), so Task 4 was re-run against the pinned
Jazzy `nav2_bringup/params/nav2_params.yaml`. **The `21 → 0` headline above did
not reproduce.** Conditions: CLI 2.1.220, `--model haiku`, `--output-format
json`/`stream-json`, WebFetch/WebSearch/Read/Bash allowed in both cells.

| | Baseline | With skills (run 1) | With skills (run 2) |
| :--- | :--- | :--- | :--- |
| Cost (USD) | 0.0283 | 0.0481 | 0.0425 |
| Turns | 2 | 6 | 6 |
| Verification tools used | **0** | skill + local defaults + both `references/` | skill + 3 attempts to find local defaults |
| Plugin string | ✅ `nav2_mppi_controller::MPPIController` | ✅ | ✅ |
| `motion_model` | ❌ invented `motion_model_type` | ✅ | ✅ |
| Checker namespace | ❌ `nav2_core::` | ✅ `nav2_controller::` | ✅ |
| `critics:` list | ❌ **absent entirely** | ⚠️ 5 real + `KeepOutCritic`, `ObstaclesCritic` | ⚠️ 7 real + `MaximumSpeedCritic` |
| Velocity/accel keys | ❌ `max_velocity_x`, `max_accel_x`, `noise_sigma_*` | ❌ `max_vel_x`, `max_decel_x` | ❌ `max_vel`, `noise_std` |
| Critic parameter keys | — (no critics) | ⚠️ invented `type:`, `angle_threshold` | ❌ `goal_weight`, `path_align_weight` … (real: all `cost_weight`) |
| **Wrong/invented keys (approx.)** | **~30** | **~16** | **~20** |

## What this actually shows

1. **The baseline is catastrophically wrong and the skills clearly help.** A
   config with no `critics:` list and `motion_model_type` cannot run MPPI at
   all. Both with-skills runs got the plugin string, `motion_model`, and the
   checker namespaces right.
2. **But "0 hallucinations" is not reproducible.** Both with-skills runs still
   invented critic names and parameter keys. The earlier `0` should be read as
   one lucky run, not a property of the skills.
3. **Neither eval run could read `/opt/ros/jazzy/`** — there is no ROS on the
   eval machine. The skill's first instruction is "read the shipped defaults",
   so both with-skills runs were forced onto their fallback path. **This test
   measures the degraded path, not the intended one.** Task 4 must be re-run
   inside a `ros:jazzy` container before any claim about MPPI accuracy stands.
   *(Done — see [Container run](#container-run--2026-07-25-live-optrosjazzy)
   below: with the live install readable, the invented-key count went to 0.)*
4. **Progressive disclosure is probabilistic.** Run 1 read both `references/`
   files; run 2 tried the local install three times and then wrote from memory
   without ever opening them. A pointer is a suggestion, not a guarantee — and
   run 2's output was the worse of the two.
5. **A defect in the repo's own reference file propagated into output.**
   `references/symbols.md` listed four MPPI critics including `ObstaclesCritic`;
   Jazzy ships eight, and uses `CostCritic` instead. Run 1 emitted
   `ObstaclesCritic` verbatim. Fixed and re-verified against the pinned source —
   a reference file is exactly as dangerous as inline content when it's wrong.
6. **The behavioral layer worked.** Run 2 asked the three `ros2-dev` gate
   questions (footprint, sim vs hardware, localization source) and stated
   plainly that it could not reach the local install — the `CLAUDE.md`
   "say so if you couldn't verify" rule, visible in the output.

Artifacts for re-grading are not committed for this run (they contain absolute
scratch paths); the commands to reproduce are in [`README.md`](./README.md).

---

# Container run — 2026-07-25 (live `/opt/ros/jazzy`)

The run the previous section said was required: same protocol, executed inside
an `osrf/ros:jazzy-desktop` container with `ros-jazzy-nav2-bringup` installed,
so `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml` physically
exists and `ros2`/`colcon` actually run. CLI 2.1.220, `--model haiku` both
cells, `--output-format stream-json` (tool calls logged), WebFetch/WebSearch/
Read/Glob/Grep/Write/Bash allowed in both cells, fresh directory per cell.
Artifacts committed under [`runs/2026-07-25-container/`](./runs/2026-07-25-container/).

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

1. **The intended path now has a measurement.** With `/opt/ros/jazzy` readable,
   the with-skills agent read the shipped defaults directly and produced a
   config with **zero invented keys, verified by mechanical diff** — the
   degraded-path caveat from the previous section is resolved.
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

## Takeaways

1. Where the base model's memory is good (sonnet × MPPI defaults), skills
   convert "probably right" into "verified right" at the cost of a few doc
   fetches.
2. Where the base model's habit is wrong (default QoS on sensor topics),
   skills prevent a silent functional failure that no compiler, linter, or
   log inspection would catch.
3. Where the base model's memory is weak (haiku × MPPI), skills are the
   difference between a config that can't start Nav2 and one identical to
   the verified defaults — the smaller the model, the larger the effect.
4. Verification behavior separated the conditions completely: 0/3 baseline
   runs consulted anything despite WebFetch being allowed; every with-skills
   run either demonstrably verified, produced output traceable to the pinned
   source, or refused to answer without the means to check.
