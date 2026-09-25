#include <gtest/gtest.h>

#include <cmath>

#include "range_cpp_monitor/conversion.hpp"

TEST(Conversion, ValidReadingReturnsMetres)
{
  range_interfaces::msg::RangeReading msg;
  msg.distance_m = 2.5;
  msg.valid = true;
  EXPECT_DOUBLE_EQ(range_cpp_monitor::normalize(msg), 2.5);
}

TEST(Conversion, InvalidReadingReturnsNan)
{
  range_interfaces::msg::RangeReading msg;
  msg.distance_m = 2.5;
  msg.valid = false;
  EXPECT_TRUE(std::isnan(range_cpp_monitor::normalize(msg)));
}
