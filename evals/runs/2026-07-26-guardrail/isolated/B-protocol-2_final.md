# Run summary — `B-protocol-2_result.jsonl`

- model: `claude-haiku-4-5-20251001`
- turns: 3
- total_cost_usd: 0.026044799999999996
- tool calls: **1**

## Tool calls, in order

1. `Skill` — ros2-perception

## Final message

The most common cause: **QoS mismatch**. Camera drivers publish with `BestEffort` reliability, but subscribers often default to `Reliable`—they won't connect.

Before I see your code, a few quick checks:

1. **What language?** (C++ / Python)
2. **What camera driver?** (usb_cam, realsense, built-in, custom?)
3. **Verify QoS incompatibility** — run this now:
   ```bash
   ros2 topic info /camera/image_raw -v
   ```
   Look for the `Reliability` field on both publisher and subscriber sides. If they differ, that's your problem.

If the publisher shows `Reliability: BEST_EFFORT` but your subscriber is `RELIABLE`, you need to subscribe with `SensorDataQoS()` (C++) or `QoSProfile(...)` with `reliability=QoSReliabilityPolicy.BEST_EFFORT` (Python).

**Show me:**
- The output of `ros2 topic info /camera/image_raw -v`
- Your subscriber code (the callback registration line)
- Confirmation that you have a spinner/executor running (e.g., `rclcpp::spin()` or `executor.spin()`)

That will pinpoint it.
