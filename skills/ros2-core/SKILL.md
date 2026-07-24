---
name: ros2-core
description: "ROS 2 Jazzy core: rclcpp/rclpy, TF2 transforms, odometry/EKF fusion, node parameters, launch, QoS."
---

# ROS 2 Jazzy (Ubuntu 24.04 LTS) Core Development Instructions

## 1. Core Principles & Distro Awareness
- **Target OS & ROS Distro**: **Ubuntu 24.04 LTS (Noble Numbat) & ROS 2 Jazzy Jalisco** (Default target; verify `$ROS_DISTRO` in shell).
- **Zero-Hallucination Policy**: Never guess C++ method names, Python API functions, QoS profile signatures, parameter names, or TF frame transformation syntax. Always refer to official ROS 2 Jazzy documentation links or local `/opt/ros/jazzy/` installed packages.

## 2. Dedicated Feature Reference Catalogs

### A. TF2 Transforms & Coordinate Frames (TF / TF2)
Refer to these exact pages when publishing or looking up coordinate frames (`map` -> `odom` -> `base_link` -> `base_footprint` -> `laser`/`camera`):
- **About TF2 & Frame Trees**: `https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html`
  - *Description*: Standard coordinate frame conventions (REP 105), frame tree hierarchy, and TF2 architecture.
- **Introduction to TF2**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Introduction-To-Tf2.html`
- **Writing a TF2 Broadcaster (C++)**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Cpp.html`
  - *Description*: Broadcasting dynamic transforms using `tf2_ros::TransformBroadcaster` and `geometry_msgs::msg::TransformStamped`.
- **Writing a TF2 Broadcaster (Python)**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Py.html`
- **Writing a Static TF2 Broadcaster (C++ & Py)**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Static-Tf2-Broadcaster-Cpp.html`
  - *Description*: Publishing fixed sensor offsets (e.g. `base_link` -> `laser_frame`) using `tf2_ros::StaticTransformBroadcaster`.
- **Writing a TF2 Listener (C++)**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Listener-Cpp.html`
  - *Description*: Listening to and looking up transformations using `tf2_ros::Buffer` and `tf2_ros::TransformListener` with `canTransform()` and `lookupTransform()`.
- **Writing a TF2 Listener (Python)**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Listener-Py.html`
- **TF2 Time Travel & Buffer Lookups**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Learning-About-Tf2-Time-Cpp.html`
  - *Description*: Handling timestamped transformations, buffer timeouts, and `tf2::ExtrapolationException`.

### B. Odometry & State Estimation (Odom, IMU & EKF)
Refer to these pages when processing wheel odometry, IMU data, and fusing sensor inputs (`nav_msgs/msg/Odometry`):
- **Setting Up Robot Transformation Tree**: `https://docs.nav2.org/setup_guides/transformation/setup_transforms.html`
  - *Description*: REP 105 compliance (`map` -> `odom` -> `base_link`), static transform setup.
- **Setting Up Odometry (Hardware & Simulation)**: `https://docs.nav2.org/setup_guides/odom/setup_odom_gz.html`
  - *Description*: Calculating 2D/3D odometry, publishing `/odom` topic and `odom` -> `base_link` TF transform.
- **Smoothing & Fusing Odometry (robot_localization)**: `https://docs.nav2.org/setup_guides/odom/setup_robot_localization.html`
  - *Description*: EKF (Extended Kalman Filter) setup with `robot_localization` (`ekf_node`), fusing wheel odometry (`nav_msgs/msg/Odometry`) and IMU (`sensor_msgs/msg/Imu`).

### C. Node Parameters & Dynamic Reconfiguration
Refer to these pages when declaring, getting, setting, and validating node parameters:
- **About ROS 2 Parameters Concept**: `https://docs.ros.org/en/jazzy/Concepts/Basic/About-Parameters.html`
  - *Description*: Parameter types, parameter descriptors, read-only vs dynamic parameters.
- **Using Parameters in C++ Class**: `https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-CPP.html`
  - *Description*: `declare_parameter()`, `get_parameter()`, parameter descriptors (`rcl_interfaces::msg::ParameterDescriptor`).
- **Using Parameters in Python Class**: `https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-Python.html`
- **Dynamic Parameter Change Monitoring (C++)**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Monitoring-For-Parameter-Changes-CPP.html`
  - *Description*: Registering runtime validation callbacks via `add_on_set_parameters_callback()` to validate parameter updates on the fly.
- **Dynamic Parameter Change Monitoring (Python)**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Monitoring-For-Parameter-Changes-Python.html`
- **CLI & YAML Parameter Overrides**: `https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters/Understanding-ROS2-Parameters.html`
  - *Description*: `ros2 param list`, `ros2 param get/set`, loading YAML files via `--ros-args --params-file`.

### D. Launch System, QoS & Build System
- **Launch System Guide**: `https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html`
- **Quality of Service (QoS)**: `https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html`
- **Ament CMake Guide**: `https://docs.ros.org/en/jazzy/How-To-Guides/Ament-CMake-Documentation.html`

### E. API Reference Indexes
- **`rclcpp` C++ API Index**: `https://docs.ros.org/en/jazzy/p/rclcpp/`
- **`rclpy` Python API Index**: `https://docs.ros.org/en/jazzy/p/rclpy/`

## 3. Local System Inspection & Interfaces (Ground Truth)
- **Message Definition Inspection**: `ros2 interface show <interface_name>` (e.g. `ros2 interface show nav_msgs/msg/Odometry` or `geometry_msgs/msg/TransformStamped`).
- **Package Installed Assets**: `ros2 pkg prefix <package_name>`
- **Live Topics / Params**: `ros2 topic list -t`, `ros2 param list <node_name>`.

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Topic listed in `ros2 topic list` but subscriber receives nothing | Incompatible QoS: BestEffort publisher vs Reliable subscriber, or volatile pub vs transient_local sub | `python3 scripts/check_qos_compat.py --topic <topic>` checks every pub/sub pair, or read `ros2 topic info <topic> -v`; align them (`SensorDataQoS` for sensors) |
| Nodes on two machines can't see each other | Different `ROS_DOMAIN_ID`/RMW implementations, or multicast blocked on the network | Match `ROS_DOMAIN_ID` and `RMW_IMPLEMENTATION`; test discovery with `ros2 multicast receive/send` |
| Parameters from YAML silently ignored at launch | Node name/namespace key in the YAML doesn't match the actual node name | Match the YAML top-level key to the node's full name, or use `/**:` wildcard |
| `set_parameters` succeeds but behavior doesn't change | Node read the value once at startup and never re-reads; no `add_on_set_parameters_callback` applying it | Implement the parameter callback, or restart the node after changes |
| TF `ExtrapolationException` even though both frames exist | Mixed clocks (`use_sim_time` inconsistent) or looking up a hardcoded timestamp | Use `tf2::TimePointZero`/`Time()` for latest; align `use_sim_time` on every node |
| Timers/subscriptions starve while one callback runs | Single-threaded executor blocked by a long or blocking callback | `MultiThreadedExecutor` + `ReentrantCallbackGroup` for blocking work; never sleep in callbacks |

## 5. Strict Coding Rules
1. Never mix ROS 1 syntax (`ros::init`, `catkin`, `.launch` XML legacy).
2. For TF lookups, always catch `tf2::TransformException` or use `canTransform()` timeout guards.
3. Always match topic subscriber QoS to publisher QoS (e.g. `SensorDataQoS` for high-rate LiDAR/IMU/Odom topics).
