---
name: ros2-testing
description: "Testing: launch_testing, gtest/pytest, rosbag2 C++/Python APIs, ros2trace profiling."
---

# ROS 2 Testing, Rosbag2 & Tracing Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Documentation Entry Points

| For | Entry point |
| :--- | :--- |
| Testing tutorials (CLI, gtest, pytest, integration) | `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/` |
| `launch_testing` / `rosbag2_cpp` / `rosbag2_py` API | `https://docs.ros.org/en/jazzy/p/<package>/` |
| rosbag2 source of truth | `https://github.com/ros2/rosbag2` |

## 2. Running Tests

```bash
colcon test --packages-select my_package
colcon test-result --all --verbose     # without --verbose you don't see WHICH case failed
```

`colcon test` reports a summary; the failing assertion lives in `colcon test-result`.
A test that was never registered in the build is indistinguishable from a passing
one in that summary — always confirm the expected test count, not just the exit code.

## 3. Key Concepts & Code Patterns

### A. Programmatic Rosbag2 Writer (C++)
```cpp
#include <rosbag2_cpp/writer.hpp>
#include <std_msgs/msg/string.hpp>

rosbag2_cpp::Writer writer;
writer.open("my_bag");
writer.create_topic({0, "chatter", "std_msgs/msg/String", "cdr", {}, ""});
writer.write<std_msgs::msg::String>(msg, "chatter", clock.now());
```

### B. Integration Testing (`launch_testing` Python)
```python
import unittest
import launch
import launch_ros.actions
import launch_testing
import launch_testing.actions
import launch_testing.asserts
def generate_test_description():
    node = launch_ros.actions.Node(package='demo_nodes_cpp', executable='talker')
    return launch.LaunchDescription([
        node,
        launch_testing.actions.ReadyToTest()
    ]), {'talker_node': node}

class TestTalkerNode(unittest.TestCase):
    def test_node_start(self, talker_node):
        self.assertIsNotNone(talker_node)

@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):
    def test_exit_code(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
```

`ReadyToTest()` marks the boundary: everything before it is launch setup, the active
tests run after it, and `@launch_testing.post_shutdown_test()` classes run once the
processes have exited.

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| `colcon test` passes but nothing actually ran | Tests never registered with the build (no `ament_add_gtest`/pytest hook, or not inside `if(BUILD_TESTING)`) | `colcon test-result --all` and check the test count is what you expect, not just the exit code |
| Test fails but the output says nothing useful | Assertion detail is only in the result files | `colcon test-result --all --verbose` |
| Node under test never receives the test publisher's messages | QoS mismatch between test fixture and node — same silent DDS failure as production | Match the node's QoS in the fixture; see `ros2-troubleshooting` (`check_qos_compat.py`) |
| Rosbag2 playback in a test produces no callbacks | Bag recorded with `use_sim_time` semantics but the test runs on wall clock, or `/clock` not published during playback | Align `use_sim_time` across the test nodes; play with `--clock` when the bag drives time |
