<!-- Detailed write-up for this run. The summary that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Guardrail run — 2026-07-26 (testing the fix for a defect that turned out not to reproduce)

The previous section blamed the `rclcpp.qos`-in-Python error on routing to a
C++-only skill, and two fixes were written for that diagnosis:

- `CLAUDE.md` gained two lines stating that `rclcpp` is C++ only and `rclpy` is
  Python only, so the rule is in context regardless of which skill routes
  (26 → 28 lines of always-loaded protocol).
- `ros2-perception`'s QoS row now names **both** symbols — `rclcpp::SensorDataQoS()`
  and `rclpy.qos.qos_profile_sensor_data` — where it previously named only the
  C++ one.

Then the fix was tested properly, and the diagnosis did not survive.
Artifacts in [`runs/2026-07-26-guardrail/`](./); the
isolation harness is [`harness/isolate_guardrail.sh`](../../harness/isolate_guardrail.sh).

## Step 1 — repeat the normal pair three times

| Repeat | Skill routed | `rclcpp` in Python | Cost |
| :--- | :--- | :--- | :--- |
| 1 | `ros2-core` | clean | $0.0283 |
| 2 | `ros2-troubleshooting` | clean | $0.0325 |
| 3 | `ros2-core` | clean | $0.0285 |

Clean, but **uninformative**: `ros2-perception` — the condition under suspicion —
was never selected. Combined with the two earlier runs, the routing distribution
for this one prompt is `ros2-core` ×3, `ros2-perception` ×1,
`ros2-troubleshooting` ×1. Roadmap item 7 has its first data: **the skill chosen
for an identical prompt is genuinely variable.**

## Step 2 — force the suspected condition, with a real control

Four cells, each given `ros2-perception` as its **only** skill, ×2 repeats. The
control uses the **pre-patch skill body read out of git**, so it is the original
failing configuration rather than the current file:

| Cell | Skill body | `CLAUDE.md` | Result (×2) |
| :--- | :--- | :--- | :--- |
| A control | pre-patch | absent | **clean, clean** |
| B protocol only | pre-patch | present | clean, clean |
| C skill only | patched | absent | clean, clean |
| D both (shipped) | patched | present | clean, clean |

**8/8 clean, including both controls.** The configuration that produced the error
does not produce it again.

## What this actually shows

1. **The causal claim was wrong and is retracted.** Across every Task 3
   with-skills cell measured — 13 of them — the `rclcpp.qos` error occurred
   **once (~8%)**. `ros2-perception` was in context for 5 of those cells and the
   error appeared in 1. A forced-perception design with a true control does not
   reproduce it. This was low-frequency stochastic hallucination, not a
   structural consequence of skill content.
2. **The fixes therefore have no measured effect on the thing they targeted**, and
   cannot be credited with the clean results. They are kept on separate grounds:
   `ros2-perception` genuinely named only the C++ symbol, naming both is correct,
   and the cost is one table row plus two protocol lines with no regression across
   8 cells. That is the honest claim — a closed content gap, not a fixed bug.
3. **Skill activation is not guaranteed, and that is the bigger finding.** In the
   isolated cells, **4 of 8 made zero tool calls** — the agent never loaded the
   one skill available to it. Two of those four had `CLAUDE.md` present, whose
   first instruction is "Load the matching `ros2-*` skill." In the full 11-skill
   install something was always loaded (5/5); with only a weakly-matching skill
   offered, the router often preferred nothing. **A skill that does not load
   cannot help, and the always-loaded protocol does not reliably make it load.**
4. **n=1 was hiding more than it revealed.** A single run produced a defect, a
   plausible mechanism, and a fix — and 12 further cells showed the mechanism was
   imagined. Any single-run claim in this file, including the favourable ones,
   should be read with that in mind.

## Follow-ups this run created

- ⏳ Measure skill-activation rate as a first-class metric, per task and per
  skill. It is upstream of every other number here: routing variance and
  non-activation both determine whether skill content is even in context.
- ⏳ Repeat the favourable results too. Task 1's fix verification is currently
  n=1 in the same way the retracted claim was.
- ⏳ `ros2-perception` still has no Python examples (only C++ `cv_bridge` and
  `pcl_ros`). That remains a real gap even though it did not cause the observed
  error; it was left unwritten here because `cv_bridge` is not installed on this
  machine and the project's rules forbid writing its API from memory.
