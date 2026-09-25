#!/usr/bin/env python3
"""Which processes belong to this eval run -- and only those.

Every process a round starts (scenario publishers, the cell's `claude`, whatever
the agent launches in the background, the checker and its probes) inherits one
environment entry, `EVAL_RUN_TAG=<tag>`, exported by `run_ab.sh` through
`procscope.sh`. Selecting processes by that entry replaces the host-wide
`pkill -9 -f robot_state_publisher` / `controller_server` / `^python3 .*/node.py`
the checkers used to run. That older form killed the matching processes of
*anyone* on the host. On a robotics workstation that includes a live robot's
controller_manager.

An inherited environment survives `nohup`, `setsid`, `disown`, `ros2 launch`
and the unprivileged user namespace `isolate_cell.sh` creates, so the agent's
own background bringup is still found. A process that clears its environment is
simply not ours any more. It leaks rather than being killed by mistake, which
is the safe direction.

    python3 procscope.py new-tag
    python3 procscope.py pids [--any-tag] [PATTERN ...]
    python3 procscope.py kill [--signal KILL|TERM] [--any-tag] [PATTERN ...]
    python3 procscope.py foreign-ros

PATTERNs are Python regexes searched in the space-joined command line (what
`pkill -f` matched). No pattern means every process carrying the tag. The
caller and all of its ancestors are always excluded. Without a tag in the
environment and without --any-tag, `pids`/`kill` refuse (exit 2) -- they never
fall back to an untagged, host-wide selection.
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import signal
import sys

TAG_VAR = "EVAL_RUN_TAG"
TAG_PREFIX = "ros2eval-"
PROC = "/proc"


def new_tag() -> str:
    return TAG_PREFIX + secrets.token_hex(8)


def _read(path: str) -> bytes | None:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def environ(pid: int, proc: str = PROC) -> list[str] | None:
    raw = _read(f"{proc}/{pid}/environ")
    if raw is None:
        return None
    return [e.decode(errors="replace") for e in raw.split(b"\0") if e]


def cmdline(pid: int, proc: str = PROC) -> str:
    raw = _read(f"{proc}/{pid}/cmdline") or b""
    return " ".join(a.decode(errors="replace") for a in raw.split(b"\0") if a)


def parent(pid: int, proc: str = PROC) -> int | None:
    raw = _read(f"{proc}/{pid}/stat")
    if not raw:
        return None
    # comm may contain spaces and parentheses; ppid is the 2nd field after the
    # LAST ')'.
    try:
        return int(raw[raw.rindex(b")") + 2:].split()[1])
    except (ValueError, IndexError):
        return None


def ancestors(pid: int, proc: str = PROC) -> set[int]:
    """pid itself plus every ancestor up to init."""
    seen: set[int] = set()
    cur: int | None = pid
    while cur and cur not in seen:
        seen.add(cur)
        if cur == 1:
            break
        cur = parent(cur, proc)
    return seen


def all_pids(proc: str = PROC) -> list[int]:
    return sorted(int(d) for d in os.listdir(proc) if d.isdigit())


def has_tag(env: list[str], tag: str | None) -> bool:
    """tag=None means 'any eval tag'."""
    if tag is None:
        return any(e.startswith(f"{TAG_VAR}={TAG_PREFIX}") for e in env)
    return f"{TAG_VAR}={tag}" in env


def select(tag: str | None, patterns: list[str], *, proc: str = PROC,
           me: int | None = None, uid: int | None = None) -> list[int]:
    """PIDs of `uid` carrying `tag` whose command line matches any pattern.

    Pure given a /proc-shaped directory, which is how it is unit-tested.
    """
    me = os.getpid() if me is None else me
    uid = os.getuid() if uid is None else uid
    skip = ancestors(me, proc)
    regs = [re.compile(p) for p in patterns]
    out = []
    for pid in all_pids(proc):
        if pid in skip:
            continue
        try:
            if os.stat(f"{proc}/{pid}").st_uid != uid:
                continue
        except OSError:
            continue
        env = environ(pid, proc)
        if env is None or not has_tag(env, tag):
            continue
        if regs:
            cl = cmdline(pid, proc)
            if not any(r.search(cl) for r in regs):
                continue
        out.append(pid)
    return out


# Command lines that are a ROS 2 process somebody else started. Used only to
# REFUSE to run (see run_ab.sh preflight), never to kill anything.
_ROS_HINT = re.compile(r"/opt/ros/[^ ]+/lib/|\bros2 (launch|run) |--ros-args")
_ROS_DAEMON = re.compile(r"_ros2_daemon")


def foreign_ros(proc: str = PROC, me: int | None = None) -> list[tuple[int, str]]:
    """ROS processes on this host that no eval run started."""
    me = os.getpid() if me is None else me
    skip = ancestors(me, proc)
    found = []
    for pid in all_pids(proc):
        if pid in skip:
            continue
        cl = cmdline(pid, proc)
        if not cl or not _ROS_HINT.search(cl) or _ROS_DAEMON.search(cl):
            continue
        env = environ(pid, proc)
        if env is not None and has_tag(env, None):
            continue  # an eval process (this run or a leftover one)
        found.append((pid, cl[:160]))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("new-tag")
    for name in ("pids", "kill"):
        sp = sub.add_parser(name)
        sp.add_argument("--any-tag", action="store_true",
                        help="any eval run's processes, not just this run's")
        sp.add_argument("patterns", nargs="*")
        if name == "kill":
            sp.add_argument("--signal", choices=("KILL", "TERM"), default="KILL")
    sub.add_parser("foreign-ros")
    a = ap.parse_args(argv)

    if a.cmd == "new-tag":
        print(new_tag())
        return 0
    if a.cmd == "foreign-ros":
        for pid, cl in foreign_ros():
            print(f"{pid} {cl}")
        return 0

    tag = None if a.any_tag else os.environ.get(TAG_VAR)
    if not a.any_tag and not tag:
        print(f"procscope: {TAG_VAR} is not set -- refusing an untagged, "
              f"host-wide selection", file=sys.stderr)
        return 2
    pids = select(tag, a.patterns)
    if a.cmd == "pids":
        for p in pids:
            print(p)
        return 0
    sig = signal.SIGKILL if a.signal == "KILL" else signal.SIGTERM
    for p in pids:
        try:
            os.kill(p, sig)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
