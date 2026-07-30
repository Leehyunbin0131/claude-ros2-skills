# Verification design (v2)

Written **before** any measurement, deliberately. The previous round measured
the wrong thing for a defensible-sounding reason and produced 5,156 cells of
answers to a question nobody asked. That data has been deleted. This document
fixes the question first.

---

## 1. What a skill is for

A skill file exists to supply what the agent **cannot reach on its own**.

That is the whole test. Not "is this true", not "is this useful to a human", not
"does the model do better with it" — **can the agent get here without it?**

An agent in real use has: the model's own knowledge, web search, and a live ROS 2
install it can read and run. If a line's content is inside that reach, the line
is decoration paid for on every load.

## 2. Three things the agent cannot reach

The criterion above is not only about errors. Three distinct categories pass it,
and a skill should contain these and close to nothing else.

| # | Category | Test | Example |
| :-- | :--- | :--- | :--- |
| 1 | **Wrong even with search** | agent searches, still gets it wrong | rarer than expected — see the pre-check below |
| 2 | **Not reachable at all** | nothing on the web or in the install contains it | the four `check_*.py` scripts shipped beside `ros2-troubleshooting`; this robot's real wheel radius; this workspace's conventions |
| 3 | **Known but not done** | the agent can state the right behaviour when asked, and does not do it unprompted | **the example that was here has been refuted** — see the note below |

Category 3 is not knowledge. Search cannot fix it. It was the highest-value
content measured in the previous round and is the easiest to mistake for padding.

### Category 1 is much smaller than it looked — measured before designing anything

The two "gaps" the previous round found were re-tested with `WebSearch` and
`WebFetch` enabled, one prompt each, before any task was written:

| Question | tools off (v1) | **with search** |
| :--- | :--- | :--- |
| what does Jazzy's `moveit_servo` use to switch command types? | prescribes the removed `/servo_node/start_servo` + `std_srvs/srv/Trigger`, 4 times in 4 | **correct** — finds `switch_command_type` and `moveit_msgs/srv/ServoCommandType`, cites the MoveIt docs and the Jazzy API page |
| what does `diff_drive_controller` subscribe to, and does `use_stamped_vel` exist? | invents `use_stamped_vel`, 4 times in 4 | **correct** — `TwistStamped` only, names the Humble-era default as the reason for the confusion, cites the docs and `ros2_controllers` |

Both lines were **added to the skills by the previous round** and both measured
`KEEP`. Under the criterion in section 1 neither survives: the agent reaches the
answer on its own. They stay in the files only until v2 confirms this at n≥5,
and they are the first thing v2 should try to remove.

That is the clearest possible demonstration of why the old measurement was
wrong. It was not slightly optimistic; it manufactured two keepers out of a
restriction the deployed agent does not have.

**What this does not settle:** whether the agent *bothers* to search. Both
pre-checks told it to. An agent that answers from memory when nobody insists is
a category 3 problem, not category 1, and v2 grades that separately.

### Why search makes the remaining category 1 sharper, not weaker

Searching does not only help. The web is full of Humble- and Iron-era answers,
and both errors found in the previous round have that shape — the model's wrong
answer *used to be right*. Search can confirm the wrong answer with more
confidence than the model had alone.

So a skill's job on category 1 is often **not to supply the fact** but to pin
the version and name the authoritative local source. That is an argument for
keeping a small number of pointers, not for deleting them.

> **Category 3, as illustrated, did not survive measurement.** The example
> written here was: asked to "set up Nav2", the agent writes a parameter file
> instead of first asking for footprint and drive type. Round 1's `t3` measured
> baseline asking unprompted **4/5**, so that is not a gap.
>
> Round 3 then found a real instance — the agent verifying against the install
> instead of answering from memory, 3/10 vs 10/10 — and round 4 showed that
> belongs to `CLAUDE.md`, not to any skill. So category 3 has **one confirmed
> instance and it lives in `CLAUDE.md`**. The category is not empty; it is just
> not somewhere a `SKILL.md` has yet been shown to reach.

## 3. The environment must be the real one

The previous round ran every cell single-turn with `--tools ""`. That was not
arbitrary: per-claim ablation *requires* it, because an agent with tools reads
the real file and ablating a line from its context proves nothing.

The mistake was letting the ablation instrument define the whole project. Tools
off answers "which line is load-bearing **given that the agent cannot look
anything up**", and nobody ships that agent.

**v2 measures in the environment the skills actually run in:**

- tools enabled — `Read`, `Grep`, `Glob`, `Bash`, `WebSearch`, `WebFetch`
- multi-turn, not one question and one answer
- a real workspace on a live Jazzy install
- the skill loaded the way it is really loaded, or absent entirely

`evals/harness/run_ab.sh` already does most of this and predates the ablation
work. It is the starting point, not a rewrite.

## 4. What gets graded

Grading must be anchored outside the file. Ranked, and v2 uses the highest
available for each task:

1. **Did it work.** `colcon build` succeeds, the node runs, `ros2 topic echo`
   shows data, a check script exits 0. Cannot be satisfied by wording.
2. **Is it true against the install.** `ros2 interface show`, a header at that
   path, a `.srv` declaring those constants, a class pluginlib registers.
3. **Did the agent go and check.** Read off the transcript: which tools it
   called, whether it read the installed defaults before writing a parameter,
   whether it asked before generating 200 lines. This is the only way to measure
   category 3, and the previous harness made it structurally invisible.

Never grade on "does the answer contain the file's phrasing". The previous round
proved where that leads: every suite whose checks were written that way returned
`full` = 1.000, which is a statement about the checks.

The real-outcome graders already built are kept and reused: `colcon build` in a
scratch workspace, `g++ -fsyntax-only` against the installed include dirs,
`gz sdf --check`, and the 233-class pluginlib index.

## 5. How a line earns its place

Per candidate line, in order. Stop at the first failure.

1. **True?** Verify against `/opt/ros/jazzy/` or the authoritative doc. A wrong
   line is worse than a missing one — it manufactures the error it claims to
   prevent.
2. **Reachable?** Give the agent the task with tools and search, no skill. If it
   gets there, the line does not ship. This is the step the previous round could
   not perform.
3. **Which category?** If it survives step 2, say which of the three it is. A
   line that fits none of them is being kept on intuition.
4. **Does it change the outcome?** With and without, n≥5, graded by section 4's
   anchors. Ablation on a single line only where tools-off is defensible for
   that specific check.

## 6. What carried over from v1, and what did not

**Deleted:** all 23 run directories, all authored variants, every `VERIFIED`
status. Those verdicts answered "does the model know this unaided", which is not
the criterion any more, and a `KEEP` under the old question does not transfer to
the new one.

**Kept, because it does transfer:** every `CUT` decision already applied to the
skill files. The logic is one-way — content the model produces *without* tools
it certainly produces *with* them — so those cuts are conservative under the
stricter rule. They stay cut.

**Kept, because it is independent of any harness:** the two facts verified
against the install. Jazzy's `diff_drive_controller` subscribes to `TwistStamped`
only and has no `use_stamped_vel` parameter; Jazzy replaced
`/servo_node/start_servo` with `/servo_node/switch_command_type`
(`moveit_msgs/srv/ServoCommandType`). Both are properties of the install, not of
the measurement.

**Kept, because v2 needs it:** the harness code, the real-outcome graders, and
the method failures written up in `FINDINGS.md` — non-answers must not be scored
as wrong answers, checks must be anchored outside the file, a probe prompt must
read like a user's question and never hint that context exists to be found.

## 7. Expected outcome, stated in advance

So it can be wrong later rather than rationalised later: applying this criterion
should leave **far less** than the 622 lines currently shipped — a rough guess
is 50–150. Most surviving content should be category 2, a little category 1
around version-specific breakage, and a small amount of category 3 prose whose
job is to make the agent stop and ask.

If v2 comes back saying most of the current content earns its place, that is a
result worth having and this paragraph is the record that it was not expected.

## 8. Order of work

1. **Confirm `run_ab.sh` runs end-to-end.** Done — one sonnet A/B pair on the
   `/scan` task completed with a live publisher up. Tool counts differed in the
   expected direction (`baseline` 3 calls, `skills` 9, including one `Skill`
   load), which is the signal the tools-off harness could not see at all.
2. **Confirm the environment can actually search.** Done — `WebSearch` and
   `WebFetch` are present in the cell and work, and the pre-check in section 2
   is the result.
3. **Write the tasks.** Done — [`TASKS.md`](./TASKS.md): three targeting one
   category each, plus a null control that must show no difference or the round
   is void.
4. **Build what the tasks need** — a wrong-mount IMU publisher, a `ros2_control`
   bring-up, a `scripts-only` cell, and `grade_v2.py` so nothing is graded by
   reading.
5. Run, then judge lines per section 5.

Nothing is measured until step 4 is complete.
