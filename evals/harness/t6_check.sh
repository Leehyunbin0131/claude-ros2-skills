#!/usr/bin/env bash
# Real-outcome checks for T6 -- `ros2-package` ladder rung L2. See
# evals/LADDER.md for the rung definition and the rules that freeze it.
#
#   ./t6_check.sh <cell-workdir> <out.json>
#
# L2 adds three mechanisms over L1, and each has exactly one check:
#
#   a C++ ament_cmake package WITH an executable  -> t6_cpp_run_works
#     (L1 had no C++ executable, so the `install(TARGETS ... DESTINATION
#      lib/${PROJECT_NAME})` rule was never exercised)
#   a .srv used from both C++ and Python          -> t6_srv_resolves,
#                                                    t6_service_available
#   a launch file including another package's     -> t6_composed_launch
#     (needs install(DIRECTORY launch ...) in the C++ package for the include
#      to resolve)
#
# Verified to discriminate before the rung ran (2026-07-30, this install):
#
#   variant         builds  srv  cpp_run  py_run  composed  service
#   good              y      y      y        y       y         y
#   cpp_bin           y      y     FAIL      y      FAIL      FAIL
#   no_cpp_launch     y      y      y        y      FAIL      FAIL
#
# Both defects build clean, as at L1.
set -uo pipefail

WORK="${1:?usage: t6_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: t6_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

WS=""
while IFS= read -r d; do
  [ -n "$(find "$d/src" -maxdepth 3 -name package.xml -print -quit 2>/dev/null)" ] || continue
  WS="$d"; break
done < <(find "$WORK" -maxdepth 4 -type d -name src -printf '%h\n' 2>/dev/null | sort)

if [ -z "$WS" ]; then
  printf '{"t6_workspace_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

# A unique domain per check run: the composed-launch check reads `ros2 node
# list`, and anything else on the default domain would show up in it.
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

rm -rf "$WS/build" "$WS/install" "$WS/log"
BUILD_LOG="$(mktemp)"
( cd "$WS" && colcon build --event-handlers console_direct+ ) >"$BUILD_LOG" 2>&1
BUILD_RC=$?

p_builds=false; [ $BUILD_RC -eq 0 ] && p_builds=true
p_srv=false; p_cpp=false; p_py=false; p_comp=false; p_svc=false

if [ -f "$WS/install/setup.bash" ]; then
  set +u
  # shellcheck disable=SC1091
  source "$WS/install/setup.bash"
  set -u

  # 1. the .srv generated, with both fields on the right side of the ---
  SRV="$(ros2 interface show battery_msgs/srv/SetLimit 2>&1)"
  if grep -q 'float32[[:space:]]\+max_voltage' <<<"$SRV" \
     && grep -q 'bool[[:space:]]\+accepted' <<<"$SRV"; then
    p_srv=true
  fi

  # 2/3. `ros2 run` finds each executable. The C++ one is the check that
  # catches an install destination other than lib/<pkg>/.
  for pair in "battery_cpp guard:cpp" "battery_py monitor:py"; do
    spec="${pair%:*}"; tag="${pair#*:}"
    o="$(timeout 12 ros2 run $spec 2>&1)"
    if ! grep -qi 'no executable found\|package .* not found\|No such file' <<<"$o"; then
      [ "$tag" = cpp ] && p_cpp=true || p_py=true
    fi
  done

  # 4/5. the composed launch brings BOTH nodes up, and the service appears with
  # the right type. This is the only check that exercises the cross-package
  # launch include end to end.
  LOG="$(mktemp)"
  timeout 30 ros2 launch battery_py system.launch.py >"$LOG" 2>&1 &
  LPID=$!
  NODES=""; SVCS=""
  for _ in $(seq 1 20); do
    NODES="$(timeout 5 ros2 node list 2>/dev/null)"
    SVCS="$(timeout 5 ros2 service list -t 2>/dev/null)"
    grep -q 'guard' <<<"$NODES" && grep -q 'monitor' <<<"$NODES" && break
    sleep 1
  done
  grep -q 'guard' <<<"$NODES" && grep -q 'monitor' <<<"$NODES" && p_comp=true
  grep -q '/set_limit \[battery_msgs/srv/SetLimit\]' <<<"$SVCS" && p_svc=true
  kill $LPID 2>/dev/null || true
  wait $LPID 2>/dev/null || true
  LAUNCH_TAIL="$(tail -c 1200 "$LOG")"
  rm -f "$LOG"
else
  LAUNCH_TAIL="(no install tree)"
fi

{
  printf '{\n'
  printf '  "t6_workspace_found": true,\n'
  printf '  "ws": %s,\n'                    "$(printf '%s' "$WS" | json_escape)"
  printf '  "t6_builds": %s,\n'             "$p_builds"
  printf '  "t6_srv_resolves": %s,\n'       "$p_srv"
  printf '  "t6_cpp_run_works": %s,\n'      "$p_cpp"
  printf '  "t6_py_run_works": %s,\n'       "$p_py"
  printf '  "t6_composed_launch": %s,\n'    "$p_comp"
  printf '  "t6_service_available": %s,\n'  "$p_svc"
  printf '  "build_rc": %d,\n'              "$BUILD_RC"
  printf '  "nodes_seen": %s,\n'            "$(printf '%s' "${NODES:-}" | json_escape)"
  printf '  "launch_tail": %s,\n'           "$(printf '%s' "$LAUNCH_TAIL" | json_escape)"
  printf '  "build_tail": %s\n'             "$(tail -c 2000 "$BUILD_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"

rm -f "$BUILD_LOG"
