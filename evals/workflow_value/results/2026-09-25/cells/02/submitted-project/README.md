# Range monitor workspace

ROS 2 Jazzy workspace. All packages are under `src/`.

| Package | Build type | Purpose |
| :--- | :--- | :--- |
| `range_interfaces` | ament_cmake (rosidl) | `RangeReading` message |
| `range_py_monitor` | ament_python | `ros2 run range_py_monitor monitor` subscribes to `/sensor/range` and publishes `std_msgs/msg/Float64` on `/monitor/py_range_m` |
| `range_cpp_monitor` | ament_cmake | `ros2 run range_cpp_monitor monitor` subscribes to `/sensor/range` and publishes `std_msgs/msg/Float64` on `/monitor/cpp_range_m` |

Both nodes publish the distance computed by their package's public
conversion helper. Downstream tools call these helpers directly:

- Python: `range_py_monitor.conversion.normalize(msg) -> float`, defined in
  `src/range_py_monitor/range_py_monitor/conversion.py`.
- C++: `double range_cpp_monitor::normalize(const range_interfaces::msg::RangeReading & msg)`, declared in
  `src/range_cpp_monitor/include/range_cpp_monitor/conversion.hpp` and defined in `src/range_cpp_monitor/src/conversion.cpp`.
