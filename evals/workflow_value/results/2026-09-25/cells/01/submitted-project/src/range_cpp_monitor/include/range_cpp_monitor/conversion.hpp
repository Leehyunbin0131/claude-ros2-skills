#ifndef RANGE_CPP_MONITOR__CONVERSION_HPP_
#define RANGE_CPP_MONITOR__CONVERSION_HPP_

#include "range_interfaces/msg/range_reading.hpp"

namespace range_cpp_monitor
{

/// Public conversion helper: the distance in metres, or NaN if the reading is not valid.
double normalize(const range_interfaces::msg::RangeReading & msg);

}  // namespace range_cpp_monitor

#endif  // RANGE_CPP_MONITOR__CONVERSION_HPP_
