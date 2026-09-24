---
name: ros2-development
description: "Implement or change ROS 2 Jazzy packages, nodes, interfaces, launch files and configuration in a colcon workspace. Use for building and validating a development change, including tests that report success without running. For a live QoS, TF, IMU or odometry fault, use ros2-troubleshooting."
---

# ROS 2 development

Work from the workspace's actual package graph and installed artifacts. This
skill supplies a development workflow and a check for empty test runs; it does
not prescribe a new workspace layout or replace the project's build conventions.

## Build the affected package graph

Use `colcon list` to identify package names and build types. Build the changed
package and its workspace dependencies with `colcon build --packages-up-to
<package>`. `--packages-select` alone does not build its dependencies. For a
message or public API change, include affected consumers in the build and tests.
Preserve the project's existing build/install flags and dependency versions.

Build in a shell with the intended underlay, not the workspace's old overlay.
Use a separate shell to source the resulting `install/setup.bash` and inspect
`ros2 pkg prefix <package>`: otherwise an older installed copy can appear to
validate the source change.

## Require tests to have run

`colcon test` and `colcon test-result` can both succeed with zero tests. Use a
fresh result directory so a previous passing report cannot satisfy this run:

```bash
# After building, in the workspace root. Replace my_package with actual names.
results="$(mktemp -d /tmp/ros2-test-results.XXXXXX)"
colcon test --packages-select my_package --return-code-on-test-failure \
  --test-result-base "$results" &&
python3 "${CLAUDE_SKILL_DIR}/scripts/check_test_results.py" "$results" \
  --packages my_package
```

The bundled check uses installed `colcon test-result`, accepts JUnit/CTest
formats it supports, and requires at least one non-skipped test in **each named
package**. Exit **0** means those reports contain executed, passing tests;
**1** means a test failure; **2** means missing, empty or unparseable evidence.
It reads reports and sends no ROS commands. Keep the printed result directory
when reporting a failure. A package intentionally without tests is not a failed
implementation; state the missing coverage and verify its changed behaviour.

## Verify the installed behaviour

Choose the smallest runtime check that exercises the change. A successful build
does not prove that a launch file, parameter file or executable was installed.
Use [verification.md](references/verification.md) for the relevant artifact:
Python/C++ nodes, interfaces, launch/config, or lifecycle and sensor behaviour.
Check the observable result again after a correction; keep a failed probe
separate from a confirmed defect in the implementation.

## Evidence

The result checker is tested against passing, failing, empty and skipped
reports, including fresh-directory separation in real Python and CMake colcon fixtures. This workflow is new: an
agent comparison has **not** established a performance gain from its prose.
Official semantics: [package selection](https://colcon.readthedocs.io/en/released/reference/package-selection-arguments.html),
[test](https://colcon.readthedocs.io/en/released/reference/verb/test.html),
[test results](https://colcon.readthedocs.io/en/released/reference/verb/test-result.html).
