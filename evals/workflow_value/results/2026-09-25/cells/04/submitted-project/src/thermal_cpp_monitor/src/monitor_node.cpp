#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64.hpp"
#include "thermal_cpp_monitor/conversion.hpp"

class Monitor : public rclcpp::Node
{
public:
  Monitor()
  : Node("thermal_cpp_monitor")
  {
    publisher_ = create_publisher<std_msgs::msg::Float64>("monitor/cpp_temperature_c", 10);
    subscription_ = create_subscription<thermal_interfaces::msg::ThermalReading>(
      "sensor/thermal", 10,
      [this](const thermal_interfaces::msg::ThermalReading & msg) {
        std_msgs::msg::Float64 out;
        out.data = thermal_cpp_monitor::normalize(msg);
        publisher_->publish(out);
      });
  }

private:
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
  rclcpp::Subscription<thermal_interfaces::msg::ThermalReading>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Monitor>());
  rclcpp::shutdown();
  return 0;
}
