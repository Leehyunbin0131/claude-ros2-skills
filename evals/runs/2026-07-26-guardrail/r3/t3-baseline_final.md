# Run summary — `t3-baseline_result.jsonl`

- model: `claude-haiku-4-5-20251001`
- turns: 1
- total_cost_usd: 0.019207099999999998
- tool calls: **0**

## Tool calls, in order

_none — the agent answered without consulting anything._

## Final message

This is almost always a **QoS (Quality of Service) mismatch** or **not spinning the executor**. Here are the most common causes:

**1. QoS mismatch (most common)**
Camera publishers typically use `SENSOR_DATA` QoS (volatile, best-effort). If your subscriber uses the default `DEFAULT` QoS (transient_local, reliable), they won't connect.

```cpp
// Subscribe with matching QoS
auto qos_profile = rclcpp::SensorDataQoS();  // or rclcpp::QoS(10).best_effort()
subscription_ = node_->create_subscription<sensor_msgs::msg::Image>(
    "/camera/image_raw", 
    qos_profile,  // Add this!
    [this](const sensor_msgs::msg::Image::SharedPtr msg) { /* ... */ });
```

Check what the publisher uses: `ros2 topic info /camera/image_raw -v` and match it.

**2. Not spinning the executor**
Your callback won't fire unless you spin:

```cpp
rclcpp::spin(node_);  // Required! This runs the event loop
```

Or if using an executor:
```cpp
rclcpp::executors::SingleThreadedExecutor executor;
executor.add_node(node_);
executor.spin();  // This invokes callbacks
```

**3. Quick diagnostics**
- Post your subscriber code (especially QoS settings and the spin call)
- Run: `ros2 topic info /camera/image_raw -v` to see publisher QoS
- Check if your node is actually blocking on `spin()` or exits immediately

Which of these sounds most likely?
