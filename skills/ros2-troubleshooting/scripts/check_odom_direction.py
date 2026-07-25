#!/usr/bin/env python3
"""Verify odometry direction against physical reality (REP 103).

Procedure: the script records the robot's odometry pose, you physically push
(or drive) the robot FORWARD about 1 meter, then it records the pose again and
projects the displacement onto the robot's initial heading. If odometry says
the robot moved backward while you pushed it forward, the wheel/encoder signs
or a TF are inverted — the classic "logs look fine, robot drives backward" bug.

Usage:  python3 check_odom_direction.py [--topic /odom] [--dist 1.0]
Exit codes: 0 PASS, 1 FAIL, 2 could not sample (no data / no ROS).
"""
import argparse
import math
import sys


def yaw_from_quat(x, y, z, w):
    """Yaw (rad) from quaternion, ZYX convention. Pure, unit-tested."""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def forward_displacement(start, end):
    """Displacement of end relative to start, projected on start's heading.

    start/end: (x, y, yaw). Positive = moved forward. Pure, unit-tested.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    yaw0 = start[2]
    return dx * math.cos(yaw0) + dy * math.sin(yaw0)


def verdict_for(fwd, expected):
    """Pure, unit-tested. expected: rough distance the user moved the robot."""
    threshold = max(0.1, 0.2 * expected)
    if fwd >= threshold:
        return "PASS", (f"odometry moved {fwd:+.2f} m along the initial "
                        "heading — direction matches physical motion.")
    if fwd <= -threshold:
        return "FAIL", (f"odometry moved {fwd:+.2f} m — BACKWARD while the "
                        "robot physically moved forward. Check, in order: "
                        "motor/PWM signs, encoder direction, wheel joint axis "
                        "in URDF, base_link TF yaw.")
    return "INCONCLUSIVE", (f"odometry moved only {fwd:+.2f} m. Robot barely "
                            "moved in odom, wheels slipped, or odometry is "
                            "not integrating — check encoder ticks.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", default="/odom")
    p.add_argument("--dist", type=float, default=1.0,
                   help="approximate distance you will move the robot (m)")
    p.add_argument("--timeout", type=float, default=10.0,
                   help="seconds to wait for each odometry sample")
    args = p.parse_args()

    try:
        import rclpy
        from rclpy.qos import qos_profile_sensor_data
        from nav_msgs.msg import Odometry
    except ImportError:
        print("ERROR: rclpy not found. Source your ROS 2 setup first:\n"
              "  source /opt/ros/jazzy/setup.bash", file=sys.stderr)
        return 2

    rclpy.init()
    node = rclpy.create_node("check_odom_direction")
    latest = []
    node.create_subscription(
        Odometry, args.topic,
        lambda m: latest.append((
            m.pose.pose.position.x,
            m.pose.pose.position.y,
            yaw_from_quat(m.pose.pose.orientation.x,
                          m.pose.pose.orientation.y,
                          m.pose.pose.orientation.z,
                          m.pose.pose.orientation.w))),
        qos_profile_sensor_data)

    def sample():
        latest.clear()
        deadline = node.get_clock().now().nanoseconds + int(args.timeout * 1e9)
        while not latest and node.get_clock().now().nanoseconds < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        return latest[-1] if latest else None

    print(f"Sampling initial pose from {args.topic}...")
    start = sample()
    if start is None:
        print(f"ERROR: no messages on {args.topic}. Check the topic name "
              "(`ros2 topic list`).", file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        return 2

    input(f">>> Physically push or drive the robot FORWARD about "
          f"{args.dist:.1f} m, then press Enter... ")

    end = sample()
    node.destroy_node()
    rclpy.shutdown()
    if end is None:
        print(f"ERROR: odometry stopped publishing on {args.topic}.",
              file=sys.stderr)
        return 2

    fwd = forward_displacement(start, end)
    verdict, msg = verdict_for(fwd, args.dist)
    print(f"[{verdict}] {msg}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
