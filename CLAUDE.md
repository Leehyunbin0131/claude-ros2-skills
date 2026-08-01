# READ THIS FIRST — ROS 2 verification protocol

Do NOT answer ROS 2 / Gazebo / Nav2 / MoveIt / ros2_control / perception questions from memorized knowledge. Pretrained API details are frequently wrong or outdated for Jazzy.

On every task, before writing code or answering:

1. Verify the specific API / message / parameter against local `/opt/ros/jazzy/` (`ros2 interface show`, `ros2 topic list -t`, `ros2 pkg prefix`, `ros2 param list`) or against the official Jazzy docs for that package.
2. Resolve any frame/TF question against `ros2-troubleshooting` (REP 103/105) as ground truth.
3. When a system logs healthy and does not work, run `ros2-troubleshooting`'s check for it before reasoning about the symptom. An exit code settles it; a hypothesis does not.

Never invent message types, API method names, QoS signatures, param names, or TF frames. Look them up.

**`rclcpp` is C++ only, `rclpy` is Python only.** They are separate libraries, not two spellings of one: `rclcpp.qos` in Python and `rclpy::` in C++ do not exist. An example found in one language translates as a concept, never as a namespace. Answer in the language the user is using, and if you are unsure a symbol exists in that language, check (`python3 -c "import rclpy.qos"`).

## Establish before writing (no doc can tell you these)

Ask when the request doesn't say — guessing one of these and writing 200 lines costs far more than one question:

- **Real hardware, simulation, or both?** Sets `use_sim_time`, decides whether physical checks apply, and whether any tuning transfers.
- **Existing workspace or greenfield?** Match the package layout, naming, and launch conventions already in the repo before inventing your own.
- **Who already publishes the topic or TF you're about to add?** Two publishers on one transform is a silent failure that looks healthy in every log.
- **Real geometry** — sensor mounting orientation, wheel radius/separation — whenever the task touches them. The robot is not its CAD model.

## Done means it ran

Writing the code is not the deliverable. Report what you actually observed — a build succeeding, `ros2 topic echo` showing data, a lifecycle node reaching `active`, a check script passing — or state plainly that you could not verify and what you'd need to.

This is the single highest-value line here. Config that reads correctly and is never started is this pack's most reproducible failure: a Nav2 parameter file that names every plugin correctly and puts every value in the right place, which the servers then refuse to configure. Bringing the same file up once finds it in one sitting. Run what you wrote.

Target: **Ubuntu 24.04 LTS / ROS 2 Jazzy Jalisco**. Legacy (Gazebo Classic, pre-Jazzy APIs) is out of scope unless explicitly asked.
