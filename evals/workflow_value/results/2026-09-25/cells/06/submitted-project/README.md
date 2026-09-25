# Power monitor workspace

ROS 2 Jazzy workspace. All packages are under `src/`.

| Package | Build type | Purpose |
| :--- | :--- | :--- |
| `power_interfaces` | ament_cmake (rosidl) | `PowerReading` message |
| `power_py_monitor` | ament_python | `ros2 run power_py_monitor monitor` subscribes to `/sensor/power` and publishes `std_msgs/msg/Float64` on `/monitor/py_power_w` |
| `power_cpp_monitor` | ament_cmake | `ros2 run power_cpp_monitor monitor` subscribes to `/sensor/power` and publishes `std_msgs/msg/Float64` on `/monitor/cpp_power_w` |

Both nodes publish the power computed by their package's public
conversion helper. Downstream tools call these helpers directly:

- Python: `power_py_monitor.conversion.normalize(msg) -> float`, defined in
  `src/power_py_monitor/power_py_monitor/conversion.py`.
- C++: `double power_cpp_monitor::normalize(const power_interfaces::msg::PowerReading & msg)`, declared in
  `src/power_cpp_monitor/include/power_cpp_monitor/conversion.hpp` and defined in `src/power_cpp_monitor/src/conversion.cpp`.
