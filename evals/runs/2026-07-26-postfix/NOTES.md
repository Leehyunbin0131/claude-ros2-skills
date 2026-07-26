<!-- Detailed write-up for this run. The summary that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Post-fix re-run — 2026-07-26 (do the patches actually work?)

The previous section ended with four skill defects and applied fixes for all of
them. This is the run that tests whether the patches change behaviour, rather
than assuming they do. Identical protocol, identical prompts, same machine, same
model, fresh directories. Artifacts under
[`runs/2026-07-26-postfix/`](./).

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
3. ~~**The loaded skill actively caused the new defect.**~~ **Retracted — see the
   isolation run below.** The original reading was that `ros2-perception`'s
   exclusively-C++ examples (`#include <rclcpp/rclcpp.hpp>`, cv_bridge and
   pcl_ros in C++) contaminated a Python answer, since it is the only skill with
   no Python content and `ros2-core` is the only one of 11 that mentions `rclpy`.
   That is a real content gap, but it is **not** an established cause: a
   controlled run that forces `ros2-perception` to be the only skill, using the
   pre-patch body as a true control, failed to reproduce the error in any cell.
   The inference was drawn from a single occurrence and does not survive testing.

## What this run establishes

1. **The fixes work where they are loaded.** Task 1 went from a wrong number to
   the right one, verified by running the node, and Task 2's two defects are gone.
   Patching a skill body does change output, reproducibly and near-verbatim.
2. **Coverage of a rule matters as much as its content.** Two of three tasks
   improved; the third was untouched because the rule lived in the wrong file.
3. **One with-skills answer was worse than baseline** — Python code using a module
   that does not exist. Whether the pack caused it is answered below: no.
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

---
