Perfect! The package is built and working. Here's what was created and the output from `ros2 topic echo`:

## Summary

**Package Structure Created:**
- `demo_pkg/` — ROS 2 Python package
  - `demo_pkg/publisher_node.py` — Node that publishes String messages at 1 Hz
  - `launch/demo.launch.py` — Launch file to start the node
  - `package.xml` — Package metadata with rclpy and std_msgs dependencies
  - `setup.py` — Build configuration with entry point and launch data files

**Build Result:**
✅ Successfully built with `colcon build --symlink-install`

**Output from `ros2 topic echo /greeting`:**
```
data: 'Hello! Message #8'
---
data: 'Hello! Message #9'
---
data: 'Hello! Message #10'
---
data: 'Hello! Message #11'
---
```

The node is publishing messages on `/greeting` at exactly 1 Hz (one message per second with incrementing counters). The launch file successfully started the publisher node, and the echo shows it's receiving the messages correctly. The numbers are higher (8+) because the node had been running for a few seconds before we started echoing the topic.