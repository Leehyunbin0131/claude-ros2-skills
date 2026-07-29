# Reduction plan

The rule for cutting the 622 lines currently shipped, and the coverage that has
to exist before each cut is allowed.

**Nothing is cut yet.** A first attempt cut 756 lines to 212 in a single scripted
pass and was reverted — see "The attempt that was reverted" at the bottom. That
failure is the reason the coverage table below exists.

## The rule, from three rounds

A line ships if and only if it is something the agent **cannot reach on its
own**, given the model's knowledge, web search, and a live install. Three rounds
found exactly two things that qualify:

| Keep | Evidence |
| :--- | :--- |
| **Files the agent cannot reach** — bundled scripts, project-local facts | round 2: 0/7 vs 8/8 on running the check, p=0.0002 |
| **Instructions to verify** — not the answer, the prompt to go look | round 3: 3/10 vs 10/10, q=0.009 |

And one thing that clearly does not:

| Cut | Evidence |
| :--- | :--- |
| **Facts the model already has or can search for** | round 3: 10/10 unaided on the exact fact v1 added a line for |

## Per-line decision procedure

For every line, in order. First answer decides.

1. **Is it a pointer to a bundled file or a project-local fact?** → keep.
   These are unreachable by construction.
2. **Is it an instruction to verify, measure, or ask — with no answer attached?**
   → keep. This is what round 3 measured.
3. **Is it a fact, a code example, a parameter name, a symptom-cause pair?**
   → cut. The model has it or can search it. Round 3 measured this on the one
   line v1 was most confident about.
4. **Is it a rule about behaviour that is not an instruction to verify?**
   → cut, and note it. Round 1's T3 found the model asks before writing config
   4/5 unaided, so "ask first" prose is not carrying weight on its own.

## What is deliberately *not* being done

- **No line is kept because it is true.** Correct is the floor and was never the
  bar. Three rounds found true content failing to change anything.
- **No line is kept because it looks non-obvious to a human.** That instinct is
  what produced 622 lines.
- **Doc-entry-point tables are cut.** The model reaches `docs.ros.org` and
  `control.ros.org` unaided; round 3's search behaviour was driven by an
  instruction to check, not by a URL list. This is the least certain cut in the
  pass and is marked as such below.
- **The verification scripts are not touched.** They are the only thing with an
  unambiguous measured effect.

## Coverage: what may be cut, and what may not

A cut needs a v2 measurement **of that skill**. Generalising "facts are
reachable" from two skills to the other eight is an inference, not a
measurement, and it is exactly what went wrong on the first attempt.

| Skill | v2 coverage | May cut? |
| :--- | :--- | :--- |
| `ros2-troubleshooting` | t2, n=10, scripts 0/7 vs 8/8 | **yes** — for the script section |
| `ros2-control` | t1, n=10, the `cmd_vel` fact 10/10 unaided | **yes** — for that row |
| `ros2-moveit` | t1 covers the servo row indirectly | partially — the servo row needs its own task |
| `ros2-core` | none | **no** |
| `ros2-package` | none | **no** |
| `ros2-testing` | none | **no** |
| `ros2-perception` | none | **no** |
| `ros2-dev` | round 1 T3 only, which was null | **no** |
| `gazebo-sim` | none | **no** |
| `ros2-microros` | none — out of scope | **no** |

Seven skills have no v2 measurement at all. They stay as shipped until one
exists, however confident the generalisation feels.

## Expected result, recorded in advance

50-150 lines total, mostly:

- `ros2-troubleshooting` keeps the script section — the one measured keeper.
- Every skill keeps at most a short "verify X against the install before writing
  it" line.
- Everything else goes: architecture prose, code examples, symptom tables,
  tuning baselines, parameter names, plugin strings.

If the result lands near 300 the rule was not applied honestly. If it lands near
20 something load-bearing was probably cut and the next round should catch it.

## How this gets checked

The reduced bodies are not trusted on argument. After the pass:

1. `t2` re-run — the script section must still work (`baseline` vs `skills`).
2. `t1` re-run — the verify instruction must still produce 10/10 searching.
3. `t4` re-run — the null control must stay null.

A reduction that breaks any of those is reverted, not defended.


---

## The attempt that was reverted

Recorded because the failure is more instructive than the plan.

**What was done.** A Python script with one `VERIFY` template generated nine
new `SKILL.md` bodies from scratch, `ros2-troubleshooting` was rewritten by hand,
and `ros2-dev/references/` (134 lines) was deleted. 756 lines became 212 in a
single pass.

**Why it was wrong.** Three reasons, in order of severity:

1. **402 of those lines were cut with no v2 measurement of the skill they came
   from.** `gazebo-sim` lost 65 lines, `ros2-package` 51, `ros2-microros` 47,
   `ros2-dev` 38 plus 134 reference lines — and not one of those skills has been
   measured under the real-environment criterion. The justification was
   "facts are reachable", which two skills demonstrated and seven did not.

2. **The procedure in this document was not followed.** It says: for every line,
   in order, first answer decides. What happened was wholesale replacement from a
   template — most of the deleted content was never read, let alone classified.
   Writing the rule down and then not applying it is worse than not writing it.

3. **A single-task result was stated as general fact inside all nine files.**
   Every generated body contained "measured: without an instruction to check,
   seven answers in ten come straight from memory". That is one number from t1.
   Presenting it as a property of every domain overstates it.

**And the verification would not have caught any of it.** The check launched
afterwards ran t1, t2 and t4 — which touch `ros2-control`, `ros2-moveit`,
`ros2-troubleshooting` and a `/scan` node. Nothing in that set exercises the
402 lines that had just disappeared. It would have come back green and been read
as "the reduction is safe".

**What replaces it.** The coverage table above. One skill at a time: design a
task with a real-outcome grader, measure `baseline` vs `skills`, then cut what
the measurement says is reachable — and only in that skill.
