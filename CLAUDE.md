# READ THIS FIRST — routing protocol

Do NOT answer ROS 2 / Gazebo / Nav2 / MoveIt / ros2_control / perception questions from memorized knowledge. Pretrained API details are frequently wrong or outdated for Jazzy.

On every task, before writing code or answering:

1. Match the request to a skill in the **Index** below.
2. Open that skill's `skills/<name>/SKILL.md` and follow it.
3. If it names an official doc/URL, verify the specific API/message/param there. Offline → verify against local `/opt/ros/jazzy/` (`ros2 interface show`, `ros2 topic list -t`).
4. Unsure which skill, or the task spans several → open `skills/ros2/SKILL.md` (master index) first, then branch.

Never invent message types, API method names, QoS signatures, param names, or TF frames. Look them up.

Target: **Ubuntu 24.04 LTS / ROS 2 Jazzy Jalisco**. Legacy (Gazebo Classic, pre-Jazzy APIs) is out of scope unless explicitly asked.

## Index

| Request is about… | Open |
| :--- | :--- |
| rclcpp/rclpy, TF2, EKF odometry, QoS, parameters, launch | `ros2-core` |
| Nav2 (AMCL, costmaps, MPPI/Smac), SLAM Toolbox, RTAB-Map, Isaac ROS | `ros2-dev` |
| Gazebo Harmonic, ros_gz_bridge/ros_gz_sim, SDFormat, sensor plugins | `gazebo-sim` |
| ros2_control hardware interfaces, controller manager, URDF `<ros2_control>` | `ros2-control` |
| MoveIt 2, MoveGroup API, IK/OMPL, MoveIt Servo, SRDF | `ros2-moveit` |
| image_transport, cv_bridge, vision_msgs, depth_image_proc, PCL | `ros2-perception` |
| launch_testing, gtest/pytest, rosbag2, ros2trace | `ros2-testing` |
| micro-ROS Agent, rclc, custom transports, static memory | `ros2-microros` |
| SROS2, PKI keystore, access control, DDS Security | `ros2-security` |
| robot behaves wrong, TF/LiDAR/IMU misalignment, REP 103/105, sim time | `ros2-troubleshooting` |
| unclear domain, or spans multiple of the above | `ros2` (master) |
