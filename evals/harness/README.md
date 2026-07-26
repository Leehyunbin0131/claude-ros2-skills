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
| [`runner.py`](./runner.py) | Runs cells in parallel and resumably across conditions (`naked`, `protocol`, `full`, `shipped`, `ablate:<id>`, `only:<id>`), grades each with its probe's predicate, records cost and context size per cell. |

```bash
python3 claims.py inventory                       # -> ../claims/claims.jsonl
python3 runner.py plan --suite core --repeats 5    # cells and estimated spend
python3 runner.py run  --suite core --repeats 5 --workers 12 --out $(date +%F)-claims
```

**Status: no published result depends on these yet.** They exist, the round trip
is tested, and nothing in `RESULTS.md` cites them. Treat any output as
provisional until it appears there with its n.

Two design choices worth knowing before reading the code:

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

## Grading

Mechanical wherever possible, in both generations: does the symbol exist in the
install, does the command succeed when the grader re-runs it, does the generated
node print the right number against a live publisher. A check returns pass, fail,
or **ungradable** — and ungradable is never counted as a failure. A grader that
scores unparseable output as "fail" invents effects.
