# Run summary — `t3-skills_result.jsonl`

- model: `claude-haiku-4-5-20251001`
- turns: 3
- total_cost_usd: 0.028471299999999998
- tool calls: **1**

## Tool calls, in order

1. `Skill` — ros2-core

## Final message

This is almost always a **QoS mismatch**. The topic exists and is publishing, but your subscriber's QoS profile is incompatible with the publisher's.

Check the actual QoS right now:

```bash
ros2 topic info /camera/image_raw -v
```

Look at the `QoS values` row. If the publisher is **BestEffort** but your subscriber code uses the default (RELIABLE), they won't connect — even though both are running.

**Before you fix it, answer:**
1. Are you using C++ (`rclcpp`) or Python (`rclpy`)?
2. What does the `-v` output show for the publisher's Reliability and Durability?
3. In your subscriber code, are you passing any QoS argument, or using the default?

**Most likely fix:** Camera/image topics should use sensor QoS:

**C++:**
```cpp
subscription_ = create_subscription<sensor_msgs::msg::Image>(
  "/camera/image_raw",
  rclcpp::SensorDataQoS(),  // ← This one
  [this](const sensor_msgs::msg::Image::SharedPtr msg) { ... }
);
```

**Python:**
```python
self.subscription = self.create_subscription(
    Image,
    '/camera/image_raw',
    self.callback,
    qos_profile=rclpy.qos.qos_profile_sensor_data  # ← This one
)
```

Run `ros2 topic info /camera/image_raw -v` and paste the output — that will confirm the mismatch.
