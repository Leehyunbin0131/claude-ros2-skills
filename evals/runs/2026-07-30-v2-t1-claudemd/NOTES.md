<!-- Round 4. Design and pre-registration in ../../TASKS.md, "Round 4". The
     prediction and the decision table were written before any cell ran. -->

# v2 round 4 — `CLAUDE.md` owns the only prose result this project had

20 cells, `t1` only, `baseline` vs `claude-md-only`, n=10, isolated.

Round 3 reported the project's first and only significant effect attributable to
skill *prose*: `t1_searched_or_read` went 3/10 → 10/10, q=0.009, and was written
up as evidence that "instructions to verify" earn their place in a `SKILL.md`.

**That reading was confounded and is now retracted.** `run_ab.sh`'s `run_cell`
copies `CLAUDE.md` into the `skills` cell along with `skills/*`, and `CLAUDE.md`
opens with:

> Do NOT answer ROS 2 / Gazebo / Nav2 / MoveIt / ros2_control / perception
> questions from memorized knowledge. [...] Verify the specific API / message /
> parameter against the doc that skill names, or against local `/opt/ros/jazzy/`

That is the measured behaviour stated outright, in the file that is always in
context. This round removes the skills and keeps only that file.

## The result

| Check | baseline | `claude-md-only` | Δ | q |
| :--- | ---: | ---: | ---: | ---: |
| `t1_correct_type` | 10/10 | 10/10 | +0.00 | 1.000 |
| `t1_no_invented_param` | 4/10 | 6/10 | +0.20 | 0.984 |
| `t1_searched_or_read` | 2/10 | **10/10** | +0.80 | **0.002** |

## Side by side with round 3

| Check | baseline | `claude-md-only` | `skills` (r3) |
| :--- | ---: | ---: | ---: |
| `t1_correct_type` | 10/10 | 10/10 | 10/10 |
| `t1_no_invented_param` | 4/10 | 6/10 | 6/10 |
| `t1_searched_or_read` | 2/10 | 10/10 | 10/10 |

`CLAUDE.md` alone reproduces the `skills` cell **exactly**, on every check.

Cross-round comparisons (weaker than a concurrent pair, and labelled as such —
but the two rounds share task, scenario, model, grader and isolation):

| Comparison | | | Δ | p |
| :--- | ---: | ---: | ---: | ---: |
| `skills` r3 vs `claude-md-only` r4, searched | 10/10 | 10/10 | +0.00 | 1.000 |
| `skills` r3 vs `claude-md-only` r4, invented param | 6/10 | 6/10 | +0.00 | 1.000 |

**Adding ten `SKILL.md` files on top of `CLAUDE.md` moves nothing.**

## The control held

Round 4 re-ran `baseline` concurrently rather than reusing round 3's. It had to
reproduce round 3's 3/10 or neither round could be read:

| | round 3 | round 4 | p |
| :--- | ---: | ---: | ---: |
| `baseline`, `t1_searched_or_read` | 3/10 | 2/10 | 1.000 |

The harness has not drifted. This is a stronger control for this question than
re-running `t4` would have been, because it is the same grader on the same task.

## What this retracts

Round 3's own notes said `t1_searched_or_read` was "the first significant result
in the project attributable to skill *prose* rather than to a shipped file."
Replace that with: **it is attributable to `CLAUDE.md`.** After four rounds the
score is

| Content | Status |
| :--- | :--- |
| bundled scripts (`check_imu_gravity.py`) | **earns its place** — round 2, 10/10 vs 1/10, q<0.001 |
| `CLAUDE.md`'s verify paragraph | **earns its place** — this round, 10/10 vs 2/10, q=0.002 |
| any `SKILL.md` prose | **no measured effect anywhere** |

That is not proof the skills are worthless — seven of them have never been
measured at all, and this is one task. It is proof that the one result being
used to justify keeping skill prose does not say what it was read as saying.

## What it licenses, and what it does not

**Licensed, for `ros2-control` only** — the skill this task actually exercises.
Every measured effect in its `/cmd_vel` row is reproduced by `CLAUDE.md`:

| Content in that row | baseline | `claude-md-only` | `skills` |
| :--- | ---: | ---: | ---: |
| the `TwistStamped` fact | 10/10 | 10/10 | 10/10 |
| the verify instruction | 2–3/10 | 10/10 | 10/10 |
| the `use_stamped_vel` warning | 3–4/10 | 6/10 | 6/10 |

Nothing in it ships on measurement. The row goes.

**Not licensed.** Cutting verify prose from the other nine skills. That is one
task generalised to nine unmeasured files, which is precisely the error that
caused the reverted reduction. `t1` exercises `ros2-control` and touches
`ros2-moveit`; it says nothing about `gazebo-sim` or `ros2-perception`.

## One thing to be careful about

`t1_searched_or_read` asks whether the agent verified *at all* — a `WebSearch`,
or a read under `/opt/ros/jazzy`. It does not ask whether the verification was
aimed at the right thing. A `SKILL.md` that names *which* file to read could in
principle beat `CLAUDE.md`'s general instruction without moving this grader.
Nothing here rules that out; it is simply not what was measured, and it cannot
be claimed until it is.
