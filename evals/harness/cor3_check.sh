#!/usr/bin/env bash
# Real-outcome checks for the ros2-core ladder, rung L3.
#
#   ./cor3_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a managed lifecycle node, externally drivable -> cor3_lifecycle_node
#   publication GATED on the active state        -> cor3_silent_when_inactive
#   publication once activated                   -> cor3_publishes_when_active
#
# `cor3_silent_when_inactive` is the rung. A plain node that publishes from a
# timer satisfies "publishes at 10 Hz on /count" completely, and the only thing
# that separates it from a real lifecycle node is that it never stops. So the
# checker subscribes BEFORE configuring anything, confirms silence, drives
# configure+activate from outside, and confirms traffic appears.
#
# The node is expected to keep running (the prompt says "Do not exit on your
# own"), so it is killed by the checker rather than waited on.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * pkill anchored to `^python3 `
#   * never `wait` on a node that ignores SIGTERM
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: cor3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: cor3_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"cor3_node_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*count_probe\.py' 2>/dev/null || true
}
kill_all
sleep 1

RUN_LOG="$(mktemp)"
timeout 120 python3 "$NODE" >"$RUN_LOG" 2>&1 &
NODE_PID=$!

# Wait for the node to appear, then find its lifecycle name from the graph.
LC_NAME=""
for _ in $(seq 1 30); do
  LN="$(timeout 6 ros2 lifecycle nodes 2>/dev/null || true)"
  first="$(printf '%s' "$LN" | awk 'NF {print $1; exit}')"
  if [ -n "$first" ]; then LC_NAME="$first"; break; fi
  sleep 1
done

PROBE_LOG="$(mktemp)"
cat > /tmp/count_probe.py <<'PYEOF'
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class Probe(Node):
    def __init__(self):
        super().__init__("count_probe")
        self.n = 0
        self.create_subscription(Int32, "/count", self.cb, 10)
        self.create_timer(0.5, self.report)

    def cb(self, msg):
        self.n += 1

    def report(self):
        print(f"COUNT {self.n}", flush=True)


rclpy.init()
try:
    rclpy.spin(Probe())
except SystemExit:
    pass
PYEOF
timeout 90 python3 /tmp/count_probe.py >"$PROBE_LOG" 2>&1 &
PROBE=$!
for _ in $(seq 1 30); do
  awk '/^COUNT/ {f=1} END {exit !f}' "$PROBE_LOG" 2>/dev/null && break
  sleep 0.5
done

# --- 1. silence while unconfigured/inactive ---------------------------------
sleep 4
N_BEFORE=$(awk '/^COUNT/ {n=$2} END {print n+0}' "$PROBE_LOG" 2>/dev/null)

# --- 2. drive the transitions from outside ----------------------------------
CONFIG_OUT="-"
ACTIVATE_OUT="-"
if [ -n "$LC_NAME" ]; then
  CONFIG_OUT="$(timeout 30 ros2 lifecycle set "$LC_NAME" configure 2>&1 | head -1)"
  ACTIVATE_OUT="$(timeout 30 ros2 lifecycle set "$LC_NAME" activate 2>&1 | head -1)"
fi

sleep 5
N_AFTER=$(awk '/^COUNT/ {n=$2} END {print n+0}' "$PROBE_LOG" 2>/dev/null)

kill -9 $PROBE 2>/dev/null || true
kill -9 $NODE_PID 2>/dev/null || true
kill_all

N_STATE=$(awk '/STATE/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)

p_lifecycle=false; [ -n "$LC_NAME" ] && p_lifecycle=true
p_silent=false;    [ "${N_BEFORE:-0}" -eq 0 ] && p_silent=true
p_active=false;    [ $(( ${N_AFTER:-0} - ${N_BEFORE:-0} )) -ge 10 ] && p_active=true

{
  printf '{\n'
  printf '  "cor3_node_found": true,\n'
  printf '  "node": %s,\n'                        "$(printf '%s' "$NODE" | json_escape)"
  printf '  "cor3_lifecycle_node": %s,\n'         "$p_lifecycle"
  printf '  "cor3_silent_when_inactive": %s,\n'   "$p_silent"
  printf '  "cor3_publishes_when_active": %s,\n'  "$p_active"
  printf '  "lifecycle_name": %s,\n'              "$(printf '%s' "${LC_NAME:--}" | json_escape)"
  printf '  "n_before": %d,\n'                    "${N_BEFORE:-0}"
  printf '  "n_after": %d,\n'                     "${N_AFTER:-0}"
  printf '  "n_state_lines": %d,\n'               "${N_STATE:-0}"
  printf '  "configure": %s,\n'                   "$(printf '%s' "$CONFIG_OUT" | json_escape)"
  printf '  "activate": %s,\n'                    "$(printf '%s' "$ACTIVATE_OUT" | json_escape)"
  printf '  "run_tail": %s\n'                     "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG" "$PROBE_LOG"
