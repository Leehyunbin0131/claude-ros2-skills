---
name: ros2-core
description: "ROS 2 Jazzy core: rclcpp/rclpy, TF2 transforms, odometry/EKF fusion, node parameters, launch, QoS."
---

# ROS 2 Jazzy (Ubuntu 24.04 LTS) Core Development Instructions

## 1. Documentation Entry Points

Navigate within these rather than guessing deep URLs.

| For | Entry point |
| :--- | :--- |
| Jazzy concepts, tutorials, how-to guides | `https://docs.ros.org/en/jazzy/` |
| `rclcpp` C++ API index | `https://docs.ros.org/en/jazzy/p/rclcpp/` |
| `rclpy` Python API index | `https://docs.ros.org/en/jazzy/p/rclpy/` |
| Robot bringup: TF tree, odometry, EKF fusion | `https://docs.nav2.org/setup_guides/index.html` |

## 2. Symbols to Verify There (never write these from memory)

- **TF2** — `tf2_ros::TransformBroadcaster`, `tf2_ros::StaticTransformBroadcaster`, `tf2_ros::Buffer`, `tf2_ros::TransformListener`, `canTransform()`, `lookupTransform()`, `tf2::TimePointZero`, `tf2::ExtrapolationException`; message `geometry_msgs/msg/TransformStamped`. Frame conventions are REP 105 (`map` -> `odom` -> `base_link` -> `base_footprint` -> sensor frames) — see `ros2-troubleshooting`.
- **Odometry / state estimation** — `nav_msgs/msg/Odometry`, `sensor_msgs/msg/Imu`, `robot_localization`'s `ekf_node`.
- **Parameters** — `declare_parameter()`, `get_parameter()`, `add_on_set_parameters_callback()`, `rcl_interfaces::msg::ParameterDescriptor`; CLI `ros2 param list|get|set`, YAML via `--ros-args --params-file`.
- **QoS** — `rclcpp::SensorDataQoS()` / `rclpy.qos.qos_profile_sensor_data` on sensor topics; inspect real endpoint QoS with `ros2 topic info <topic> -v`.
- **Packaging & build wiring** — see `ros2-package`.

## 3. Local System Inspection & Interfaces (Ground Truth)
- **Message Definition Inspection**: `ros2 interface show <interface_name>` (e.g. `ros2 interface show nav_msgs/msg/Odometry` or `geometry_msgs/msg/TransformStamped`).
- **Package Installed Assets**: `ros2 pkg prefix <package_name>`
- **Live Topics / Params**: `ros2 topic list -t`, `ros2 param list <node_name>`.

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Topic listed in `ros2 topic list` but subscriber receives nothing | Incompatible QoS: BestEffort publisher vs Reliable subscriber, or volatile pub vs transient_local sub | `check_qos_compat.py --topic <topic>` (bundled in `ros2-troubleshooting`) checks every pub/sub pair, or read `ros2 topic info <topic> -v`; align them (`SensorDataQoS` for sensors) |
| Nodes on two machines can't see each other | Different `ROS_DOMAIN_ID`/RMW implementations, or multicast blocked on the network | Match `ROS_DOMAIN_ID` and `RMW_IMPLEMENTATION`; test discovery with `ros2 multicast receive/send` |
| Parameters from YAML silently ignored at launch | Node name/namespace key in the YAML doesn't match the actual node name | Match the YAML top-level key to the node's full name, or use `/**:` wildcard |
| `set_parameters` succeeds but behavior doesn't change | Node read the value once at startup and never re-reads; no `add_on_set_parameters_callback` applying it | Implement the parameter callback, or restart the node after changes |
| TF `ExtrapolationException` even though both frames exist | Mixed clocks (`use_sim_time` inconsistent) or looking up a hardcoded timestamp | Use `tf2::TimePointZero`/`Time()` for latest; align `use_sim_time` on every node |
| Timers/subscriptions starve while one callback runs | Single-threaded executor blocked by a long or blocking callback | `MultiThreadedExecutor` + `ReentrantCallbackGroup` for blocking work; never sleep in callbacks |

## 5. Strict Coding Rules
1. Never mix ROS 1 syntax (`ros::init`, `catkin`, `.launch` XML legacy).
2. For TF lookups, always catch `tf2::TransformException` or use `canTransform()` timeout guards.
3. Always match topic subscriber QoS to publisher QoS (e.g. `SensorDataQoS` for high-rate LiDAR/IMU/Odom topics).
