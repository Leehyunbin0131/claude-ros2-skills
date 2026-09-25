#include <gtest/gtest.h>

#include <cmath>

#include "thermal_cpp_monitor/conversion.hpp"

TEST(Conversion, ValidReadingReturnsDegreesCelsius)
{
  thermal_interfaces::msg::ThermalReading msg;
  msg.temperature_c = 21.5;
  msg.valid = true;
  EXPECT_DOUBLE_EQ(thermal_cpp_monitor::normalize(msg), 21.5);
}

TEST(Conversion, InvalidReadingReturnsNaN)
{
  thermal_interfaces::msg::ThermalReading msg;
  msg.temperature_c = 21.5;
  msg.valid = false;
  EXPECT_TRUE(std::isnan(thermal_cpp_monitor::normalize(msg)));
}

TEST(Conversion, DefaultReadingIsInvalid)
{
  thermal_interfaces::msg::ThermalReading msg;
  EXPECT_TRUE(std::isnan(thermal_cpp_monitor::normalize(msg)));
}
