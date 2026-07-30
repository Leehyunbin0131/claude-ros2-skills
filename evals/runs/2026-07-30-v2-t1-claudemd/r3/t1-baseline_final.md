# Run summary — `t1-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.12222109999999999
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t1-baseline-fPJf 2>/dev/null | head -50

## Final message

Since you've already confirmed the controller is `active` and interfaces are claimed, this is almost certainly a **message type mismatch**, not a lifecycle/hardware issue.

## Root cause

Starting with Iron and carried into Jazzy, `diff_drive_controller` changed its default `use_stamped_vel` parameter to `true`. That means the controller's `/cmd_vel` subscription is typed as `geometry_msgs/msg/TwistStamped`, **not** plain `geometry_msgs/msg/Twist` (which is what Humble-era tutorials and most muscle-memory `ros2 topic pub` commands still use).

If you publish a `Twist` on `/cmd_vel`, ROS 2 doesn't throw an error — DDS just never matches your publisher to the controller's subscriber because the type names differ. You get a topic that exists, with a publisher, and zero errors, and the controller simply never receives anything. That matches your symptom exactly.

## Confirm it

```bash
ros2 topic info /cmd_vel -v
```

Look at the subscription entry for the controller node — if it says `geometry_msgs/msg/TwistStamped`, that's the mismatch.

## Command that will actually move it

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/TwistStamped "{header: {stamp: {sec: 0, nanosec: 0}, frame_id: ''}, twist: {linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}" -r 10
```

Two things baked into that command matter:
- **`TwistStamped`, not `Twist`** — fixes the type mismatch.
- **`-r 10`** (repeat) — `diff_drive_controller` has a `cmd_vel_timeout` (default 0.5 s) that zeros the command velocity if nothing new arrives in time. A one-shot `pub` will make the wheels twitch for a fraction of a second and then stop, which can look like "nothing happened" too.

If you want to go back to plain `Twist` instead of patching every publisher, set `use_stamped_vel: false` in your controller's YAML config and restart the controller — but note that's deprecated and may be removed in a future release, so `TwistStamped` is the more future-proof fix.

If after this the wheels *still* don't move, the next things to check are: whether `/cmd_vel` is actually remapped to the controller's namespaced topic (e.g. `/diff_drive_controller/cmd_vel`) in your launch file rather than global `/cmd_vel`, and whether a safety/twist-mux node is sitting between you and the controller and swallowing the command.
