---
name: ros2-package
description: "Package & build wiring: ros2 pkg create, package.xml, ament_cmake CMakeLists, ament_python setup.py, colcon build/source, installing launch & config, custom .msg/.srv interface packages."
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

## 2. Scaffolding

```bash
ros2 pkg create --build-type ament_cmake  --license Apache-2.0 --node-name my_node my_package
ros2 pkg create --build-type ament_python --license Apache-2.0 --node-name my_node my_package
```

## 3. The Wiring That Makes a Node Runnable

### ament_cmake
```cmake
find_package(rclcpp REQUIRED)

add_executable(my_node src/my_node.cpp)
ament_target_dependencies(my_node rclcpp)      # links deps AND their headers

install(TARGETS my_node
  DESTINATION lib/${PROJECT_NAME})             # exact path — ros2 run looks only here

install(DIRECTORY launch params
  DESTINATION share/${PROJECT_NAME})           # launch/config are NOT installed by default

ament_package()                                # last call, exactly once per package
```

### ament_python
```python
data_files=[
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    # add launch/config explicitly, e.g.:
    # (os.path.join('share', package_name, 'launch'), glob('launch/*launch.py')),
],
entry_points={
    'console_scripts': [
        'my_node = my_package.my_node:main',   # <exe name> = <module path>:<function>
    ],
},
```

`package.xml` also needs `<export><build_type>ament_python</build_type></export>` —
without it colcon tries to configure the package as `ament_cmake` and fails looking
for a `CMakeLists.txt` that was never meant to exist. Verify against any installed
pure-Python package's `package.xml` under `/opt/ros/jazzy/share/`.

`setup.cfg` needs the ROS-specific install location, not just `[metadata]`:
```ini
[develop]
script_dir=$base/lib/my_package
[install]
install_scripts=$base/lib/my_package
```
Without it, `console_scripts` still builds and installs, just not to
`lib/${PROJECT_NAME}` — the same place `ros2 run` looks for `ament_cmake`
executables — so the node is present but undiscoverable.

## 4. Custom Interfaces (`.msg` / `.srv`)

Interfaces require an **`ament_cmake`** package — they cannot live in an `ament_python`
package. Standard practice is a dedicated `<project>_interfaces` package that your
node packages depend on.

```cmake
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}     # first arg must start with the package name
  "msg/Num.msg"
  "srv/AddThreeInts.srv"
  DEPENDENCIES geometry_msgs
)
```
```xml
<buildtool_depend>rosidl_default_generators</buildtool_depend>
<exec_depend>rosidl_default_runtime</exec_depend>
<member_of_group>rosidl_interface_packages</member_of_group>
```

Verify the result with `ros2 interface show my_pkg/msg/Num` — if that fails, the
generation never ran.

## 5. Build & Source Loop

```bash
colcon build --symlink-install --packages-select my_package
source install/setup.bash        # every new shell, and after adding any new file
```

## 6. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| `ros2 launch` reports the launch file doesn't exist, though it's in the source tree | `launch/` never installed | ament_cmake: `install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})`; ament_python: add it to `data_files` |

## 7. Strict Rules
After adding any new file, directory, or entry point: rebuild **and** re-source
before concluding something is broken.
