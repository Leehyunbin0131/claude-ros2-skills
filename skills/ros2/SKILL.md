---
name: ros2
description: "Master router: directs any ROS 2 Jazzy task to the matching domain skill (core, Nav2, Gazebo, control, MoveIt, perception, testing, micro-ROS, security, troubleshooting)."
---

# ROS 2 Jazzy Master Router (Ubuntu 24.04 LTS)

Target: **Ubuntu 24.04 LTS & ROS 2 Jazzy Jalisco** (verify `$ROS_DISTRO`).

Do not answer from memorized knowledge. Route to the domain skill below, follow its doc links, and verify APIs against official docs or local `/opt/ros/jazzy/` packages (`ros2 interface show`, `ros2 topic list -t`, `ros2 node info`).

| Task is about… | Use skill |
| :--- | :--- |
| rclcpp/rclpy, TF2, odometry/EKF, parameters, launch, QoS | `ros2-core` |
| Nav2 (AMCL, costmaps, MPPI/Smac, BT), SLAM Toolbox, RTAB-Map, VSLAM | `ros2-dev` |
| Gazebo Harmonic, ros_gz_bridge/ros_gz_sim, SDF, sensor plugins | `gazebo-sim` |
| ros2_control hardware interfaces, controller manager, URDF tags | `ros2-control` |
| MoveIt 2, MoveGroup API, IK/OMPL, MoveIt Servo, SRDF | `ros2-moveit` |
| image_transport, cv_bridge, vision_msgs, depth, PCL | `ros2-perception` |
| launch_testing, gtest/pytest, rosbag2 APIs, ros2trace | `ros2-testing` |
| micro-ROS Agent, rclc, embedded targets | `ros2-microros` |
| SROS2, keystore, access control, DDS Security | `ros2-security` |
| Wrong robot behavior, TF/sensor misalignment, sim time, deadlocks | `ros2-troubleshooting` |

Task spans multiple domains → load each relevant skill; resolve TF/frame questions with `ros2-troubleshooting` conventions (REP 103/105) as ground truth.
