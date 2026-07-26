# Run summary — `t3-skills_result.jsonl`

- model: `claude-haiku-4-5-20251001`
- turns: 3
- total_cost_usd: 0.0264868
- tool calls: **1**

## Tool calls, in order

1. `Skill` — ros2-perception

## Final message

This is almost certainly a **QoS mismatch**. Camera drivers publish with `BestEffort` QoS, but subscriber defaults to `Reliable` — they won't connect.

Verify with:
```bash
ros2 topic info /camera/image_raw -v
```

Look for the publisher's QoS. If it says `Best Effort`, that's your issue.

**Fix:** Subscribe with `SensorDataQoS()` instead of the default:

**C++:**
```cpp
auto sub = this->create_subscription<sensor_msgs::msg::Image>(
  "/camera/image_raw",
  rclcpp::SensorDataQoS(),  // ← Add this
  std::bind(&MyNode::image_callback, this, std::placeholders::_1)
);
```

**Python:**
```python
self.subscription = self.create_subscription(
    Image,
    '/camera/image_raw',
    self.image_callback,
    qos_profile=rclcpp.qos.QoSProfile(
        reliability=rclcpp.qos.ReliabilityPolicy.BEST_EFFORT,
        history=rclcpp.qos.HistoryPolicy.KEEP_LAST,
        depth=1
    )
)
```

After changing, rebuild and restart the node. The callback should fire immediately. If it still doesn't work, paste the output of `ros2 topic info -v` and your subscriber code.
