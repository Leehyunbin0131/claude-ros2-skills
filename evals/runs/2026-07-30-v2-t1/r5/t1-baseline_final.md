# Run summary — `t1-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 7
- total_cost_usd: 0.2880366999999999
- tool calls: **6**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t1-baseline-mIl8 2>/dev/null | head -50
2. `ToolSearch`
3. `WebSearch`
4. `WebSearch`
5. `ToolSearch`
6. `WebFetch` — https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html

## Final message

Two Jazzy-specific gotchas combine to produce exactly this symptom (silent no-op, no errors):

**1. The message type changed.** As of Jazzy, `diff_drive_controller` subscribes on `~/cmd_vel` using **`geometry_msgs/msg/TwistStamped`**, not the old `geometry_msgs/msg/Twist`. If you're publishing plain `Twist` (old habit from Humble/Foxy tutorials), `ros2 topic pub` will happily "succeed" since it doesn't check for a matching subscriber type — the message just never gets delivered because the types don't match. No error, no motion.

**2. `cmd_vel_timeout` defaults to 0.5s.** Even with the right type, if you publish a single message (`ros2 topic pub -1 ...`) instead of a stream, the controller treats the command as stale after 0.5s and zeroes velocity, so a one-shot publish effectively does nothing.

**Verify first:**
```bash
ros2 topic info /cmd_vel -v          # confirm actual type expected + that a subscriber exists
ros2 control list_controllers        # confirm diff_drive_controller is active
```
If `/cmd_vel` doesn't show up at all, the controller's `~/cmd_vel` hasn't been remapped to that global name in your launch file — check your controller launch/params for a remap.

**Command that will actually move it** (continuous stream, correct type):
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
  "{twist: {linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
```
`-r 10` keeps it under the 0.5s timeout. Ctrl+C stops publishing and the robot will halt automatically once the timeout elapses.

For interactive driving instead, `teleop_twist_keyboard` still publishes plain `Twist` by default — pipe it through `twist_stamper` to convert, or set `enable_stamped_cmd_vel: false` / your controller's equivalent legacy param if you'd rather keep using unstamped `Twist` everywhere (check your specific `diff_drive_controller` YAML — this option exists on some distros/builds but was fixed to stamped-only in vanilla Jazzy per the docs above).

Sources:
- [diff_drive_controller — ROS2_Control: Jazzy](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)
- [Jazzy to Kilted — Nav2 migration notes on stamped cmd_vel](https://docs.nav2.org/migration/Jazzy.html)
- [twist_stamper](https://github.com/joshnewans/twist_stamper)
