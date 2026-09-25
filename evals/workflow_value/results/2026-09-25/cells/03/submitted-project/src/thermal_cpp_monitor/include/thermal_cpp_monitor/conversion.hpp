#ifndef THERMAL_CPP_MONITOR__CONVERSION_HPP_
#define THERMAL_CPP_MONITOR__CONVERSION_HPP_

#include "thermal_interfaces/msg/thermal_reading.hpp"

namespace thermal_cpp_monitor
{

/// Public conversion helper: the temperature in degrees Celsius, or NaN if the reading is invalid.
double normalize(const thermal_interfaces::msg::ThermalReading & msg);

}  // namespace thermal_cpp_monitor

#endif  // THERMAL_CPP_MONITOR__CONVERSION_HPP_
