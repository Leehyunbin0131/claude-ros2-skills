# Harness

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

**Joint ablation is not optional.** Single ablation cannot distinguish "this line
does nothing" from "this line is one of two that each suffice": drop either member
of a redundant pair and Δ=0 for both. Declare such groups in the probe's `joint`
field, which adds an `ablate:a+b` condition. In the first run all three of
`ros2-core`'s groups measured Δ=0 member-by-member and Δ≈+1.00 as a group — cutting
them on the single-ablation reading would have deleted a rule with a runtime-proven
effect.

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

## Grading

Mechanical wherever possible, in both generations: does the symbol exist in the
install, does the command succeed when the grader re-runs it, does the generated
node print the right number against a live publisher. A check returns pass, fail,
or **ungradable** — and ungradable is never counted as a failure. A grader that
scores unparseable output as "fail" invents effects.
