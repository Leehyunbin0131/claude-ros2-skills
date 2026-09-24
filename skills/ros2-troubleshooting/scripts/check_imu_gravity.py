#!/usr/bin/env python3
"""Verify IMU mounting: with the robot resting flat and still, gravity must
appear as ~+9.81 m/s^2 on +Z after transforming acceleration into base_link.

A correctly declared rotated IMU can report gravity on any axis in its own
frame. TF is required by default; --assume-aligned explicitly skips rotation
when you know the message axes already align with the level robot's base.

Usage:  ros2 run <nothing needed> — just:  python3 check_imu_gravity.py [--topic /imu/data]
Exit codes: 0 PASS, 1 FAIL, 2 inconclusive (unusable/insufficient data / no ROS).
"""
import argparse
import math
import sys
import time

from _check_common import exit_code, positive_float, positive_int, unit_quaternion

G = 9.81
# Fixed tolerances assume a robot at rest on flat ground; consumer-grade IMU
# bias/noise sits well inside +/-1.5 m/s^2. Widen --tol-mag if uncalibrated.
DEFAULT_MAG_TOL = 1.5      # |a| must be within G ± this (m/s^2)
DEFAULT_AXIS_RATIO = 0.8   # dominant axis must carry >= this fraction of |a|


def rotate_acceleration(vector, quaternion):
    """Rotate a sensor vector into the target frame using target<-sensor TF."""
    x, y, z, w = unit_quaternion(*quaternion)
    ax, ay, az = vector
    tx, ty, tz = 2*(y*az-z*ay), 2*(z*ax-x*az), 2*(x*ay-y*ax)
    return (ax+w*tx+y*tz-z*ty, ay+w*ty+z*tx-x*tz, az+w*tz+x*ty-y*tx)


def analyze(samples, mag_tol=DEFAULT_MAG_TOL, axis_ratio=DEFAULT_AXIS_RATIO):
    """Pure logic, unit-tested without ROS.

    samples: list of (ax, ay, az) tuples.
    Returns (verdict, message) where verdict is 'PASS' | 'FAIL' | 'INCONCLUSIVE'.
    """
    if not samples:
        return "INCONCLUSIVE", "no samples collected"
    if not math.isfinite(mag_tol) or mag_tol <= 0:
        raise ValueError("mag_tol must be finite and greater than zero")
    if not math.isfinite(axis_ratio) or not 0 < axis_ratio <= 1:
        raise ValueError("axis_ratio must be in (0, 1]")
    if any(not math.isfinite(value) for sample in samples for value in sample):
        return "INCONCLUSIVE", "acceleration contains non-finite values"
    n = len(samples)
    ax = sum(s[0] for s in samples) / n
    ay = sum(s[1] for s in samples) / n
    az = sum(s[2] for s in samples) / n
    mag = math.sqrt(ax * ax + ay * ay + az * az)
    if not math.isfinite(mag):
        return "INCONCLUSIVE", "acceleration magnitude is not finite"
    detail = f"mean accel = ({ax:+.2f}, {ay:+.2f}, {az:+.2f}) m/s^2, |a| = {mag:.2f}"

    if abs(mag - G) > mag_tol:
        return "FAIL", (f"{detail}. Magnitude is not ~{G}: robot is moving, "
                        "vibrating, or the IMU scale/units are wrong.")
    axes = {"X": ax, "Y": ay, "Z": az}
    dom = max(axes, key=lambda k: abs(axes[k]))
    if abs(axes[dom]) < axis_ratio * mag:
        return "FAIL", (f"{detail}. Gravity is split across axes: IMU is "
                        "mounted tilted relative to its TF frame.")
    if dom != "Z":
        return "FAIL", (f"{detail}. Gravity is on {dom}, not Z: IMU is mounted "
                        "rotated 90 deg relative to its declared TF frame.")
    if az < 0:
        return "FAIL", (f"{detail}. Z is negative: IMU is upside-down relative "
                        "to its declared TF frame (or reports acceleration in "
                        "NED instead of REP 103 ENU/body convention).")
    return "PASS", f"{detail}. Gravity on +Z as REP 103 requires."


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", default="/imu/data")
    p.add_argument("--base", default="base_link", help="level robot body frame")
    p.add_argument("--assume-aligned", action="store_true",
                   help="explicitly assume message axes align with --base; skip TF")
    p.add_argument("--samples", type=positive_int, default=50)
    p.add_argument("--timeout", type=positive_float, default=10.0, help="seconds")
    p.add_argument("--tol-mag", type=positive_float, default=DEFAULT_MAG_TOL)
    args = p.parse_args()
    if not args.base.strip():
        p.error("--base must name a frame")

    try:
        import rclpy
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Imu
        if not args.assume_aligned:
            from rclpy.time import Time
            from tf2_ros import Buffer, TransformListener, TransformException
    except ImportError:
        print("ERROR: ROS Python messages/TF support not found. Source ROS 2 first:\n"
              "  source /opt/ros/jazzy/setup.bash", file=sys.stderr)
        return 2

    print(f"Keep the robot RESTING FLAT and STILL. Sampling {args.samples} "
          f"messages from {args.topic} (timeout {args.timeout}s)...")

    rclpy.init()
    node = rclpy.create_node("check_imu_gravity")
    samples = []
    unavailable = 0
    last_error = ""
    buffer = None

    def receive(message):
        nonlocal unavailable, last_error
        # sensor_msgs/Imu explicitly declares this estimate unavailable.
        if message.linear_acceleration_covariance[0] == -1:
            unavailable += 1
            last_error = "sensor marks acceleration unavailable"
            return
        a = message.linear_acceleration
        acceleration = (a.x, a.y, a.z)
        if buffer is not None:
            if not message.header.frame_id:
                unavailable += 1
                last_error = "IMU message has no frame_id"
                return
            try:
                transform = buffer.lookup_transform(args.base, message.header.frame_id,
                                                    Time.from_msg(message.header.stamp))
                q = transform.transform.rotation
                acceleration = rotate_acceleration(acceleration, (q.x, q.y, q.z, q.w))
            except (TransformException, ValueError) as error:
                unavailable += 1
                last_error = f"TF {args.base} <- {message.header.frame_id}: {error}"
                return
        samples.append(acceleration)

    try:
        if args.assume_aligned:
            print(f"ASSUMPTION: message axes align with {args.base}; TF is not checked.")
        else:
            buffer = Buffer()
            listener = TransformListener(buffer, node)
        node.create_subscription(Imu, args.topic, receive, qos_profile_sensor_data)
        deadline = time.monotonic() + args.timeout
        while len(samples) < args.samples and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(0.1, max(0.0, deadline-time.monotonic())))
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    if len(samples) < args.samples:
        print(f"[INCONCLUSIVE] collected {len(samples)}/{args.samples} usable "
              f"messages on {args.topic}; {unavailable} unavailable. "
              f"{last_error or 'Check the topic, QoS and sensor output.'}", file=sys.stderr)
        return 2

    verdict, msg = analyze(samples, mag_tol=args.tol_mag)
    print(f"[{verdict}] In {args.base}: {msg}")
    return exit_code(verdict)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
