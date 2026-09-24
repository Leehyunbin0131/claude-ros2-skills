#!/usr/bin/env python3
"""Check every publisher/subscriber QoS pair using the installed Jazzy RMW.

A BEST_EFFORT publisher cannot satisfy a RELIABLE subscriber even though both
appear in the graph. Deadline, durability and liveliness can also prevent
communication. Unresolved policies are inconclusive, never a proven match.

Usage: python3 check_qos_compat.py --topic /scan
Exit codes: 0 all pairs compatible, 1 a definite mismatch, 2 inconclusive/no ROS.
"""
import argparse
import sys
import time

from _check_common import exit_code, positive_float


def compatibility_verdict(compatibility):
    """Map an RMW result name; remain conservative for future/unknown values."""
    return {"OK": "PASS", "ERROR": "FAIL"}.get(compatibility, "INCONCLUSIVE")


def combined_verdict(verdicts):
    """A proven mismatch takes priority; otherwise every pair must be proven."""
    if "FAIL" in verdicts:
        return "FAIL"
    if not verdicts or any(v != "PASS" for v in verdicts):
        return "INCONCLUSIVE"
    return "PASS"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", required=True)
    p.add_argument("--wait", type=positive_float, default=5.0,
                   help="seconds to allow DDS discovery before reading")
    args = p.parse_args()
    try:
        import rclpy
        from rclpy.qos import qos_check_compatible
    except ImportError:
        print("ERROR: rclpy not found. Source your ROS 2 setup first:\n"
              "  source /opt/ros/jazzy/setup.bash", file=sys.stderr)
        return 2

    rclpy.init()
    node = rclpy.create_node("check_qos_compat")
    try:
        deadline = time.monotonic() + args.wait
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(0.1, max(0.0, deadline-time.monotonic())))
        pubs = node.get_publishers_info_by_topic(args.topic)
        subs = node.get_subscriptions_info_by_topic(args.topic)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    if not pubs or not subs:
        print(f"[INCONCLUSIVE] {args.topic}: discovered {len(pubs)} publishers "
              f"and {len(subs)} subscribers; both are needed to check QoS. "
              "Check ROS_DOMAIN_ID/discovery configuration or increase --wait.")
        return 2

    verdicts = []
    for pub in pubs:
        for sub in subs:
            compatibility, reason = qos_check_compatible(pub.qos_profile, sub.qos_profile)
            verdict = compatibility_verdict(compatibility.name)
            verdicts.append(verdict)
            pub_name = f"{pub.node_namespace.rstrip('/')}/{pub.node_name}"
            sub_name = f"{sub.node_namespace.rstrip('/')}/{sub.node_name}"
            print(f"[{verdict}] {pub_name} -> {sub_name}")
            if reason:
                print(f"       {reason}")
    return exit_code(combined_verdict(verdicts))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
