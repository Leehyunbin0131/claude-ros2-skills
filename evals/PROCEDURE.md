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

The useful mental model, from the skills measured so far:

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
- **A worked example may act as a ceiling.** Replacing a 23-line code example
  with one sentence describing the concept did not lose anything — the answers
  got *better*, gaining four correct API details the example never showed. The
  model reproduces an example and stops; name the concept and it brings its own
  knowledge. One probe, not a law, but try prose before assuming a code block
  is doing the work.

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

**Writing probes for a skill that has none yet?** Two rules, both learned the
expensive way.

*Measure before you design.* Ask the model your candidate questions with nothing
in context first — a handful of one-off calls, far cheaper than a sweep. Any
question it already answers correctly is a question that will measure nothing,
and building a probe suite out of those produces a table of CUT verdicts that is
really a table about the probes. Aim the probes at what the model **cannot**
know: facts local to this project, filenames and paths that exist nowhere else,
behaviours of tools that ship with the skill.

*The prompt must read like a user's question.* Do not tell the model that a
skill, a repo, or any other context exists — not even to be "fair" about
expecting it to find something. That turns the cell into a hunt for context,
and with tools off the hunt stalls into a non-answer. One run put "I have this
repo's skills installed" in four prompts and stubbed nine of sixteen baseline
cells, leaving the comparison at n=1 and the run unusable.

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
can look useless alone because the other covers for it. The harness tests those
groups jointly, but **only if the group was declared in `probes.py` before the
run** (`joint=[[...]]`). Declare them by reading the file, not by looking for
suspicious zeros afterwards.

**A clean joint ablation does not tell you whether to merge or to delete.**
It only says the lines cover each other. Which action is right depends on a
different number — the naked baseline:

| Joint ablation clean, and... | Meaning | Action |
| :--- | :--- | :--- |
| `naked` is low | the lines say one true thing the model cannot supply, said more than once | **merge** (step 5) |
| `naked` is at ceiling | the model already knows it; the lines are covering for each other *and* for nothing | **delete** |

Both cases have been hit here. In one skill a jointly-ablatable group of six
claims contained a line scoring **0/8** unaided — deleting on the joint result
would have removed the strongest line in the file. In another, a jointly
ablatable pair sat at `naked` **1.00** and was correctly cut. Never act on the
joint number alone.

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

## Step 5 — try rewriting, not just deleting

**Do this before you commit to any edit.** Deletion is only one way to make a
file smaller, and usually not the best one. Three lines might work better as
one. The harness cannot invent that — every other condition is derived
mechanically from the text that already exists — so the alternative has to be
**authored by you** and then measured.

1. Write a complete alternative body to `evals/variants/<skill>/<name>.md`.
   It is a whole `SKILL.md`, frontmatter included, not a patch.
2. Run it against the current body:

```bash
python3 harness/runner.py run --suite <suite> \
        --conditions naked,full,variant:<name> --repeats 8 --models sonnet \
        --out $(date +%F)-<skill>-variant
```

`analyze.py` prints a "Rewrite variants" table comparing the two per check.

**Adoption rule: on a tie, the smaller body wins.** A variant that loses any
check is rejected. A variant that wins one is adopted. A variant that ties is
adopted if it is shorter.

Every redundancy group from step 2 is a candidate. So is any worked example
that the model might not need — see the ceiling note near the top of this file.

This is the step most easily skipped, because nothing in the ablation output
suggests it. The ablation only ever answers "should this line go?", never
"should these three lines be one?"

## Step 6 — measure the body that will actually ship

**Per-line results do not add up.** Line A can look harmless because line B was
covering for it, and a variant was measured as a *proposal*, not as the shipped
file. So once `SKILL.md` is edited — whether by cutting, by adopting a variant,
or both — measure that exact file in a fresh directory:

```bash
python3 harness/runner.py run --suite <suite> --conditions naked,full \
        --repeats 8 --models sonnet --out $(date +%F)-<skill>-confirm
```

Two things have to hold:

- `full` must not have dropped against the pre-edit body.
- `full` must still beat `naked`. Pool every check to get one number — that
  pooled `naked → full` pair is what goes in the RESULTS.md effect column, so
  it describes the shipped file and cannot drift from it.

If either fails, put the lines back.

**If the edit changed the number of claims, re-map `probes.py` first.**
Merging four claims into one renumbers everything after it, so constants that
pointed at the right lines yesterday now point at the wrong ones — or at
nothing. Re-run the claim-ID check from "Before you start", set cut claims to
`None`, drop the `joint=[[...]]` groups whose members no longer exist
separately, and leave a comment saying what moved and why. Stable *names* in
`probes.py` deliberately do not track the numbers in the IDs; the mismatch
looks like a bug and is not, so say so in the comment or someone will "fix" it.

## Step 7 — write it down

1. `evals/runs/<run>/NOTES.md` — what was measured, the numbers, and why each
   decision was made. Four things belong here that are easy to leave out:
   the axis-1 number first (`naked` vs `full` on the shipped body), what you
   **rejected** and why, anything you got wrong during the run, and any answer
   you read by hand that changed a decision. A run whose notes only list what
   worked is not a record, it is an advertisement.
2. `evals/RESULTS.md` — update the status row. The effect column takes the
   `naked → full` number from the confirmation run, so the table cannot drift
   away from what actually ships.
3. Commit with the reasoning in the message, and push.

Status values:

| | Meaning |
| :--- | :--- |
| IN PROGRESS | not measured yet, or only one axis done |
| VERIFIED | both questions answered, n≥5, run linked |
| DID NOT CLEAR | question 1 failed — the body does not beat an empty context |

## The whole thing in order

```
check claim IDs resolve          <- before you start
check answers are gradable       <- before you start
sweep at n=4                     <- step 1
read analyze.py                  <- step 2   (naked first; joint clean = merge, not delete)
top up only unclear claims       <- step 3
read naked answers by hand       <- step 4   (can cancel a cut; nothing else can)
author and measure a rewrite     <- step 5   (before editing SKILL.md)
edit SKILL.md
re-map probes.py claim IDs       <- step 6   (only if the claim count changed)
confirmation run on the real body<- step 6
NOTES.md, RESULTS.md, commit     <- step 7
```

## Failure modes to expect

These are written as general failure modes, because they are not specific to
this harness or to ROS 2 — any setup that measures whether written guidance
changes a model's output will hit them. Each is stated as the rule first, then
the concrete case here that paid for it.

They are listed because **none of them looked like a mistake at the time.**
Every one produced a clean, plausible number. If a step in this file seems like
pointless ceremony, it exists because of one of these.

### Two things being interchangeable is not the same as either being useless

When several lines cover the same ground, removing any one of them costs
nothing, and removing all of them may also cost nothing — because the model
already knew it. Those are different situations with the same measurement. The
first calls for merging; only the second calls for deleting.

*Why it hides:* the group measurement is correct. Both readings fit it exactly.

*Rule:* a group that ablates cleanly is a **rewrite candidate first**. Before
deleting it, check what the model does with no file at all. If that is bad, the
content is load-bearing and only its wording is redundant.

*Here:* six claims looked jointly removable. One of them scored **0/8** unaided
— the strongest single line in the skill. On another, larger skill three
successive rewrites were rejected, each on a *different* check whose claim had
measured `naked = full = ablate = 1.00`. When a file's content reinforces
itself, per-claim CUT verdicts stop predicting what happens to the body they
are cut from; the confirmation or variant run is the only thing that knows.

*Know when to stop.* If two or three rewrites are each rejected on a different
CUT-verdict line, the answer is "this file does not compress that way", not
"try a fourth". Record it and move on -- each further round buys one line back
and finds another.

### A grader tests a pattern, not knowledge

Any mechanical check accepts some correct answers and rejects others. The
rejections look identical to genuine failures, and the acceptances look
identical to genuine successes.

*Why it hides:* failures on a check that is *supposed* to be hard are exactly
what you expect to see.

*Rule:* before acting on a score, read the raw answers behind it. A pattern is
evidence about a pattern. Never let a regex be the last thing that looked at
the output.

*Here:* a check required one specific attribute order in generated XML, so
every equally valid answer written in a different order scored as wrong.

### A non-answer is not a wrong answer

Models fail in ways that are neither right nor wrong: refusing, truncating,
asking a clarifying question, or trying to use a tool that is not available and
stopping. Counting those as failures corrupts every rate you compute.

*Why it hides:* it shows up only as a score being a little lower than expected
— easy to explain away as the model being weaker than you thought.

*Rule:* grade three-valued — pass, fail, **ungradable** — and never count
ungradable as fail. Sample the raw output before a large run to see which
non-answers your setup provokes. Expect the shape to keep changing and prefer
a loose detector to a precise one; precise patterns keep being precisely wrong
about the next format.

*Here:* tool-call stubs were scored as failures, and in two checks a stub that
merely *mentioned* the target function while trying to look it up was scored a
pass. The stub rendering changed four times before a loose pattern held.

### An identifier that survives an edit may no longer mean the same thing

Any scheme that references parts of a document by position or index breaks
silently when the document is edited. The run still completes; the labels are
just wrong.

*Why it hides:* nothing errors. The output looks completely ordinary, and only
reading the referenced content next to the result reveals the mismatch.

*Rule:* validate every reference resolves **before** each run, and record a
hash of the document each result set was collected against so stale analysis is
detectable later.

*Here:* claim IDs pointed at renumbered lines three separate times — twice
after a cut, once after a rewrite that merged four claims into one.

### A quick substitute for the real analysis tool will be subtly wrong

Aggregation code is easy to write and easy to get wrong in ways that produce
believable numbers. A second implementation doubles the surface where that can
happen, and it is always the unreviewed one.

*Why it hides:* the throwaway version is simple enough to look obviously
correct.

*Rule:* one tool does the tallying. If it does not answer your question, extend
it. It only has to be right once.

*Here:* a quick script keyed pass rates on `(probe, check)` instead of
`(probe, condition, check)`, pooling baseline failures into the treatment
numbers. It reported two regressions that did not exist, and two lines were
restored on that evidence.

### Removing content can leave a trace that changes the result

When you generate a modified document to test against, the modification itself
can leak information — an empty heading, a gap in a numbered list, a dangling
reference. The model reacts to the trace, not just to the missing content.

*Why it hides:* the modified document is generated and thrown away. Nobody
reads it.

*Rule:* the modified version must read as though it were authored that way.
Any new code that edits a document owes this check explicitly — verify it, do
not assume it.

*Here:* removing the only item under a subheading left the heading standing
over nothing. It still named the topic, so the ablated body scored *higher*
than one that never mentioned it — biasing every such verdict toward cutting.
Fixing it changed the test inputs for 27 claims.

### A grader that has never seen a wrong answer proves nothing

A check that passes every good answer is not validated — a check that returns
"pass" unconditionally does that too. Negative-form checks ("true when the bad
thing is absent") are the worst case, since anything empty passes them.

*Why it hides:* a grader agreeing with you on every case you looked at feels
validated. You have tested one half of it.

*Rule:* feed every new grader something that *should* fail and confirm it does.

*Here:* a check that was true whenever the wrong syntax was absent passed a
stub that never answered at all.

### The baseline for "should this go" is not "no document at all"

Removing something has two possible comparisons: against nothing, and against
the rest of the document. They can point opposite ways, because surrounding
content shapes the answer in a way an empty prompt does not.

*Why it hides:* the empty baseline is the natural-looking one and is genuinely
useful — for the other question, whether the document helps at all.

*Rule:* "does this document help" compares against nothing. "should this part
go" compares with-it against without-it, in the document that will actually
ship.

*Here:* one line measured inert (Δ=+0.12, p=1.000, baseline already 7/8).
Removed for real it scored *below* what no document at all achieves — with its
own row gone the model borrowed neighbouring rows' framings.

### A verdict is about the model that produced it

Results do not transfer across models, and the disagreement has structure
rather than being noise. A stronger model needs less factual content and more
pointers; a weaker one is the reverse.

*Why it hides:* cheaper models are attractive for large sweeps, and their
results look just as clean.

*Rule:* grade on the model you actually ship against. If you must use a cheaper
one, only "remove it" transfers upward — never "keep it".

*Here:* a full pass on a smaller model returned "keep everything" for a skill
that lost most of its body on the real one. Those runs were deleted rather than
kept, because their most likely error direction was known and unfixed.

### Measure only what is actually unresolved

When one result is ambiguous, the reflex is to re-run everything around it.
Sampling is the expensive part of this work and the ambiguity is usually
narrow.

*Rule:* widen the sample for the specific comparison in question, not the whole
group it belongs to.

*Here:* two ambiguous checks were resolved by re-running two entire probes —
64 cells to answer what a dozen would have.

### The instrument can be the finding

Roughly half of what this project has "discovered" turned out to be bugs in its
own measurement rather than facts about the documents. That ratio is normal
early on and it is not a reason to distrust the work — it is a reason to treat
every surprising result as a claim about the instrument until it survives a
second look.

*Rule:* when a number is surprising, check the measurement before writing the
conclusion. When a number is *unsurprising*, that is the dangerous case — it
will not prompt anyone to check anything.

## Rules that are not negotiable

- **Never report a result you did not measure.** If something could not be
  verified, write that plainly and write what would be needed.
- **Never lower `--repeats` below 4.** It cannot resolve anything.
- **Never cut on statistics alone.** Read the answers (step 4).
- **Never act on a joint ablation without the naked baseline** (step 2).
- **Never cut several lines without a confirmation run** (step 6).
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
- **A skill is only measured where its probes point.** Covering the part of a
  file the model cannot know produces a very large effect and says nothing about
  the rest. Report the coverage — how many claims have a probe at all — next to
  the effect number, and do not call a skill finished on a favourable subset.
