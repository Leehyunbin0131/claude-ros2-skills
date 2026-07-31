#!/usr/bin/env bash
# Real-outcome checks for the ros2-perception ladder, rung L1.
#
#   ./per1_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   BEST_EFFORT camera vs default RELIABLE subscriber -> per1_frames
#     Verified on this install before the rung ran: a default rclpy subscriber
#     on /camera/image_raw gets 0 messages in 6 s and logs "offering
#     incompatible QoS ... Last incompatible policy: RELIABILITY". A
#     BEST_EFFORT one receives normally. `ros2 topic echo` auto-negotiates and
#     therefore CANNOT be used to probe this -- it reports data either way.
#
#   cv_bridge round trip + republish -> per1_publishes
#     Graded by subscribing to /annotated from outside the node while it runs.
#
# Graded by RUNNING the cell's node.py against the live camera. Nothing reads
# the source: SensorDataQoS, an explicit QoSProfile, image_transport or
# anything else that works is equally correct.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1, so `|| echo 0` yields
#     "0\n0" and printf %d chokes. awk instead.
#   * pkill anchored to `^python3 ` so it cannot match a wrapper shell
#   * kill -9, and never `wait` on a child that may ignore SIGTERM: rclpy inside
#     spin() does not reliably act on it, and that hung a checker for 4 h 48 m
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: per1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: per1_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"per1_node_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f '^python3 .*camera_publisher\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*annotated_probe\.py' 2>/dev/null || true
}
kill_all
sleep 1

python3 "$HARNESS/camera_publisher.py" >/dev/null 2>&1 &
for _ in $(seq 1 20); do
  TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
  case "$TL" in *camera/image_raw*) break ;; esac
  sleep 1
done

# Independent subscriber on /annotated, started BEFORE the node so it cannot
# miss the early frames. Accepts either reliability: the prompt does not say
# which the cell must publish with, so grading one of them would assert
# something the task never required.
PROBE_LOG="$(mktemp)"
cat > /tmp/annotated_probe.py <<'PYEOF'
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

class Probe(Node):
    def __init__(self):
        super().__init__("annotated_probe")
        self.n = 0
        for rel in (ReliabilityPolicy.BEST_EFFORT, ReliabilityPolicy.RELIABLE):
            self.create_subscription(
                Image, "/annotated", self.cb,
                QoSProfile(depth=10, reliability=rel))
        # Report continuously, not once at the end. Reporting only on a final
        # timer meant the checker -- which kills the probe as soon as the cell's
        # node has exited -- read a count that had never been printed, and a
        # correct reference scored 0. Caught by validating against a known-good
        # reference before the rung ran.
        self.create_timer(0.5, self.report)
    def cb(self, m):
        self.n += 1
    def report(self):
        print(f"ANNOTATED {self.n}", flush=True)

rclpy.init()
try:
    rclpy.spin(Probe())
except SystemExit:
    pass
PYEOF
timeout 50 python3 /tmp/annotated_probe.py >"$PROBE_LOG" 2>&1 &
PROBE=$!
sleep 2

RUN_LOG="$(mktemp)"
# 20 frames at 20 Hz needs 1 s. 40 s is unreachable for a subscriber that never
# matches, and generous for one that does.
START=$(date +%s)
timeout 40 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))

# Let the probe drain anything still in flight, then read its count.
sleep 3
kill -9 $PROBE 2>/dev/null || true
N_ANN=$(awk '/^ANNOTATED/ {print $2; found=1} END {if (!found) print 0}' "$PROBE_LOG" 2>/dev/null | tail -1)
kill_all

N_FRAME=$(awk '/FRAME/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)
SAW_WARN=$(awk '/incompatible QoS/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)

p_frames=false;  [ "${N_FRAME:-0}" -ge 20 ] && p_frames=true
p_pub=false;     [ "${N_ANN:-0}" -ge 1 ] && p_pub=true
p_nohang=false;  [ "$RC" -ne 124 ] && p_nohang=true
p_clean=false;   [ "$RC" -eq 0 ] && p_clean=true

{
  printf '{\n'
  printf '  "per1_node_found": true,\n'
  printf '  "node": %s,\n'              "$(printf '%s' "$NODE" | json_escape)"
  printf '  "per1_frames": %s,\n'       "$p_frames"
  printf '  "per1_publishes": %s,\n'    "$p_pub"
  printf '  "per1_no_hang": %s,\n'      "$p_nohang"
  printf '  "per1_exits_clean": %s,\n'  "$p_clean"
  printf '  "n_frame": %d,\n'           "${N_FRAME:-0}"
  printf '  "n_annotated": %d,\n'       "${N_ANN:-0}"
  printf '  "saw_incompat_warn": %d,\n' "${SAW_WARN:-0}"
  printf '  "exit_code": %d,\n'         "$RC"
  printf '  "elapsed_s": %d,\n'         "$ELAPSED"
  printf '  "run_tail": %s\n'           "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG" "$PROBE_LOG"
