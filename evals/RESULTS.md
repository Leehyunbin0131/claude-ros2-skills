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
| `ros2-core` | ✅ Verified | [2026-07-26 ablation](./runs/2026-07-26-core/NOTES.md) + [confirmation](./runs/2026-07-26-core-confirm/NOTES.md) |
| `ros2-security` | ✅ Verified | [2026-07-27 ablation](./runs/2026-07-27-security/NOTES.md) |
| `ros2-testing` | ✅ Verified | [2026-07-27 ablation](./runs/2026-07-27-testing/NOTES.md) + [confirmation](./runs/2026-07-27-testing-confirm/NOTES.md) |
| `ros2-package` | ✅ Verified | [2026-07-27 ablation](./runs/2026-07-27-package/) + [final confirmation](./runs/2026-07-28-package-final/) |
| `ros2-dev` | 🔄 In progress | — |
| `ros2-troubleshooting` | 🔄 In progress | — |
| `ros2-perception` | 🔄 In progress | — |
| `gazebo-sim` | 🔄 In progress | — |
| `ros2-control` | 🔄 In progress | — |
| `ros2-moveit` | 🔄 In progress | — |
| `ros2-microros` | 🔄 In progress | — |

Status vocabulary — a skill is only ✅ when **both** axes have passed:

| | Meaning |
| :--- | :--- |
| 🔄 In progress | not yet measured, or measured on one axis only |
| ✅ Verified | effect **and** efficiency, at n≥5, with the run linked |
| ❌ Did not clear | measured and failed — recorded, not hidden |

**No skill has completed verification.** Results are published here per skill as
each one clears both axes — not before, and including the ones that fail.

`ros2-core` is the first skill to clear both axes and shows what a finished row
looks like. Measured at n=8 across 558 cells: the body takes the pass rate from
**0.54 to 0.94** (p<0.0001) pooled over 20 mechanical checks, five lines were cut
as things the model already does unaided (50 → 45 lines), and three behaviours
turned out to be stated redundantly — where removing any single line looks
harmless and removing the group breaks the behaviour.

The confirmation run that closed the efficiency axis caught a sixth candidate cut
as a false negative: single-ablation Δ=0 said "cut," but removing it for real and
re-measuring at higher n showed the reduced body performing *worse than doing
nothing* on the behaviour that line taught (naked 1.00 vs cut 0.40, p=0.0017). The
line was restored before shipping. Detail: [ablation](./runs/2026-07-26-core/NOTES.md),
[confirmation and correction](./runs/2026-07-26-core-confirm/NOTES.md).

Two findings from that run are about the pack rather than the skill:

- **The always-loaded 28-line `CLAUDE.md` protocol did not change generated code
  at all** — 0.56 vs 0.54 against no context, p=0.73.
- **Contamination was looked for and not found.** Adding the protocol on top of
  the body scored 0.92 vs 0.94, p=0.67. Individual checks drop, the aggregate does
  not.

`ros2-security` is the second skill verified, and closes both axes in a single
run: 0.60 → **1.00** (p<0.0001) pooled over 14 checks across 6 claims, and every
ablatable claim came back load-bearing — zero cuts, so the 52-line body is
already the smallest one the harness can find. The same false-negative shape
`ros2-core` hit showed up here too, on the architecture sentence naming which RMW
implementations carry DDS-Security: Δ=+0.25, p=0.467 at n=8 looked like a cut,
and a targeted top-up to n=16 turned it into a real KEEP (p=0.007). Same
contamination check, same result — 1.00 vs 1.00, p=1.00. Detail:
[ablation](./runs/2026-07-27-security/NOTES.md).

`ros2-testing` is the third, and the first run to test more than deletion: every
claim was also tried alone (`only:<id>`, does one line by itself already produce
the effect) and the whole body was tried with its sections reordered
(`reorder:`, does *where* a rule sits change anything). Position turned out to
be a clean null — 52/52 either way, p=1.00, not underpowered, both sides already
at ceiling. Addition turned out to reinforce the deletion story rather than add
a new one: the two redundancy groups' members each reproduced their own effect
alone *and* each measured Δ=0 when singly removed — sufficient alone, unnecessary
once a sibling is present, the two-sided proof of redundancy neither prior run
had. Repeats were kept to n=4 by request, the floor where Fisher's exact can
resolve anything at all — most claims needed a top-up to n=8–16 as a result, and
one showed the same "ablated score below naked" shape investigated twice before;
this time it was noise, not a third hidden regression, but it still took the
top-up to tell the two apart.

Two lines were cut (78 → 76), and getting there surfaced a new failure mode,
distinct from the false negatives the first two runs caught: single-ablating
each cut candidate showed what looked like a real, if borderline, effect — and
both dragged down a check neither one owns. Both symptoms turned out to be
artifacts of the specific state single ablation produces (one row missing from
a six-row table, a shape nothing ships) rather than of the claims themselves —
measuring the real candidate (both rows gone, the actual 76-line body) made
both vanish: 104/104 across all 13 checks, p=1.00 against the pre-cut body.
**When more than one cut is on the table, the state that matters is the one
that will actually ship, not any single-claim reading along the way.** Detail:
[ablation](./runs/2026-07-27-testing/NOTES.md),
[confirmation](./runs/2026-07-27-testing-confirm/NOTES.md).

`ros2-package` is the fourth, and the first to grade one probe against real
ground truth instead of a regex: `pkg-build-ground-truth` actually runs
`colcon build` on the model's generated files in a scratch workspace and checks
`ros2 pkg executables` for the node, rather than pattern-matching the answer.
Against that ground truth the original 126-line, 29-claim body had two real
content gaps, not just cuttable lines: nothing named `package.xml`'s
`<export><build_type>ament_python</build_type></export>` tag or `setup.cfg`'s
`script_dir`/`install_scripts` keys, and generated packages built but the node
was undiscoverable — both confirmed missing against installed packages under
`/opt/ros/jazzy/`, then added as pointer-style corrections and verified at
n=16 (`export_build_type` and `setup_cfg_script_dir` both p<0.002 naked vs
full). Fifteen lines were cut as things the model already produces unaided
(a full CMakeLists.txt/setup.py/rosidl reference block was deliberately kept
regardless of per-clause ceiling effects — structural completeness for a
"copy this shape" reference has value a per-line naked/full test can't see),
taking the body to 16 claims.

Closing the efficiency axis took three failed confirmation attempts before a
correct one. The first sweep's single-ablation results looked clean, but an
ad hoc analysis script used for the follow-up confirmation runs tallied
per-check results keyed on `(probe, check)` instead of `(probe, condition,
check)`, so `naked`-condition failures silently pooled into the `full`
numbers. That produced three consecutive false regression reports against two
of the cut candidates (a `ModuleNotFoundError` symptom-table row and a "one
concern per package" rule), which were restored on the strength of those
reports. Tracing it down (comparing answer length as a first, discarded
hypothesis, then reading the one flagged failure cell directly and finding
the supposedly-missing content present in the answer) pointed straight at the
scoring bug. Re-run through the project's own `analyze.py` — which has always
keyed correctly — on a fresh n=8 sweep: the reduced 16-claim body still beats
naked significantly on the check the restored lines were meant to drive
(`iface_location_cause` 1/8 naked vs 6/8 full, p=0.041), and every check
compared against the pre-revert 18-claim body shows no significant
difference (p≥0.2, most ≥0.47) — both lines were cut back out. **A hand-rolled
substitute for the project's own analysis tooling reintroduced exactly the
kind of unverified conclusion this whole project exists to catch; use
`analyze.py`, not an inline script, even for a quick confirmation.** Detail:
[initial ablation](./runs/2026-07-27-package/), [content-gap
additions](./runs/2026-07-27-package-additions/), [the three miscored
confirmation runs](./runs/2026-07-27-package-confirm3/) (also
`-confirm`/`-confirm2`), [corrected final confirmation](./runs/2026-07-28-package-final/).

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
