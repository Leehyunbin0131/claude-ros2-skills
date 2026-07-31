#!/usr/bin/env bash
# Real-outcome checks for the ros2-perception ladder, rung L2.
#
#   ./per2_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   reading intrinsics off a live CameraInfo    -> per2_pixel_correct
#   publishing a vision_msgs/Detection2D        -> per2_detection_published
#   the detection's centre matching that pixel  -> per2_detection_correct
#
# The scenario's intrinsics are a plain pinhole model with no distortion, so the
# projection has exactly one right answer:
#
#   fx = fy = 100.0, cx = 80.0, cy = 60.0
#   (0.1, 0.05, 2.0) -> u = 100*0.1/2.0 + 80 = 85.0
#                       v = 100*0.05/2.0 + 60 = 62.5
#
# K and P carry the same values on purpose: per2 grades the pixel, not which
# matrix was read, so a cell that picks either is correct and the check cannot
# punish a defensible choice.
#
# Tolerance is 1.0 px, which admits rounding to int pixel coordinates (85, 62 or
# 85, 63) and excludes reading the wrong field or forgetting the principal
# point -- both of which land tens of pixels away.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * a probe that reports only at the end reads as zero when the checker kills
#     it as soon as the cell's node exits -- report continuously
#   * pkill anchored to `^python3 `
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: per2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: per2_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"per2_node_found": false}\n' > "$OUT"
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
  pkill -9 -f '^python3 .*detection_probe\.py' 2>/dev/null || true
}
kill_all
sleep 1

python3 "$HARNESS/camera_publisher.py" >/dev/null 2>&1 &
for _ in $(seq 1 20); do
  TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
  case "$TL" in *camera/camera_info*) break ;; esac
  sleep 1
done

PROBE_LOG="$(mktemp)"
cat > /tmp/detection_probe.py <<'PYEOF'
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from vision_msgs.msg import Detection2D

U, V, TOL = 85.0, 62.5, 1.0


class Probe(Node):
    def __init__(self):
        super().__init__("detection_probe")
        self.n = 0
        self.ok = 0
        self.last = ""
        # Accept either reliability: the prompt does not say which the cell must
        # publish with, so grading one of them would assert something the task
        # never required.
        for rel in (ReliabilityPolicy.BEST_EFFORT, ReliabilityPolicy.RELIABLE):
            self.create_subscription(
                Detection2D, "/detection", self.cb,
                QoSProfile(depth=10, reliability=rel))
        self.create_timer(0.5, self.report)

    def cb(self, msg):
        self.n += 1
        c = msg.bbox.center
        # vision_msgs Pose2D on Jazzy nests position under .position
        x = getattr(getattr(c, "position", c), "x", None)
        y = getattr(getattr(c, "position", c), "y", None)
        if x is None or y is None:
            return
        self.last = f"{x:.2f},{y:.2f}"
        if abs(x - U) <= TOL and abs(y - V) <= TOL:
            self.ok += 1

    def report(self):
        print(f"DET {self.n} OK {self.ok} LAST {self.last}", flush=True)


rclpy.init()
try:
    rclpy.spin(Probe())
except SystemExit:
    pass
PYEOF
timeout 70 python3 /tmp/detection_probe.py >"$PROBE_LOG" 2>&1 &
PROBE=$!
sleep 2

RUN_LOG="$(mktemp)"
START=$(date +%s)
timeout 50 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))

sleep 3
kill -9 $PROBE 2>/dev/null || true
read -r N_DET N_OK LAST <<<"$(awk '/^DET/ {d=$2; o=$4; l=$6} END {printf "%d %d %s", d+0, o+0, (l=="" ? "-" : l)}' "$PROBE_LOG" 2>/dev/null)"
kill_all

# PIXEL <u> <v> lines from the node itself, checked against the one right answer.
read -r N_PIX N_PIX_OK <<<"$(awk '
  /PIXEL/ {
    for (i = 1; i <= NF; i++) if ($i ~ /PIXEL/) { u = $(i+1) + 0; v = $(i+2) + 0; break }
    n++
    du = u - 85.0; if (du < 0) du = -du
    dv = v - 62.5; if (dv < 0) dv = -dv
    if (du <= 1.0 && dv <= 1.0) ok++
  }
  END { printf "%d %d", n+0, ok+0 }' "$RUN_LOG" 2>/dev/null)"

p_pix=false;    [ "${N_PIX_OK:-0}" -ge 20 ] && p_pix=true
p_detpub=false; [ "${N_DET:-0}" -ge 1 ] && p_detpub=true
p_detok=false;  [ "${N_OK:-0}" -ge 1 ] && p_detok=true
p_clean=false;  [ "$RC" -eq 0 ] && p_clean=true

{
  printf '{\n'
  printf '  "per2_node_found": true,\n'
  printf '  "node": %s,\n'                       "$(printf '%s' "$NODE" | json_escape)"
  printf '  "per2_pixel_correct": %s,\n'         "$p_pix"
  printf '  "per2_detection_published": %s,\n'   "$p_detpub"
  printf '  "per2_detection_correct": %s,\n'     "$p_detok"
  printf '  "per2_exits_clean": %s,\n'           "$p_clean"
  printf '  "n_pixel_lines": %d,\n'              "${N_PIX:-0}"
  printf '  "n_pixel_correct": %d,\n'            "${N_PIX_OK:-0}"
  printf '  "n_detections": %d,\n'               "${N_DET:-0}"
  printf '  "n_detections_correct": %d,\n'       "${N_OK:-0}"
  printf '  "last_detection_centre": %s,\n'      "$(printf '%s' "${LAST:--}" | json_escape)"
  printf '  "exit_code": %d,\n'                  "$RC"
  printf '  "elapsed_s": %d,\n'                  "$ELAPSED"
  printf '  "run_tail": %s\n'                    "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG" "$PROBE_LOG"
