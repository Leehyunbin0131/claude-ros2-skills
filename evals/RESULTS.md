# Verification status

**Nothing is currently verified.** The measurement round that produced the
previous table has been deleted, and the criterion it used has been replaced.

## What happened

The first round asked: *does the model produce this behaviour without the file?*
It answered that question carefully — 5,156 graded cells across nine skills —
using a harness that ran every cell single-turn with tools disabled.

Tools-off is a requirement of per-claim ablation: an agent with tools reads the
real file, so ablating a line from its context proves nothing. The mistake was
letting that constraint define the project. **Nobody ships an agent that cannot
look anything up**, so "the model does not know this unaided" is not the same as
"the skill earns its place", and the numbers systematically overstated what the
files were buying.

The criterion is now: **a skill supplies what the agent cannot reach on its own**
— with the model's knowledge, web search, and a live install all available. See
[`DESIGN.md`](./DESIGN.md), written before any v2 measurement.

## What survived the reset

| | |
| :--- | :--- |
| All 23 run directories, all authored variants, every VERIFIED status | **deleted** — they answer the old question, and a KEEP does not transfer to the new one |
| Every CUT already applied to a skill file | **kept** — one-way logic: content the model produces without tools it certainly produces with them, so those cuts are conservative under the stricter rule |
| Two facts verified against the install | **kept** — properties of Jazzy, not of any harness (below) |
| Harness code and the real-outcome graders | **kept** — v2 needs them |
| Method failures in [`FINDINGS.md`](./FINDINGS.md) | **kept** — lessons about measuring, not about skills |

### The two install-verified facts

Both were found by asking the model cold and checking its answer against
`/opt/ros/jazzy/`. **Both are still true about Jazzy. Neither is still a reason
to ship a line, and the first is no longer in any skill:**

- Jazzy's `diff_drive_controller` subscribes to `geometry_msgs/msg/TwistStamped`
  only, and has **no `use_stamped_vel` parameter**. The tools-off model
  prescribed one 4 times out of 4. (`diff_drive_controller_parameters.hpp`
  declares 23 parameters; none is that.)
  **Round 3 measured an agent with a shell and a web search at 10/10 on this,
  unaided. Cut from `ros2-control` after round 4.**
- Jazzy replaced `/servo_node/start_servo` (`std_srvs/srv/Trigger`) with
  `/servo_node/switch_command_type` (`moveit_msgs/srv/ServoCommandType`). The
  tools-off model prescribed the removed service 4 times out of 4, and the skill
  used to agree with it. **Still in `ros2-moveit`, and still unmeasured under the
  v2 criterion** — `t1` touches it only indirectly. The `DESIGN.md` pre-check
  found search fixes it, so it is expected to go the same way.

This section used to say both facts "are now in the shipped skills", which
stopped being true the moment the first was cut. It is left visible rather than
quietly reworded, because a record that silently agrees with the present is not
a record.

## v2 round 1 — first measurement under the new criterion

45 cells, tools on, live install, n=5.
[Notes](./runs/2026-07-29-v2/NOTES.md) · [machine output](./runs/2026-07-29-v2/ANALYSIS.md)

**The control gate passed** — `t4`, a task the model handles cold, is 5/5 vs 5/5
on both checks, so the harness is not tilted toward the skills condition.

**Nothing reached q<0.05, and the one thing that came closest is the shipped
scripts rather than any skill text.**

| Task | What it tested | Result |
| :--- | :--- | :--- |
| T1 | version-specific breakage | baseline names `TwistStamped` **5/5 with zero searches** — it knows. It also volunteers the nonexistent `use_stamped_vel` 5/5, so it has the right fact and a wrong one side by side and no habit of checking. Both skill effects point the right way, neither clears the bar |
| T2 | content that exists nowhere else | `scripts-only` vs `baseline` **+1.00** on "ran the script" and "reported its verdict" (q=0.063). `skills` vs `scripts-only` **+0.00 on every check** |
| T3 | asking before writing | reported **null** at the time: baseline asks for footprint and drive type before writing config 4/5 on its own. **Corrected by a later audit — see below.** |
| T4 | null control | 5/5 vs 5/5. Gate passed |

> **AUDIT CORRECTION, added after the round was closed.** This round predates
> `isolate_cell.sh`, and unlike every round after it, this write-up never carried
> an Isolation section. A full-project leak scan found **2 of the 5 `t3-baseline`
> cells had read the repository** — `r2` read 200 lines of `TASKS.md`, which
> states T3's grader verbatim ("a question mentions footprint / inscribed
> radius / robot radius", "differential / omni / ackermann"); `r3` listed the
> repo directory. **Both leaked cells passed all three T3 checks.** Excluding
> them: `t3_asked_before_writing`, `t3_asked_footprint`, and
> `t3_asked_drive_type` each drop from the reported **4/5 (80%)** to a clean
> **2/3 (67%)** — still not zero, but a materially weaker "asks unprompted"
> story than what was published and than what fed into `DESIGN.md`'s original
> category-3 discussion. T3 has never been re-run under isolation. Nothing
> currently shipped rests on this number, but the figure above is unreliable
> and should not be cited without this caveat.

Two of the three predictions recorded in [`TASKS.md`](./TASKS.md) before the
round held; T3 did not. In v1 that same behaviour measured 1/7 against 5/7 and
was written up as the highest-value content in the pack — it was an artifact of a
harness where the agent could not ask, look anything up, or do anything but emit
text in one turn.

**What this establishes.** The v1 verdicts were measuring the restriction, not
the skills: two of three targeted effects vanish once the agent can search and
act. Category 2 (files the agent cannot reach) is the only category with support
so far, and even there the prose describing the files adds nothing measurable on
top of shipping them. The two lines v1 added to the skills are now expected to
fail as well.

> **AUDIT CORRECTION, added after the round was closed — a second, structural
> gap.** `t1_command_runs` is `t1`'s only real-outcome check — TASKS.md
> describes it as running the agent's command "verbatim against a live
> `diff_drive_controller`" and reading actual wheel velocity. It has **never
> graded a single cell, in this round or any later T1 round.** `grade_v2.t1()`
> only computes it when called with `live=True`; `analyze_v2.py` hardcodes
> `fn(c, live=False)` for every T1 analysis, so the field is `None` every time.
> Every T1 conclusion in this project — including the `ros2-control` `/cmd_vel`
> row deletion in round 4 — rests entirely on transcript-tier checks
> (`t1_correct_type` is a regex for "TwistStamped" in the final answer text;
> `t1_no_invented_param` and `t1_searched_or_read` read tool calls), never on
> the real-outcome tier this project's own check-anchoring hierarchy calls
> strongest. Separately, even with `live=True` the implementation does not
> execute anything — it regex-matches the transcript for a `ros2 topic pub`
> invocation containing the right type name, which is weaker than "runs
> verbatim" as described. Not corrected here: wiring this up and re-running T1
> is a real measurement decision, not a documentation fix, and is left as an
> open item rather than done unprompted.

## v2 round 2 — the bundled scripts earn their place

20 cells, `t2` only, `baseline` vs `scripts-only`, n=10. Pre-registered in
[`TASKS.md`](./TASKS.md) before any cell existed.
[Notes](./runs/2026-07-30-v2-t2/NOTES.md) · [machine output](./runs/2026-07-30-v2-t2/ANALYSIS.md)

| Check | baseline | scripts-only | Δ | q |
| :--- | ---: | ---: | ---: | ---: |
| `t2_exit_code_read` | 0/10 | **10/10** | +1.00 | **0.000** |
| `t2_ran_script` | 1/10 | **10/10** | +0.90 | **0.000** |
| `t2_evidence_not_guess` | 9/10 | 10/10 | +0.10 | 1.000 |

**First thing in this project to clear the bar under the real-environment
criterion.** Both graders that turn on a real outcome — did the script run, was
its verdict reported — are unambiguous.

The baseline is not helpless: 9/10 on `t2_evidence_not_guess`, because it writes
its own throwaway subscriber and samples the topic. What it never produces is a
checked, exit-coded verdict — 0/10. **The script's value is not the knowledge,
it is the pass/fail.**

A contamination path was found and is recorded rather than papered over: cells
globbed `$HOME`, found this repository, and read `evals/DESIGN.md` and the
scenario source, which names the planted answer. Hand-reading one transcript
found one instance; a mechanical detector added afterwards found **5 of 20**.
Excluding them makes the result *cleaner* — `t2_ran_script` goes from 1/10 vs
10/10 to **0/7 vs 8/8** — because the leak strengthened the baseline.

Closed for every round after this one by
[`isolate_cell.sh`](./harness/isolate_cell.sh): each cell runs in an unprivileged
mount namespace with the repo path bind-mounted over by an empty directory, and
`run_ab.sh` refuses to run without it rather than silently producing an
unisolated round. The detector itself first reported a false all-clear because
committed transcripts are gzipped and were being read as text — the same run also
said "0 cells graded", which was the tell.

**What two rounds have established.** Category 2 — content the agent cannot
reach — is real. The prose describing that content is not: `skills` vs
`scripts-only` was +0.00 on every check. Nothing in either round has shown any
*prose* in any skill earning its place, and the two lines v1 added are still
expected to fail.

## v2 round 3 — the fact is dead weight, the instruction to check is not

20 cells, `t1` only, `baseline` vs `skills`, n=10. First round with cells isolated
from the repository; **no cell reached it**.
[Notes](./runs/2026-07-30-v2-t1/NOTES.md) · [machine output](./runs/2026-07-30-v2-t1/ANALYSIS.md)

Both lines under test were *added* by v1 after it found the model getting them
wrong, and both measured KEEP under the tools-off harness. `DESIGN.md` predicted
both would fail. It was half right.

| Check | baseline | skills | Δ | q |
| :--- | ---: | ---: | ---: | ---: |
| names `TwistStamped` | **10/10** | 10/10 | +0.00 | 1.000 |
| verified against install or web | 3/10 | **10/10** | +0.70 | **0.009** |
| did not prescribe `use_stamped_vel` | 3/10 | 6/10 | +0.30 | 0.555 |

**The fact does not earn its place.** Every baseline cell names `TwistStamped`
unaided. v1 added that line because the tools-off model failed it 4/4; in a real
session it is right 10/10.

**The instruction to verify does — but it is not the skill's.** 3/10 against
10/10, q=0.009. With the skill loaded every cell searched or read
`/opt/ros/jazzy`; without it, seven answered from memory and checked nothing.
That is category 3, which round 1's T3 had suggested was empty.

This was originally written up as the first significant result attributable to
skill *prose*. **Round 4 shows that attribution was wrong** — the `skills` cell
also ships `CLAUDE.md`, which contains the same instruction, and `CLAUDE.md`
alone reproduces the 10/10. See below.

**And the error the line was written to prevent still happens.** Seven baseline
cells prescribe `use_stamped_vel` — a parameter that does not exist — *alongside*
the correct answer, in the same reply. With the skill, four still do. The line
halves the error, not significantly, and is ignored 40% of the time by an agent
that has read it. What should survive in that row is the instruction to check,
not the answer.

Two rounds were lost to the harness before this one and both produced
plausible-looking numbers: the isolation wrapper moved `HOME`, which broke
authentication for all 20 cells, and the grader then scored those dead cells
**10/10** on a negative check because "Not logged in" does not contain the
forbidden parameter name. Both fixed and verified.

## v2 round 4 — the one prose result belongs to `CLAUDE.md`, not to any skill

20 cells, `t1` only, `baseline` vs **`claude-md-only`**, n=10, isolated.
Pre-registered in [`TASKS.md`](./TASKS.md), prediction included, before any cell
existed.
[Notes](./runs/2026-07-30-v2-t1-claudemd/NOTES.md) · [machine output](./runs/2026-07-30-v2-t1-claudemd/ANALYSIS.md)

Round 3's result was confounded. `run_ab.sh` installs `CLAUDE.md` into the
`skills` cell along with `skills/*`, and `CLAUDE.md` opens by telling the agent
not to answer from memorized knowledge and to verify against `/opt/ros/jazzy` —
which is exactly what `t1_searched_or_read` measures. This round installs that
one file and nothing else.

| Check | baseline | `claude-md-only` | `skills` (r3) |
| :--- | ---: | ---: | ---: |
| names `TwistStamped` | 10/10 | 10/10 | 10/10 |
| verified against install or web | **2/10** | **10/10** (q=0.002) | 10/10 |
| did not prescribe `use_stamped_vel` | 4/10 | 6/10 | 6/10 |

**`CLAUDE.md` alone reproduces the `skills` cell exactly, on every check.**
Adding ten `SKILL.md` files on top of it moves nothing.

The control held without spending cells on `t4`: round 4 re-ran `baseline`
concurrently and it reproduced round 3's figure (3/10 vs 2/10, p=1.000), which is
a stronger check for this question than `t4` because it is the same grader on the
same task.

**Score after four rounds:**

| Content | Status |
| :--- | :--- |
| bundled scripts (`check_imu_gravity.py`) | **earns its place** — round 2, q<0.001 |
| `CLAUDE.md`'s verify paragraph | **earns its place** — round 4, q=0.002 |
| any `SKILL.md` prose | **no measured effect anywhere** |

That is not a verdict that the skills are worthless: seven have never been
measured, and this is one task. It is a verdict on the single number that was
being used to justify keeping skill prose.

**Applied.** `ros2-control`'s `/cmd_vel` row was cut in full — every effect in it
(the fact, the verify instruction, the `use_stamped_vel` warning) is reproduced
by `CLAUDE.md` alone, and `ros2-control` is the skill `t1` directly exercises.
**Not applied** to the other nine: `t1` says nothing about `gazebo-sim` or
`ros2-perception`, and generalising it there is the error that caused the
reverted reduction.

## v2 round 5 — `ros2-package`: the build loop reaches every seam unaided

20 cells, `t5` only, `baseline` vs `skills`, n=10, isolated. First of the seven
skills that had no v2 measurement at all.
[Notes](./runs/2026-07-30-v2-t5-package/NOTES.md) · [machine output](./runs/2026-07-30-v2-t5-package/ANALYSIS.md)

**120 out of 120.** Six real-outcome checks — clean build, `ros2 interface
show`, `ros2 run`, `ros2 launch`, params in `share/`, first build clean — all
10/10 in **both** cells.

A total ceiling is when to distrust the grader, so three things were checked
before reading anything into it:

- The graders were **validated against three deliberately broken workspaces
  before the round**, and each defect is caught by exactly the check meant to
  catch it. All three broken packages **exit `colcon build` with code 0** — the
  obvious grader, reading the build log, would have passed every one.
- **Nobody iterated into correctness.** 17 of 20 cells ran `colcon build` once,
  3 ran it twice, and no build in the round failed.
- **Two baseline workspaces were opened on disk**: `setup.cfg` with the ROS
  install paths, the script at `install/battery_monitor/lib/battery_monitor/`,
  launch and config under `share/`. The wiring is genuinely right.

The prediction recorded in `TASKS.md` was that `launch`/`params` installation
would separate the cells, since nothing in the prompt asks the agent to run
`ros2 launch` and find out. It did not: asked for a launch file that runs the
node with a config, agents install both, because a launch file they cannot
launch is obviously not the deliverable.

**Applied.** `ros2-package` goes from 69 lines to 31 — the `ament_python`
`build_type` export, the `setup.cfg` install location, and the entire custom
interfaces section, all measured 10/10 unaided. **Kept, unexercised:** the
`ament_cmake` `lib/${PROJECT_NAME}` rule and `install(DIRECTORY ...)`, because
every node package in this task was `ament_python`. A C++ variant of `t5`
settles both in one round.

## The ladder — `ros2-package` climbed to the top and was deleted

[`LADDER.md`](./LADDER.md) replaced the audit after round 5. The audit asked
"does this line change anything?", which can only delete. The ladder asks **where
the model stops being able to do the task unaided** — so it can also find content
to *write*. Six rules stop it becoming search: the whole ladder is written and
frozen first, rungs are defined by mechanisms added rather than difficulty felt,
the length is fixed at three, you stop at the first rung that fails, and an
exhausted ladder is a verdict — **adding a rung 4 is forbidden.**

Rungs run `baseline` only, n=10. A rung fails at ≤7/10 on a real-outcome check.

| Rung | Mechanisms added | Result |
| :--- | :--- | ---: |
| **L1** (`t5`) | `ament_python` node package, `ament_cmake` interfaces, launch, params | 60/60 |
| **L2** (`t6`) | + C++ executable, `.srv` used from both languages, cross-package launch include | 70/70 |
| **L3** (`t7`) | + cross-package `.msg` field, composable node loaded into a live container, `colcon test` that must run | 60/60 real outcomes |
[L1](./runs/2026-07-30-v2-t5-package/NOTES.md) · [L2](./runs/2026-07-30-ladder-pkg-L2/NOTES.md) · [L3](./runs/2026-07-30-ladder-pkg-L3/NOTES.md)

**19 real-outcome checks, n=10 each, 190 cell-checks, nothing below ceiling.** An
agent with a shell and no skill file writes the `ros2 run`-discoverable console
script, the `lib/${PROJECT_NAME}` install, the installed `launch/` and `config/`,
the cross-package launch include, `.msg`/`.srv` generation with `DEPENDENCIES`, a
component registered and **loaded into a running container**, and a test
`colcon test` actually runs and passes.

The only non-ceiling number in three rungs was `t7_first_build_clean` at 8/10,
and the two failures were unrelated one-offs — a redundant `<depend>` that
`catkin_pkg` rejects out loud, and a gtest target that did not link the library
under test — both fixed on the next build. Two different loud errors is ordinary
iteration, not a shared gap.

**Rule 5 fired: `skills/ros2-package/` is deleted.** Of its 31 remaining lines,
§2 and §3 were measured 10/10 unaided (and checked on disk in all 10 L2 cells);
§1's documentation-entry-point table was never graded directly and goes out on
the ladder verdict rather than on a number of its own — recorded as such.

Two real Jazzy silent failures turned up while building the rung fixtures, and
are kept in [`LADDER.md`](./LADDER.md) because they are the shape this project is
hunting: omitting `<export><build_type>ament_cmake</build_type></export>` makes
colcon treat the package as catkin, so it never reaches `AMENT_PREFIX_PATH` —
build rc=0, every file installed, and `ros2 run` says `Package not found`. And
**`colcon test` exits 0 when there are no tests**, which is why `t7_tests_ran` is
graded separately from `t7_tests_pass`.

## The ladder, second run — `gazebo-sim` deleted

Three rungs, `baseline` only, n=10 each. Design and rules in
[`LADDER.md`](./LADDER.md).
[L1](./runs/2026-07-30-ladder-gz-L1/NOTES.md) ·
[L2](./runs/2026-07-30-ladder-gz-L2/NOTES.md) ·
[L3](./runs/2026-07-31-ladder-gz-L3/NOTES.md)

| Rung | Mechanisms added | Result |
| :--- | :--- | ---: |
| L1 | SDF world, physics system, diff-drive robot, headless run | 40/40 |
| L2 | + `ros_gz_bridge` direction chars, `gpu_lidar` + `gz-sim-sensors-system`, `/clock` | 40/40 |
| L3 | + URDF spawn via `ros_gz_sim`, `gz-sim-imu-system`, frame naming, `use_sim_time` | 28/30 |

**108 of 110 cell-checks unaided.** Every headline row of the skill's symptom
table was exercised, and none of them was a thing a cell got wrong:

| Symptom row | Rung | Cells wrong |
| :--- | :--- | ---: |
| bridge direction char (`[` vs `]`) | L2 | 0/10 |
| rendering sensor silent without `gz-sim-sensors-system` | L2 | 0/10 |
| `/clock` unbridged, `use_sim_time` broken | L2, L3 | 0/10 |
| IMU silent without `gz-sim-imu-system` | L3 | 0/10 |
| frame composed as `<model>/<link>/<sensor>` | L3 | 0/10 |

The only genuine cell failure was r3 at L3: its bridge line was correct and its
world loaded the IMU system, but its own sensor published on `/imu/raw` while it
bridged `/imu`. A self-inconsistency in one cell, not a shared gap — and one in
ten is what the pre-registered threshold calls noise.

**Rule 5 fired: `skills/gazebo-sim/` is deleted.**

### This ladder was mostly a fight with the grader

Nine grader defects, none model-side. The two worth carrying forward:

- **`set -o pipefail` + `grep -q` reports a match as a failure.** `grep -q` exits
  the instant it matches, the producer takes SIGPIPE, and `pipefail` propagates
  it. Racy, so it passes standalone and fails inside a script.
- **Every grader assertion must trace to a sentence in the frozen prompt.** Three
  false gaps came from checks asserting things the prompt never required: that
  the odometry topic is `/odom`, that a world has a ground plane, that the
  Gazebo model name equals the URDF robot name. Two of them arrived at exactly
  the threshold, in the shape the experimenter would find most interesting.

`g3_spawned` was removed after the round — set out in full in
[the L3 notes](./runs/2026-07-31-ladder-gz-L3/NOTES.md), because dropping a
failing check after seeing it fail is the manufacturing pattern in reverse. It
never had a demonstrated failing case, that was recorded *before* the round, and
its failures were provably false.

## Status

| Skill | Status |
| :--- | :--- |
| `ros2-package` | **DELETED** — ladder exhausted at ceiling, 190 cell-checks across three rungs |
| `gazebo-sim` | **DELETED** — ladder exhausted, 108/110 cell-checks across three rungs |
| `ros2-control` | PARTIALLY VERIFIED — t1, n=10 across rounds 3 and 4. The `/cmd_vel` row is cut; the rest is unmeasured |
| `ros2-core`, `ros2-testing`, `ros2-perception`, `ros2-troubleshooting`, `ros2-moveit`, `ros2-dev` | NOT VERIFIED — no ladder written yet |
| `ros2-microros` | OUT OF SCOPE — no `micro_ros_agent` or `micro_ros_setup` in apt for Jazzy; needs a multi-repository source build |

`ros2-security` was deleted during the first round because the model reproduced
all of it unaided, including details no check tested. That decision was already
the one resting on an argument rather than a number, and v2 is the setting that
can actually test it — a file of documentation pointers cannot pay off in a
harness with no second turn and no tool to follow a link with.

## Reading order

- [`DESIGN.md`](./DESIGN.md) — the criterion and the v2 plan. Start here.
- [`TASKS.md`](./TASKS.md) — the four v2 tasks, their graders, and what was
  decided in advance so it cannot be adjusted after seeing numbers.
- [`FINDINGS.md`](./FINDINGS.md) — what the first round taught, including what
  it got wrong. Read the "what we got wrong" half.
- [`PROCEDURE.md`](./PROCEDURE.md) — step-by-step, being rewritten for v2.
- [`harness/README.md`](./harness/README.md) — the tools.
