#ifndef POWER_CPP_MONITOR__CONVERSION_HPP_
#define POWER_CPP_MONITOR__CONVERSION_HPP_

#include "power_interfaces/msg/power_reading.hpp"

namespace power_cpp_monitor
{

/// Public conversion helper: the power in watts, or NaN if the reading is not valid.
double normalize(const power_interfaces::msg::PowerReading & msg);

}  // namespace power_cpp_monitor

#endif  // POWER_CPP_MONITOR__CONVERSION_HPP_
