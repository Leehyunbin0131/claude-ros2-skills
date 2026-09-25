# Thermal monitor workspace

ROS 2 Jazzy workspace. All packages are under `src/`.

| Package | Build type | Purpose |
| :--- | :--- | :--- |
| `thermal_interfaces` | ament_cmake (rosidl) | `ThermalReading` message |
| `thermal_py_monitor` | ament_python | `ros2 run thermal_py_monitor monitor` subscribes to `/sensor/thermal` and publishes `std_msgs/msg/Float64` on `/monitor/py_temperature_c` |
| `thermal_cpp_monitor` | ament_cmake | `ros2 run thermal_cpp_monitor monitor` subscribes to `/sensor/thermal` and publishes `std_msgs/msg/Float64` on `/monitor/cpp_temperature_c` |

Both nodes publish the temperature computed by their package's public
conversion helper. Downstream tools call these helpers directly:

- Python: `thermal_py_monitor.conversion.normalize(msg) -> float`, defined in
  `src/thermal_py_monitor/thermal_py_monitor/conversion.py`.
- C++: `double thermal_cpp_monitor::normalize(const thermal_interfaces::msg::ThermalReading & msg)`, declared in
  `src/thermal_cpp_monitor/include/thermal_cpp_monitor/conversion.hpp` and defined in `src/thermal_cpp_monitor/src/conversion.cpp`.
