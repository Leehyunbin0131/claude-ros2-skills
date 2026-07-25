#!/usr/bin/env python3
"""Verify IMU mounting: with the robot resting flat and still, gravity must
appear as ~+9.81 m/s^2 on the +Z axis of linear_acceleration (REP 103).

A dominant reading on X or Y, or a negative Z, means the IMU is mounted
rotated/flipped relative to its TF frame — the exact bug that makes EKF
odometry diverge while every topic still "looks" healthy.

Usage:  ros2 run <nothing needed> — just:  python3 check_imu_gravity.py [--topic /imu/data]
Exit codes: 0 PASS, 1 FAIL, 2 could not sample (no data / no ROS).
"""
import argparse
import math
import sys

G = 9.81
# Fixed tolerances assume a robot at rest on flat ground; consumer-grade IMU
# bias/noise sits well inside +/-1.5 m/s^2. Widen --tol-mag if uncalibrated.
DEFAULT_MAG_TOL = 1.5      # |a| must be within G ± this (m/s^2)
DEFAULT_AXIS_RATIO = 0.8   # dominant axis must carry >= this fraction of |a|


def analyze(samples, mag_tol=DEFAULT_MAG_TOL, axis_ratio=DEFAULT_AXIS_RATIO):
    """Pure logic, unit-tested without ROS.

    samples: list of (ax, ay, az) tuples.
    Returns (verdict, message) where verdict is 'PASS' | 'FAIL' | 'INCONCLUSIVE'.
    """
    if not samples:
        return "INCONCLUSIVE", "no samples collected"
    n = len(samples)
    ax = sum(s[0] for s in samples) / n
    ay = sum(s[1] for s in samples) / n
    az = sum(s[2] for s in samples) / n
    mag = math.sqrt(ax * ax + ay * ay + az * az)
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
    p.add_argument("--samples", type=int, default=50)
    p.add_argument("--timeout", type=float, default=10.0, help="seconds")
    p.add_argument("--tol-mag", type=float, default=DEFAULT_MAG_TOL)
    args = p.parse_args()

    try:
        import rclpy
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Imu
    except ImportError:
        print("ERROR: rclpy not found. Source your ROS 2 setup first:\n"
              "  source /opt/ros/jazzy/setup.bash", file=sys.stderr)
        return 2

    print(f"Keep the robot RESTING FLAT and STILL. Sampling {args.samples} "
          f"messages from {args.topic} (timeout {args.timeout}s)...")

    rclpy.init()
    node = rclpy.create_node("check_imu_gravity")
    samples = []
    node.create_subscription(
        Imu, args.topic,
        lambda m: samples.append((m.linear_acceleration.x,
                                  m.linear_acceleration.y,
                                  m.linear_acceleration.z)),
        qos_profile_sensor_data)

    deadline = node.get_clock().now().nanoseconds + int(args.timeout * 1e9)
    while (len(samples) < args.samples
           and node.get_clock().now().nanoseconds < deadline):
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    rclpy.shutdown()

    if not samples:
        print(f"ERROR: no messages on {args.topic}. Check the topic name "
              f"(`ros2 topic list`) and QoS.", file=sys.stderr)
        return 2

    verdict, msg = analyze(samples, mag_tol=args.tol_mag)
    print(f"[{verdict}] {msg}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
