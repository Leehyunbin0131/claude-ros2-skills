# Harness

This file is the tool reference — what each script does and why it works the
way it does. If you are here to *run* a verification, read
[`../PROCEDURE.md`](../PROCEDURE.md) first: it is the ordered checklist, in
plain language, and it links back here for detail.

Two generations of tooling live here because they answer two different questions.
Pick by the question, not by the filename.

## "Do the skills help on a realistic task?" — task-level A/B

| File | What it does |
| :--- | :--- |
| [`run_ab.sh`](./run_ab.sh) | Brings up the live scenario a task needs, runs the baseline and with-skills cells with identical flags in fresh directories, reduces both transcripts. Tasks 1–3. |
| [`summarize_run.py`](./summarize_run.py) | Reduces a `stream-json` log to the final message plus the tool calls actually invoked, so "verified before writing" is read off the transcript rather than recalled. |
| [`isolate_guardrail.sh`](./isolate_guardrail.sh) | Forces one suspected condition (a single skill, with and without `CLAUDE.md`) and uses the **pre-patch body read out of git** as a true control. This is the run that produced the retraction written up in [`../runs/2026-07-26-guardrail/NOTES.md`](../runs/2026-07-26-guardrail/NOTES.md). |
| [`fake_scan_pub.py`](./fake_scan_pub.py), [`fake_camera_pub.py`](./fake_camera_pub.py), [`reliable_image_sub.py`](./reliable_image_sub.py), [`task3_scenario.sh`](./task3_scenario.sh) | The live scenarios. Both cells always face the same one. |

```bash
# needs a sourced ROS 2 Jazzy install; ros-jazzy-ros-base is enough for 1-3
MODEL=haiku ./run_ab.sh 1 ../runs/$(date +%F)-native
```

This generation measures the **effect** axis. It cannot attribute a result to any
particular line, because every cell varies all ~958 lines at once — and it mixes
in routing, which decides whether the skill was in context at all.

## "Does *this line* earn its place?" — per-line ablation

The instrument for the **efficiency** axis — is this the smallest body that
produces the effect? See [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md#two-bars-and-which-one-your-line-has-to-clear).

| File | What it does |
| :--- | :--- |
| [`claims.py`](./claims.py) | Splits every body into atomic claims with stable ids and exact line spans, and reassembles a body with one claim removed. Removal renumbers lists so the result reads as if authored that way — a visible gap would itself be a signal to the model. |
| [`probes.py`](./probes.py) | One prompt per task, several mechanical checks, each tied to the claims it tests. Prompts never name the rule they are testing, or they would measure instruction-following instead. |
| [`runner.py`](./runner.py) | Runs cells in parallel and resumably across conditions (`naked`, `protocol`, `full`, `shipped`, `ablate:<id>`, `ablate:<id>+<id>`, `only:<id>`), grades each with its probe's predicate, records cost and context size per cell. |
| [`analyze.py`](./analyze.py) | Turns the cell log into per-claim verdicts — P(naked), Δ, Fisher exact, redundancy groups, interference, grading coverage. Reads `cells.jsonl` or the committed `cells.jsonl.gz`. |

```bash
python3 claims.py inventory                       # -> ../claims/claims.jsonl
python3 runner.py plan --suite core --repeats 8    # cells and estimated spend
python3 runner.py run  --suite core --repeats 8 --workers 12 \
        --out $(date +%F)-core --max-total-usd 5
python3 analyze.py 2026-07-26-core
```

First real use: [`../runs/2026-07-26-core/`](../runs/2026-07-26-core/) — all 26
`ros2-core` claims, 558 cells, six lines cut on single-ablation evidence. The
[confirmation run](../runs/2026-07-26-core-confirm/NOTES.md) that measured the
reduced body as a whole caught one of those six as a false negative — restored
before shipping, five lines cut in the end. That is the reason joint measurement
of the reduced body is not optional either, symmetric with the joint-ablation
point below.

Second use: [`../runs/2026-07-27-security/`](../runs/2026-07-27-security/) — all 6
`ros2-security` claims, 176 cells, zero cuts. The same false-negative shape hit
again, on a single-sentence claim this time (single-ablation Δ=+0.25, p=0.467 →
top-up to n=16, p=0.007), which is the reason that top-up step is now routine
whenever a single-ablation Δ isn't near zero *and* isn't significant, not
something to reach for only after a suite-wide confirmation run flags it.

Third use: [`../runs/2026-07-27-testing/`](../runs/2026-07-27-testing/) — added
two condition types beyond deletion. `only:<id>` (addition — does this claim
alone, with nothing else in the system prompt, already produce its own effect)
and `reorder:<n1,n2,...>` (position — the same claims, sections moved). Both are
opt-in per probe (`Probe.probe_only`, `Probe.extra_conditions`) so existing
suites are unaffected. `reorder:` needed a new primitive,
`claims.reorder_sections()`, which moves whole `## N. Title` sections and
renumbers headers without touching a single claim's text — the same
"the model must not see a seam" discipline `ablate()` already applies to
numbered lists. Position came back a clean null (52/52 either order, p=1.00 —
not underpowered, both sides at ceiling). Addition turned the single-ablation
redundancy story from one-sided to two-sided: a group's members had already
shown Δ=0 when removed singly; `only:` now showed each one *alone* reproduces
the group's effect too — sufficient alone, unnecessary next to a sibling, proven
from both directions instead of inferred from one. Repeats were held to n=4 (the
floor where Fisher's exact can resolve anything — n=3 can never reach p<0.05),
which meant most claims needed a targeted top-up before their verdict was
trustworthy, same discipline as the first two runs, just triggered more often
because the starting power was lower on purpose.

Cutting its two dead lines surfaced a failure mode neither prior run had: not a
false negative from too little power, but a false *signal* from testing the
wrong state. Single-ablating each of two cut candidates individually — the only
read available before the candidates are actually removed together — showed a
borderline real-looking effect on one claim's own check, and both dragged down
a check neither owns. Both vanished when the real candidate (both rows gone at
once, the body about to ship) was measured directly: 104/104 across every
check. The lesson generalizes past this one run: **whenever more than one cut
is on the table, single-ablation of each candidate is a reading of a state
nothing ships — the confirmation run against the actual final body is not an
optional extra step, it is the only measurement of the thing being decided.**

Fourth use: [`../runs/2026-07-27-package/`](../runs/2026-07-27-package/) (plus
`-additions`, [`-confirm`](../runs/2026-07-27-package-confirm/),
[`../runs/2026-07-28-package-final/`](../runs/2026-07-28-package-final/)) — the
first probe graded against real ground truth instead of regex: `colcon build`
actually runs on the model's generated files in a scratch workspace, and
`ros2 pkg executables` checks the node exists, rather than pattern-matching the
answer text. That surfaced two genuine content gaps (a missing `package.xml`
export tag, a missing `setup.cfg` install path) that no amount of ablation on
the *existing* text could have found — ablation only tells you whether a line
you already wrote is load-bearing, not whether a line is missing. Both were
added and verified at n=16.

The confirmation side of this run is the reason this paragraph exists: the
confirmation run reported regressions on two cut candidates, and both were
restored on that evidence. The regressions were not real. The ad hoc script
written for that run (to avoid re-running the full `analyze.py` pipeline for
a quick check) tallied per-check pass rates keyed on `(probe, check)` instead of
`(probe, condition, check)`, so `naked`-condition failures — expected to be
low, that's the baseline the content is supposed to beat — silently pooled
into the `full` numbers each time. `analyze.py` itself has always keyed
correctly; the bug was entirely in the throwaway substitute for it. Re-run
through `analyze.py` on a fresh sweep, there was no regression: the reduced
body still beats naked significantly on the check the restored lines were
meant to drive (p=0.041), and every check compared against the pre-revert body
came back not significant (p≥0.2). **Do not write an inline substitute for
`analyze.py`, even for a "quick" confirmation — it is exactly as easy to get
subtly wrong, and the whole point of having one tool that does the tallying is
that it only has to be gotten right once.**

Fifth use: [`../runs/2026-07-28-perception/`](../runs/2026-07-28-perception/)
(+ [`-confirm`](../runs/2026-07-28-perception-confirm/),
[`-final`](../runs/2026-07-28-perception-final/)) — ground truth got cheap.
`_compiles_cpp()` runs `g++ -fsyntax-only` over whatever C++ the answer
contains, against every per-package include dir under `/opt/ros/jazzy`, in
about two seconds and with no workspace to build. Verify a new compile grader
*discriminates* before trusting it: the skill's own snippet was compiled, then
recompiled with the pre-Jazzy `cv_bridge/cv_bridge.h` spelling to confirm the
second form actually fails. It does, and unaided the model writes it 7 times
out of 8 — an error no regex over the answer text would have caught, since
both spellings look equally plausible.

This run also fixed a flaw in `ablate()` itself. Removing the only claim under
a `### A. cv_bridge ...` subheading left the heading standing over nothing: a
seam that still names the topic, so the ablated body scores higher than a body
that never mentioned it, understating the claim's effect and biasing toward
cutting. `_drop_orphaned_headings()` now closes that gap the way `_renumber()`
already closed it for numbered lists. It changes ablation bodies for 27 claims
across every skill; all 27 had been KEPT, so no shipped decision rested on a
seam — but that was checked, not assumed, and the same check is owed to any
future primitive that edits a body.

**A line can be inert against nothing and load-bearing against its own table.**
The `pointcloud_to_laserscan` row single-ablated at Δ=+0.12, p=1.000 with naked
already at 7/8 — inert by every reading available before the cut. Removed for
real, it scored 5/8, *below* the 8/8 that no context at all achieves. The
failing answers show the mechanism: with its own row gone the model borrows the
neighbouring rows' framings (`frame_id`, TF, QoS) rather than the height band,
while an empty prompt leaves it free to answer from its own knowledge. Naked is
therefore not the right baseline for a cut decision — full-with-line versus
full-without-line is, and only the confirmation run produces the latter.

## "Would a different wording be better?" — rewrite variants

Deletion, joint deletion, isolation and reorder are all *deterministic functions
of the file*: given the body, the harness computes the condition. That bounds
the search to subsets and permutations of the text already written. It cannot
ask whether three lines would work better as one, whether a table beats prose,
or whether the sections are split in the right places — those have no
mechanical derivation, so an alternative has to be **authored** and then
measured.

`variant:<name>` reads `evals/variants/<skill>/<name>.md` and runs it through
the same probes as `full`. Claude Code never loads these; only the harness does.

```bash
python3 runner.py run --suite perception --probe perc-depth-encoding \
        --conditions full,variant:merge-encoding --repeats 8 \
        --out $(date +%F)-perception-variant
python3 analyze.py 2026-07-28-perception-variant     # prints a "Rewrite variants" table
```

**Adoption rule: on a tie, the smaller body wins.** A variant that loses any
check significantly is rejected. A variant that wins one is adopted. A variant
indistinguishable from the current body is adopted only if it is *smaller* —
which is the efficiency axis applied to wording instead of to deletion, and the
only way "fewer tokens for the same result" can be claimed about a rewrite.

Candidates should not be invented at random; the sweep already points at them:

| Signal already in the output | Rewrite it suggests |
| :--- | :--- |
| A **redundancy group** (members Δ=0 alone, load-bearing together) | Several lines doing one job — try merging them into one |
| **INERT** (P(naked) low, Δ≈0 — present and doing nothing) | The wording isn't landing; try restating or moving it |
| A check that only ever reads `prose()` while its claim is a table row | The table may be the wrong container for that content |
| Ablating a row makes the model borrow a *neighbouring* row's framing | The section groups things that don't belong together |

The last one is not hypothetical: it is what the `pointcloud_to_laserscan` row
did in `ros2-perception`, and a merge or a regroup is the response that
deletion alone cannot express.

**Claim IDs go stale silently when a file is cut, and a `naked`/`full`-only
confirmation run will not catch it.** Every skill's `SKILL.md` is cut with
sections renumbered, and `probes.py`'s claim ID constants are string literals
that do not move with the file. `ros2-core` and `ros2-testing` both shipped
with stale IDs in `probes.py` for as long as they'd been cut — nine of
`ros2-core`'s sixteen constants and four of `ros2-testing`'s six pointed at the
wrong line, or at an ID that no longer existed at all. Neither skill's
original confirmation run caught it, because both were `naked`-vs-`full` only:
that condition loads the whole file and never resolves an individual claim ID,
so a stale constant sits inert until the next `ablate:<id>` sweep touches it —
which for both skills was this sonnet re-check, run days after the cuts
shipped. Run this before spending on any sweep, every time, not just when
writing new probes:

```python
import json, probes
valid = {json.loads(l)["id"] for l in open("../claims/claims.jsonl")}
bad = [(p.id, c) for p in probes.PROBES for c in p.claim_ids if c not in valid]
assert not bad, bad
```

**Joint ablation is not optional.** Single ablation cannot distinguish "this line
does nothing" from "this line is one of two that each suffice": drop either member
of a redundant pair and Δ=0 for both. Declare such groups in the probe's `joint`
field, which adds an `ablate:a+b` condition. In the first run all three of
`ros2-core`'s groups measured Δ=0 member-by-member and Δ≈+1.00 as a group — cutting
them on the single-ablation reading would have deleted a rule with a runtime-proven
effect. The same gap can hide in a probe nobody revisits: `ros2-core`'s
`tf-lookup` probe had two claims driving one check with no `joint=` between them
from the day it was written — found only when the sonnet re-check tried to cut
one of them and both read as ceiling-flat individually. Added before either was
cut, not after.

**Budget.** `--max-budget-usd` caps a single cell; `--max-total-usd` stops
dispatching once the sweep's running total is reached. Cells already in flight
finish, so the cap is approached from below and can be overshot by roughly
`workers × cost-per-cell` — set it lower than the hard limit.

Three design choices worth knowing before reading the code:

- **Content is injected through `--append-system-prompt`, not installed as a
  skill.** A skill that does not load has zero effect regardless of content, and
  the agent loaded nothing in 4 of 8 cells of one measured run. Injecting
  guarantees the text is in context, so the number that comes out is the content's
  effect and not the router's. The routing tax is measured separately, against a
  real install.
- **`--bare` / `CLAUDE_CODE_SIMPLE=1` must not be used.** Bare mode reads Anthropic
  auth only from `ANTHROPIC_API_KEY`, so on an OAuth machine every cell returns
  "Not logged in" and records as a silent failure. Isolation comes from
  `--setting-sources ""` instead.
- **A cell that never reached the model is not a cell.** Usage limits, auth
  failures and refusals come back as a normal-looking result whose text happens to
  be an error message, and a predicate handed `"You've hit your session limit"`
  scores it `False` — indistinguishable from the model getting it wrong. 438 cells
  of the first sweep were graded that way before this was caught. Cells with
  `is_error` or no cost are now recorded as errors, never graded, and retried on
  the next run.
- **A cell where the model tried to use a tool and gave up is also not a cell.**
  Same principle, new shape, found on the 2026-07-28 switch to sonnet: tools are
  off here by design, but sonnet reaches for one far more readily than haiku did
  and sometimes stops after the attempt rather than answering — leaving
  `"I'll check the current directory structure first... **Tool: bash**"` and
  nothing else. That is a non-answer, not a wrong answer, and every
  `full`-condition failure in one `ros2-core` confirmation run was one of these.
  Worse, two checks regexed the raw answer instead of going through
  `code()`/`prose()`, so a stub that *mentioned* `add_on_set_parameters_callback`
  while trying to look it up scored a **pass**. `_is_tool_stub()` now gates both
  extraction helpers, so a stub grades ungradable in either direction. It is
  length-gated (<700 chars) because a long answer that mentions a tool in passing
  while still delivering real content must not be swept up — verify any change to
  it against real stored answers, in both directions, before trusting it.
  The rendering keeps varying, and an anchored pattern keeps losing to the next
  one: `**Tool: bash**`, `**tool_call**: Bash`, an icon glyph in front of the
  word, `**Tool Call:**` with a space instead of an underscore, and a bare
  function-call shape (`Search(pattern: "x")`) were each a separate miss found
  re-checking `ros2-core` and `ros2-security` on 2026-07-28, each scoring a hard
  `False` before being caught. The pattern that survived stopped trying to
  anchor the surrounding punctuation and just matched the word `Tool` followed
  by a colon within 20 characters, case-sensitive so lowercase "the tool: X" in
  ordinary prose is never swept up — loose beats precise here, because precise
  kept being precisely wrong about the next format.

**Re-grading costs nothing; re-running costs money.** When a *check function* was
wrong — not the skill body — `runner.py regrade --out <run-dir>` re-applies the
current predicates to a run's stored answers in place, gzip or not, and reports
how many results changed. `--dry-run` first. This is only valid when the model's
input was unchanged: if `SKILL.md` moved, the model never saw the new text and a
real re-run is the only honest option. A good regrade of a grading-bug fix moves
results *to* ungradable and never flips a pass to a fail or back; check that it
does before keeping the result.

## Grading

Mechanical wherever possible, in both generations: does the symbol exist in the
install, does the command succeed when the grader re-runs it, does the generated
node print the right number against a live publisher. A check returns pass, fail,
or **ungradable** — and ungradable is never counted as a failure. A grader that
scores unparseable output as "fail" invents effects.

## Statistical honesty in `analyze.py`

Found auditing the `ros2-core` sonnet re-check (2026-07-28), all three fixed the
same day:

- **Uncorrected p-values across one sweep overstate significance.** The
  `ros2-core` sonnet sweep alone ran 166 Fisher tests; at `alpha=0.05`
  uncorrected, ~8 "significant" results are expected from noise alone before a
  single real effect exists. `bh_qvalues()` Benjamini-Hochberg corrects every
  effect test in a run as one family (harm tests, full vs naked, as their own
  family), and `KEEP`/`HARMFUL` are gated on the corrected `q` column, not the
  raw `p` column the table still prints for reference.
- **A large Δ that misses significance is a power problem, not a verdict.**
  Folding it into `CUT`/`INERT`/`unclear` the same as a genuinely flat Δ≈0
  result is how a real regression hides — it is the same shape that produced
  two of this project's worst misses (`ros2-core` 4:05, the `ros2-perception`
  `pointcloud_to_laserscan` row). `UNDERPOWERED` (|Δ| ≥ 0.25 but not
  significant) is now its own bucket: top it up before treating it as settled,
  don't read it as either KEEP or CUT.
- **Claim IDs are only valid against the file state they were collected
  against.** `runner.py` now writes `skill_snapshot.json` (a hash of each
  probed skill's `SKILL.md`) into a run directory the first time it's used.
  `analyze.py` compares that snapshot to the file on disk and prints a loud
  warning — not a quiet skip — when they differ, because a later cut can
  renumber a section and leave the *same numeric claim-ID suffix* pointing at
  different content than it did when the run's answers were collected. This
  bit during the improvement pass itself: re-running `analyze.py` against the
  pre-cut `ros2-core` sonnet sweep with post-cut `probes.py` silently relabeled
  the bounds-redundancy group's data as the shutdown group's. The shipped
  decision was unaffected (it was read correctly at the time), but the
  re-analysis after the fact was not, which is exactly the failure this
  warning exists to catch going forward. `runner.py regrade` is unaffected by
  this — a `Check`'s function only ever reads the answer text, never a claim
  ID, so re-grading cannot mislabel anything the way the per-claim table can.
