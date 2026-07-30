# What measuring nine skills taught

> **Mixed validity — read with this in mind.** Every number here comes from the
> **v1** harness, which ran cells with tools disabled. That data was deleted
> because it measured a restriction nobody ships.
>
> - **Still valid:** the lessons about *measuring* — correct is not useful, a
>   grader that has only seen good answers is not validated, single runs
>   generate mechanisms that do not survive.
> - **Not valid:** every verdict about a specific skill or line. Two lines v1
>   *added* after the model failed them 4/4 were later measured 10/10 correct by
>   an agent with a shell. `ros2-security`'s deletion rests on a tools-off
>   1.000 and is flagged in [`RESULTS.md`](./RESULTS.md) as the decision that
>   rested on an argument rather than a number.
>
> Current: [`LADDER.md`](./LADDER.md), [`RESULTS.md`](./RESULTS.md).

`RESULTS.md` is the per-skill record and `PROCEDURE.md` is how to run a
verification. This file is the part worth reading if you are never going to run
one: what came out of 5,156 graded cells and $122 of measurement, stated as
claims about skill files rather than about this repository.

Every number here is on `sonnet`, the model these skills ship against, against a
live ROS 2 Jazzy install.

---

## 1. Correct is not useful, and the gap is enormous

The instinct when writing a skill is to record what is true and hard-won. Almost
all of that is already in the model.

Across nine skills, most lines that were cut were true, well-written, and
reproduced near-verbatim by the model with no file in context. Concretely:

- Asked for the `ROS_DOMAIN_ID` range, the model gives `0-232`, the `0-101`
  ephemeral-port caveat, and the `7400 + 250×id` arithmetic behind it — strictly
  more than the skill said.
- Asked to stand up SROS2, it produces every command with the right positional
  arguments and short flags, verified against `--help`.
- Asked to diagnose a silent topic, it reaches for `ros2 topic info -v` unprompted.

**`ros2-security` was deleted entirely on this basis.** Its measured baseline
was 1.000 unaided — a perfect score with no file at all leaves nothing for a
file to add.

The practical rule: before writing a line, ask the model the question cold and
read the answer. If it is already there, the line is decoration.

## 2. Content expires, and ablation cannot tell you

A per-claim sweep scores the lines that exist. It is silent about two things.

**Lines whose failure has been fixed since.** `ros2-package` gained two lines
because the model kept omitting a `package.xml` export tag and a `setup.cfg`
install path. It now supplies both unaided. `ros2-dev` still opens by calling a
dropped package prefix "the single most common startup-killing error" — measured
against the real pluginlib index of 233 registered classes, every plugin string
the model emits unaided is real, 9 times in 9.

**Lines that should exist and do not.** `ros2-control` said nothing about
`/cmd_vel`, while the model — asked why an active `diff_drive_controller`
ignores it — correctly diagnoses a `Twist`/`TwistStamped` mismatch and then
prescribes `use_stamped_vel`, a parameter that exists nowhere in Jazzy, 4 times
in 4. A row naming the real interface was added and measured **KEEP at q=0.050**.

Only asking the model cold and checking its answer against the install finds
either case.

## 3. A skill can be a liability, not merely inert

`ros2-moveit` told readers to call `/servo_node/start_servo` with
`std_srvs/srv/Trigger`. Jazzy removed that interface; `moveit_msgs` ships
`ServoCommandType.srv` instead. The model prescribes the same dead service 4
times in 4 — so the file was **confirming the model's error rather than
correcting it**.

This is invisible to ablation by construction: measuring a wrong line only asks
whether the model repeats it, and it does, so the line scores as load-bearing.
The verdict table cannot distinguish "this line is working" from "this line and
the model are wrong together". Only an external source can.

## 4. Keep the reason, not just the instruction

The most expensive lesson in the project. Three consecutive rewrites of
`ros2-troubleshooting` were rejected on measurement, and the cause was not the
file — it was how the rewrites were written.

A body that explains a cause and then gives a fix compresses very naturally into
the fix alone:

> *"a single-threaded executor cannot process service responses while executing a
> blocking callback, so use `MultiThreadedExecutor` with a `ReentrantCallbackGroup`"*

became

> *"use `MultiThreadedExecutor` with a `ReentrantCallbackGroup`"*

and the check looking for the diagnosis dropped from 16/16 to 9/16. The model
followed the shorter framing and produced the action without the reason.

**Cut the worked example before you cut the "because".**

## 5. A terse summary can be worse than saying nothing

Not merely worse than the full text — worse than omission.

One check scored **8/8 in the variant that omitted its topic entirely** and
**7/16 once a short summary of a *different* topic was added nearby**. Omit a
topic and the model answers from its own knowledge, completely. Summarise it
badly and the summary becomes the frame the answer is built on, so whatever the
summary dropped is dropped from the answer too.

If a section cannot be shortened without losing its reasoning, deleting it
outright is a real option and sometimes the better one.

## 6. Prose often beats a worked example

Replacing a 23-line `launch_testing` example with one descriptive sentence tied
on every check **and gained four correct API details the example never showed** —
`@pytest.mark.launch_test`, `assertWaitForStartup`, `proc_output.assertWaitFor`,
and the `add_launch_test()` CMake call, all verified present in the install. The
same substitution worked on a CMake reference block in `ros2-package`.

A worked example appears to act as a ceiling: the model reproduces it and stops.
Name the concept and it brings its own knowledge.

This only holds when the prose names the **specifics** — the exact install path,
the exact flag, the exact ordering constraint. A sentence that gestures at the
topic without them is finding 4 again.

## 7. What survives hardest is what the model cannot know

The strongest KEEP verdicts in the project are filenames and behaviours local to
this repository: the four `check_*.py` scripts shipped beside
`ros2-troubleshooting`, the rule that they are plain files run with `python3`
rather than a ROS 2 package, and one deliberately counter-intuitive behaviour of
`check_tf_tree.py`. Those score **0.05 unaided against 0.98 with the file**.

Everything else in a skill competes with what the model already has.

## 8. The highest-value content is not a fact

`ros2-dev`, asked cold to "set up Nav2 and tune it", writes a full parameter
file immediately. With the skill loaded it stops and asks for footprint, drive
type, and who publishes `map -> odom` first:

| | naked | with the skill |
| :--- | ---: | ---: |
| asks for footprint | 1/7 | 5/7 |
| asks which drive type | 1/7 | 5/7 |
| asks who publishes `map -> odom` | 0/7 | 5/7 |
| checks odometry before tuning AMCL | 1/7 | 7/7 |

Prose whose whole job is to make the agent **stop and ask** is the most valuable
content measured here — and the content most easily destroyed by compression,
because it reads like padding.

---

## What we got wrong, and how

Roughly half of what this project "discovered" turned out to be defects in its
own measurement. That ratio is normal early on. It is also the reason every
surprising result got checked twice before it was written down — and the reason
two of them still had to be retracted afterwards.

**Verdicts are about the grading model, not the skill.** An entire first pass
was run on `haiku` and then deleted rather than kept. A `KEEP` from a smaller
model does not transfer upward, and the disagreement has a *direction*:
small-model grading over-keeps inlined technical facts and under-values pointers
to documentation, exactly inverting this pack's stated philosophy. The one
direction that does transfer is `CUT`.

**A `full` score of 1.000 is a statement about the checks.** Three suites whose
probes were written by reading the skill returned `full` = 1.000. Of course they
did: the file says X, the model with the file says X, the check greps for X.
Split by what each check is anchored to:

| | naked | full |
| :--- | ---: | ---: |
| checks anchored to the install or a real parser | 0.05 – 0.74 | 0.97 – 0.98 |
| checks that echo the file's own phrasing | 0.50 – 0.83 | **1.000** |

Same runs, same answers. Once checks were anchored to a real SDF parser and a
real plugin index instead, `full` came back at 0.976 and 0.882. **Anchor every
check to something outside the file**, and treat `naked` as the trustworthy half
of the comparison — no amount of check-wording bias can inflate it.

**Single-claim results do not predict what happens to the body they are cut
from.** A line can measure `naked = full = ablate = 1.00` and still break a
check when the section around it goes. A line can be inert against an empty
prompt and load-bearing against its own table — one row measured Δ=+0.12,
p=1.000 alone, and scored *below the no-context baseline* when actually removed,
because the model then borrowed a neighbouring row's framing and produced a
confident wrong answer. The state that matters is the one that will ship.

**Non-answers are not wrong answers.** The single most persistent bug here.
Models refuse, truncate, or try to use a tool the harness has disabled, and each
new rendering of that had to be caught separately — `**Tool: bash**`, an icon
glyph, `Tool Call:` with a space, `Search(pattern: "x")`, and a bare
`Bash(grep …)` complete with a *fabricated* result block citing a line number
the file does not have. Every one of them was being scored as a wrong answer,
deflating whichever baseline it landed in.

**And a probe prompt must read like a user's question.** Four prompts said "I
have this repo's Claude skills installed", meaning to be fair about expecting
the agent to find a script. It did the opposite — it told the model that context
existed to be hunted for, and with tools off the hunt stalls. Nine of sixteen
baseline cells stubbed and the run was unusable.

---

## The limit this method does not clear

Every cell here is **one question, one answer, tools off**. Real work is many
turns with tools available, and `CLAUDE.md` tells the agent to go verify against
the live install — which is exactly the behaviour this harness disables.

That is not a footnote. It is why:

- `ros2-security`'s deletion is the one decision in this project resting on an
  argument rather than a number: its remaining content was documentation
  pointers, and a pointer cannot pay off in a setting with no second turn and no
  tool to follow it with.
- The most valuable thing measured (finding 8, asking before writing) is a
  *disposition*, and this harness can barely see dispositions.
- A cross-check across grading models found that navigational lines gain value
  as the model gets stronger while technical facts lose it — measured only
  indirectly, because the instrument cannot follow a link.

Closing this means building a different harness — tools enabled, multi-turn,
grading whether the agent *went and checked* — not writing a different probe.
It is the largest open item, and nothing above should be read as settled in that
setting.
