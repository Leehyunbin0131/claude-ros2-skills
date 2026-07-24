---
name: gazebo-sim
description: "Gazebo Harmonic simulation: ros_gz_bridge, ros_gz_sim, SDF modeling, sensor & diff-drive plugins."
---

# Gazebo Simulation & ROS 2 Integration Instructions (Ubuntu 24.04 LTS)

## 1. Core Principles & Distro Pairings
- **Target OS & Distro Pairings**:
  - **Ubuntu 24.04 LTS & ROS 2 Jazzy**: Officially paired with **Gazebo Harmonic** (`https://gazebosim.org/docs/harmonic/`).
  - *(Legacy reference: Ubuntu 22.04 LTS & ROS 2 Humble pair with Gazebo Fortress `https://gazebosim.org/docs/fortress/`)*.
- **Modern Gazebo Architecture**: Strictly use modern Gazebo Sim (formerly Ignition Gazebo / `gz`) and `ros_gz`. Do not mix legacy Gazebo Classic (`gazebo_ros_pkgs` / `gazebo_ros`) unless explicitly requested for older legacy systems.
- **Zero-Hallucination Policy**: Always verify plugin system filenames (e.g., `gz-sim-diff-drive-system`), SDF tags, and `ros_gz_bridge` topic syntax against official documentation.

## 2. Official Documentation Reference Directives
Whenever creating simulation worlds, URDF/SDF models, Gazebo sensor plugins, or `ros_gz` launch files:

### A. Master Gazebo Documentation Portals
- **Gazebo Sim Master Docs**: `https://gazebosim.org/docs`
- **Gazebo Harmonic Docs (Jazzy)**: `https://gazebosim.org/docs/harmonic/`
- **Gazebo Fortress Docs (Humble)**: `https://gazebosim.org/docs/fortress/`
- **SDFormat Specification**: `https://sdformat.org/`

### B. ROS 2 & Gazebo Integration (`ros_gz`)
- **`ros_gz` Repository & Integration Guide**: `https://github.com/gazebosim/ros_gz`
- **`ros_gz_bridge` Topic Bridge**: `https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_bridge`
  - *Description*: Bidirectional topic bridging between Gazebo Transport and ROS 2 topics (`/scan`, `/odom`, `/cmd_vel`, `/camera/image_raw`, `/imu`).
  - *Bridge Syntax*: `ros2 run ros_gz_bridge parameter_bridge /scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan` or YAML bridge config files.
- **`ros_gz_sim` Launch & Spawning**: `https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_sim`
  - *Description*: Launching Gazebo world files (`.sdf`), spawning robot models using `ros_gz_sim create -topic robot_description` or `gz_sim.launch.py`.

### C. Nav2 Simulation Setup Guides
- **Nav2 Setup Guide for Gazebo**: `https://docs.nav2.org/setup_guides/gazebo.html`
- **URDF & Robot State Publisher Setup**: `https://docs.nav2.org/setup_guides/urdf/setup_urdf.html`
- **SDF World & Model Setup**: `https://docs.nav2.org/setup_guides/sdf/setup_sdf.html`
- **Simulating Odometry in Gazebo**: `https://docs.nav2.org/setup_guides/odom/setup_odom_gz.html`
  - *Description*: Differential drive plugin (`gz-sim-diff-drive-system`) setup and broadcasting `odom` -> `base_link`.
- **Simulating Sensors in Gazebo**: `https://docs.nav2.org/setup_guides/sensors/setup_sensors_gz.html`
  - *Description*: Configuring GPU Lidar (`gpu_lidar`), IMU (`imu`), and Depth Camera sensors in Gazebo Sim.

## 3. Sensor & Motion Plugins Reference (SDF)

### A. Differential Drive Motion Plugin
```xml
<plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
  <left_joint>left_wheel_joint</left_joint>
  <right_joint>right_wheel_joint</right_joint>
  <wheel_separation>0.3</wheel_separation>
  <wheel_radius>0.05</wheel_radius>
  <odom_publish_frequency>50</odom_publish_frequency>
  <topic>/cmd_vel</topic>
  <odom_topic>/odom</odom_topic>
  <frame_id>odom</frame_id>
  <child_frame_id>base_link</child_frame_id>
</plugin>
```

### B. GPU LiDAR Sensor Plugin
```xml
<sensor name="gpu_lidar" type="gpu_lidar">
  <update_rate>10</update_rate>
  <topic>/scan</topic>
  <lidar>
    <scan>
      <horizontal>
        <samples>360</samples>
        <resolution>1</resolution>
        <min_angle>-3.14159</min_angle>
        <max_angle>3.14159</max_angle>
      </horizontal>
    </scan>
    <range>
      <min>0.15</min>
      <max>12.0</max>
    </range>
  </lidar>
  <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
    <render_engine>ogre2</render_engine>
  </plugin>
</sensor>
```

## 4. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Robot spawns then falls through the ground | Missing `<collision>` on links, or zero/invalid `<inertial>` | Add collision geometry; give every non-fixed link real mass and inertia |
| `/cmd_vel` published but robot doesn't move in sim | Bridge direction wrong (`[` is GZ->ROS, `]` is ROS->GZ, `@` bidirectional) or plugin `<topic>` mismatch | Check bridge arg direction char; `gz topic -l` to see what the plugin actually subscribes to |
| LiDAR/camera topic exists but publishes nothing | `gz-sim-sensors-system` plugin missing from the world SDF (rendering sensors need it) | Add `<plugin filename="gz-sim-sensors-system">` with `render_engine` to the world |
| IMU topic silent in sim | `gz-sim-imu-system` world plugin missing | Add the IMU system plugin to the world SDF |
| TF extrapolation errors as soon as sim starts | `/clock` not bridged, or nodes missing `use_sim_time: true` | Bridge `/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock`; set `use_sim_time` on every node |
| Sensor data arrives in an unknown/prefixed frame | Gazebo composes frame as `<model>/<link>/<sensor>` while URDF expects the bare link name | Set explicit `<gz_frame_id>`/frame remapping, or align `frame_id` with the URDF link |
| Sim odometry perfect but Nav2 behaves differently on the real robot | Sim plugin uses ideal kinematics; real `wheel_radius`/friction differ | Never tune Nav2 solely in sim; re-verify on hardware with `scripts/check_odom_direction.py` |

## 5. Local System Verification
Check installed Gazebo & ROS 2 bridge packages locally:
- Run `ros2 pkg prefix ros_gz_bridge` to inspect bridge dependencies.
- Run `gz sim --version` in terminal to confirm active Gazebo Harmonic or Fortress version.
