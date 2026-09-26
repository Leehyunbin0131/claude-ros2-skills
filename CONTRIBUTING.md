# Contributing

Help an agent complete a real ROS 2 development task with fewer incorrect
assumptions, missing artifacts and unverified claims. Fixes, focused workflows
and reproducible counterexamples are welcome. Target **Ubuntu 24.04 / ROS 2
Jazzy**; follow the user's workspace conventions rather than imposing a new one.

## What belongs in a skill

In accordance with the [Agent Skills standard](https://agentskills.io/home),
skills package contextual knowledge, focused workflows, and executable tools
for specific development tasks.

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

Maintenance is reopened only for a concrete supported-scope defect, a required
test regression, an observed environment compatibility change, or an explicit
user scope expansion; upstream model updates alone are insufficient.

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

Do not claim a token, total-cost, or speed advantage without proven causal
evidence. In the historical interface study of the frozen 0.1.2 snapshot, all
three pairs passed across baseline and pack conditions; pack output tokens and
API estimates were higher, while lower elapsed wall time was subject to prompt
caching, execution order, and probe wait confounds. Release 0.2.0 ships opt-in
evidence handoff tools alongside targeted IMU fixes; that historical 0.1.2 study
does not evaluate the new handoff tool. Codex
compatibility evidence covers offline installation and discovery, plus two
project workflows whose model identity was unrecorded; it does not establish an
efficiency or performance advantage.

## Implementation conventions

Scripts ship under the skill that uses them. Keep decision logic importable
without ROS so it can be tested independently. For diagnostic tools, use:

- `0`: the checked property passed;
- `1`: observed failure of that property;
- `2`: inconclusive, missing prerequisites/evidence, or invalid request.

State the observed problem and the next relevant check. Do not manufacture a
PASS from NaN, unavailable fields, a missing required transform, fewer than two
IMU samples,
excessive sample variation (>1.5 m/s² RMS across axes, adjustable via
`--max-variation`), old messages or an empty test run. The IMU check cannot
prove physical stillness; a PASS verdict confirms only measured +Z gravity in
the level base frame after declared TF or an explicit aligned-axis assumption,
not whole-robot correctness.
Runtime probes need bounded waits and cleanup. Test fixtures must be separated
from operational robots; never use host-wide process-name cleanup.

For the evidence tracker (`evidence.py`):
- **Caller execution decoupled from tracking**: The evidence tracker does not
  wrap or execute user commands in a subshell runner. Callers execute commands directly
  and supply the raw log and exit code. (Other tools like `check_test_results.py`
  invoke `colcon test-result` directly as needed).
- **Strict separation of declared vs. observed**: The evidence tracker records
  caller-declared parameters (`scope`, `command`, `exit_code`, `outcome`, `log`) and
  separately inspects observed filesystem and environment hashes.
- **Atomic records**: Output directories contain `manifest.json`, `command.log`,
  and `COLCON_IGNORE`, finalized via atomic replacement. Files are bounded to 16 MiB.
- For evidence inspection (`evidence.py inspect`):
  - `0` = Consistent (monitored paths and environment match snapshot);
  - `1` = Changed (monitored paths or environment altered between snapshots or after finish);
  - `2` = Incomplete (missing metadata, unfinalized, missing/altered log, or timed out).

Installation changes must preserve user instructions and unrelated skills.
The Claude plugin hook and manual rules transport the source `CLAUDE.md`
unchanged. The Codex installer embeds the same protocol after each skill's
frontmatter, so it arrives when the skill is loaded without modifying AGENTS.md.
Keep source skills and scripts shared; do not maintain separate agent-specific
ROS implementations. Treat changes to that shared protocol as behaviour changes
and validate them separately from delivery mechanics.

## Before opening a PR

For documentation and translation changes:
- Verify Markdown formatting and link validity. No full ROS integration run is required.

For code and test changes:
```bash
python3 -m compileall -q skills scripts tests evals/harness evals/development evals/workflow_value
for file in evals/harness/*.sh; do bash -n "$file"; done
python3 skills/ros2-troubleshooting/scripts/test_checks.py
python3 tests/test_install.py
python3 tests/test_development.py
python3 tests/test_evidence.py
python3 evals/development/test_runner.py
python3 evals/workflow_value/test_runner.py
python3 evals/workflow_value/test_oracle.py
python3 evals/harness/grade_v2.py --selftest
python3 evals/harness/test_harness.py

# Requires colcon-common-extensions, pytest, CMake and a C++ compiler.
# Uses temporary packages; verifies empty-test vs executed-test diagnostics
# and detects modified binaries under identical source trees.
python3 tests/test_colcon_workflow.py

# Requires the Jazzy message packages, tf2_ros and ament_cmake_pytest.
# Synthetic localhost data only; no hardware or motion commands.
source /opt/ros/jazzy/setup.bash
python3 tests/test_ros_checks.py
python3 tests/test_colcon_workflow.py
python3 tests/test_ament_test_results.py
python3 evals/development/test_oracles.py
ROS2_ACCEPTANCE_SEED=1 python3 evals/development/test_oracles.py
```

The interface-migration study adds [independent oracle controls](evals/workflow_value/README.md).
CI runs their first variant without model calls; a new study requires all variants
before freezing inputs and invoking a model.

CI runs these checks plus documentation links. Immutable `evals/runs/`
transcripts are excluded from link checks: historical failed URLs are evidence,
not maintained documentation. A skipped integration test is not a passing
integration test; report the missing dependency.

With Codex CLI installed, also run `python3 tests/test_codex_discovery.py`.
It checks native skill discovery at the project root and a nested directory via
the local app server, without a model call or user configuration changes. Without
Codex this optional test is skipped; installation regressions still run in CI.
Actual Codex workflow observations and limits are recorded in [evals/CODEX.md](evals/CODEX.md).

The harness requires additional packages for individual tasks. Read its
[README](evals/harness/README.md) before running evaluations. Do not edit it
while a round is running, and do not represent a loading smoke test as an agent
performance benchmark.
