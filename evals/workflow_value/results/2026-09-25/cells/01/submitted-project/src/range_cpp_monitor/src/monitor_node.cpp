#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64.hpp"
#include "range_cpp_monitor/conversion.hpp"

class Monitor : public rclcpp::Node
{
public:
  Monitor()
  : Node("range_cpp_monitor")
  {
    publisher_ = create_publisher<std_msgs::msg::Float64>("monitor/cpp_range_m", 10);
    subscription_ = create_subscription<range_interfaces::msg::RangeReading>(
      "sensor/range", 10,
      [this](const range_interfaces::msg::RangeReading & msg) {
        std_msgs::msg::Float64 out;
        out.data = range_cpp_monitor::normalize(msg);
        publisher_->publish(out);
      });
  }

private:
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
  rclcpp::Subscription<range_interfaces::msg::RangeReading>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Monitor>());
  rclcpp::shutdown();
  return 0;
}
