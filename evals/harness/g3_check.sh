#!/usr/bin/env bash
# Real-outcome checks for gazebo-sim ladder rung L3 (evals/LADDER.md).
#
#   ./g3_check.sh <cell-workdir> <out.json>
#
# L3's mechanisms and the check that catches each:
#
#   URDF on /robot_description, spawned with ros_gz_sim -> g3_spawned
#   gz-sim-imu-system in the world                      -> g3_imu_in_ros
#     (without it /imu never publishes -- silent, like the sensors-system case
#      at L2)
#   sensor frame naming                                 -> g3_frame_id_is_link
#     (Gazebo composes <model>/<link>/<sensor> unless <gz_frame_id> says
#      otherwise; SKILL.md's symptom table calls this out)
#   /clock bridged, so use_sim_time works               -> g3_sim_time
#     (checked by running a ROS node with use_sim_time:=true and reading its
#      clock -- sim time starts near 0, wall time is ~1.7e9 s)
#
# The cell's own bringup.sh is executed. Render engine forced via harness/gzshim.
#
# Two traps this file exists downstream of, both cost a full round at L2:
#   * `cmd | grep -q X` under `set -o pipefail` reports FAILURE on a match --
#     grep exits early, the producer takes SIGPIPE. Capture first, then match.
#   * `gz sim` ignores SIGTERM headless; strays survive `pkill` and leak into
#     `gz topic -l`. Kill with -9, before and after.
set -uo pipefail

WORK="${1:?usage: g3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: g3_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"g3_bringup_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export PATH="$HARNESS/gzshim:$PATH"
export GZ_PARTITION="g3check$$"
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_sims() {
  pkill -f '^gz sim' 2>/dev/null || true
  pkill -f '^.*/parameter_bridge' 2>/dev/null || true
  pkill -f 'robot_state_publisher' 2>/dev/null || true
  sleep 2
  pkill -9 -f '^gz sim' 2>/dev/null || true
  pkill -9 -f '^.*/parameter_bridge' 2>/dev/null || true
  pkill -9 -f 'robot_state_publisher' 2>/dev/null || true
}
kill_sims
sleep 1

p_spawn=false; p_imu=false; p_frame=false; p_time=false
BR_LOG="$(mktemp)"
( cd "$(dirname "$BRINGUP")" && timeout 240 bash "$BRINGUP" ) >"$BR_LOG" 2>&1

for _ in $(seq 1 30); do
  TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
  case "$TL" in */imu*) break ;; esac
  sleep 1
done

# 1. the model reached the running simulation.
#
# NOT "at least 2 models". The first version assumed a ground plane plus the
# robot and scored 5 of 10 cells as "never spawned" while their IMU was
# publishing into ROS -- impossible for a robot that is not in the world. Those
# five simply built a world with no ground plane, which **the g3 prompt never
# asked for**. Identical mistake to hardcoding /odom at L2: the grader asserting
# something the frozen prompt does not require.
#
# The robot's name comes from the cell's own URDF, and that exact name has to
# appear in the model list.
ROBOT_NAME="$(grep -ho '<robot[^>]*name="[^"]*"' "$WORK"/*.urdf "$WORK"/**/*.urdf \
              "$WORK"/*.xacro "$WORK"/**/*.xacro 2>/dev/null \
              | head -1 | sed 's/.*name="//;s/"//')"
MODELS="$(timeout 10 gz model --list 2>/dev/null || true)"
N_MODELS=$(grep -c '^ *- ' <<<"$MODELS" 2>/dev/null || echo 0)
if [ -n "$ROBOT_NAME" ]; then
  case "$MODELS" in *"$ROBOT_NAME"*) p_spawn=true ;; esac
else
  # No URDF name to match on: fall back to "some model besides a ground plane".
  NON_GROUND=$(grep '^ *- ' <<<"$MODELS" | grep -icv 'ground' || echo 0)
  [ "${NON_GROUND:-0}" -ge 1 ] && p_spawn=true
fi

# 2/3. the IMU reaches ROS, and its frame_id is a link the URDF declares --
#      not Gazebo's composed <model>/<link>/<sensor>.
IMU="$(timeout 25 ros2 topic echo /imu --once 2>&1 | head -c 4000)"
case "$IMU" in *linear_acceleration*) p_imu=true ;; esac

FRAME="$(sed -n 's/^ *frame_id: *//p' <<<"$IMU" | head -1 | tr -d '\r')"
URDF="$(find "$WORK" -maxdepth 4 \( -name '*.urdf' -o -name '*.xacro' -o -name '*.urdf.xml' \) \
        -print0 2>/dev/null | xargs -0 cat 2>/dev/null || true)"
LINKS="$(grep -o '<link[^>]*name="[^"]*"' <<<"$URDF" | sed 's/.*name="//;s/"//' | sort -u)"
if [ -n "$FRAME" ] && [ -n "$LINKS" ]; then
  while IFS= read -r l; do
    [ -n "$l" ] || continue
    [ "$FRAME" = "$l" ] && { p_frame=true; break; }
  done <<<"$LINKS"
fi

# 4. a ROS node with use_sim_time:=true sees Gazebo time. Sim time starts near
#    zero; wall time is ~1.7e9 seconds since the epoch, so the two are never
#    ambiguous.
CLK="$(mktemp /tmp/g3clk-XXXX.py)"
cat > "$CLK" <<'PY'
import rclpy
from rclpy.node import Node
rclpy.init()
n = Node("g3_clock_probe",
         parameter_overrides=[rclpy.parameter.Parameter("use_sim_time", value=True)])
for _ in range(80):
    rclpy.spin_once(n, timeout_sec=0.1)
    t = n.get_clock().now().nanoseconds
    if 0 < t < 10**15:          # sim time: small. wall time: ~1.75e18 ns.
        print("SIMTIME", t)
        break
else:
    print("WALLTIME", n.get_clock().now().nanoseconds)
rclpy.shutdown()
PY
CLK_OUT="$(timeout 40 python3 "$CLK" 2>&1 | tail -1)"
case "$CLK_OUT" in SIMTIME*) p_time=true ;; esac
rm -f "$CLK"

kill_sims
sleep 1

{
  printf '{\n'
  printf '  "g3_bringup_found": true,\n'
  printf '  "bringup": %s,\n'             "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "g3_spawned": %s,\n'          "$p_spawn"
  printf '  "g3_imu_in_ros": %s,\n'       "$p_imu"
  printf '  "g3_frame_id_is_link": %s,\n' "$p_frame"
  printf '  "g3_sim_time": %s,\n'         "$p_time"
  printf '  "frame_id": %s,\n'            "$(printf '%s' "$FRAME" | json_escape)"
  printf '  "urdf_links": %s,\n'          "$(printf '%s' "$LINKS" | json_escape)"
  printf '  "n_models": %d,\n'            "${N_MODELS:-0}"
  printf '  "robot_name": %s,\n'          "$(printf '%s' "${ROBOT_NAME:-}" | json_escape)"
  printf '  "models": %s,\n'              "$(printf '%s' "$MODELS" | json_escape)"
  printf '  "clock_probe": %s,\n'         "$(printf '%s' "$CLK_OUT" | json_escape)"
  printf '  "bringup_tail": %s\n'         "$(tail -c 1500 "$BR_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BR_LOG"
