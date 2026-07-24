---
name: ros2-control
description: "ros2_control: controller manager, hardware interfaces, URDF ros2_control tags, controller spawners."
---

# ros2_control Development Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Core Principles & Architecture
- **Target OS & ROS Distro**: **Ubuntu 24.04 LTS & ROS 2 Jazzy Jalisco**.
- **Hardware Abstraction**: `ros2_control` decouples robot hardware drivers (`hardware_interface::SystemInterface`, `ActuatorInterface`, `SensorInterface`) from controller logic (`diff_drive_controller`, `joint_trajectory_controller`).
- **Zero-Hallucination Policy**: Always verify C++ hardware interface class inheritance, state/command interface names (`position`, `velocity`, `effort`), and URDF `<ros2_control>` XML tags against official documentation.

## 2. Official Documentation Catalog

### A. Master Documentation Portals
- **ros2_control Main Documentation**: `https://control.ros.org/jazzy/index.html`
- **Getting Started Guide**: `https://control.ros.org/jazzy/doc/getting_started/getting_started.html`
- **ros2_control Core Architecture**: `https://control.ros.org/jazzy/doc/ros2_control/doc/index.html`
- **ros2_controllers Index**: `https://control.ros.org/jazzy/doc/ros2_controllers/doc/controllers_index.html`
- **Official ros2_control Demos**: `https://control.ros.org/jazzy/doc/ros2_control_demos/doc/index.html`
- **Simulation Integration (Gazebo / Ignition)**: `https://control.ros.org/jazzy/doc/simulators/simulators.html`

## 3. Key Concepts & Patterns

### A. URDF `<ros2_control>` Tag Structure
```xml
<ros2_control name="RobotSystem" type="system">
  <hardware>
    <plugin>gz_ros2_control/GazeboSimSystem</plugin>
  </hardware>
  <joint name="left_wheel_joint">
    <command_interface name="velocity">
      <param name="min">-10</param>
      <param name="max">10</param>
    </command_interface>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
  </joint>
</ros2_control>
```

### B. Controller Spawning via Launch
```python
joint_state_broadcaster_spawner = Node(
    package="controller_manager",
    executable="spawner",
    arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
)

diff_drive_spawner = Node(
    package="controller_manager",
    executable="spawner",
    arguments=["diff_drive_controller", "--controller-manager", "/controller_manager"],
)
```

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Spawner times out waiting for `/controller_manager` | controller_manager not running, wrong namespace, or `use_sim_time` mismatch delaying clock | Check `ros2 node list` for controller_manager; pass `--controller-manager` with the actual namespace |
| Controller activation fails with resource/interface conflict | Two controllers claim the same `command_interface` | `ros2 control list_hardware_interfaces` — check which interfaces are claimed; deactivate the conflicting controller |
| `/joint_states` silent, robot model gray in RViz | `joint_state_broadcaster` never spawned (it is NOT automatic) | Spawn `joint_state_broadcaster` before other controllers |
| Controller loads then fails to configure | Params YAML not passed to controller_manager, or controller type string wrong | Verify params file reaches the `ros2_control_node`/`gz_ros2_control` node; check `type:` matches installed plugin (`ros2 control list_controller_types`) |
| Hardware activates but robot doesn't move on commands | Command interface names in URDF `<ros2_control>` don't match what the controller expects (`velocity` vs `position`), or hardware `write()` not implemented | Compare `ros2 control list_hardware_interfaces` vs controller's required interfaces |
| Odometry from `diff_drive_controller` drifts vs real distance | `wheel_radius` / `wheel_separation` don't match the physical chassis | Measure the real chassis; verify with `scripts/check_odom_direction.py` after fixing |
| Robot drives backward on forward command, logs look fine | Wheel joint axis flipped in URDF, or motor polarity inverted in hardware interface | Fix sign at the hardware interface or joint axis — never patch it in application code |

## 5. Calibration Baselines (`diff_drive_controller`)
Real hardware never matches CAD — measure, then use the built-in calibration knobs instead of fudging geometry:
1. **`wheel_radius`**: drive a measured straight line (e.g. 2.0 m by tape). Reported/actual ratio -> correct via `left_wheel_radius_multiplier` / `right_wheel_radius_multiplier` (baseline 1.0).
2. **`wheel_separation`**: rotate the robot exactly 5 full turns in place; error in reported yaw -> correct via `wheel_separation_multiplier` (baseline 1.0). Tire deformation under load makes the effective value differ from the measured chassis.
3. Re-verify after every tire/load change with `scripts/check_odom_direction.py`; straight-line drift to one side usually means the two radius multipliers need to differ slightly.
