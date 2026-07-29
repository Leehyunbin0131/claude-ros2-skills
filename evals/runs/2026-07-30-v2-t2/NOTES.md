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

## A contamination path — and a correction to the first count

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

**This was first written up as one cell. It was five.** A leak detector added
straight afterwards — `grade_v2.leaked()`, which flags any tool input containing
the repository path — reports **5 of 20 cells**: `r1` and `r9` baseline, `r7`
baseline, `r2` and `r8` scripts-only. Reading one transcript by hand found one
instance and implied it was isolated; only the mechanical check gave the real
number. That is the same lesson as everywhere else in this project, arriving
again: do not hand-count what a script can count.

The conclusion is unaffected, and excluding the contaminated cells makes it
*cleaner* rather than weaker:

| Check | all 20 cells | 15 uncontaminated cells |
| :--- | :--- | :--- |
| `t2_ran_script` | 1/10 vs 10/10 | **0/7 vs 8/8**, p=0.0002 |
| `t2_exit_code_read` | 0/10 vs 10/10 | **0/7 vs 8/8**, p=0.0002 |
| `t2_evidence_not_guess` | 9/10 vs 10/10 | 6/7 vs 8/8, p=0.467 |

The leak strengthened the baseline, as expected — the single baseline cell that
"ran the script" was reading the harness's own scenario source, and it
disappears once contaminated cells are dropped.

**Fixed for every round after this one.** `isolate_cell.sh` runs each cell in an
unprivileged mount namespace with an empty directory bind-mounted over the repo
path: inside the cell the repository is an empty folder, `/opt/ros` and the cell
directory are untouched, and `HOME` points at the cell directory so listing it
finds only the cell's own files. Verified — `ls` of the repo path inside the
namespace prints nothing, `cat` of `DESIGN.md` fails, and `ros2` still works.
`run_ab.sh` now refuses to run a cell if `unshare` is unavailable rather than
silently producing an unisolated round.

This round's numbers are reported with the leak present rather than re-run to
hide it, with the uncontaminated subset shown above.

### The detector itself was broken first

Its first run reported "no cell reached the repository" — a clean all-clear on a
round known to contain a leak. Committed transcripts are gzipped, and `Cell`
was reading them as plain text, so it saw nothing at all: the same invocation
also said **"0 cells graded"**, which is the tell that was there to be noticed.
Both readers now handle `.gz`. A false all-clear is worse than a crash, and this
one was two lines away from being believed.

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
