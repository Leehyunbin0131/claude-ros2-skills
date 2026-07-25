#!/usr/bin/env python3
"""Verify the REP 105 TF tree and print sensor mount transforms for
physical comparison.

Checks that the expected chains resolve (map -> odom -> base_link by default,
skippable before Nav2/SLAM bringup with --no-global), then prints each
base -> sensor transform as translation + roll/pitch/yaw in degrees so you can
compare the numbers against how the sensor is ACTUALLY mounted. A LiDAR that
is level on the robot but shows roll/pitch/yaw = 180 deg here is the classic
"TF declared opposite to the physical mount" bug.

Usage:
  python3 check_tf_tree.py --sensors laser_frame,imu_link
  python3 check_tf_tree.py --no-global --base base_link --sensors laser_frame
Exit codes: 0 all chains resolve, 1 something missing, 2 no ROS.
"""
import argparse
import math
import sys


def quat_to_rpy(x, y, z, w):
    """Quaternion -> (roll, pitch, yaw) in radians, ZYX. Pure, unit-tested."""
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    s = 2.0 * (w * y - z * x)
    s = max(-1.0, min(1.0, s))  # clamp for numeric safety
    pitch = math.asin(s)
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return roll, pitch, yaw


def describe_mount(roll_deg, pitch_deg, yaw_deg, tol=5.0):
    """Human warning for suspicious sensor orientations. Pure, unit-tested."""
    def near(a, target):
        return min(abs(a - target), abs(a + 360 - target), abs(a - 360 - target)) <= tol
    warnings = []
    if near(roll_deg, 180.0):
        warnings.append("roll ~180 deg: declared UPSIDE-DOWN")
    if near(yaw_deg, 180.0):
        warnings.append("yaw ~180 deg: declared FACING BACKWARD")
    if near(pitch_deg, 180.0):
        warnings.append("pitch ~180 deg: declared FLIPPED")
    return warnings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="base_link")
    p.add_argument("--odom-frame", default="odom")
    p.add_argument("--map-frame", default="map")
    p.add_argument("--sensors", default="",
                   help="comma-separated sensor frames, e.g. laser_frame,imu_link")
    p.add_argument("--no-global", action="store_true",
                   help="skip map->odom->base checks (before SLAM/Nav2 bringup)")
    p.add_argument("--timeout", type=float, default=5.0, help="per lookup, seconds")
    args = p.parse_args()

    try:
        import rclpy
        from rclpy.duration import Duration
        from rclpy.time import Time
        from tf2_ros.buffer import Buffer
        from tf2_ros.transform_listener import TransformListener
    except ImportError:
        print("ERROR: rclpy/tf2_ros not found. Source your ROS 2 setup first:\n"
              "  source /opt/ros/jazzy/setup.bash", file=sys.stderr)
        return 2

    rclpy.init()
    node = rclpy.create_node("check_tf_tree")
    buf = Buffer()
    TransformListener(buf, node)

    def lookup(parent, child):
        """Returns TransformStamped or an error string."""
        deadline = node.get_clock().now().nanoseconds + int(args.timeout * 1e9)
        last_err = "timeout"
        while node.get_clock().now().nanoseconds < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            try:
                return buf.lookup_transform(parent, child, Time(),
                                            timeout=Duration(seconds=0.0))
            except Exception as e:  # tf2 raises several lookup exception types
                last_err = type(e).__name__
        return last_err

    chains = []
    if not args.no_global:
        chains += [(args.map_frame, args.odom_frame), (args.odom_frame, args.base)]
    sensors = [s.strip() for s in args.sensors.split(",") if s.strip()]
    chains += [(args.base, s) for s in sensors]

    if not chains:
        print("Nothing to check: pass --sensors and/or drop --no-global.")
        node.destroy_node()
        rclpy.shutdown()
        return 1

    failed = False
    for parent, child in chains:
        res = lookup(parent, child)
        if isinstance(res, str):
            failed = True
            print(f"[MISSING] {parent} -> {child}  ({res}). "
                  f"Check who should publish it: SLAM/AMCL for map->odom, "
                  f"odometry/EKF for odom->base, URDF/static_transform_publisher "
                  f"for sensor frames. Also check use_sim_time consistency.")
            continue
        t = res.transform.translation
        r, pch, y = quat_to_rpy(res.transform.rotation.x, res.transform.rotation.y,
                                res.transform.rotation.z, res.transform.rotation.w)
        rd, pd, yd = map(math.degrees, (r, pch, y))
        line = (f"[OK] {parent} -> {child}  xyz=({t.x:+.3f}, {t.y:+.3f}, {t.z:+.3f}) m  "
                f"rpy=({rd:+.1f}, {pd:+.1f}, {yd:+.1f}) deg")
        warns = describe_mount(rd, pd, yd) if (parent, child) in [(args.base, s) for s in sensors] else []
        print(line)
        for w in warns:
            print(f"     ^ VERIFY PHYSICALLY: {w}. If the sensor is NOT "
                  f"physically mounted that way, this TF is the bug.")

    node.destroy_node()
    rclpy.shutdown()
    if failed:
        return 1
    print("All checked chains resolve. Compare the rpy values above against "
          "the physical sensor mounting before trusting them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
