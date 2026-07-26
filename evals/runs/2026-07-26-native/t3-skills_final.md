# Run summary — `t3-skills_result.jsonl`

- model: `claude-haiku-4-5-20251001`
- turns: 3
- total_cost_usd: 0.027091800000000003
- tool calls: **1**

## Tool calls, in order

1. `Skill` — ros2-core

## Final message

This is almost always a **QoS mismatch**. The publisher and subscriber have incompatible Quality of Service settings, so they can't connect even though both see the same topic.

Most common: the **publisher is using `SensorDataQoS`** (BestEffort, Volatile), but your subscriber is using the default `SystemDefaultsQoS` (Reliable, Transient Local). They're incompatible — messages never flow.

To diagnose, run:
```bash
ros2 topic info /camera/image_raw -v
```

That shows the actual QoS settings of the publisher. Then share your subscription code so I can verify it matches.

The fix (if it's QoS): add the same QoS profile to your subscriber. For a camera, that's usually:

**C++:**
```cpp
auto sub = node->create_subscription<sensor_msgs::msg::Image>(
  "/camera/image_raw",
  rclcpp::SensorDataQoS(),  // Match the publisher
  callback);
```

**Python:**
```python
self.subscription = self.create_subscription(
    Image,
    '/camera/image_raw',
    self.callback,
    qos_profile=QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=1))
```

Can you share the `create_subscription` call from your code and the output of `ros2 topic info /camera/image_raw -v`?
