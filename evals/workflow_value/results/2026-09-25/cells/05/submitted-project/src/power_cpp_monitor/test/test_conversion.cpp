#include <gtest/gtest.h>

#include <cmath>

#include "power_cpp_monitor/conversion.hpp"

TEST(Conversion, ReturnsWattsWhenValid)
{
  power_interfaces::msg::PowerReading msg;
  msg.power_w = 12.5;
  msg.valid = true;
  EXPECT_DOUBLE_EQ(power_cpp_monitor::normalize(msg), 12.5);
}

TEST(Conversion, ReturnsNanWhenInvalid)
{
  power_interfaces::msg::PowerReading msg;
  msg.power_w = 12.5;
  msg.valid = false;
  EXPECT_TRUE(std::isnan(power_cpp_monitor::normalize(msg)));
}
