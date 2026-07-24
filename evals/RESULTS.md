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
