<!-- Narrow follow-up to ../2026-07-29-v2. Pre-registered in ../../TASKS.md
     ("Round 2 — narrow, by design") before any cell here existed. -->

# v2 round 2 — does shipping the scripts earn its place?

20 cells, `t2` only, `baseline` vs `scripts-only`, n=10. Four tests to correct
across instead of round 1's sixteen.

**Result: yes, and it is the first thing in this project to clear the bar under
the real-environment criterion.**

| Check | baseline | scripts-only | Δ | q |
| :--- | ---: | ---: | ---: | ---: |
| `t2_exit_code_read` | 0/10 | **10/10** | +1.00 | **0.000** |
| `t2_ran_script` | 1/10 | **10/10** | +0.90 | **0.000** |
| `t2_evidence_not_guess` | 9/10 | 10/10 | +0.10 | 1.000 |
| `t2_no_ros2_run` | 1/1 | 10/10 | +0.00 | 1.000 |

Both real-outcome graders — *did the script actually run*, and *was its verdict
reported* — are unambiguous. The pre-registered rule said clearing q<0.05 means
the scripts ship, so they ship.

## What the baseline does instead, and why it is not enough

`t2_evidence_not_guess` is **9/10 for the baseline**. It is not helpless: given a
live `/imu/data` and no script, it writes its own throwaway subscriber, samples
the topic, and reports a measured acceleration. It reaches evidence by a longer
route almost every time.

So the finding is not "the agent cannot diagnose an IMU mount". It is narrower
and more useful: **a checked, exit-coded verdict is something it does not produce
on its own** — 0/10 on `t2_exit_code_read`. The script's value is not the
knowledge, it is the pass/fail.

## A contamination path, found while reading the one anomalous cell

`t2_ran_script` is 1/10 for the baseline rather than 0/10. Tracing that cell
(`r7`) shows why, and it is a defect in the harness, not a fluke:

```
Bash:  ls -la /home/hyunlee/home/claude-ros2-skills
Read:  /home/hyunlee/home/claude-ros2-skills/evals/DESIGN.md
Read:  /home/hyunlee/home/claude-ros2-skills/evals/harness/fake_imu_pub.py
```

The cell ran in an isolated `/tmp` directory, but nothing stopped it from
globbing `$HOME`, finding this repository, and reading **the eval design document
and the scenario source**. `fake_imu_pub.py` names `check_imu_gravity.py` in its
docstring and states the planted answer outright — gravity on `+X`.

**Direction of the bias: it strengthens the baseline**, so the measured effect is
understated, and the result cleared q<0.05 anyway. The conclusion is safe. But
the leak is real and has to be closed before any round where it could cut the
other way — a `skills` cell reading `TASKS.md` would learn exactly which graders
it is being scored on.

Fix for future rounds: cells must not be able to reach the repository. Options,
in order of preference — run cells in a container with only `/opt/ros` and the
cell directory mounted; or move the repo out of `$HOME` for the duration of a
round; or at minimum verify per cell that no read touched the repo path and
discard cells that did. **Not fixed in this round**, and this round's numbers are
reported with the leak present rather than re-run to hide it.

## What this round settles, and what it does not

**Settles:** category 2 in [`DESIGN.md`](../../DESIGN.md) — content the agent
cannot reach — is real and measurable. Files that exist nowhere else change
behaviour outright.

**Already settled by round 1, and unchanged:** the `SKILL.md` prose describing
those scripts adds nothing on top of shipping them (`skills` vs `scripts-only`,
+0.00 on every check, n=5). This round did not include the `skills` cell because
round 1 had already answered that.

**Does not settle:** whether any *prose* in any skill earns its place. Nothing in
either round has shown that. Round 1's T1 and T3 both came back null or
underpowered, and the two lines v1 added to the skills are still expected to
fail.

## Bookkeeping

- Control gate inherited from round 1 (`t4` 5/5 vs 5/5), not re-paid. This round
  has no `skills` cell for that bias to act on.
- `t2_no_ros2_run` is 1/1 gradable for the baseline because it returns ungradable
  unless the answer engages with the scripts at all — nine baseline cells never
  mentioned them, and scoring those as "did not misuse the scripts" would be a
  free pass.
- No top-up. The two nulls stay null.
