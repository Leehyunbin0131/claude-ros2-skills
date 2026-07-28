# How to verify a skill

This is the step-by-step. It assumes you have never seen this project before.
`RESULTS.md` is the record of what is already finished; `harness/README.md` is
the reference for the tools. This file is the order you do things in.

## The two questions

Everything here exists to answer two questions, **in this order**:

1. **Does this skill file help at all?** (effect)
2. **If it helps, which lines are actually doing the work?** (efficiency)

Question 2 only matters if question 1 is yes. If a file does not beat an empty
context, the answer is not "trim it" — it is **delete it**. That has already
happened once: a skill scored a perfect 1.000 with no file at all, so the file
was removed rather than shortened.

A skill is not finished because it is correct. Correct is the floor. It is
finished when both questions have a number behind them.

## What we are actually looking for

The useful mental model, learned from five skills:

- **Lines that get cut are usually not wrong.** They are correct explanations,
  correct code, correct concepts — that the model already knows. Being right is
  not a reason to keep a line.
- **Lines that survive** tend to be one of three kinds: something the model
  cannot know (a fact about *this* project, this robot, this workspace),
  a pointer to where the real answer lives, or something the model knows but
  does not do unless told.
- **Short is not the goal.** This was measured: adding 85% more harmless filler
  to a skill changed nothing on 19 checks. Cutting is for the humans who have
  to read and maintain the file, not for the model.

## Before you start

Two things to check, every time.

**1. Do the claim IDs still resolve?** The harness splits `SKILL.md` into
numbered lines called claims, and `probes.py` refers to them by ID. If the file
was edited since those IDs were written, they now point at the wrong line — or
at nothing — and every result will be quietly mislabeled. This has caused real
errors twice.

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, 'evals/harness')
import claims as C, probes as P
ids = {c.id for c in C.inventory()}
bad = [(pr.id, n, cl) for pr in P.PROBES for n, ch in pr.checks.items()
       for cl in (ch.claims or []) if cl and cl not in ids]
bad += [(pr.id, cl) for pr in P.PROBES
        for cl in (pr.extra_claims or []) if cl and cl not in ids]
print('dangling:', bad or 'none')
EOF
```

Anything listed is a bug to fix before running. A claim that was cut should be
set to `None` in `probes.py`, and the checks that used to own it should carry
an empty claim list.

**2. Will the answers actually be gradable?** The model sometimes tries to use
a tool, gets blocked (the harness runs with tools off), and writes a stub
instead of an answer. Those must be graded "ungradable", not "wrong". Run two
or three cells first and read them:

```bash
python3 harness/runner.py run --suite <suite> --probe <one-probe> \
        --repeats 2 --models sonnet --conditions naked,full \
        --out scratch-stubcheck
```

Read the answers. If they are real answers, delete the scratch directory and
continue. If any is a tool stub that got graded True or False, fix
`_is_tool_stub()` in `probes.py` first.

## Step 1 — the main sweep

Ask each probe question many times, under different conditions.

```bash
python3 harness/runner.py run --suite <suite> --repeats 4 --models sonnet \
        --out $(date +%F)-<skill>-sonnet --workers 8
```

The conditions it runs:

| Condition | What the model is given |
| :--- | :--- |
| `naked` | nothing — this is the baseline |
| `full` | the whole `SKILL.md` |
| `protocol` | `CLAUDE.md` only |
| `shipped` | both, as a real user would have them |
| `ablate:<id>` | everything **except** that one line |
| `only:<id>` | **just** that one line |
| `reorder:...` | the same lines in a different order |

**Use `sonnet`, not `haiku`.** A verdict from a small model does not transfer
upward: one skill came back "zero cuttable lines" on haiku and then lost most
of its body on sonnet. The one direction that does transfer is CUT — if a small
model does not need a line, a bigger one will not either.

**`--repeats 4` is the floor, not a default to lower.** With 3 samples, even a
perfect 0/3 versus 3/3 split cannot reach statistical significance. Four is the
smallest number where the method can say anything at all.

## Step 2 — read the results

```bash
python3 harness/analyze.py <run-directory-name>
```

Pass the bare directory name, not a path — the tool prepends `evals/runs/`.

Read three things, in this order.

**First, the baseline table.** Look at `P(naked)`. This is question 1. If naked
is already at or near a perfect score on every check, **the sweep measured
nothing** — a perfect score leaves no room for a file to add anything. That is
not evidence the file is useless; it is evidence the questions were too easy.
Do not read the verdicts table as meaningful when this happens. Either write
harder probes or accept that this skill cannot be measured with the current
instrument, and say which in the notes.

**Second, the verdicts table.** For each line:

| Reading | Meaning |
| :--- | :--- |
| removing it drops the score | the line is working — keep |
| removing it changes nothing | cut candidate |
| naked already scores full marks | the model knows it — no reason to write it |
| `UNDERPOWERED` | the gap looks big but the sample is too small to be sure — **not** a cut |

Judge on the `q` column, not `p`. One sweep runs a dozen-plus tests at once, so
some will look significant by luck alone; `q` is the corrected version that
accounts for that.

**Third, the redundancy groups.** When two lines say overlapping things, each
can look useless alone because the other covers for it — and cutting both
breaks things. The harness tests those groups jointly, but **only if the group
was declared in `probes.py` before the run** (`joint=[[...]]`). Declare them by
reading the file, not by looking for suspicious zeros afterwards.

## Step 3 — top up only what is unclear

If something came back `UNDERPOWERED` or ambiguous, run more samples for
**that claim only**. Do not re-run the whole probe — narrow it with
`--conditions`:

```bash
python3 harness/runner.py run --suite <suite> --probe <probe> --repeats 8 \
        --models sonnet --conditions naked,full,ablate:<the-one-claim-id> \
        --out <same-run-directory>
```

Writing to the same output directory resumes it; cells already collected are
not re-run. Going to `--repeats 8` on a whole probe when one check was unclear
wastes most of the spend.

## Step 4 — read the actual answers before cutting

**This step is not optional and cannot be replaced by statistics.**

The checks are text patterns. They can be fooled — an answer can match the
pattern and still be wrong, or fail the pattern and be right. Two real
examples: a check demanded one specific attribute order in generated XML and
scored equally valid output as wrong; a check scored tool stubs as wrong
answers instead of ungradable.

So for every line you are about to cut, open the `naked` answers and read them
whole. You are asking: **does the model really know this, or did it just
happen to match?** Look past what the check tests. In the run that produced
this project's one whole-file deletion, the naked answers reproduced the
skill's own example byte-for-byte, including structure no check verified, and
named details no check asked for. That is knowing it.

If anything in those answers is wrong, cancel the cut. The written answer
outranks the number.

## Step 5 — cutting several lines at once needs its own run

Per-line results do not add up. Line A can look harmless because line B was
covering for it. So after you edit `SKILL.md`, measure the **real edited file**
in a fresh directory:

```bash
python3 harness/runner.py run --suite <suite> --conditions naked,full \
        --repeats 8 --models sonnet --out $(date +%F)-<skill>-confirm
```

The new `full` must hold up against the old one, and against `naked`. If it
does not, put the lines back.

## Step 6 — try rewriting, not just deleting

Deletion is only one way to make a file smaller. Three lines might work better
as one. The harness cannot invent that — every other condition is derived
mechanically from the text that exists — so you have to **write the
alternative yourself**:

1. Save a complete alternative body as `evals/variants/<skill>/<name>.md`
2. Run it against the current body:

```bash
python3 harness/runner.py run --suite <suite> \
        --conditions naked,full,variant:<name> --repeats 8 --models sonnet \
        --out $(date +%F)-<skill>-variant
```

**Adoption rule: on a tie, the smaller body wins.** A variant that loses any
check is rejected. A variant that wins one is adopted. A variant that ties is
adopted if it is shorter.

This is the step most easily forgotten, because the ablation output never
suggests it. Redundancy groups — several lines that each look useless alone
but break when all are removed — are the obvious place to try a merged
rewrite.

## Step 7 — write it down

1. `evals/runs/<run>/NOTES.md` — what was measured, the numbers, and why each
   decision was made. Include what you rejected and why.
2. `evals/RESULTS.md` — update the status row. The effect column takes the
   `naked → full` number from the confirmation run, so the table cannot drift
   away from what actually ships.
3. Commit with the reasoning in the message, and push.

Status values:

| | Meaning |
| :--- | :--- |
| IN PROGRESS | not measured yet, or only one axis done |
| VERIFIED | both questions answered, n≥5, run linked |
| VERIFIED (haiku) | axis 2 passed before the switch to sonnet grading — re-check before calling it closed |
| DID NOT CLEAR | question 1 failed — the body does not beat an empty context |

## Rules that are not negotiable

- **Never report a result you did not measure.** If something could not be
  verified, write that plainly and write what would be needed.
- **Never lower `--repeats` below 4.** It cannot resolve anything.
- **Never cut on statistics alone.** Read the answers (step 4).
- **Never cut several lines without a confirmation run** (step 5).
- **Never hand-roll a substitute for `analyze.py`.** If it does not answer the
  question, fix it; a one-off script that skips the corrections will mislead
  you.
- **No emoji** in any document except the top-level `README.md`.

## Known limits of this method

State these when reporting; do not pretend they are solved.

- **The ceiling problem.** When `naked` already scores perfectly, this method
  can only ever say "cut". It cannot tell "unnecessary" apart from "not
  measured". Harder probes are the only fix.
- **Test conditions are not use conditions.** Every cell is one question, one
  answer, tools off. Real work is many turns with tools available, and
  `CLAUDE.md` tells the agent to go verify against the live install — which is
  exactly the behaviour this harness disables. A line whose value is
  *making the agent go check something* is invisible here. This is the single
  biggest gap, and closing it means building a different harness, not writing
  a different probe.
- **Results are tied to a model.** Verified on sonnet means verified on sonnet.
