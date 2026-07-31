# Runtime faults where every node logs healthy

## QoS mismatch

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

## Sim clock (`use_sim_time`)

TF lookups fail with `Lookup would require extrapolation into the past/future`,
or Nav2 goals freeze, when some nodes run on `/clock` and others on wall time.
Under Gazebo or bag playback every node needs it:

```python
Node(package='my_pkg', executable='my_node', parameters=[{'use_sim_time': True}])
```

## Lifecycle state

Nav2 servers answer `ros2 topic echo` while rejecting or timing out every
action goal, because `controller_server` / `planner_server` / `amcl` are still
`unconfigured` or `inactive`. `ros2 lifecycle get /controller_server` shows the
state; `nav2_lifecycle_manager` should own the transitions.

## DDS domain

Unrelated machines on one network exchanging topics, or heavy packet loss, is
the default `ROS_DOMAIN_ID=0` shared across a LAN. `export ROS_DOMAIN_ID=N` per
developer or robot — 0–101 is safe on Linux; higher IDs can collide with
ephemeral ports.

## MoveIt planning refuses to start

`No valid path found` or `State in collision` immediately, with no motion, is
usually overlapping collision geometry in the URDF or a missing SRDF Allowed
Collision Matrix. Regenerate the SRDF with the MoveIt Setup Assistant so
adjacent fixed joints are excluded from collision checking.
