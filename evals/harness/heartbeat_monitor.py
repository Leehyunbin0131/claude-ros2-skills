#!/usr/bin/env python3
"""Measures whether a cell's `/heartbeat` actually stayed at rate.

Usage: heartbeat_monitor.py <out.json> <seconds>

Records the arrival time of every `std_msgs/msg/Int32` on `/heartbeat` and
reports the **largest gap between consecutive messages**, not the average rate.

Average rate hides the failure this rung is about. A node whose executor stalls
for one second per service call still averages a respectable number over a long
run; what gives it away is a single 1 s hole in a stream that should have no gap
wider than 0.1 s. Reporting the max gap makes the stall visible no matter how
long the run is.
"""
import json
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Int32


class Monitor(Node):
    def __init__(self):
        super().__init__("heartbeat_monitor")
        # BEST_EFFORT so a cell publishing with sensor-style QoS is still
        # matched; a RELIABLE subscriber would silently never connect to it.
        qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.stamps = []
        self.create_subscription(Int32, "/heartbeat", self.on_beat, qos)

    def on_beat(self, _msg):
        self.stamps.append(time.monotonic())


def main():
    out_path = sys.argv[1]
    duration = float(sys.argv[2])
    rclpy.init()
    node = Monitor()
    end = time.monotonic() + duration
    while rclpy.ok() and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)

    s = node.stamps
    gaps = [b - a for a, b in zip(s, s[1:])]
    span = (s[-1] - s[0]) if len(s) >= 2 else 0.0
    json.dump({
        "count": len(s),
        "span_s": round(span, 3),
        "avg_hz": round(len(s) / span, 2) if span > 0 else 0.0,
        "max_gap_s": round(max(gaps), 3) if gaps else None,
    }, open(out_path, "w"))

    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
