---
name: ros2-moveit
description: "MoveIt 2: MoveGroup C++/Python API, IK solvers, OMPL planning, MoveIt Servo, SRDF."
---

# MoveIt 2 Motion Planning Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Core Principles & Architecture
- **Target OS & ROS Distro**: **Ubuntu 24.04 LTS & ROS 2 Jazzy Jalisco**.
- **Manipulation Stack**: MoveIt 2 provides motion planning, inverse kinematics (IK), collision checking, 3D perception (OctoMap), and real-time arm servoing via `moveit_servo` (`MoveItServo` / `servo_node`), with path planning managed via `MoveGroupInterface`.
- **Zero-Hallucination Policy**: Never speculate about MoveIt 2 C++ methods (`setPoseTarget`, `plan`, `execute`), planning scene monitors, or SRDF tag configurations. Verify all signatures against official MoveIt 2 documentation.

## 2. Official Documentation Catalog

### A. Master Documentation Portals
- **MoveIt 2 Main Portal**: `https://moveit.picknik.ai/main/index.html`
- **MoveIt 2 Core Concepts**: `https://moveit.picknik.ai/main/doc/concepts/concepts.html`
- **MoveGroup Architecture**: `https://moveit.picknik.ai/main/doc/concepts/move_group.html`
- **Kinematics & IK Solvers**: `https://moveit.picknik.ai/main/doc/concepts/kinematics.html`
- **Motion Planning & OMPL**: `https://moveit.picknik.ai/main/doc/concepts/motion_planning.html`
- **Code Examples Index**: `https://moveit.picknik.ai/main/doc/examples/examples.html`
- **MoveIt 2 C++ API Reference**: `https://moveit.picknik.ai/main/doc/api/cpp_api/api.html`
- **MoveIt 2 Python API Reference**: `https://moveit.picknik.ai/main/doc/api/python_api/api.html`

## 3. Key C++ Usage Patterns

### A. MoveGroupInterface Pose Target Planning
```cpp
#include <moveit/move_group_interface/move_group_interface.hpp>  // Jazzy (MoveIt 2.10+): .hpp headers; legacy .h is deprecated

rclcpp::NodeOptions node_options;
node_options.automatically_declare_parameters_from_overrides(true);
auto node = std::make_shared<rclcpp::Node>("arm_planner", node_options);
moveit::planning_interface::MoveGroupInterface move_group(node, "arm");
geometry_msgs::msg::Pose target_pose;
target_pose.orientation.w = 1.0;
target_pose.position.x = 0.28;
target_pose.position.y = -0.2;
target_pose.position.z = 0.5;

move_group.setPoseTarget(target_pose);

moveit::planning_interface::MoveGroupInterface::Plan my_plan;
bool success = (move_group.plan(my_plan) == moveit::core::MoveItErrorCode::SUCCESS);
if (success) {
    move_group.execute(my_plan);
}
```

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Planning fails instantly with `State in collision` / `No valid path found` | Start state already colliding: overlapping URDF collision geometry or missing SRDF Allowed Collision Matrix entries | Inspect the planning scene in RViz; regenerate the ACM with MoveIt Setup Assistant for adjacent/fixed links |
| IK fails for poses the arm can clearly reach | Default KDL solver is weak for >=6-DOF chains, or wrong `tip_link`/planning group | Switch kinematics.yaml to TRAC-IK or PickIK; verify the group's base/tip links match the URDF chain |
| `plan()` succeeds but `execute()` times out or is rejected | `moveit_controllers.yaml` action namespace doesn't match the running `FollowJointTrajectory` controller | Compare `ros2 action list` vs the controller names/action_ns in moveit_simple_controller_manager config |
| Trajectory aborts mid-execution with path tolerance errors | Velocity/acceleration limits zero or missing in `joint_limits.yaml`, so time parameterization produces infeasible timing | Fill real limits for every joint; re-run time parameterization |
| Planning hangs for seconds then fails on cluttered scenes | `allowed_planning_time`/attempts too low with heavy collision meshes | Raise planning time; replace visual meshes with primitive collision shapes |
| MoveIt Servo receives twists but arm never moves | Servo not activated (start service not called) or stale command timeout | Call the servo start trigger service; publish twists faster than `incoming_command_timeout` |

## 5. Tuning Baselines
- **Kinematics**: `kinematics.yaml` `kinematics_solver_search_resolution: 0.005`, `kinematics_solver_timeout: 0.005` are sane starts; raise timeout to 0.05 if IK intermittently fails near workspace edges.
- **OMPL**: start with `RRTConnect` (fast, no optimization); switch to `RRTstar`/`BiTRRT` only when path quality matters more than planning time.
- **Collision meshes**: keep collision geometry under ~1000 triangles per link; planning time scales with collision checking, not IK.
