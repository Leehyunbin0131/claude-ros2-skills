# Verification status

**This file is the record of what is finished.** It is the first thing to read
before working on a skill, and the last thing to update after — the final stage of
a verification run writes its own row here, so the record cannot drift from the
runs behind it.

## What "verified" means here

A skill is not verified because it is correct. Correct is the floor. It is
verified when both of these are answered:

- **Effect** — does it change what the agent produces on a task that exercises
  *its own* content, measured against a live ROS 2 Jazzy install?
- **Efficiency** — is this body the *smallest* one that produces that effect?
  Fewer tokens and less text may buy the same result, and until that is tested,
  "the agent used it" is only half an answer.

Both are measured by A/B runs graded mechanically — does the symbol exist in the
install, does the command succeed when re-run, does the generated node print the
right number against a live publisher — not by review.

## Status

| Skill | Status | Evidence |
| :--- | :--- | :--- |
| `ros2-core` | 🔄 Effect measured, efficiency partly | [2026-07-26 ablation](./runs/2026-07-26-core/NOTES.md) — all 26 claims ablated, n=8, 558 cells |
| `ros2-package` | 🔄 In progress | — |
| `ros2-dev` | 🔄 In progress | — |
| `ros2-troubleshooting` | 🔄 In progress | — |
| `ros2-perception` | 🔄 In progress | — |
| `gazebo-sim` | 🔄 In progress | — |
| `ros2-control` | 🔄 In progress | — |
| `ros2-moveit` | 🔄 In progress | — |
| `ros2-testing` | 🔄 In progress | — |
| `ros2-microros` | 🔄 In progress | — |
| `ros2-security` | 🔄 In progress | — |

Status vocabulary — a skill is only ✅ when **both** axes have passed:

| | Meaning |
| :--- | :--- |
| 🔄 In progress | not yet measured, or measured on one axis only |
| ✅ Verified | effect **and** efficiency, at n≥5, with the run linked |
| ❌ Did not clear | measured and failed — recorded, not hidden |

**No skill has completed verification.** Results are published here per skill as
each one clears both axes — not before, and including the ones that fail.

`ros2-core` is the furthest along and shows what a finished row will contain.
Measured at n=8 across 558 cells: the body takes the pass rate from **0.54 to
0.94** (p<0.0001) pooled over 20 mechanical checks, six lines were cut as things
the model already does unaided (50 → 44 lines), and three behaviours turned out to
be stated redundantly — where removing any single line looks harmless and removing
the group breaks the behaviour. It stays 🔄 because the reduced body has not been
re-measured as a whole, which is what the efficiency axis actually requires.

Two findings from that run are about the pack rather than the skill:

- **The always-loaded 28-line `CLAUDE.md` protocol did not change generated code
  at all** — 0.56 vs 0.54 against no context, p=0.73.
- **Contamination was looked for and not found.** Adding the protocol on top of
  the body scored 0.92 vs 0.94, p=0.67. Individual checks drop, the aggregate does
  not.

Interim measurements are deliberately not published. An earlier round of this work
produced a plausible conclusion from a single run that a controlled re-run then
disconfirmed; publishing partial results invites exactly that error to spread
before it can be caught.

## Before measuring a skill: is it even runnable here?

The effect axis needs the skill's packages actually installed — a skill whose
first instruction is "read the installed defaults" cannot be measured where those
defaults do not exist. Checked on the eval machine
(`ros-jazzy-ros-base`, 204 packages):

| Runnable now | Blocked until installed |
| :--- | :--- |
| `ros2-core`, `ros2-package`, `ros2-troubleshooting`, `ros2-testing`, `ros2-security` | `ros2-dev` (`nav2-bringup`, `slam-toolbox`) · `gazebo-sim` (`ros-gz` + Gazebo Harmonic) · `ros2-control` (`ros2-controllers`) · `ros2-moveit` (`moveit`) · `ros2-perception` (`cv-bridge`, `image-transport`) · `ros2-microros` (`micro-ros-agent`, source build) |

Re-check with `ros2 pkg prefix <pkg>` rather than trusting this table — it is a
snapshot of one machine.

How the runs are set up and re-run: [`README.md`](./README.md).
