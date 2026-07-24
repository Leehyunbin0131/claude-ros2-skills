---
name: ros2-testing
description: "Testing: launch_testing, gtest/pytest, rosbag2 C++/Python APIs, ros2trace profiling."
---

# ROS 2 Testing, Rosbag2 & Tracing Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Core Principles & Architecture
- **Target OS & ROS Distro**: **Ubuntu 24.04 LTS & ROS 2 Jazzy Jalisco**.
- **Quality & Diagnostics Stack**: Integration testing via `launch_testing`, unit testing via `ament_cmake_gtest` / `pytest`, data recording/playback programmatically via `rosbag2` C++/Python APIs, and performance profiling via `ros2trace`.
- **Zero-Hallucination Policy**: Never speculate about `rosbag2` C++/Python API methods (`open`, `write`, `create_topic`) or `launch_testing` assertions. Verify all signatures against official ROS 2 Jazzy documentation.

## 2. Official Documentation Catalog

### A. Master Documentation & Tutorials
- **Writing Integration Tests with `launch_testing`**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/Integration.html`
- **`launch_testing` API Docs**: `https://docs.ros.org/en/jazzy/p/launch_testing/`
- **`rosbag2_cpp` API Docs**: `https://docs.ros.org/en/jazzy/p/rosbag2_cpp/`
- **`rosbag2_py` API Docs**: `https://docs.ros.org/en/jazzy/p/rosbag2_py/`
- **ROS 2 Tracing Guide (`ros2_tracing`)**: `https://docs.ros.org/en/jazzy/Tutorials/Advanced/ROS2-Tracing-Trace-and-Analyze.html`
- **Rosbag2 Official Repository**: `https://github.com/ros2/rosbag2`

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
