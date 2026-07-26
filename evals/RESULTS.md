# Eval results

Measured A/B pairs: the identical prompt run in a fresh, headless Claude Code
session twice — once without these skills, once with them — using the same model
in both cells. Only runs graded against a **live ROS 2 Jazzy install** are kept
here; earlier pairs measured on a machine with no ROS installed have been
superseded by the runs below and removed rather than carried along.

All artifacts and final responses are committed under [`runs/`](./runs/), and the
harness that produces the Task 1-3 pairs is in [`harness/`](./harness/).

## Conditions & disclosure

| | |
| :--- | :--- |
| Harness | Claude Code CLI 2.1.220, headless (`claude -p`), fresh directory per cell |
| Grading | Mechanical wherever possible: does the symbol exist in the installed package (`ros2 pkg prefix`, `ros2 interface show`, grep over the installed sources)? does the command succeed when re-run by the grader? |
| Sample size | **n=1 per cell.** These are single honest runs, not statistics. |
| Independence | **None — disclosed conflict of interest.** The protocol was designed, the runs executed, and the outputs graded by the same project that publishes them. Mitigations: artifacts are committed under `runs/` and grading is mechanical, so anyone can re-grade without trusting us. Independent re-grades and adversarial task PRs are the point of the protocol. |

---

# Container run — 2026-07-25 (live `/opt/ros/jazzy`)

Task 4 and Task 5, executed inside
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

# Simulation run — 2026-07-25 (Gazebo Harmonic, headless)

The last gap: "0 invented keys" proves the YAML is *spelled* correctly, not
that a robot obeys it. So both Task 4 outputs from the container run were
loaded into a live simulation. Environment: `osrf/ros:jazzy-desktop` container
+ `ros-jazzy-nav2-bringup`, `ros-jazzy-nav2-minimal-tb3-sim`, `ros_gz`
(Gazebo Sim 8.11), `gz sim` server-only (no GUI, software rendering).
Each YAML was spliced verbatim into the shipped `nav2_params.yaml` — the
`controller_server:` section replaced wholesale — and launched with
`nav2_bringup tb3_simulation_launch.py headless:=True`. Artifacts (params
files, launch logs) in [`runs/2026-07-25-sim/`](./runs/2026-07-25-sim/).

## A/B: do the two YAMLs actually drive a robot?

| | Baseline YAML | With-skills YAML |
| :--- | :--- | :--- |
| Controller plugin load | **`[FATAL] Failed to create controller … class mppi_generic::ControllerServer … does not exist`** — Nav2 aborts bringup; nothing ever moves | `Created controller : FollowPath of type nav2_mppi_controller::MPPIController`, all **8 critics loaded** |
| `NavigateToPose` (−2.0, −0.5) → (0.5, 0.5) | unreachable — no controller server | **`Goal finished with status: SUCCEEDED`**; final AMCL pose (0.15, 0.53), inside the goal checker's tolerance |
| Sensor pipeline during the run | — | `/scan` 5 Hz, `/odom` 28 Hz through `ros_gz_bridge`, MPPI consuming both |

One incident during with-skills bringup, honestly noted: `global_costmap`
activation timed out on its first attempt because the operator (this session)
published the AMCL initial pose *after* the 60 s activation window — a launch
sequencing issue, not a parameter issue. After publishing the pose and
re-activating the remaining lifecycle nodes, the same params file ran to
`SUCCEEDED` with no further intervention. The baseline failure, by contrast,
is unrecoverable: the plugin class it names does not exist in the registry.

## Verification scripts against live data — first time

Until now `skills/ros2-troubleshooting/scripts/` had only pure-logic unit
tests. Run against the live simulation:

| Script | Result | What it means |
| :--- | :--- | :--- |
| `check_tf_tree.py --sensors base_scan` | **[OK]** — resolved `map → odom → base_link`, printed the real TB3 mount (x −0.064 m, z +0.122 m, level) | works on a live tree |
| `check_tf_tree.py --sensors rear_lidar` (Task 2 scenario: static TF published with roll 180°, yaw 180°) | **flagged both**: "declared UPSIDE-DOWN … declared FACING BACKWARD … If the sensor is NOT physically mounted that way, this TF is the bug" | the Task 2 diagnostic works end to end |
| `check_qos_compat.py --topic /scan` | **[PASS] × 4** endpoint pairs (`ros_gz_bridge` → amcl, collision_monitor, both costmaps) | live endpoint introspection works |
| `check_odom_direction.py` while driving forward | **[PASS]** "+1.64 m along the initial heading" over a 14 s non-interactive window — sign and magnitude match the commanded forward motion ([`odom_check2.log`](./runs/2026-07-25-sim/odom_check2.log)) | direction logic confirmed against real motion |
| `check_imu_gravity.py --topic /imu` | **[FAIL]** `|a| = 0.01` — and that verdict is *correct*: the sim's IMU publishes gravity-free acceleration, which violates the REP 103/145 expectation the script tests (gravity must appear as ~+9.81 m/s² on +Z at rest) | the check catches a genuinely non-physical sensor config, which is its job |

**Defect found and fixed.** `check_odom_direction.py` blocked on `input()` and
died with `EOFError` when run without a terminal — unusable headless/CI. Fixed
in the same commit: `--wait-secs N` for non-interactive use, and a closed-stdin
fallback that waits instead of crashing. Re-verified in the sim ([PASS],
`odom_check2.log`) and the pure-logic unit tests still pass (7 groups).

## What the simulation run establishes

1. **The chain is now closed end to end**: skill → gate questions → read the
   installed defaults → 0 invented keys → plugin loads → **robot reaches the
   goal**. Every link measured, none assumed.
2. **The baseline's ~16 invented keys were never the whole story** — its single
   wrong plugin string alone kills the entire Nav2 stack at bringup, before any
   other key is even parsed.
3. **The verification scripts survived first contact with live data**, caught a
   real non-physical sensor config, and the one defect the exercise exposed was
   in *our* tooling — found because we ran it, fixed, and re-verified.

---

# Native-install run — 2026-07-26 (Tasks 1–3, live `/opt/ros/jazzy`)

Roadmap item 3: the three remaining tasks, measured against a live install for
the first time. No container this time — `ros-jazzy-ros-base` installed natively
on Ubuntu 24.04 (WSL2), which satisfies the same grading criterion (the agent can
read the real install and actually run nodes). Artifacts under
[`runs/2026-07-26-native/`](./runs/2026-07-26-native/); the harness that produced
them is committed in [`harness/`](./harness/) so the pairs are re-runnable.

| | |
| :--- | :--- |
| Harness | CLI 2.1.220, `claude -p`, `--output-format stream-json` in **both** cells (so "tools used" is counted from the transcript, not recalled), `acceptEdits`, `--allowedTools WebFetch WebSearch Read Glob Grep Write Bash`, fresh `mktemp -d` per cell |
| Model | `haiku` in both cells |
| Environment | native `ros-jazzy-ros-base`, `rmw_fastrtps_cpp`, 194 packages |
| Live scenario | up for both cells: a BEST_EFFORT `/scan` publisher (Task 1), `map→odom→base_link` only (Task 2 — writing the sensor TF is the agent's job), a 30 Hz BEST_EFFORT camera + default-RELIABLE subscriber (Task 3) |
| Sample size | **n=1 per cell**, same disclosed conflict of interest as above |

## Task 1 — `/scan` monitor, graded by running it

Both agents wrote a node; both nodes were then run for 6 s against the live
publisher. The scan contains `inf`, `nan`, a below-`range_min` value (0.02) and
an above-`range_max` value (99.0); **the correct in-bounds minimum is 0.45 m.**

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| Subscription QoS | ❌ `create_subscription(..., 10)` → RELIABLE | ✅ `qos_profile_sensor_data` |
| **Messages actually received** | ❌ **zero.** rclpy itself logged `New publisher discovered on topic '/scan', offering incompatible QoS. No messages will be received from it. Last incompatible policy: RELIABILITY` | ✅ receives at 5 Hz |
| Reported minimum | — (never received; logged `Awaiting first scan message...` every second) | ⚠️ **`0.020 m` — wrong**, the below-`range_min` reading |
| `range_min`/`range_max` bounds filter | ❌ absent (`r > 0 and r != inf`) | ❌ absent (`not float('inf') == r`) |
| `nan` handling | ✅ incidentally excluded by `r > 0` | ❌ `nan` passes the filter |
| Independent 1 Hz timer | ✅ | ✅ |
| Says something when no data | ✅ | ✅ |
| Turns / cost / tool calls | 2 / $0.0307 / 1 | 4 / $0.0344 / 2 (`Skill: ros2-core`, `Write`) |

**Honest read: skills win the decisive bit and both fail the numeric one.** Only
the with-skills node connects at all — that is the difference between a working
sensor pipeline and a node that will never fire, and it is what the skill's QoS
rule exists to produce. But neither node filters against `range_min`/`range_max`,
so the with-skills node confidently reports `0.020 m` instead of `0.45 m`. The
baseline's identical bug is merely invisible because it never receives data.

**One nuance worth stating precisely.** The QoS failure is silent *at the DDS
level*, which is where it matters — but it is not necessarily silent in the logs.
This baseline logs on a timer, so it repeats `Awaiting first scan message...`
forever, and Jazzy's rclpy prints an incompatible-QoS warning of its own. The
argument for the skill's QoS rule rests on the middleware behavior (zero messages
delivered), not on the claim that nothing is printed.

## Task 2 — inverted LiDAR TF

Graded on the transcript **and** by publishing each agent's transform verbatim
and running the diagnostic on it ([`t2_agent_output_check.log`](./runs/2026-07-26-native/t2_agent_output_check.log)).

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| Asks about the physical mounting before writing | ❌ answered in one turn | ✅ **asked the back-distance / offset question first**, before emitting the transform |
| RPY encodes roll≈180° **and** yaw≈180° | ✅ | ✅ |
| REP 105 parent/child (`base_link` → sensor) | ✅ | ✅ |
| Published output flagged by `check_tf_tree.py` | ✅ both roll and yaw flagged | ✅ both flagged |
| Jazzy argument form | ✅ named args | ⚠️ named args in the launch file, but the "one-liner" uses the **positional form**, which the install answers with `[WARN] Old-style arguments are deprecated` |
| Invented symbols | ❌ a `static_transforms:` YAML schema no core node consumes | ❌ **`ros2 run ros2_troubleshooting_helpers check_tf_tree.py` — no such package** (`ros2 pkg prefix` → `Package not found`) |
| Physical-confirmation advice | ⚠️ RViz, but a **PointCloud2** display for a LiDAR | ✅ `tf2_echo` + a **LaserScan** display + "points should wrap around the back" |
| Turns / cost / tool calls | 1 / $0.0254 / **0** | 3 / $0.0475 / 1 (`Skill: ros2-troubleshooting`) |

**The gate fired, and the skills still hallucinated.** The behavioral win is
real and reproducible — with skills the agent stopped and asked for the mounting
geometry, which is the checklist's first item and the thing that prevents 200
wrong lines. But the same answer invented a package name **for the skill's own
script**, and told the user the check "should show RPY matching your physical
mount without flagging ~180° as suspicious" — the opposite of what the script
does (it flags ~180° every time, by design). A skill that ships tooling has to
state how to invoke it, or the model will invent a plausible `ros2 run`.

## Task 3 — silent QoS mismatch

The premise was made real first: `ros2 topic hz /camera/image_raw` reported
**30.000 Hz** while the RELIABLE subscriber logged `images received: 0`
([`t3_hz.log`](./runs/2026-07-26-native/t3_hz.log),
[`t3_sub.log`](./runs/2026-07-26-native/t3_sub.log)).

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| Names reliability mismatch as prime suspect, first attempt | ✅ | ✅ |
| Recommends inspecting real endpoint QoS | ✅ `ros2 topic info --verbose` | ✅ `ros2 topic info -v` |
| **Actually inspected the live system** | ❌ 0 tool calls | ❌ loaded the skill, then answered — never ran the command it recommended |
| Fix uses a real QoS API | ✅ | ✅ |
| Factual accuracy of the QoS claim | ✅ | ❌ calls the default `(Reliable, **Transient Local**)`; the installed default is RELIABLE + **VOLATILE** (`QoSProfile(depth=10)` → `RELIABLE`, `VOLATILE`) |
| Turns / cost / tool calls | 1 / $0.0194 / 0 | 3 / $0.0271 / 1 (`Skill: ros2-core`) |

**Honest read: a tie the skills slightly lost.** Diagnosis is the one thing haiku
already knows cold — this is the single most-written-about ROS 2 failure, so both
cells nailed it in one turn. The with-skills cell added a wrong durability claim
and, despite a live reproduction sitting right there with `Bash` allowed,
recommended a command it did not run. Task 3 as written cannot separate the
conditions; a fair version would have to require the answer be *demonstrated*
against the live endpoints, not asserted.

## Verification scripts — the FAIL path, first time

Every previous live run of `check_qos_compat.py` returned PASS. The Task 3
scenario produced its first real failure:

```
[FAIL] fake_camera_pub -> reliable_image_sub
       reliability: publisher offers BEST_EFFORT, subscriber requests RELIABLE —
       subscriber will receive NOTHING; use qos_profile_sensor_data or a
       BEST_EFFORT subscription for sensor streams
exit code = 1
```

`check_tf_tree.py` was also tested for **specificity**, not just sensitivity: run
against a tree carrying both an inverted rear sensor and a correctly-mounted
forward one, it flagged the first for roll and yaw and left the second alone
([`t2_tf_check.log`](./runs/2026-07-26-native/t2_tf_check.log)).

## What this run establishes

1. **Tasks 1–3 now have live-install measurements.** Roadmap item 3 is closed;
   every task in the suite has been run against a real ROS 2 install.
2. **The QoS result is now a runtime fact, not a code review.** The baseline node
   received zero messages from a publisher visibly running at 5 Hz, and the
   middleware said why. This is the repo's central claim and it reproduces.
3. **The pre-write gate reproduces too** — third independent run in which the
   with-skills agent asked for physical/geometric facts before writing.
4. **Skills do not stop hallucination; they move it.** Two invented symbols in
   with-skills output across three tasks (`ros2_troubleshooting_helpers`, a wrong
   default durability), one of them about the repo's own tooling. Routing to docs
   raises the floor; it does not make the model correct.
5. **On tasks the model already knows, skills cost ~1.4× and buy little.**
   Baseline total $0.0755 vs with-skills $0.1090 across the three pairs. Task 3
   is the clear case: same answer, more money, one extra error.

## Follow-ups this run created

**Read the tables above as measurements of the skills as they were *before* these
fixes.** Everything marked applied below landed after the run, in the same commit
as this write-up; whether the fixes work is an open question until Tasks 1–3 are
re-run.

- ✅ **Applied.** `ros2-troubleshooting` §1a now gives the literal invocation
  (`python3 <skill-dir>/scripts/<name>.py`) and names `ros2 run
  ros2_troubleshooting_helpers` as a known failure mode. A skill that ships a
  script must state how to run it, or the model invents a package.
- ✅ **Applied.** `ros2-core` now carries the bounds rule as both a
  symptom→cause→action row and a strict rule: a `LaserScan` reading is usable only
  when finite **and** within `[range_min, range_max]`. "Filter `inf`" is what the
  model already does, and it produces a confidently wrong minimum.
- ✅ **Applied.** `ros2-core` gained the shutdown pattern — both agents' nodes died
  with `rcl_shutdown already called` / `ExternalShutdownException` on SIGTERM.
- ✅ **Applied.** `ros2-troubleshooting` now states that `check_tf_tree.py` always
  prints the `VERIFY PHYSICALLY` advisory for a ~180° roll or yaw, even when the
  mounting is intentional — the with-skills run told the user the opposite.
- ⏳ **Open.** Task 3's checklist should require a *demonstrated* inspection, not a
  recommended one, or it will keep scoring as a tie.
- ⏳ **Open.** Re-run Tasks 1–3 against the patched skills. The specific
  regressions to watch: does the Task 1 node now filter bounds, and does the
  Task 2 answer stop inventing a package?

---

# Post-fix re-run — 2026-07-26 (do the patches actually work?)

The previous section ended with four skill defects and applied fixes for all of
them. This is the run that tests whether the patches change behaviour, rather
than assuming they do. Identical protocol, identical prompts, same machine, same
model, fresh directories. Artifacts under
[`runs/2026-07-26-postfix/`](./runs/2026-07-26-postfix/).

**Verdict: two tasks fixed and verified at runtime, one task regressed — and the
regression has a specific, reproducible cause.**

## Task 1 — fixed, and now correct at runtime

| | Pre-fix (with skills) | Post-fix (with skills) | Post-fix baseline |
| :--- | :--- | :--- | :--- |
| Skill routed | `ros2-core` | `ros2-core` | — |
| Verification tool calls | 0 | **1** — ran `ros2 interface show sensor_msgs/msg/LaserScan` | 0 |
| Bounds filter | ❌ absent | ✅ `math.isfinite(r) and msg.range_min <= r <= msg.range_max` | ❌ absent |
| **Minimum reported, live** | `0.020 m` ❌ | **`0.450 m` ✅ correct** | never received a message |
| Shutdown on SIGTERM | ❌ traceback | ✅ clean, 0 tracebacks | ❌ traceback |
| Turns / cost | 4 / $0.0344 | 6 / $0.0438 | 2 / $0.0266 |

Both patched rules appear in the generated code close to verbatim, and the node
was executed against the live BEST_EFFORT publisher to confirm it. The baseline
is unchanged: rclpy still reports `Last incompatible policy: RELIABILITY` and the
node still receives nothing. **This is the first task in the suite where the
with-skills output is fully correct rather than merely better.**

## Task 2 — both defects fixed

The first turn asked four gate questions and deliberately withheld the transform,
so the session was resumed once with answers (the container-run pattern); the
resumed turn is where the fixed material appears.

| | Pre-fix | Post-fix |
| :--- | :--- | :--- |
| Script invocation | ❌ `ros2 run ros2_troubleshooting_helpers check_tf_tree.py` — no such package | ✅ `python3 ~/.claude/skills/ros2-troubleshooting/scripts/check_tf_tree.py --sensors rear_lidar` |
| What it says the check does | ❌ "should show RPY … **without** flagging ~180° as suspicious" | ✅ "**It will flag the ~180° roll/yaw as a `VERIFY PHYSICALLY` prompt** — that's expected; compare it against your actual mounted hardware" |
| Argument form | ⚠️ named args, plus a deprecated positional one-liner | ✅ named args only |
| Gate questions | 1 (back distance) | 4 (frame names, orientation decomposition, hardware vs sim, existing URDF/launch) |
| Turns / cost | 3 / $0.0475 | 3 + 1 / $0.0350 + $0.0372 |

## Task 3 — regressed, and worse than baseline

| | Pre-fix (with skills) | Post-fix (with skills) | Post-fix baseline |
| :--- | :--- | :--- | :--- |
| **Skill routed** | `ros2-core` | **`ros2-perception`** | — |
| Diagnosis correct, first turn | ✅ | ✅ | ✅ |
| Wrong durability claim | ❌ `TRANSIENT_LOCAL` | not made — **the patched skill was never loaded** | not made |
| Python QoS API | ✅ correct | ❌ **`rclcpp.qos.QoSProfile` in Python code** — `import rclcpp` raises `ModuleNotFoundError`; the snippet cannot run | ✅ correct |
| Inspected the live endpoints | ❌ | ❌ | ❌ |
| Turns / cost | 3 / $0.0271 | 3 / $0.0265 | 1 / $0.0186 |

## Why Task 3 regressed — mechanism, not speculation

Three findings, each checked against the install and the skill sources:

1. **Skill routing is non-deterministic across identical runs.** Same prompt,
   same model, same machine: the pre-fix run loaded `ros2-core`, the post-fix run
   loaded `ros2-perception`. The `/camera/image_raw` topic makes both plausible.
   Nothing about the fix caused this — it is variance that was always there and
   that the pre-fix run happened to hide.
2. **The fix was in a skill the router did not pick.** The durability correction
   went into `ros2-core`. `ros2-perception` has no QoS-policy guidance beyond one
   symptom row, so the patched text was never in context. A fix placed in one
   skill does not protect a task that routes elsewhere.
3. **The loaded skill actively caused the new defect.** `ros2-perception`'s
   examples are **exclusively C++** — `#include <rclcpp/rclcpp.hpp>`, cv_bridge
   and pcl_ros in C++ — and it is the only skill in the pack with no Python
   content at all. Of the 11 skills, **`ros2-core` is the only one that mentions
   `rclpy`**. Asked for a Python fix with nothing but `rclcpp::` in context, the
   model fused the two into `rclcpp.qos`. For a Python question, loading that
   skill was worse than loading nothing: the baseline, with no skill at all, got
   the API right.

The uncomfortable implication is that the pack's per-skill isolation — the thing
that makes it context-efficient — is also a correctness hazard. A rule is only
active if the router happens to select the file it lives in.

## What this run establishes

1. **The fixes work where they are loaded.** Task 1 went from a wrong number to
   the right one, verified by running the node, and Task 2's two defects are gone.
   Patching a skill body does change output, reproducibly and near-verbatim.
2. **Coverage of a rule matters as much as its content.** Two of three tasks
   improved; the third was untouched because the rule lived in the wrong file.
3. **A C++-only skill is a liability on a Python question.** This is the first
   measured case of the pack making output *worse* than baseline, and the cause is
   in the skill content, not the model.
4. **The post-write verification gap did not close.** Across pre- and post-fix
   runs, **0 of 4** with-skills cells ran the QoS inspection command they
   recommended, with a live reproduction running and `Bash` allowed. `CLAUDE.md`'s
   "done means it ran" governs code tasks; it does not reach diagnosis answers.
   Task 1 is the counter-example that shows the mechanism can work: there the
   agent did run `ros2 interface show` before writing.
5. **Cost:** baseline $0.0684 total across the three pairs, with-skills $0.1425
   including the resumed Task 2 turn (~2.1×), or $0.1053 excluding it (~1.5×).

## Follow-ups this run created

- ⏳ Duplicate the language guardrail. `rclpy` appears in exactly one of 11
  skills. Every skill that shows client-library code needs the C++/Python
  separation stated locally, or a shared rule must be promoted into `CLAUDE.md`
  where routing cannot miss it.
- ⏳ `ros2-perception` needs Python examples (`cv_bridge` in `rclpy`), not only
  C++ ones — it is routed for camera-topic questions that are frequently Python.
- ⏳ Re-run Task 3 several times to measure the routing distribution. With n=1 per
  cell, "which skill gets picked" is currently unmeasured variance sitting
  underneath every other number in this file.
- ⏳ Task 3 still cannot separate the conditions on diagnosis quality; require a
  demonstrated inspection.

## Takeaways

1. Where the base model already knows the answer (haiku × QoS diagnosis), skills
   convert "probably right" into "verified right" at the cost of a few doc
   fetches — and sometimes buy nothing at all.
2. Where the base model's *habit* is wrong (default QoS on sensor topics), skills
   prevent a silent functional failure that no compiler, linter, or log
   inspection would catch — measured twice now, and on 2026-07-26 confirmed at
   runtime: the baseline node received **zero** messages from a publisher running
   at 5 Hz.
3. Where the base model's memory is weak (haiku × Nav2 MPPI), skills are the
   difference between a config that aborts bringup and one whose every key matches
   the installed defaults — and the simulation run shows what that difference is
   worth: a robot that reaches the goal versus one that never moves.
4. **Knowing the answer and demonstrating it are different axes.** haiku
   diagnosed the QoS mismatch perfectly from memory (Task 3) and neither cell ran
   the one command that would have proven it. Skills reliably change what the
   agent *asks* before writing; they do not reliably change what it *checks*
   after.
5. No baseline cell in any run verified against the install or the docs *before*
   writing, despite WebFetch and Bash being allowed. The one baseline that used
   tools heavily — Task 5, 35 calls — spent them on corrections after the fact
   that never converged.
6. **Skills raise the floor; they do not make the model correct.** With-skills
   output has contained invented symbols in every measured round —
   `ros2_troubleshooting_helpers`, a wrong default durability, missing
   `range_min`/`range_max` bounds, `rclcpp.qos` in Python. The reproducible wins
   are structural — correct QoS, correct plugin strings, gate questions asked,
   claims that match an independent re-run — not "no hallucinations".
7. **Patching a skill body demonstrably changes output.** The 2026-07-26 post-fix
   run is the direct test: two of three defects were corrected near-verbatim, and
   Task 1's node went from a wrong minimum to the right one, confirmed by running
   it. This pack's content is causally connected to what the agent produces — the
   mechanism works.
8. **But a rule only exists if the router loads the file it lives in.** The same
   run produced the first case of the pack making output *worse* than baseline:
   a Python question routed to a C++-only skill, and the answer came back with a
   Python module that does not exist. Rule placement and cross-skill duplication
   are correctness concerns, not just tidiness — and routing variance under n=1
   sits underneath every number in this file.
