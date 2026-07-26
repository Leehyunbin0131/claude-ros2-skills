# Roadmap — what to build next, and why

The short public list lives in [`README.md`](./README.md#roadmap). This file is
the working version: what each item is for, what "done" means, what it costs, and
what evidence created it.

Everything here follows from the runs written up in
[`evals/RESULTS.md`](./evals/RESULTS.md). Where an item exists because a
measurement surprised us, the measurement is cited.

---

## The two axes this repo is optimizing

Content curation is the axis the project was designed around: put in what the
agent gets wrong, leave out what it already knows, because wrong content is worse
than no content. There is direct evidence for that thesis on both sides —

- a wrong critic list in `references/symbols.md` was emitted **verbatim** by the
  agent, so a bad line does not merely waste context, it manufactures the
  hallucination it was meant to prevent;
- the two smallest rules ever added here (a `range_min`/`range_max` bounds
  predicate, a shutdown pattern) showed up near-verbatim in generated code and
  turned a wrong answer into the right one;
- on the one task the model already knew cold, the skills bought nothing and cost
  ~1.4×.

The second axis surfaced only when we measured it, and it currently dominates:
**reachability**. A curated rule is worth zero if the skill carrying it never
loads.

- In a stripped install offering one weakly-matching skill, the agent made **zero
  tool calls in 4 of 8 cells** — it never loaded the only skill available. Two of
  those four had `CLAUDE.md` present, whose first instruction is "load the
  matching `ros2-*` skill".
- One identical prompt selected **three different skills across five runs**
  (`ros2-core` ×3, `ros2-perception` ×1, `ros2-troubleshooting` ×1).

So the authoring question is not only *what to write* but *where it has to live to
be reached*. A rule that can be wrong in several domains belongs in the
always-loaded protocol; a rule that only matters inside one domain belongs in that
skill.

## Two bars, not one

A line does not have to be A/B-tested to earn its place. It has to clear the bar
that matches what it claims:

| Bar | Question | Method | Marginal cost |
| :--- | :--- | :--- | :--- |
| **Verifiable** | Is this statement *true* right now, on Jazzy? | grep the installed package: `ros2 interface show`, `ros2 pkg prefix`, source grep | ~0 |
| **Measured** | Does this statement *change what the agent produces*? | run the A/B pair, grade the outcome | $0.03–0.07 per cell |

Every line must be verifiable. Only lines claiming to change agent behaviour need
to be measured. The `ObstaclesCritic` defect was caught by verification, not by an
eval — a cheaper net that catches a larger class of problem. Phase 1 exists
because that net is currently hand-operated.

---

## Phase 1 — Automate verification (highest leverage, do first)

**Why.** A one-off manual audit found 11 interface symbols across the skills and
0 defects, but nothing prevents the next wrong symbol from landing, and the one
wrong symbol we know about reached agent output. Verification requires no human
judgement, which matters because human judgement is exactly what failed when we
*guessed* at a failure mechanism and a controlled run disconfirmed it.

**Do.**

1. Add `evals/harness/verify_symbols.py`: extract candidate symbols from
   `skills/**/*.md` and check each against the installed system.
   - `pkg/msg/Name`, `pkg/srv/Name`, `pkg/action/Name` → `ros2 interface show`
   - C++ include paths `pkg/msg/name.hpp` → the header exists under
     `/opt/ros/jazzy/include/`
   - bare package names in `ros2 run <pkg>` / `ros2 pkg prefix <pkg>` position →
     `ros2 pkg prefix`
   - `ros2 <verb> ... --flag` → the flag appears in `--help`
   - Exit 0 clean, 1 on any symbol that the installed system contradicts, 2 if
     the package needed to judge is not installed (report, do not fail).
   - Must distinguish **absent package** (unjudgeable) from **absent symbol in a
     present package** (a real defect). The first manual pass produced four false
     positives by conflating C++ header paths with message type names — the
     script must not repeat that.
2. Add a `symbols` job to `.github/workflows/ci.yml` running in a
   `ros:jazzy` container, installing the packages the skills reference
   (`nav2-bringup`, `moveit`, `ros2-control`, `cv-bridge`, `ros-gz`, …) and
   running the script. Keep it separate from the existing `tests` job so a
   missing apt package cannot mask a logic failure.
3. Report the unjudgeable set in the job summary so coverage is visible rather
   than silently partial.

**Done when.** CI fails on a PR that introduces a symbol the installed Jazzy does
not have, and the job summary lists how many symbols were checked vs skipped.

**Cost.** One script, one CI job. Runtime is dominated by apt, so cache the layer.

---

## Phase 2 — Cover the skills no task exercises

**Why.** Two different counts matter here, and only one of them is flattering.

*Loaded at least once* — 5 of 11: `ros2-core` (6 cells), `ros2-perception` (5),
`ros2-troubleshooting` (3), `ros2-package` (1), `ros2-dev` (1).

*Has a task designed to exercise its own content* — **4 of 11**.
`ros2-perception` only ever loaded because Task 3's routing picked it for a
camera-topic question; it was graded against Task 3's QoS checklist, so none of
its actual subject matter — `cv_bridge` encodings, `16UC1` vs `32FC1`, depth
registration, `image_transport` — has been tested at all.

Six skills have never been loaded in any cell: `gazebo-sim`, `ros2-control`,
`ros2-moveit`, `ros2-testing`, `ros2-microros`, `ros2-security`. Across the three
measured tasks, with-skills output contained four defects; there is no reason to
assume the untested skills are cleaner.

**Do.** One task per skill, each with a **binary, runtime** outcome, in the style
of Task 5 (`ros2 topic echo` prints or it doesn't). Judgement-free grading is the
point: it removes the grader from the loop.

| Skill | Candidate task | Binary outcome |
| :--- | :--- | :--- |
| `ros2-control` | Bring up a diff-drive `ros2_control` stack on a URDF and drive it | `joint_state_broadcaster` + controller reach `active`; `/cmd_vel` moves the joints |
| `gazebo-sim` | Spawn a sensor-equipped SDF model and bridge one topic | `ros2 topic echo` on the bridged topic carries data |
| `ros2-perception` | Subscribe to a `16UC1` depth topic, convert with `cv_bridge`, publish metres | the derived topic carries values scaled by 1/1000, not raw millimetres |
| `ros2-testing` | Write a `launch_testing` test for an existing node and run it | `colcon test` reports a passing test, not zero tests |
| `ros2-moveit` | Plan and execute to a named target on a shipped demo robot | the action reports success and the joint states change |
| `ros2-microros` | Build a rclc publisher against the agent, run the agent | the topic appears on the host side |
| `ros2-security` | Generate a keystore and bring two nodes up with enclaves | communication succeeds with security enabled, fails without the key |

Start with `ros2-control` and `gazebo-sim`: both have unambiguous runtime
outcomes and both are high-traffic. `ros2-security` is last — it is the hardest
to make binary and the least likely to be a first-session task.

**Done when.** Every skill in the table has one committed A/B pair with a binary
grade, and `RESULTS.md` reports it including the failures.

**Cost.** ~$0.05 per cell × 2 cells × 2 repeats × 7 tasks ≈ **$1.4**, plus the
apt time to install each domain's packages. The repeat is not optional — see
Phase 3.

---

## Phase 3 — Measure reliability, not just correctness

**Why.** This is the phase the last run argued for most loudly. A single cell
produced a defect, a tidy causal story, and a fix; twelve further cells showed
the story was invented. Meanwhile the genuinely large effect — half the cells not
loading the skill at all — was invisible until an experiment was designed to look
for it.

**Do.**

1. **Skill-activation rate.** Record, per task and per condition, whether the
   `Skill` tool fired and which skill it selected. `summarize_run.py` already
   extracts this; promote it to a reported column in `RESULTS.md` rather than a
   line in a transcript summary.
2. **Routing distribution.** Run each task's skills cell **n≥5** and publish the
   distribution over selected skills. A task whose routing is split across three
   skills is not measuring one skill, and the tables should say so.
3. **Repeat the favourable results.** Task 1's fix verification is n=1 in exactly
   the way the retracted mechanism claim was. Re-run it at n≥3 before it is cited
   as established.
4. Add a `--repeats N` flag to `evals/harness/run_ab.sh` and aggregate, so that
   n>1 is the default path and not a manual loop.

**Done when.** Every claim in `RESULTS.md` carries its n, activation rate is a
column, and no conclusion rests on a single cell.

**Cost.** Multiplies Phase 2 by the repeat count. At n=5 the whole suite is still
under $10.

---

## Phase 4 — Ablation tooling: make SKILL.md testable like code

**Why.** The standing question for every line is "does removing this change the
outcome?" and it is currently answerable only by hand. `isolate_guardrail.sh` is
that experiment in special-case form: it reads the **pre-patch skill body out of
git** to build a true control, which is the only reason the retraction was
possible — the first attempt used the already-patched file as its "control" and
proved nothing.

**Do.** Generalize it into `evals/harness/ablate.sh`:

```
ablate.sh --skill ros2-core --task 1 --drop 'range_min' --repeats 3
```

- Build two skill trees: as-is, and with the matched line/section removed.
- Run the task's cell against each, identical otherwise.
- Report whether the graded outcome differs.
- Support `--from-git <ref>` to use a historical body as the control.

**Done when.** A contested line can be settled with one command, and the result
is committable as evidence in the PR that proposes removing it.

**Cost.** One script. Per-question cost is 2 cells × repeats.

---

## Phase 5 — Known content debt

Each of these is a specific, already-identified gap. None is speculative.

| Item | Evidence | Note |
| :--- | :--- | :--- |
| `ros2-perception` has **no Python examples** — only C++ `cv_bridge` and `pcl_ros` | it is the only skill of 11 with no Python content; `ros2-core` is the only one mentioning `rclpy` | Deliberately not written yet: `cv_bridge` is not installed on the eval machine, and writing its Python API from memory is exactly what this repo forbids. Do it in the Phase 1 container. |
| Post-write verification does not fire on diagnosis answers | **0 of 4** with-skills cells ran the `ros2 topic info -v` they recommended, with a live reproduction running and `Bash` allowed | The "done means it ran" rule reaches code tasks (Task 1's agent ran `ros2 interface show` first) but not answers. Needs a rule that survives being an *answer* rather than a deliverable. |
| Task 3 cannot separate the conditions | both cells correct in one turn, every run | Rewrite it to require a *demonstrated* inspection of live endpoints. Until then it measures nothing. |
| Two skill bodies are ~2× the target length | `ros2-package` 126 lines, `ros2-troubleshooting` 119, against a documented 60–80 | Either split into `references/` or adjust the documented target. Currently `ros2-dev` is the only skill of 11 with a `references/` dir, so the "three-layer architecture" is one skill's reality, not the pack's. |
| Independence | every run graded by the project that publishes it | Unfixable in-house. The mitigation is mechanical grading plus committed artifacts; the ask is an outside re-grade. |

---

## Explicitly not planned

- **Multi-distro support.** Jazzy only, by design. A skill that hedges toward
  Humble is a skill that is wrong on both.
- **Embedding API snippets to raise offline accuracy.** The `ObstaclesCritic`
  incident is the argument: embedded content rots silently and is emitted
  verbatim when wrong. Links plus exact symbol names stay the strategy.
- **A router skill or an index table in `CLAUDE.md`.** Routing happens through
  `description` frontmatter. Phase 3 measures it instead of replacing it.

---

## Order of work

1. **Phase 1** — automated symbol verification. Cheapest, needs no judgement,
   permanently closes the class of defect we know reached output.
2. **Phase 3.1 and 3.4** — activation reporting and `--repeats`. Do this *before*
   Phase 2, so the new coverage is measured at n>1 from the start rather than
   generating another round of n=1 claims to retract.
3. **Phase 2** — `ros2-control` and `gazebo-sim` first.
4. **Phase 5** — the `ros2-perception` Python gap, once the Phase 1 container
   makes `cv_bridge` available to verify against.
5. **Phase 4** — ablation, when the first real disagreement about a line arrives.
