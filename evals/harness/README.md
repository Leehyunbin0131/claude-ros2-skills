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
