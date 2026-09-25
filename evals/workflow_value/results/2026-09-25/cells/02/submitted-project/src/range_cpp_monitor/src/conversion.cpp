#include "range_cpp_monitor/conversion.hpp"

#include <limits>

namespace range_cpp_monitor
{

double normalize(const range_interfaces::msg::RangeReading & msg)
{
  if (!msg.valid) {
    return std::numeric_limits<double>::quiet_NaN();
  }
  return msg.distance_m;
}

}  // namespace range_cpp_monitor
