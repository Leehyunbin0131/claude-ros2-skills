# QoS mismatch

The one runtime fault in this pack a baseline agent keeps walking into. It was
measured across four separate rounds — a plain `/sensor` subscriber, a camera
image, image + `CameraInfo`, depth + `CameraInfo` — and cost cells in every one.

A publisher offering BEST_EFFORT cannot match a RELIABLE subscriber, and
rclpy's default subscriber is RELIABLE. `ros2 topic hz` shows traffic, the
publisher is fine, and the callback never fires.

It is **not** silent, and it is worth reading the log before theorising.
Observed on this install (Jazzy, rclpy, 2026-07-31):

```
[WARN] [sensor_listener]: New publisher discovered on topic '/sensor',
offering incompatible QoS. No messages will be received from it.
Last incompatible policy: RELIABILITY
```

`scripts/check_qos_compat.py --topic <topic>` reports every incompatible
publisher/subscriber pair on a topic. Two other policies fail the same way and
name themselves the same way in that warning: DURABILITY (a VOLATILE subscriber
never receives a TRANSIENT_LOCAL publisher's retained sample, so a
latched-once config topic delivers nothing to a late joiner) and DEADLINE (a
subscriber requesting a period stricter than the publisher offers).

`ros2 topic echo` cannot answer this question. It auto-negotiates QoS, so it
matches publishers a real subscriber would not — a topic that echoes perfectly
can still deliver nothing to the node you are debugging. Run the script, or run
an actual subscriber.

## Why this section is here and the others are not

This file also covered sim clock, lifecycle state, DDS domains and MoveIt
startup. Each was cut after a ladder measured the baseline agent handling it
unaided: `use_sim_time` under Gazebo (28/30), driving Nav2 servers to `active`
(30/30), setting an isolated `ROS_DOMAIN_ID` (done spontaneously — the grader
had to be fixed to stop penalising it), MoveIt planning against a self-authored
URDF and SRDF (100/100).

QoS survived the same treatment because it kept failing. The diagnosis is that
it is **not a knowledge gap**: cells that ran their own node read the warning
and fixed it, cells that wrote the file and stopped did not. One passing cell
never looked up the publisher's QoS at all — it ran the node, read the warning,
and corrected it. That is why `CLAUDE.md` carries "Done means it ran", and why
this section points at a script rather than explaining DDS.
