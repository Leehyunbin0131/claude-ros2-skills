#!/usr/bin/env python3
"""Verify QoS compatibility between every publisher and subscriber on a topic.

The classic silent failure: a sensor driver publishes BEST_EFFORT, a default
subscriber requests RELIABLE — DDS matches nothing, `ros2 topic list` still
shows the topic, and the subscriber just never receives a message. Same story
for VOLATILE publishers vs TRANSIENT_LOCAL subscribers (late-joiner configs),
and for deadline/liveliness offers weaker than what the subscriber requested.

Usage:  python3 check_qos_compat.py --topic /scan
Exit codes: 0 PASS (all pairs compatible), 1 FAIL, 2 could not sample.
"""
import argparse
import sys

# DDS treats these as request-vs-offered: the publisher's offer must be at
# least as strong as the subscriber's request, per policy.
_RELIABILITY_STRENGTH = {"BEST_EFFORT": 0, "RELIABLE": 1}
_DURABILITY_STRENGTH = {"VOLATILE": 0, "TRANSIENT_LOCAL": 1}
_LIVELINESS_STRENGTH = {"AUTOMATIC": 0, "MANUAL_BY_TOPIC": 1}


def check_pair(pub, sub):
    """Pure logic, unit-tested without ROS.

    pub/sub: dicts with keys 'reliability', 'durability', 'liveliness'
    (policy-name strings, or None when the RMW reports UNKNOWN/SYSTEM_DEFAULT)
    and 'deadline', 'lease' (seconds as float, or None meaning infinite).
    Returns a list of human-readable incompatibility strings (empty = match).
    """
    problems = []

    for key, strength, hint in (
        ("reliability", _RELIABILITY_STRENGTH,
         "subscriber will receive NOTHING; use qos_profile_sensor_data or a "
         "BEST_EFFORT subscription for sensor streams"),
        ("durability", _DURABILITY_STRENGTH,
         "late-joining subscriber expects a latched sample the publisher "
         "never stores; publish TRANSIENT_LOCAL or subscribe VOLATILE"),
        ("liveliness", _LIVELINESS_STRENGTH,
         "publisher cannot assert liveliness the way the subscriber demands"),
    ):
        p, s = pub.get(key), sub.get(key)
        if p is None or s is None:
            continue  # UNKNOWN/SYSTEM_DEFAULT: nothing provable
        if strength[p] < strength[s]:
            problems.append(
                f"{key}: publisher offers {p}, subscriber requests {s} — {hint}")

    # Durations: None = infinite. Offered period must be <= requested period.
    for key, label in (("deadline", "deadline period"),
                       ("lease", "liveliness lease duration")):
        p, s = pub.get(key), sub.get(key)
        if s is None:
            continue  # subscriber accepts anything
        if p is None or p > s:
            offered = "infinite" if p is None else f"{p:g}s"
            problems.append(
                f"{key}: publisher offers {label} {offered}, subscriber "
                f"requires <= {s:g}s")

    return problems


def _policy_name(value, allowed):
    """Map an rclpy QoS enum to a plain string, or None if not provable."""
    name = getattr(value, "name", str(value))
    return name if name in allowed else None


def _duration_s(d):
    """rclpy Duration -> float seconds, or None for the DDS 'infinite'."""
    ns = d.nanoseconds
    return None if ns >= 2**62 else ns / 1e9


def endpoint_to_dict(qos):
    """Runtime-only: flatten an rclpy QoSProfile for check_pair()."""
    return {
        "reliability": _policy_name(qos.reliability, _RELIABILITY_STRENGTH),
        "durability": _policy_name(qos.durability, _DURABILITY_STRENGTH),
        "liveliness": _policy_name(qos.liveliness, _LIVELINESS_STRENGTH),
        "deadline": _duration_s(qos.deadline),
        "lease": _duration_s(qos.liveliness_lease_duration),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", required=True)
    p.add_argument("--wait", type=float, default=2.0,
                   help="seconds to allow DDS discovery before reading")
    args = p.parse_args()

    try:
        import rclpy
    except ImportError:
        print("ERROR: rclpy not found. Source your ROS 2 setup first:\n"
              "  source /opt/ros/jazzy/setup.bash", file=sys.stderr)
        return 2

    rclpy.init()
    node = rclpy.create_node("check_qos_compat")
    deadline = node.get_clock().now().nanoseconds + int(args.wait * 1e9)
    while node.get_clock().now().nanoseconds < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    pubs = node.get_publishers_info_by_topic(args.topic)
    subs = node.get_subscriptions_info_by_topic(args.topic)
    node.destroy_node()
    rclpy.shutdown()

    if not pubs and not subs:
        print(f"ERROR: no publishers or subscribers on {args.topic}. Check "
              "the topic name (`ros2 topic list`).", file=sys.stderr)
        return 2
    if not pubs or not subs:
        side = "publishers" if not pubs else "subscribers"
        print(f"[INCONCLUSIVE] {args.topic} has no {side} yet — nothing to "
              "match against.")
        return 2

    failed = False
    for pub in pubs:
        for sub in subs:
            problems = check_pair(endpoint_to_dict(pub.qos_profile),
                                  endpoint_to_dict(sub.qos_profile))
            pair = f"{pub.node_name} -> {sub.node_name}"
            if problems:
                failed = True
                print(f"[FAIL] {pair}")
                for prob in problems:
                    print(f"       {prob}")
            else:
                print(f"[PASS] {pair}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
