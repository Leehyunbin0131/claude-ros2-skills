#!/usr/bin/env bash
# Real-outcome checks for gazebo-sim ladder rung L2 (evals/LADDER.md).
#
#   ./g2_check.sh <cell-workdir> <out.json>
#
# L2's mechanisms and the check that catches each:
#
#   gz-sim-sensors-system in the world  -> g2_scan_in_ros
#     (without it /scan advertises in Gazebo and never publishes -- the
#      headline silent failure in SKILL.md's symptom table)
#   360-sample lidar as specified       -> g2_scan_360
#   /clock bridged GZ->ROS              -> g2_clock_in_ros
#   bridge direction char on /cmd_vel   -> g2_ros_cmd_moves
#     ('[' is GZ->ROS, ']' is ROS->GZ, '@' bidirectional. With '[' the ROS
#      publisher never reaches the plugin and the robot sits still, with every
#      process healthy and nothing logged.)
#
# The cell's own `bringup.sh` is executed -- the checker does not reconstruct
# the bring-up, because then it would be grading its own wiring.
#
# THE RENDER ENGINE IS FORCED, via harness/gzshim on PATH. ogre2 segfaults
# headless on this machine, which would fail every cell for a reason unrelated
# to its SDF. See LADDER.md; no cell is scored on that crash.
set -uo pipefail

WORK="${1:?usage: g2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: g2_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"g2_bringup_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export PATH="$HARNESS/gzshim:$PATH"
export GZ_PARTITION="g2check$$"
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

p_scan=false; p_360=false; p_clock=false; p_moves=false
BR_LOG="$(mktemp)"
( cd "$(dirname "$BRINGUP")" && timeout 180 bash "$BRINGUP" ) >"$BR_LOG" 2>&1

# Give discovery time on both middlewares.
for _ in $(seq 1 30); do
  timeout 5 ros2 topic list 2>/dev/null | grep -q '/scan' && break
  sleep 1
done

SCAN="$(timeout 25 ros2 topic echo /scan --once --full-length 2>&1 | head -c 40000)"
# ranges: at least one finite value, and how many entries in total.
# `ros2 topic echo` prints float arrays as a YAML BLOCK SEQUENCE -- one
# "- value" per line -- not as an inline [a, b, c] list. The first version of
# this parser looked for brackets and reported 0 ranges on a lidar that was
# publishing perfectly, which would have failed every cell.
read -r N_RANGES N_FINITE <<<"$(python3 -c '
import re,sys
t=sys.stdin.read()
lines=t.splitlines()
try:
    i=next(k for k,l in enumerate(lines) if l.strip()=="ranges:")
except StopIteration:
    print("0 0"); raise SystemExit
vals=[]
for l in lines[i+1:]:
    s=l.strip()
    if not s.startswith("- "):
        break
    vals.append(s[2:].strip())
fin=[v for v in vals
     if re.fullmatch(r"-?[0-9.]+(?:[eE][-+]?[0-9]+)?", v)]
print(len(vals), len(fin))' <<<"$SCAN")"
[ "${N_FINITE:-0}" -gt 0 ] && p_scan=true
[ "${N_RANGES:-0}" -eq 360 ] && p_360=true

CLOCK="$(timeout 20 ros2 topic echo /clock --once 2>&1 | head -c 2000)"
grep -q 'sec:' <<<"$CLOCK" && p_clock=true

# Drive from the ROS side. Reading the pose on the GAZEBO side deliberately:
# the prompt never asked for /odom to be bridged, so requiring it would grade
# something the rung did not ask for.
gz_x() {
  timeout 8 gz topic -e -t /odom -n 1 2>/dev/null | python3 -c '
import re,sys
t=sys.stdin.read()
m=re.search(r"position\s*\{(.*?)\}", t, re.S)
if not m:
    print("nan"); raise SystemExit
mm=re.search(r"x:\s*(-?[0-9.]+(?:[eE][-+]?[0-9]+)?)", m.group(1))
print(mm.group(1) if mm else "0")'
}
X0="$(gz_x)"
timeout 20 ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.4}}' >/dev/null 2>&1 &
PUB=$!
sleep 6
X1="$(gz_x)"
kill $PUB 2>/dev/null || true
wait $PUB 2>/dev/null || true

V="$(mktemp)"
python3 -c '
import sys, math
x0, x1 = (float(v) if v not in ("nan", "") else math.nan for v in sys.argv[1:3])
moved = (not math.isnan(x0)) and (not math.isnan(x1)) and (x1 - x0) > 0.15
open(sys.argv[3], "w").write(str(int(moved)))' "$X0" "$X1" "$V"
[ "$(cat "$V")" = 1 ] && p_moves=true
rm -f "$V"

# Everything the bring-up started is a child of this shell's process group.
pkill -f "gz sim" 2>/dev/null || true
pkill -f "parameter_bridge" 2>/dev/null || true
sleep 1

{
  printf '{\n'
  printf '  "g2_bringup_found": true,\n'
  printf '  "bringup": %s,\n'         "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "g2_scan_in_ros": %s,\n'  "$p_scan"
  printf '  "g2_scan_360": %s,\n'     "$p_360"
  printf '  "g2_clock_in_ros": %s,\n' "$p_clock"
  printf '  "g2_ros_cmd_moves": %s,\n' "$p_moves"
  printf '  "n_ranges": %d,\n'        "${N_RANGES:-0}"
  printf '  "n_finite": %d,\n'        "${N_FINITE:-0}"
  printf '  "pose_x": "%s -> %s",\n'  "$X0" "$X1"
  printf '  "bringup_tail": %s\n'     "$(tail -c 1500 "$BR_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BR_LOG"
