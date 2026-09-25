#include "thermal_cpp_monitor/conversion.hpp"

#include <limits>

namespace thermal_cpp_monitor
{

double normalize(const thermal_interfaces::msg::ThermalReading & msg)
{
  if (!msg.valid) {
    return std::numeric_limits<double>::quiet_NaN();
  }
  return msg.temperature_c;
}

}  // namespace thermal_cpp_monitor
