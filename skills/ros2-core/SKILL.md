---
name: ros2-core
description: "ROS 2 Jazzy core: rclcpp/rclpy, TF2, QoS, node parameters, launch. The traps that compile, pass review, and fail silently at the DDS layer."
---

# ROS 2 core

## Verify against the install, not memory

`ros2 interface show <type>`, `ros2 topic info <topic> -v`, `ros2 param list
<node>` answer symbol and live-QoS questions faster and more reliably than
recalling them. API index: `docs.ros.org/en/jazzy/p/rclcpp/` (C++),
`docs.ros.org/en/jazzy/p/rclpy/` (Python) — separate libraries; `rclcpp::` has
no Python spelling and `rclpy.qos` has no C++ one.

Frame conventions (REP 103/105) and the runnable checks for TF, QoS
compatibility, IMU mount and odometry direction are `ros2-troubleshooting`'s —
load it rather than reasoning about a frame from code alone.

## Traps that compile and pass review

- `create_subscription(..., 10)` is RELIABLE + **VOLATILE**, not
  TRANSIENT_LOCAL. It will not match a BEST_EFFORT sensor publisher, and the
  callback simply never fires — no error, `ros2 topic hz` still shows traffic.
  Sensor topics: `rclcpp::SensorDataQoS()` / `rclpy.qos.qos_profile_sensor_data`.
- Filtering a `LaserScan` for `inf` alone still lets `nan` and readings outside
  `[range_min, range_max]` through. A reading is usable only when
  `math.isfinite(r) and range_min <= r <= range_max` — the message docs require
  discarding the rest.
- A blocking or slow callback starves every other timer/subscription on a
  single-threaded executor with no error printed. `MultiThreadedExecutor` +
  `ReentrantCallbackGroup` for anything that can block; never sleep in a
  callback.
- `rclpy.shutdown()` called after the context is already down raises. Catch
  both `KeyboardInterrupt` and `rclpy.executors.ExternalShutdownException`
  around `spin()`, and guard teardown with `if rclpy.ok(): rclpy.shutdown()`.
