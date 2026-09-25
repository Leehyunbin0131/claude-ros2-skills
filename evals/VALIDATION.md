# Development and diagnostic validation — 2026-09-25

This records operational validation for the development-workflow update. It is
not an agent performance benchmark. The previous source baseline is
`39fed2a093a811aa8797d28daff6bef737b94b6f`.

## Observable changes

| Case | Earlier behaviour / ordinary command | Updated outcome |
| :--- | :--- | :--- |
| CMake package has no registered tests | Both `colcon test` and `colcon test-result` return 0 | Development evidence check returns 2: no executed tests |
| New setuptools ignores `tests_require` in Python metadata | Colcon may choose a runner that collects none of the intended pytest tests | Select `--python-testing pytest` explicitly for pytest packages; fixtures cover this without relying on the deprecated metadata |
| All package tests skipped | Test command returns 0 | Evidence check returns 2 |
| A linter passes but the regression is skipped | Package-level success alone appears green | `--require-test PACKAGE::ID` requires the selected behavior test to execute; observed IDs are printed |
| An ament CMake wrapper succeeds with only skipped inner tests | CTest wrapper can look passed | Follow its recorded JUnit path, including paths configured in the build directory; return 2 |
| An ament test process crashes | Missing result can resemble missing evidence | CTest and ament crash reports return 1; inspect the log before attributing the cause |
| A named package has no result in the new run directory | An older passing report exists elsewhere | Missing current evidence returns 2 |
| Passing Python and CMake tests | Reports contain executed tests | Evidence check returns 0 |
| Failing Python assertion | Test report contains failure | Evidence check returns 1 |
| IMU acceleration contains NaN | Original check could return PASS | Inconclusive (2) |
| IMU marks acceleration unavailable | Original check ignored covariance sentinel | Inconclusive (2) |
| Inverted IMU has a correct declared TF | Raw negative Z was treated as a mounting fault | Transform to the base frame, then PASS |
| IMU lacks the needed transform | Raw axes previously assumed aligned | Inconclusive (2), unless the user explicitly requests aligned-axis assumptions |
| No TF frames arrive at all | Missing graph could be presented as broken connectivity | Inconclusive (2); a graph that is observed but lacks a requested chain still fails |
| Odometry subscriber accumulates messages during movement | End sample could be a pre-movement queued pose | Fresh subscription for the endpoint sample |
| QoS defaults, deadlines and liveliness | Partial handwritten policy rules | Native Jazzy compatibility result; unknown is inconclusive |
| Plugin installation | Root CLAUDE.md was not loaded by the plugin mechanism | SessionStart emits the current protocol exactly |
| Evaluation never produces an answer or sidecar | Could be counted as a model failure | Ungradable, excluded from the corresponding denominator |
| Evaluation scenario never becomes ready | Runner could continue to a paid cell | Readiness failure aborts before the cell |

## Reproduce

[CONTRIBUTING.md](../CONTRIBUTING.md#before-opening-a-pr) lists the commands.
The checked-in tests create and clean their own temporary artifacts:

- `skills/ros2-troubleshooting/scripts/test_checks.py`: 11 pure decision groups.
- `tests/test_install.py`: 9 installation, preservation, rollback and protocol
  transport tests, including skill paths containing spaces.
- `tests/test_development.py`: 12 result-evidence tests without ROS or colcon.
- `evals/development/test_runner.py`: 4 isolation, inventory, protocol, paired
  script-output and frozen-input checks without model calls.
- `tests/test_colcon_workflow.py`: one integration test with five real temporary
  packages (Python pass/fail/skipped; CMake pass/empty), plus fresh-directory
  separation from an older successful report. Requires colcon, pytest, CMake
  and a C++ compiler. All branches were executed, not skipped, in local validation.
- `tests/test_ament_test_results.py`: real ament CMake pytest wrappers with
  passing, skipped and crashed inner tests, selected test IDs, and an older
  passing report that must not satisfy a current skipped wrapper. Claude also
  independently reproduced a real gtest crash and a passing/disabled gtest pair.
- `tests/test_ros_checks.py`: 12 actual Jazzy integration tests with synthetic
  localhost data, including a deliberately incorrect IMU fixture and interrupt
  cleanup. No hardware or motion commands. Positive tests allow DDS discovery
  retransmission; short missing-data tests check deadlines independently.
- `evals/harness/test_harness.py`: 42 harness regressions, including process
  ownership, mount isolation, grading and readiness; `grade_v2.py --selftest`
  also passes without Nav2 installed.
- `evals/development/test_oracles.py`: all 3 groups pass for seeds 0, 1, 2 and 3.
  Independent positive and negative controls cover installed launch/config,
  YAML changes, namespace, QoS, scan filtering, public library behavior, vacuous
  and skipped tests, three distinct math mutants, IMU statuses and injected TF.

The ROS-sourced runs use pytest 7.4.4, pytest-rerunfailures 12.0, setuptools
79.0.1 and colcon-core 0.21.3 on Ubuntu 24.04 / Jazzy. Pytest 9.1.1 failed during
Jazzy `launch_testing` plugin startup in reproduction; that runner error must not
be mistaken for a failed assertion in the candidate implementation. CI exercises
both generic Python colcon and the Ubuntu/Jazzy test environment.

All three skill manifests and the Claude Code plugin manifest validate.
At the initial development-workflow revision, `CLAUDE.md`, historical
`evals/runs/` and all 34 frozen prompt lines were unchanged from the baseline.
The subsequent release review deliberately revises the shared protocol to scope
it to ROS tasks and distinguish inconclusive results; historical records and
frozen prompts remain unchanged. Historical protocol scores describe the old text.

An offline runner smoke also brought up the real synthetic IMU/TF scenario,
passed readiness, invoked a stub CLI inside mount isolation and cleaned up its
tagged processes. It made no model call and is not an evaluation score.

A historical plugin-only loading smoke used Opus 5.5 with xhigh effort before
`ros2-development` existed. The current release review resumed actual joint
work with Claude Code **Opus 5.5 High**, including independent reproductions,
reciprocal critique and a declared live acceptance protocol.

The current two loading smokes exercise both delivery methods and the new
development skill. All nine original sessions (three baselines, three plugin,
three manual) passed the independent artifact oracles. Baselines passed too;
the results do not establish improvement or equivalence. The additional runtime
cleanup review and fresh-seed follow-ups are reported separately in
[release acceptance](development/RESULTS.md), with source hashes, actions,
paired tool outputs, final answers, source artifacts and grading results.

## Limits

The release acceptance set is not a statistically powered agent comparison.
No claim is made that the prose improves completion rate, tokens or development
time. The runtime and colcon fixtures establish specific useful distinctions,
not full application quality.

Physical robot motion, sensor calibration, MCU firmware and full Nav2, MoveIt
or Gazebo applications were not validated here. Synthetic data cannot establish
physical mounting or geometry. Historical scores remain historical and retain
the [reproducibility limits](CAPABILITIES.md) documented in the reconciliation.
