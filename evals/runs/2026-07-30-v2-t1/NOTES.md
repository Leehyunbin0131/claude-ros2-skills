<!-- Round 3. First round run with cells isolated from the repository
     (isolate_cell.sh). Design in ../../DESIGN.md, task in ../../TASKS.md. -->

# v2 round 3 — do the two lines v1 added earn their place?

> **CORRECTED BY ROUND 4 — read this first.** The `t1_searched_or_read` result
> below is real, but its attribution is wrong. `run_ab.sh` installs `CLAUDE.md`
> into the `skills` cell alongside `skills/*`, and `CLAUDE.md` already instructs
> the agent to verify against `/opt/ros/jazzy` instead of answering from memory.
> Round 4 ran a `claude-md-only` cell: **10/10, identical to `skills`, with no
> skill files at all** (`../2026-07-30-v2-t1-claudemd/`). So the sentence below
> calling this "the first significant result attributable to skill *prose*" is
> withdrawn — it is attributable to `CLAUDE.md`. The rest of this round stands.

20 cells, `t1` only, `baseline` vs `skills`, n=10. First round with isolation
enforced; **no cell reached the repository.**

The two lines under test were both *added* by v1 after it found the model getting
them wrong, and both measured `KEEP` under the tools-off harness: the
`TwistStamped`-only subscription and the absence of a `use_stamped_vel`
parameter. `DESIGN.md` predicted both would fail under the real-environment
criterion.

**The prediction was half right, and the half it got wrong is the more useful
half.**

| Check | baseline | skills | Δ | q |
| :--- | ---: | ---: | ---: | ---: |
| `t1_correct_type` — names `TwistStamped` | **10/10** | 10/10 | +0.00 | 1.000 |
| `t1_searched_or_read` — verified against install or web | 3/10 | **10/10** | +0.70 | **0.009** |
| `t1_no_invented_param` — did not prescribe `use_stamped_vel` | 3/10 | 6/10 | +0.30 | 0.555 |

## The fact does not earn its place

`t1_correct_type` is **10/10 in both cells**. Every baseline cell names
`TwistStamped` as what Jazzy's `diff_drive_controller` subscribes to, with no
skill in context.

That line was added by v1 because the tools-off model failed this 4 times out of
4. Give the model a real session and it is right every time. **As a fact, the
line is dead weight** — exactly what `DESIGN.md` predicted.

## The behaviour does

`t1_searched_or_read` is **3/10 against 10/10, q=0.009**. This is the first
significant result in the project attributable to skill *prose* rather than to a
shipped file.

With the skill loaded the agent verifies — every single cell either searched the
web or read `/opt/ros/jazzy`. Without it, seven cells out of ten answered from
memory and never checked anything.

That is category 3 in `DESIGN.md`: known but not done. The agent does not need to
be told the answer; it needs to be told to look. And round 1's T3 had suggested
category 3 was empty, because on that task the model asks questions unprompted
anyway. It is not empty — it just is not where round 1 looked.

## The error it was written to prevent still happens

`t1_no_invented_param` is the reason not to celebrate. **Seven baseline cells out
of ten prescribe `use_stamped_vel`**, a parameter that does not exist in Jazzy —
alongside the correct `TwistStamped` answer, in the same reply. The model holds
the right fact and a wrong one together.

With the skill, four cells out of ten *still* prescribe it. The line halves the
error and does not remove it, and at n=10 that difference is not significant
(Δ=+0.30, q=0.555). Recorded UNDERPOWERED, not topped up.

So the line does its job partially at best. A skill that says "there is no
`use_stamped_vel` parameter; do not invent one" is still being ignored 40% of the
time by an agent that has read it.

## What this means for the two lines

| Line | Verdict |
| :--- | :--- |
| `TwistStamped`-only subscription (the fact) | **does not earn its place** — 10/10 unaided |
| "there is no `use_stamped_vel`; do not invent one" (the warning) | **unresolved** — halves the error, not significantly, and is ignored 4/10 |
| the surrounding prose that makes the agent verify | **earns its place** — q=0.009 |

The interesting consequence: what should survive in that row is not the answer
but the instruction to check. Rewriting it to drop the fact and keep the
verification prompt is the obvious next experiment, and it is a *smaller* line
than the one shipped.

## Two rounds lost before this one, both to the harness

Worth recording because both produced numbers that looked real.

**Round 3, first attempt: all 20 cells returned "Not logged in".** The isolation
wrapper pointed `HOME` at the cell directory to hide the repo from a plain
`ls ~`; `claude` keeps its credentials under `$HOME`, so nothing authenticated.
The bind-mount is what closes the leak — moving `HOME` added nothing and cost a
round. `isolate_cell.sh` now leaves `HOME` alone and says why.

**And the grader scored that failure 10/10.** `t1_no_invented_param` is a
negative check: the error message "Not logged in · Please run /login" does not
contain `use_stamped_vel`, so every dead cell passed. `Cell.gradable()` now
rejects short answers that are nothing but a harness error, and the dead
transcript was re-checked to confirm it returns ungradable.

Also fixed: `claude -p` inside the namespace waited on stdin, warned, and
produced a stub. `exec ... </dev/null` now.

Three defects, all in the measurement, all found by asking why a number looked
odd rather than by accepting it. That ratio has not improved across the project.
