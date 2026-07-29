# Run summary — `t1-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.1278601
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t1-baseline-VIOx 2>/dev/null && echo "---" && find /tmp/eval-t1-baseline-VIOx -iname "*.yaml" -o -iname "*controller*" -o -iname "*.urdf*" -o -

## Final message

This is almost certainly one of two silent-failure modes with `diff_drive_controller` — both produce exactly your symptom (no error, no motion) because a DDS topic name/type mismatch just fails discovery silently instead of throwing.

**Cause 1 (most common in Iron/Jazzy): message type mismatch.**
Since Iron, `diff_drive_controller` has a `use_stamped_vel` parameter that defaults to `true`. When true, the controller subscribes on `/cmd_vel` as `geometry_msgs/msg/TwistStamped`, not the plain `Twist` most tutorials/muscle-memory use. If you publish `Twist` on the same topic name, ROS 2 creates a publisher with a different type — DDS won't match it to the subscriber, so nothing is ever received, and nothing errors.

**Cause 2: namespace mismatch.**
The controller node's `cmd_vel` subscription is relative to the controller's own namespace (e.g. `/diff_drive_controller/cmd_vel`), unless your launch file remaps it to the bare `/cmd_vel`. If you're publishing to `/cmd_vel` but the real subscription lives under the controller's namespace, same silent non-delivery.

**Diagnose first:**
```bash
ros2 topic info /cmd_vel --verbose
```
Look at the reported message type and whether "Subscription count" is 0. If it's 0, or the topic doesn't show your controller node's subscriber at all, run:
```bash
ros2 node info /diff_drive_controller
```
to see the actual topic name and type it's subscribed to.

**Command that will actually move it (if it's the TwistStamped case):**
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
"{twist: {linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
```
(`-r 10` matters too — the controller has a `cmd_vel_timeout`, default 0.5s, so a one-shot publish will stop the robot almost immediately.)

If `ros2 node info` instead shows the subscription living under a namespace like `/diff_drive_controller/cmd_vel`, publish there instead, or fix the remap in your controller-manager launch file so `/cmd_vel` is exposed globally.

If you'd rather keep publishing plain `Twist`, set `use_stamped_vel: false` in the controller's YAML config and restart the controller — then your original `ros2 topic pub /cmd_vel geometry_msgs/msg/Twist ...` will work as expected.
