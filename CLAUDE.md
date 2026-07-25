# READ THIS FIRST — ROS 2 verification protocol

Do NOT answer ROS 2 / Gazebo / Nav2 / MoveIt / ros2_control / perception questions from memorized knowledge. Pretrained API details are frequently wrong or outdated for Jazzy.

On every task, before writing code or answering:

1. Load the matching `ros2-*` skill. They route themselves by description; a task spanning several domains loads each one.
2. Verify the specific API / message / parameter against the doc that skill names, or against local `/opt/ros/jazzy/` (`ros2 interface show`, `ros2 topic list -t`, `ros2 pkg prefix`).
3. Resolve any frame/TF question against `ros2-troubleshooting` (REP 103/105) as ground truth.

Never invent message types, API method names, QoS signatures, param names, or TF frames. Look them up.

Target: **Ubuntu 24.04 LTS / ROS 2 Jazzy Jalisco**. Legacy (Gazebo Classic, pre-Jazzy APIs) is out of scope unless explicitly asked.
