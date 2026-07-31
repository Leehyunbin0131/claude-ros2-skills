#!/usr/bin/env bash
# Real-outcome checks for the ros2-perception ladder, rung L3.
#
#   ./per3_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   subscribing to a BEST_EFFORT depth camera  -> per3_clouds
#   building a PointCloud2 with x/y/z float32  -> per3_fields_ok
#   depth in METRES, not raw 16UC1 millimetres -> per3_metres
#   dropping invalid (zero) depth pixels       -> per3_drops_invalid
#
# The scenario publishes 16UC1 depth in MILLIMETRES, ramping 500..3000 across a
# 160x120 frame, with the left fifth zeroed to mean "no return". So:
#
#   correct  -> z within [0.5, 3.0] m, and about 4/5 of 19200 pixels kept
#   mm bug   -> z in the hundreds; `per3_metres` fails
#   zeros in -> a wall of points at z=0 and the full 19200 count;
#               `per3_drops_invalid` fails
#
# Graded by SUBSCRIBING to the cloud the cell publishes and reading the points
# back with point_cloud2.read_points. Nothing reads the source.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * the probe must be spinning and announced BEFORE the node starts, and a
#     fixed sleep is not enough under load: wait for its own first report line,
#     then retry the run once if nothing arrives
#   * pkill anchored to `^python3 `
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: per3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: per3_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"per3_node_found": false}\n' > "$OUT"
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
  pkill -9 -f '^python3 .*cloud_probe\.py' 2>/dev/null || true
}
kill_all
sleep 1

python3 "$HARNESS/camera_publisher.py" --depth >/dev/null 2>&1 &
for _ in $(seq 1 20); do
  TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
  case "$TL" in *depth/camera_info*) break ;; esac
  sleep 1
done

PROBE_LOG="$(mktemp)"
cat > /tmp/cloud_probe.py <<'PYEOF'
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2

# The scenario's depth ramps 500..3000 mm with the left fifth zeroed.
Z_LO, Z_HI = 0.4, 3.2          # metres, with slack for interpolation
TOTAL_PIXELS = 160 * 120
VALID_PIXELS = TOTAL_PIXELS * 4 // 5


class Probe(Node):
    def __init__(self):
        super().__init__("cloud_probe")
        self.n = 0
        self.fields_ok = 0
        self.metres_ok = 0
        self.drops_ok = 0
        self.last = ""
        for rel in (ReliabilityPolicy.BEST_EFFORT, ReliabilityPolicy.RELIABLE):
            self.create_subscription(
                PointCloud2, "/points", self.cb,
                QoSProfile(depth=5, reliability=rel))
        self.create_timer(0.5, self.report)

    def cb(self, msg):
        self.n += 1
        names = {f.name for f in msg.fields}
        if {"x", "y", "z"} <= names:
            self.fields_ok += 1
        try:
            pts = list(point_cloud2.read_points(
                msg, field_names=("x", "y", "z"), skip_nans=True))
        except Exception:
            return
        if not pts:
            return
        zs = [float(p[2]) for p in pts]
        finite = [z for z in zs if z == z]
        if not finite:
            return
        zmin, zmax = min(finite), max(finite)
        self.last = f"n={len(pts)} zmin={zmin:.3f} zmax={zmax:.3f}"
        # Metres, not millimetres: the whole cloud must sit in the physical range.
        if Z_LO <= zmin and zmax <= Z_HI:
            self.metres_ok += 1
        # Invalid pixels dropped: a cloud that keeps the zeros carries every
        # pixel and a z=0 wall.
        near_zero = sum(1 for z in finite if abs(z) < 0.05)
        if len(pts) <= VALID_PIXELS * 1.05 and near_zero <= len(pts) * 0.02:
            self.drops_ok += 1

    def report(self):
        print(f"CLOUD {self.n} FIELDS {self.fields_ok} METRES {self.metres_ok} "
              f"DROPS {self.drops_ok} LAST {self.last}", flush=True)


rclpy.init()
try:
    rclpy.spin(Probe())
except SystemExit:
    pass
PYEOF

RUN_LOG="$(mktemp)"
run_once() {
  : > "$PROBE_LOG"
  timeout 90 python3 /tmp/cloud_probe.py >"$PROBE_LOG" 2>&1 &
  PROBE=$!
  for _ in $(seq 1 40); do
    if awk '/^CLOUD/ {f=1} END {exit !f}' "$PROBE_LOG" 2>/dev/null; then break; fi
    sleep 0.5
  done

  START=$(date +%s)
  timeout 60 python3 "$NODE" >"$RUN_LOG" 2>&1
  RC=$?
  ELAPSED=$(( $(date +%s) - START ))

  sleep 3
  kill -9 $PROBE 2>/dev/null || true
  read -r N_CLOUD N_FIELDS N_METRES N_DROPS <<<"$(awk '
    /^CLOUD/ {c=$2; f=$4; m=$6; d=$8}
    END {printf "%d %d %d %d", c+0, f+0, m+0, d+0}' "$PROBE_LOG" 2>/dev/null)"
  LAST="$(awk '/^CLOUD/ {sub(/.*LAST /, ""); l=$0} END {print (l=="" ? "-" : l)}' "$PROBE_LOG" 2>/dev/null)"
}

ATTEMPTS=1
run_once
if [ "${N_CLOUD:-0}" -eq 0 ] && [ "$RC" -eq 0 ]; then
  ATTEMPTS=2
  pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true
  sleep 2
  run_once
fi
kill_all

N_LOG=$(awk '/CLOUD/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)
SAW_WARN=$(awk '/incompatible QoS/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)

p_clouds=false; [ "${N_CLOUD:-0}" -ge 1 ] && p_clouds=true
p_fields=false; [ "${N_FIELDS:-0}" -ge 1 ] && p_fields=true
p_metres=false; [ "${N_METRES:-0}" -ge 1 ] && p_metres=true
p_drops=false;  [ "${N_DROPS:-0}" -ge 1 ] && p_drops=true

{
  printf '{\n'
  printf '  "per3_node_found": true,\n'
  printf '  "node": %s,\n'                 "$(printf '%s' "$NODE" | json_escape)"
  printf '  "per3_clouds": %s,\n'          "$p_clouds"
  printf '  "per3_fields_ok": %s,\n'       "$p_fields"
  printf '  "per3_metres": %s,\n'          "$p_metres"
  printf '  "per3_drops_invalid": %s,\n'   "$p_drops"
  printf '  "n_clouds_seen": %d,\n'        "${N_CLOUD:-0}"
  printf '  "n_fields_ok": %d,\n'          "${N_FIELDS:-0}"
  printf '  "n_metres_ok": %d,\n'          "${N_METRES:-0}"
  printf '  "n_drops_ok": %d,\n'           "${N_DROPS:-0}"
  printf '  "n_cloud_log_lines": %d,\n'    "${N_LOG:-0}"
  printf '  "last_cloud": %s,\n'           "$(printf '%s' "${LAST:--}" | json_escape)"
  printf '  "saw_incompat_warn": %d,\n'    "${SAW_WARN:-0}"
  printf '  "exit_code": %d,\n'            "$RC"
  printf '  "elapsed_s": %d,\n'            "$ELAPSED"
  printf '  "attempts": %d,\n'             "${ATTEMPTS:-1}"
  printf '  "run_tail": %s\n'              "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG" "$PROBE_LOG"
