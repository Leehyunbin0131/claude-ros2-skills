---
name: ros2-package
description: "Package & build wiring: ros2 pkg create, package.xml, ament_cmake CMakeLists, colcon build/source, installing launch & config."
---

# ROS 2 Package Creation & Build Wiring (Ubuntu 24.04 LTS & ROS 2 Jazzy)

Most "it built fine but doesn't run" bugs are wiring, not code. This skill covers
the seams between a source file and a runnable node.

## 1. Documentation Entry Points

| For | Entry point |
| :--- | :--- |
| ament_cmake reference (install, exports, testing hooks) | `https://docs.ros.org/en/jazzy/How-To-Guides/Ament-CMake-Documentation.html` |
| Package creation, custom interfaces, colcon tutorials | `https://docs.ros.org/en/jazzy/Tutorials/` |

Ground truth beats both: read a working installed package under
`/opt/ros/jazzy/share/<pkg>/` and copy its structure.

## 2. The Wiring That Makes a Node Runnable

**`ament_cmake`**: executables must install to `lib/${PROJECT_NAME}` exactly —
that is the only place `ros2 run` looks. `launch/` and `params/` are not
installed by default and need their own `install(DIRECTORY ...)` into
`share/${PROJECT_NAME}`. `ament_package()` comes last, exactly once.

## 3. Strict Rules
After adding any new file, directory, or entry point: rebuild **and** re-source
before concluding something is broken.
