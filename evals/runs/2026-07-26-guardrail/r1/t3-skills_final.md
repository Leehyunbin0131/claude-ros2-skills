# Run summary — `t3-skills_result.jsonl`

- model: `claude-haiku-4-5-20251001`
- turns: 3
- total_cost_usd: 0.028255600000000002
- tool calls: **1**

## Tool calls, in order

1. `Skill` — ros2-core

## Final message

This is **QoS mismatch** — the most common cause. `ros2 topic hz` succeeds because it auto-adapts to the publisher's QoS, but your subscriber uses incompatible settings.

**Diagnose it immediately:**
```bash
ros2 topic info /camera/image_raw -v
```

This shows the actual publisher QoS. Likely it's `Reliability: BEST_EFFORT` (camera drivers typically use `SensorDataQoS`), but your subscriber defaults to `RELIABLE` — they can't talk.

**Show me your subscriber code** so I can verify, but the fix is almost certainly:

**C++:**
```cpp
rclcpp::SensorDataQoS()
```

**Python:**
```python
from rclpy.qos import qos_profile_sensor_data
```

Add that as the QoS argument when you create the subscription. What language is your subscriber, and can you share the creation code?
