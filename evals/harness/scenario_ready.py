#!/usr/bin/env python3
"""Bounded, read-only checks of the live state promised by frozen prompts.

An absent publisher/service/TF aborts the run before a paid model call. No
motion commands are sent. Importing this module does not require ROS.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path


def controller_active(output: str) -> bool:
    output = re.sub(r"\x1b\[[0-9;]*m", "", output)
    return any(len(parts) >= 3 and parts[0] == "diff_drive_controller"
               and parts[-1] == "active"
               for parts in (line.split() for line in output.splitlines()))


def requirements(task: str):
    """(description, command, output predicate) for every promised resource."""
    checks = []

    def topic(name, message_type):
        checks.append((name, ["ros2", "topic", "echo", name, message_type,
                              "--once", "--qos-reliability", "best_effort"],
                       lambda output: bool(output.strip())))

    def tf(*args):
        script = Path(__file__).resolve().parents[2] / "skills/ros2-troubleshooting/scripts/check_tf_tree.py"
        checks.append(("TF chain", [sys.executable, str(script), "--timeout", "1", *args],
                       lambda _: True))

    if task == "t1":
        checks.append(("active diff_drive_controller",
                       ["ros2", "control", "list_controllers"], controller_active))
    elif task == "t2":
        topic("/imu/data", "sensor_msgs/msg/Imu")
        tf("--no-global", "--sensors", "imu_link")
    elif task in ("t4", "dev2", "dev3"):
        topic("/scan", "sensor_msgs/msg/LaserScan")
        if task != "t4":
            tf("--sensors", "laser_frame")
    elif task in ("tr1", "tr2", "tr3"):
        checks.append(("/slow_check", ["ros2", "service", "list", "--no-daemon"],
                       lambda output: "/slow_check" in output.splitlines()))
        if task == "tr2":
            topic("/tick", "std_msgs/msg/Int32")
    elif task == "qos1":
        topic("/sensor", "std_msgs/msg/Int32")
    elif task in ("per1", "per2", "per3"):
        prefix = "/depth" if task == "per3" else "/camera"
        topic(prefix + "/image_raw", "sensor_msgs/msg/Image")
        if task != "per1":
            topic(prefix + "/camera_info", "sensor_msgs/msg/CameraInfo")
    return checks


def wait_until_ready(task, timeout=60.0, *, probe=subprocess.run,
                     clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    for description, command, accepts in requirements(task):
        diagnostic = "no response"
        while clock() < deadline:
            remaining = deadline - clock()
            try:
                result = probe(command, capture_output=True, text=True,
                               timeout=min(6.0, max(0.01, remaining)))
                if result.returncode == 0 and accepts(result.stdout):
                    break
                diagnostic = (result.stderr or result.stdout or
                              f"exit {result.returncode}").strip()[-1000:]
            except subprocess.TimeoutExpired:
                diagnostic = "probe timed out"
            except OSError as exc:
                return False, f"{description}: {exc}"
            sleep(min(0.2, max(0.0, deadline - clock())))
        else:
            return False, f"{description} not ready: {diagnostic}"
    return True, "all required resources observed"


def main():
    from grade_v2 import TASKS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("task", choices=sorted(TASKS))
    args = ap.parse_args()
    ready, detail = wait_until_ready(args.task)
    print(f"{args.task}: {detail}", file=sys.stdout if ready else sys.stderr)
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
