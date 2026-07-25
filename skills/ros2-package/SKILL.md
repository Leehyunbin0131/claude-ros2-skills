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

Created: `ament_cmake` → `CMakeLists.txt`, `package.xml`, `src/`, `include/my_package/`.
`ament_python` → `setup.py`, `setup.cfg`, `package.xml`, `resource/my_package`, `my_package/`.

Never hand-roll this layout — `resource/<pkg>` and the ament index registration are
easy to omit and the package then silently fails to be discovered.

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

The `lib/${PROJECT_NAME}` destination is not a convention you may vary — the ament
guide states it "must be followed exactly for the rest of the ROS tooling to find it."
`target_link_libraries` with namespaced targets (`Eigen3::Eigen`) is the accepted
alternative to `ament_target_dependencies`.

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

A Python node with no `console_scripts` line builds cleanly and is invisible to `ros2 run`.

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

`--symlink-install` links Python sources and installed data instead of copying, so
edits take effect without rebuilding. C++ still needs a rebuild.

## 6. Symptom -> Root Cause -> Action

| Symptom | Likely root cause | Action |
| :--- | :--- | :--- |
| Build succeeds, `ros2 run <pkg> <exe>` says no executable found | `install(TARGETS ...)` missing, or DESTINATION isn't `lib/${PROJECT_NAME}` | Add/fix the install rule; confirm the binary landed in `install/<pkg>/lib/<pkg>/` |
| Same, but package is `ament_python` | No matching `console_scripts` entry in `setup.py` | Add `'<exe> = <pkg>.<module>:main'`; rebuild (entry points are generated at install time) |
| `ros2 launch` reports the launch file doesn't exist, though it's in the source tree | `launch/` never installed | ament_cmake: `install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})`; ament_python: add it to `data_files` |
| Edited a Python node, behavior unchanged | Built without `--symlink-install`, so `ros2 run` executes the stale installed copy | Rebuild with `--symlink-install`, then re-source |
| `colcon build` doesn't see the package at all | Not under the workspace `src/`, or `package.xml` missing/malformed | Check location; `colcon list` shows what colcon actually discovers |
| Package builds but `ros2 pkg list` omits it; imports fail | Shell was sourced before the build, or overlay never sourced | `source install/setup.bash` again in that shell |
| Custom message: `ModuleNotFoundError` / no type support at runtime | Interfaces declared in an `ament_python` package, or `member_of_group` tag missing | Move interfaces to a dedicated `ament_cmake` package with all three package.xml tags |
| C++ link fails: undefined reference to `rclcpp::...` | `find_package` present but the target never linked | Add `ament_target_dependencies(<target> rclcpp ...)` for every dependency used |
| A dependent package can't find your headers | `include/` not installed / target not exported | `install(DIRECTORY include/ DESTINATION include/${PROJECT_NAME})` plus the export calls in the ament_cmake guide |

## 7. Strict Rules
1. Declare every dependency in `package.xml` — a build that works only because a
   sibling package happened to pull the dependency in will break on a clean machine.
2. One concern per package; keep interfaces in their own `ament_cmake` package.
3. After adding any new file, directory, or entry point: rebuild **and** re-source
   before concluding something is broken.
