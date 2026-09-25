#include "power_cpp_monitor/conversion.hpp"

#include <limits>

namespace power_cpp_monitor
{

double normalize(const power_interfaces::msg::PowerReading & msg)
{
  if (!msg.valid) {
    return std::numeric_limits<double>::quiet_NaN();
  }
  return msg.power_w;
}

}  // namespace power_cpp_monitor
