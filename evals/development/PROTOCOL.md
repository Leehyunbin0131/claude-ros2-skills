# Release acceptance: ROS 2 Jazzy development skills

This is a release acceptance exercise, not an efficacy benchmark. It asks
whether the documented installation methods and targeted workflows work in
real Claude Code sessions. Baseline runs provide descriptive context only.
The historical ladder prompts, samples and statistical thresholds are unchanged;
this exercise does not replace or add scores to those experiments.

## Agreed scope

Codex and Claude Code (Opus 5.5, high effort) reviewed the same implementation
and oracles. The cases were selected before any model outcome was observed:

| Case | User outcome | External evidence |
| :--- | :--- | :--- |
| `scan` | Extend an existing simulated sensor package with namespaced launch, YAML and threshold filtering | Fresh installed launch, sensor-data publisher, exact callback counts, a second namespace and mutation of the installed YAML |
| `tests` | Repair ratio-preserving wheel-speed limiting and its misleading green test run | Fresh installed public API; executed tests; the submitted tests pass an independent reference and reject three distinct faulty functions |
| `imu` | Diagnose consistency with declared TF without changing the simulated system | Live independent matrix-based observation; structured status for each topic; publisher GIDs, fixture PID, heartbeat and parameter state remain valid |

The prompts are in `fixtures.py`. Seed 0 uses the original names and values;
seed 1 changes package/topic/namespace names, scan limits and the IMU status-to-topic assignment. No skill name is
forced in a prompt. Facts needed to avoid spurious clarification are supplied:
existing workspace, simulation, publisher ownership and no physical robot.

## Fixed acceptance set

Nine fresh Opus 5.5 High sessions, with identical allowed tool sets:

1. Each of `scan`, `tests`, `imu`: baseline, seed 0.
2. Each case: plugin installation, seed 0.
3. Each case: manual project installation, seed 1.

This is **one observed run per installation method and task**, not an estimate
of reliability or improvement. The three baselines are not required to fail.
Acceptance requires all six installed-pack outcomes to satisfy their external
oracles. No case may be discarded to improve the result.

Before these sessions, a natural-request loading smoke under each installation method checks existing
colcon reports containing a passing style check and a skipped behavioral test.
Each smoke must show all three pack skills in the inventory, verified protocol
transport and an actual bundled script invocation with observed output and a resolved path. It is not included in the nine outcomes.
Full positive and negative controls must pass for both seeds before acceptance.
  A committed content-hash freeze covers product/installer, protocol, fixture,
  grader, runner and isolation code; acceptance aborts before any model call on
  drift. The run records the freeze hash, git HEAD, product and prompt hashes.
  The freeze does not hash itself or later results, avoiding a self-referential
  commit hash while locking every executable/input that can affect the cells.

## Environment and isolation

- Ubuntu 24.04, ROS 2 Jazzy. Current validation environment: Python 3.12,
  pytest 7.4.4, pytest-rerunfailures 12.0, setuptools 79.0.1,
  colcon-core 0.21.3; installed versions and Claude CLI version are recorded.
- Claude model `claude-opus-5-5`, `--effort high`. No fallback model.
- Fresh session and workspace; no resume, saved session, MCP, auto-memory or
  claude.ai skill/plugin synchronization. Built-in skills remain available
  equally across conditions. Read/Glob/Grep/Bash/Write/Edit/Skill/WebFetch tools
  are allowed. No user response is supplied during a cell.
- The existing mount-isolation helper hides repository copies, host instruction
  sources, coordination files, Claude history, Codex data and other cell paths. The runner
  automatically masks its output parent, sibling workspaces and recognized
  fixture/reference copies found by a bounded home and temporary-directory scan.
  OAuth credentials are neither copied nor printed. This is not a network
  security sandbox. Successful retrieval of pack/fixture/evaluation content
  outside the intended treatment is contamination and excludes the cell.
- The plugin export contains only the shipped manifest, skills, hooks, protocol
  and license. The manual condition uses the actual installer. Treatment files
  must remain unchanged by the model.
- Cells run sequentially under the same per-user lock as the legacy harness.
  Every case gets local-only DDS discovery and separate tagged model, scene and
  grader processes. Cleanup never selects untagged user processes.
- The model has 1800 seconds. A timeout is a failed acceptance session; the
  workspace is still graded and its outcome is reported separately. Runtime probes are bounded; a session limit or
  authentication/CLI error produces no valid model result. Every attempt is
  retained, including invalid and rejected cells.

## Oracles and triage

The graders do not import or invoke the pack's verification scripts. They build
from a fresh copy of the submitted source and use separate runtime observations.
The test oracle requires actual assertion failures from mutants; a crashed
runner or failed grader-staged build is not a successful mutation test.

`test_oracles.py` validates reference solutions and these negative controls:
missing launch installation, incompatible input QoS, faulty scan filtering,
dead YAML, hard-coded namespace, untouched faulty math, skipped-only tests,
vacuous tests, incorrect IMU statuses and an injected transform. Best-effort
output QoS and renamed fixture variants are positive controls.

On a failure:

- A product defect is corrected, gets a regression, and both installation-method
  sessions for that case rerun on fresh seeds. Earlier attempts remain reported.
- An isolated model error gets one fresh-variant retry. Two failures leave the
  case unaccepted; report and investigate it rather than dropping the case.
- An infrastructure/readiness/contamination failure is ungradable. Correct the
  cause and record a new attempt; do not put the failed attempt in a success-rate
  denominator. An unsupported delivery/skill path remains a product defect.
- If an allowance ends, the other collaborating agent continues as the user
  instructed. Missing model evidence or a missing final peer review must be
  disclosed; it cannot be replaced by claiming a tool unit test proves it.

Routing (skill invocation/read, script command and result), observed artifact
quality, unsupported final verification claims, tokens/turns and elapsed time are
reviewed separately. A successful output without loading the skill does not
prove that skill contributed. No p-values, pooled headline rate or general
performance claim will be reported from this acceptance set.

## Reproduce without a model call

```bash
source /opt/ros/jazzy/setup.bash
python3 evals/development/test_oracles.py
ROS2_ACCEPTANCE_SEED=1 python3 evals/development/test_oracles.py
```

Requires colcon, pytest compatible with Jazzy, launch_ros, sensor_msgs, std_msgs,
std_srvs and tf2_ros. These are synthetic local fixtures; no motion commands or
hardware are involved. Real model calls are explicit through
`run_acceptance.py --help`; use new workspace/output paths and mask previous
cells and private coordination directories. Review raw logs before sharing;
private reasoning is not part of the public evidence.

Not covered: physical robots, MCU firmware, full Nav2/MoveIt/Gazebo applications,
downstream interface consumers, stale-overlay remediation or independent
behavioral verification of `--packages-up-to` advice. These limits must remain
visible in the release report.
