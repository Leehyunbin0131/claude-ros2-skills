# Contributing

Help an agent complete a real ROS 2 development task with fewer incorrect
assumptions, missing artifacts and unverified claims. Fixes, focused workflows
and reproducible counterexamples are welcome. Target **Ubuntu 24.04 / ROS 2
Jazzy**; follow the user's workspace conventions rather than imposing a new one.

## What belongs in a skill

- A concrete trigger in `description`, so development work and live fault
  diagnosis load the appropriate material.
- A short workflow, diagnostic distinction or executable tool that changes a
  useful development decision. Link larger references from the skill and explain
  when to read them.
- Verified Jazzy symbols and commands, with local package evidence or official
  sources. Do not copy a broad API manual into the agent's context.
- An observable outcome and an honest boundary: build success, executed tests,
  received data, lifecycle state or a diagnostic verdict prove different things.

The project previously treated baseline reachability as a reason to delete most
prose. The current goal is developer usefulness, not minimal file count. New
workflow guidance may ship with documented operational validation even before
an agent comparison. That does **not** license a performance claim. Deleted
domain manuals should not be restored wholesale; explain the development
failure a proposed addition addresses and verify the proposed remedy.

## Evidence required

Separate these levels:

| Evidence | Supports | Does not support |
| :--- | :--- | :--- |
| Official or installed API/source | The command or fact is correct for that environment | The agent will choose it at the right time |
| Passing and deliberately failing fixtures | The tool/workflow distinguishes the intended outcomes | General model improvement or hardware correctness |
| Plugin/manual-install checks | Files and protocol reach the intended context | Equal behavioural effectiveness across delivery methods |
| Matched agent task comparison | An effect for the tested task, model, settings and sample | Universal improvements across ROS applications |

For new tools, demonstrate the failure before the fix, a passing case and
missing/invalid evidence. For workflow guidance, run a representative package
or runtime task and report what remains untested. For model performance claims,
use the [evaluation method](evals/LADDER.md), freeze prompts before execution,
record model/settings and preserve transcripts and verdicts. Never pool invalid,
set-aside or contaminated cells into a success rate.

Historical tables have missing evidence and disagreements with committed
verdicts. Read the [reconciliation](evals/CAPABILITIES.md) before citing them.
Do not rewrite `evals/runs/`, old prompts or statistical thresholds to improve a
reported score. A new task belongs in a new evaluation with its own artifacts.

## Implementation conventions

Scripts ship under the skill that uses them. Keep decision logic importable
without ROS so it can be tested independently. For diagnostic tools, use:

- `0`: the checked property passed;
- `1`: observed failure of that property;
- `2`: inconclusive, missing prerequisites/evidence, or invalid request.

State the observed problem and the next relevant check. Do not manufacture a
PASS from NaN, unavailable fields, a missing transform, old messages or an empty
test run. Runtime probes need bounded waits and cleanup. Test fixtures must be
separated from operational robots; never use host-wide process-name cleanup.

Installation changes must preserve user instructions and unrelated skills.
The plugin hook and manual rules currently transport the source `CLAUDE.md`
unchanged. Treat changes to that shared protocol as behaviour changes and
validate them separately from delivery mechanics.

## Before opening a PR

```bash
python3 -m compileall -q skills scripts tests evals/harness
for file in evals/harness/*.sh; do bash -n "$file"; done
python3 skills/ros2-troubleshooting/scripts/test_checks.py
python3 tests/test_install.py
python3 tests/test_development.py
python3 evals/harness/grade_v2.py --selftest
python3 evals/harness/test_harness.py

# Requires colcon-common-extensions, pytest, CMake and a C++ compiler.
# Uses temporary packages; no model or robot is called.
python3 tests/test_colcon_workflow.py

# Requires the Jazzy message packages and tf2_ros.
# Synthetic localhost data only; no hardware or motion commands.
source /opt/ros/jazzy/setup.bash
python3 tests/test_ros_checks.py
```

CI runs these checks plus documentation links. Immutable `evals/runs/`
transcripts are excluded from link checks: historical failed URLs are evidence,
not maintained documentation. A skipped integration test is not a passing
integration test; report the missing dependency.

The harness requires additional packages for individual tasks. Read its
[README](evals/harness/README.md) before running evaluations. Do not edit it
while a round is running, and do not represent a loading smoke test as an agent
performance benchmark.
