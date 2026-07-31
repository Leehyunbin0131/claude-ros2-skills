#!/usr/bin/env bash
# Real-outcome checks for the ros2-dev ladder, rung L1.
#
#   ./dev1_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a Nav2 parameter file that is valid YAML       -> dev1_yaml_valid
#   Nav2's own servers accepting it as-is          -> dev1_servers_load
#   the MPPI controller actually selected          -> dev1_mppi
#   the robot's real geometry in it, not a default -> dev1_footprint
#
# `dev1_servers_load` is the rung. A file can be perfect YAML, name every
# server, and still be rejected the moment a server parses it -- a wrong plugin
# string or a misplaced key is invisible until then. So the check LAUNCHES the
# real `controller_server` and `planner_server` against the file and asks
# whether they came up, rather than reading the YAML for the right words.
#
# `dev1_footprint` is graded from what the loaded parameters report, not from
# the text: the prompt fixes a 0.3 m radius circular footprint and a 0.4 m/s
# maximum speed, and a file copied wholesale from nav2_bringup carries the
# tutorial robot's values instead.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * lifecycle servers ignore SIGTERM -- kill -9, never `wait` on them
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: dev1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: dev1_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

PARAMS="$(find "$WORK" -maxdepth 3 -name 'nav2_params.yaml' -print -quit 2>/dev/null)"
[ -n "$PARAMS" ] || PARAMS="$(find "$WORK" -maxdepth 3 -name '*.yaml' -print -quit 2>/dev/null)"
if [ -z "$PARAMS" ]; then
  printf '{"dev1_params_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f 'controller_server' 2>/dev/null || true
  pkill -9 -f 'planner_server' 2>/dev/null || true
}
kill_all
sleep 1

# --- 1. valid YAML, and does it declare the servers? -------------------------
YAML_OUT="$(timeout 30 python3 - "$PARAMS" <<'PYEOF' 2>&1
import sys
import yaml

try:
    with open(sys.argv[1]) as f:
        d = yaml.safe_load(f)
except Exception as e:
    print(f"YAML_ERROR {e}")
    sys.exit(0)
if not isinstance(d, dict):
    print("YAML_NOT_MAPPING")
    sys.exit(0)

print("YAML_OK")
print("SERVERS " + ",".join(sorted(k for k in d if k.endswith("_server"))))

blob = yaml.safe_dump(d)
print("MPPI " + ("yes" if "nav2_mppi_controller" in blob else "no"))

# radius and speed, wherever the cell put them
rad = spd = None
def walk(node):
    global rad, spd
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "robot_radius" and isinstance(v, (int, float)):
                rad = float(v)
            if k in ("vx_max", "max_vel_x") and isinstance(v, (int, float)):
                spd = float(v)
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)
walk(d)
print(f"RADIUS {rad}")
print(f"SPEED {spd}")
PYEOF
)"

YAML_VALID=false
printf '%s' "$YAML_OUT" | awk '/^YAML_OK/ {f=1} END {exit !f}' && YAML_VALID=true

MPPI=false
printf '%s' "$YAML_OUT" | awk '/^MPPI yes/ {f=1} END {exit !f}' && MPPI=true

RADIUS="$(printf '%s' "$YAML_OUT" | awk '/^RADIUS/ {print $2; exit}')"
SPEED="$(printf '%s' "$YAML_OUT" | awk '/^SPEED/ {print $2; exit}')"
FOOTPRINT=false
if [ -n "${RADIUS:-}" ] && [ "$RADIUS" != "None" ]; then
  awk -v r="$RADIUS" 'BEGIN { exit !(r-0.3<0.02 && 0.3-r<0.02) }' && FOOTPRINT=true
fi

# --- 2. do Nav2's own servers accept the file? -------------------------------
# The decisive check: a file that parses can still be rejected by the server.
CS_LOG="$(mktemp)"
PS_LOG="$(mktemp)"
timeout 60 ros2 run nav2_controller controller_server \
  --ros-args --params-file "$PARAMS" >"$CS_LOG" 2>&1 &
timeout 60 ros2 run nav2_planner planner_server \
  --ros-args --params-file "$PARAMS" >"$PS_LOG" 2>&1 &

CS_UP=false
PS_UP=false
for _ in $(seq 1 30); do
  NL="$(timeout 5 ros2 node list 2>/dev/null || true)"
  case "$NL" in *controller_server*) CS_UP=true ;; esac
  case "$NL" in *planner_server*) PS_UP=true ;; esac
  $CS_UP && $PS_UP && break
  sleep 1
done

# Appearing in `ros2 node list` proves nothing: a Nav2 server starts
# `unconfigured` and does not touch its plugins until it is configured. Both a
# correct file and one whose controller plugin has lost its package namespace
# come up identically here -- verified on this install before the rung ran. So
# drive the lifecycle transition and read the state back; that is the point at
# which the plugin string is resolved and a bad one is rejected.
CS_STATE="-"
PS_STATE="-"
if $CS_UP; then
  timeout 45 ros2 lifecycle set /controller_server configure >/dev/null 2>&1 || true
  CS_STATE="$(timeout 15 ros2 lifecycle get /controller_server 2>&1 | head -1)"
fi
if $PS_UP; then
  timeout 45 ros2 lifecycle set /planner_server configure >/dev/null 2>&1 || true
  PS_STATE="$(timeout 15 ros2 lifecycle get /planner_server 2>&1 | head -1)"
fi

SERVERS_LOAD=false
if printf '%s' "$CS_STATE" | awk '$1=="inactive" {f=1} END {exit !f}' \
   && printf '%s' "$PS_STATE" | awk '$1=="inactive" {f=1} END {exit !f}'; then
  SERVERS_LOAD=true
fi
kill_all

p_yaml=false;    $YAML_VALID && p_yaml=true
p_servers=false; $SERVERS_LOAD && p_servers=true
p_mppi=false;    $MPPI && p_mppi=true
p_foot=false;    $FOOTPRINT && p_foot=true

{
  printf '{\n'
  printf '  "dev1_params_found": true,\n'
  printf '  "params": %s,\n'            "$(printf '%s' "$PARAMS" | json_escape)"
  printf '  "dev1_yaml_valid": %s,\n'   "$p_yaml"
  printf '  "dev1_servers_load": %s,\n' "$p_servers"
  printf '  "dev1_mppi": %s,\n'         "$p_mppi"
  printf '  "dev1_footprint": %s,\n'    "$p_foot"
  printf '  "radius": %s,\n'            "$(printf '%s' "${RADIUS:-None}" | json_escape)"
  printf '  "speed": %s,\n'             "$(printf '%s' "${SPEED:-None}" | json_escape)"
  printf '  "yaml_probe": %s,\n'        "$(printf '%s' "$YAML_OUT" | head -c 600 | json_escape)"
  printf '  "cs_state": %s,\n'         "$(printf '%s' "$CS_STATE" | json_escape)"
  printf '  "ps_state": %s,\n'         "$(printf '%s' "$PS_STATE" | json_escape)"
  printf '  "controller_tail": %s,\n'   "$(tail -c 700 "$CS_LOG" | json_escape)"
  printf '  "planner_tail": %s\n'       "$(tail -c 700 "$PS_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$CS_LOG" "$PS_LOG"
