# Development and diagnostic validation — 2026-09-25

This records operational validation for the development-workflow update. It is
not an agent performance benchmark. The previous source baseline is
`39fed2a093a811aa8797d28daff6bef737b94b6f`.

## Observable changes

| Case | Earlier behaviour / ordinary command | Updated outcome |
| :--- | :--- | :--- |
| CMake package has no registered tests | Both `colcon test` and `colcon test-result` return 0 | Development evidence check returns 2: no executed tests |
| All package tests skipped | Test command returns 0 | Evidence check returns 2 |
| A named package has no result in the new run directory | An older passing report exists elsewhere | Missing current evidence returns 2 |
| Passing Python and CMake tests | Reports contain executed tests | Evidence check returns 0 |
| Failing Python assertion | Test report contains failure | Evidence check returns 1 |
| IMU acceleration contains NaN | Original check could return PASS | Inconclusive (2) |
| IMU marks acceleration unavailable | Original check ignored covariance sentinel | Inconclusive (2) |
| Inverted IMU has a correct declared TF | Raw negative Z was treated as a mounting fault | Transform to the base frame, then PASS |
| IMU lacks the needed transform | Raw axes previously assumed aligned | Inconclusive (2), unless the user explicitly requests aligned-axis assumptions |
| Odometry subscriber accumulates messages during movement | End sample could be a pre-movement queued pose | Fresh subscription for the endpoint sample |
| QoS defaults, deadlines and liveliness | Partial handwritten policy rules | Native Jazzy compatibility result; unknown is inconclusive |
| Plugin installation | Root CLAUDE.md was not loaded by the plugin mechanism | SessionStart emits the unchanged protocol |
| Evaluation never produces an answer or sidecar | Could be counted as a model failure | Ungradable, excluded from the corresponding denominator |
| Evaluation scenario never becomes ready | Runner could continue to a paid cell | Readiness failure aborts before the cell |

## Reproduce

[CONTRIBUTING.md](../CONTRIBUTING.md#before-opening-a-pr) lists the commands.
The checked-in tests create and clean their own temporary artifacts:

- `skills/ros2-troubleshooting/scripts/test_checks.py`: 11 pure decision groups.
- `tests/test_install.py`: 9 installation, preservation, rollback and protocol
  transport tests, including skill paths containing spaces.
- `tests/test_development.py`: 6 result-evidence tests without ROS or colcon.
- `tests/test_colcon_workflow.py`: one integration test with five real temporary
  packages (Python pass/fail/skipped; CMake pass/empty), plus fresh-directory
  separation from an older successful report. Requires colcon, pytest, CMake
  and a C++ compiler. All branches were executed, not skipped, in local validation.
- `tests/test_ros_checks.py`: 11 actual Jazzy integration tests with synthetic
  localhost data, including a deliberately incorrect IMU fixture and interrupt
  cleanup. No hardware or motion commands.
- `evals/harness/test_harness.py`: 42 harness regressions, including process
  ownership, mount isolation, grading and readiness; `grade_v2.py --selftest`
  also passes without Nav2 installed.

All three skill manifests and the Claude Code plugin manifest validate.
`CLAUDE.md`, historical `evals/runs/` and all 34 frozen prompt lines remain
unchanged from the baseline.

An offline runner smoke also brought up the real synthetic IMU/TF scenario,
passed readiness, invoked a stub CLI inside mount isolation and cleaned up its
tagged processes. It made no model call and is not an evaluation score.

A separate live Claude Code loading smoke used Opus 5.5 with xhigh effort and
verified that SessionStart delivered the exact protocol. It ran before the new
`ros2-development` skill was added; it verifies hook delivery, not selection or
behavioural effectiveness of the new skill. Claude participated in audit and
implementation; its session allowance ended before final integration review.
The remaining integration and development-workflow work was completed by Codex.

## Limits

No new controlled agent comparison was run. No claim is made that the new prose
improves completion rate, tokens or development time. The runtime and colcon
fixtures establish specific useful distinctions, not full application quality.

Physical robot motion, sensor calibration, MCU firmware and full Nav2, MoveIt
or Gazebo applications were not validated here. Synthetic data cannot establish
physical mounting or geometry. Historical scores remain historical and retain
the [reproducibility limits](CAPABILITIES.md) documented in the reconciliation.
