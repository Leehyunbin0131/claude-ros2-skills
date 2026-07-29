# Run summary — `t1-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.1076155
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t1-baseline-92xz 2>/dev/null | head -50

## Final message

This is a classic `ros2_control` gotcha, not a wiring/hardware issue. Two things commonly cause exactly this symptom (publish succeeds, no errors, wheels don't move):

**1. Topic name mismatch.** `diff_drive_controller` subscribes on a topic relative to its own controller node, not on the global `/cmd_vel`. Unless your controller launch/yaml remaps it, the actual subscription is something like `/diff_drive_controller/cmd_vel` (or `/<your_controller_name>/cmd_vel`). Publishing to bare `/cmd_vel` just sends messages into a topic with zero subscribers — DDS doesn't error on that, it just drops them.

**2. Message type mismatch.** In current `ros2_controllers` (Jazzy included), `diff_drive_controller` defaults `use_stamped_vel` to `true`, meaning it expects `geometry_msgs/msg/TwistStamped`, not plain `Twist`. If you're publishing `Twist`, it won't match the subscription type either — same silent-drop symptom.

**Diagnose first:**

```bash
ros2 control list_controllers
ros2 topic info /cmd_vel -v          # check "Subscription count" — 0 confirms nobody's listening here
ros2 node info /diff_drive_controller # find the controller's real subscribed topic + type
ros2 param get /diff_drive_controller use_stamped_vel
```

If `ros2 topic info /cmd_vel -v` shows 0 subscribers, that confirms cause #1.

**Command that actually moves it** (adjust controller name/topic to what `ros2 node info` showed you):

```bash
ros2 topic pub /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped \
"{header: {stamp: {sec: 0, nanosec: 0}, frame_id: ''}, twist: {linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}" -r 10
```

Note `-r 10`: also check `cmd_vel_timeout` (default 0.5s) — a single one-shot publish will be accepted then immediately zeroed out, looking like "nothing happened." Publishing at a steady rate rules that out too.

If you want `/cmd_vel` (plain `Twist`) to work like older tutorials show, set `use_stamped_vel: false` in your controller's yaml and remap `~/cmd_vel` to `/cmd_vel` in the controller_manager launch file, then reload the controller.
