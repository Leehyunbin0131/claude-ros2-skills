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
`/opt/ros/jazzy/`, and both are now in the shipped skills:

- Jazzy's `diff_drive_controller` subscribes to `geometry_msgs/msg/TwistStamped`
  only, and has **no `use_stamped_vel` parameter** — the model prescribes one
  4 times out of 4. (`diff_drive_controller_parameters.hpp` declares 23
  parameters; none is that.)
- Jazzy replaced `/servo_node/start_servo` (`std_srvs/srv/Trigger`) with
  `/servo_node/switch_command_type` (`moveit_msgs/srv/ServoCommandType`). The
  model prescribes the removed service 4 times out of 4, and the skill used to
  agree with it.

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
| T3 | asking before writing | **null.** Baseline asks for footprint and drive type before writing config 4/5 on its own |
| T4 | null control | 5/5 vs 5/5. Gate passed |

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

**The instruction to verify does.** 3/10 against 10/10, q=0.009 — the first
significant result in this project attributable to skill *prose* rather than a
shipped file. With the skill, every cell searched or read `/opt/ros/jazzy`;
without it, seven answered from memory and checked nothing. That is category 3,
which round 1's T3 had suggested was empty. It is not empty; round 1 looked in the
wrong place.

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

## Status

| Skill | Status |
| :--- | :--- |
| `ros2-core`, `ros2-package`, `ros2-testing`, `ros2-perception`, `ros2-troubleshooting`, `ros2-control`, `ros2-moveit`, `ros2-dev`, `gazebo-sim` | NOT VERIFIED — awaiting v2 |
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
