#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64.hpp"
#include "power_cpp_monitor/conversion.hpp"

class Monitor : public rclcpp::Node
{
public:
  Monitor()
  : Node("power_cpp_monitor")
  {
    publisher_ = create_publisher<std_msgs::msg::Float64>("monitor/cpp_power_w", 10);
    subscription_ = create_subscription<power_interfaces::msg::PowerReading>(
      "sensor/power", 10,
      [this](const power_interfaces::msg::PowerReading & msg) {
        std_msgs::msg::Float64 out;
        out.data = power_cpp_monitor::normalize(msg);
        publisher_->publish(out);
      });
  }

private:
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
  rclcpp::Subscription<power_interfaces::msg::PowerReading>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Monitor>());
  rclcpp::shutdown();
  return 0;
}
