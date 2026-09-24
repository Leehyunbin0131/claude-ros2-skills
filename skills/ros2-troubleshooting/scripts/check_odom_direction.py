#!/usr/bin/env python3
"""Verify odometry direction against physical reality (REP 103).

Procedure: the script records the robot's odometry pose, you physically push
(or drive) the robot FORWARD about 1 meter, then it records the pose again and
projects the displacement onto the robot's initial heading. If odometry says
the robot moved backward while you pushed it forward, the wheel/encoder signs
or a TF are inverted — the classic "logs look fine, robot drives backward" bug.

Usage:  python3 check_odom_direction.py [--topic /odom] [--dist 1.0]
Exit codes: 0 PASS, 1 FAIL, 2 inconclusive (unusable/no data or too little motion).
"""
import argparse
import math
import sys
import time
from copy import copy

from _check_common import (exit_code, nonnegative_float, positive_float,
                           unit_quaternion)


def yaw_from_quat(x, y, z, w):
    """Yaw (rad) from quaternion, ZYX convention. Pure, unit-tested."""
    x, y, z, w = unit_quaternion(x, y, z, w)
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
    if not math.isfinite(expected) or expected <= 0:
        raise ValueError("expected distance must be finite and greater than zero")
    if not math.isfinite(fwd):
        return "INCONCLUSIVE", "odometry displacement is not finite"
    threshold = max(0.1, 0.2 * expected)
    if fwd >= threshold:
        return "PASS", (f"odometry moved {fwd:+.2f} m along the initial "
                        "heading — direction matches physical motion.")
    if fwd <= -threshold:
        return "FAIL", (f"odometry moved {fwd:+.2f} m — BACKWARD while the "
                        "robot physically moved forward. Check, in order: "
                        "encoder direction, wheel joint axis in URDF, and "
                        "base_link TF yaw. If motion was motor-driven, also "
                        "compare motor/PWM direction with the command.")
    return "INCONCLUSIVE", (f"odometry moved only {fwd:+.2f} m. Robot barely "
                            "moved in odom, wheels slipped, or odometry is "
                            "not integrating — check encoder ticks.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", default="/odom")
    p.add_argument("--dist", type=positive_float, default=1.0,
                   help="approximate distance you will move the robot (m)")
    p.add_argument("--timeout", type=positive_float, default=10.0,
                   help="seconds to wait for each odometry sample")
    p.add_argument("--wait-secs", type=nonnegative_float, default=None,
                   help="non-interactive mode: wait this many seconds for the "
                        "motion instead of prompting for Enter (headless/CI)")
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
    def sample():
        # A new VOLATILE reader cannot consume samples queued during the
        # motion prompt. Require a new publication for each measurement.
        messages = []
        qos = copy(qos_profile_sensor_data)
        qos.depth = 1
        sub = node.create_subscription(Odometry, args.topic, messages.append, qos)
        try:
            deadline = time.monotonic() + args.timeout
            while not messages and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=min(0.1, max(0.0, deadline-time.monotonic())))
            return messages[-1] if messages else None
        finally:
            node.destroy_subscription(sub)

    try:
        print(f"Sampling initial pose from {args.topic}...")
        start = sample()
        if start is None:
            print(f"[INCONCLUSIVE] no messages on {args.topic}.", file=sys.stderr)
            return 2
        try:
            start_pose = pose_from_message(start)
        except ValueError as error:
            print(f"[INCONCLUSIVE] invalid initial pose: {error}")
            return 2

        prompt = (f">>> Physically push or drive the robot FORWARD about "
                  f"{args.dist:.1f} m, then press Enter... ")
        if args.wait_secs is not None:
            print(prompt + f"(non-interactive: waiting {args.wait_secs:g}s)")
            time.sleep(args.wait_secs)
        else:
            try:
                input(prompt)
            except EOFError:
                print(f"(stdin closed — waiting {args.timeout:g}s instead; "
                      "use --wait-secs for headless runs)")
                time.sleep(args.timeout)

        end = sample()
        if end is None:
            print(f"[INCONCLUSIVE] no fresh odometry on {args.topic} after motion.",
                  file=sys.stderr)
            return 2
        try:
            end_pose = pose_from_message(end)
        except ValueError as error:
            print(f"[INCONCLUSIVE] invalid final pose: {error}")
            return 2
        if (start.header.frame_id, start.child_frame_id) != (end.header.frame_id, end.child_frame_id):
            print("[INCONCLUSIVE] odometry frames changed between measurements")
            return 2

        fwd = forward_displacement(start_pose, end_pose)
        verdict, msg = verdict_for(fwd, args.dist)
        print(f"[{verdict}] {msg}")
        return exit_code(verdict)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def pose_from_message(message):
    """Extract a finite pose in named frames (also testable with plain objects)."""
    if not message.header.frame_id or not message.child_frame_id:
        raise ValueError("odometry must name its parent and child frames")
    p = message.pose.pose.position
    q = message.pose.pose.orientation
    if not all(math.isfinite(v) for v in (p.x, p.y, p.z)):
        raise ValueError("position contains non-finite values")
    return p.x, p.y, yaw_from_quat(q.x, q.y, q.z, q.w)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
