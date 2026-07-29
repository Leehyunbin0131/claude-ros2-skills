# Run summary — `t1-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.1406281
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t1-baseline-DAkf 2>/dev/null | head -50

## Final message

This is a known Jazzy gotcha, not a config bug in your setup. Here's what's happening and how to confirm it.

## Root cause
Starting with the ros2_controllers release that ships in Jazzy, `diff_drive_controller` defaults to subscribing on `/cmd_vel` as **`geometry_msgs/msg/TwistStamped`**, not plain `Twist` (controlled by the `use_stamped_vel` param, which now defaults to `true`). If you're publishing plain `Twist` (e.g. via `teleop_twist_keyboard`, an old script, or a manual `ros2 topic pub geometry_msgs/msg/Twist ...`), the message type doesn't match the subscriber's type. ROS 2 topics require matching types to connect — DDS discovery simply never links the two endpoints. No exception, no log line, nothing: your publisher exists, the controller's subscriber exists, they just never talk to each other. That matches your symptoms exactly (active controller, claimed interfaces, dead silence).

## Confirm it
```bash
ros2 topic info /cmd_vel --verbose
```
Look at the subscription entry's `Type:` field — if it says `geometry_msgs/msg/TwistStamped`, that's your answer. Also check:
```bash
ros2 param get /<your_diff_drive_controller_name> use_stamped_vel
```

## Command that will actually move it
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
  "{twist: {linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
```
Use `-r 10` (repeat) rather than `--once` — `diff_drive_controller` has a `cmd_vel_timeout` (default 0.5s) that zeros the command if no new message arrives in time, so a single message will only twitch the wheels briefly.

## If you'd rather keep plain Twist
Set `use_stamped_vel: false` in your controller's YAML config and restart/reload the controller (this param isn't dynamically reconfigurable at runtime in most versions):
```yaml
diff_drive_controller:
  ros__parameters:
    use_stamped_vel: false
```
Then your existing `Twist`-publishing tools (teleop_twist_keyboard, joy_teleop, old scripts) will work again unchanged.
