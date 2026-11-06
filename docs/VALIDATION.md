# Evidence Tool Operational Validation (0.2.0)

> **Scope note:** This document records operational validation for the opt-in evidence tracking tool (`evidence.py`) introduced in 0.2.0. For the earlier 0.1.2 development and runtime diagnostic validation inventory, see [evals/VALIDATION.md](../evals/VALIDATION.md). For architectural rationale and CLI contracts, see [docs/DESIGN.md](DESIGN.md).

## 1. Automated Contract & Integration Suites

| Test Suite | Coverage & Observed Result |
| :--- | :--- |
| `tests/test_evidence.py` | **39 contract tests** covering snapshots, missing inputs, exclusions, symlink handling, and status transitions (`open`, `consistent`, `changed`, `incomplete`). A mutation control removing three fixes caused 4 relevant tests to fail (35 passing), confirming regression sensitivity. |
| `tests/test_colcon_workflow.py` | **2 unit/integration methods** evaluating `passing_cpp` and `empty_cpp` CMake fixtures to verify empty-test rejection (`colcon` rc `0` vs. checker rc `2`) and detection of modified installation binaries under unchanged source trees (`changed`, rc `1`). |
| `tests/test_install.py` | **22 delivery and update checks** across Claude Code and Codex installations, plus acceptance oracles passing across Seed 0 (3/3) and Seed 1 (3/3). |
| `evals/workflow_value/test_runner.py` | **14 workflow-value harness tests** (with `WV_ORACLE_CONTROLS=1`), including a control method evaluating 12 matched cases, passing in 487.5s without code edits when `WV_VENV_BIN` points to the active colcon virtualenv. |

## 2. Qualitative Smoke Observation (`n=1`)

Separately from the automated test suites, a single qualitative smoke observation (`n=1`) was conducted using DeepSeek (`deepseek/deepseek-flash`) on a synthetic ROS 2 workspace where the prompt specified that no physical robot was involved:

- **Setup**: A configuration parameter was modified from `0.5` to `1.5` while source files remained untouched.
- **Observed Tool Behavior**: `evidence.py inspect` reported `record_status: "changed"` (exit code `1`) and isolated the modified configuration file. The agent then independently re-ran the declared Python check and observed the resulting assertion failure.
- **Observed Agent Caveats**:
  1. The agent proposed additional colcon packaging steps—interpreted by reviewers as scope expansion beyond the narrow snapshot inspection.
  2. The agent noted unset ROS variables in the `parentenv` snapshot as a sign that the check ran outside ROS, overlooking that parent-shell records do not capture child-process sourcing. (See [handoff review principles](../skills/ros2-development/references/handoff.md#handoff-review-principles).)
- **Interpretation Boundary**: This single qualitative session had no baseline comparison, licenses no inference regarding developer productivity gains, and no follow-up model comparison was conducted after amending the review instructions.
