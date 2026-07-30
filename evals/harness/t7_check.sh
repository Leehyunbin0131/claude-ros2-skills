#!/usr/bin/env bash
# Real-outcome checks for T7 -- `ros2-package` ladder rung L3. Rung frozen in
# evals/LADDER.md before any cell ran.
#
#   ./t7_check.sh <cell-workdir> <out.json>
#
# L3 adds three mechanisms over L2, each with its own check:
#
#   a .msg field typed by another package's message  -> t7_msg_dep_resolves
#   a composable node in an rclcpp_components        -> t7_component_registered
#     container                                         t7_component_loads
#   a test that colcon test actually runs            -> t7_tests_ran,
#                                                       t7_tests_pass
#
# `t7_tests_ran` is separate from `t7_tests_pass` on purpose: **`colcon test`
# exits 0 when there are no tests at all.** "The tests pass" is not a claim
# until something has been shown to run, which is the same class of silent
# success as a packaging defect that builds clean.
set -uo pipefail

WORK="${1:?usage: t7_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: t7_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

WS=""
while IFS= read -r d; do
  [ -n "$(find "$d/src" -maxdepth 3 -name package.xml -print -quit 2>/dev/null)" ] || continue
  WS="$d"; break
done < <(find "$WORK" -maxdepth 4 -type d -name src -printf '%h\n' 2>/dev/null | sort)

if [ -z "$WS" ]; then
  printf '{"t7_workspace_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

rm -rf "$WS/build" "$WS/install" "$WS/log"
BUILD_LOG="$(mktemp)"; TEST_LOG="$(mktemp)"
( cd "$WS" && colcon build --event-handlers console_direct+ ) >"$BUILD_LOG" 2>&1
BUILD_RC=$?

p_builds=false; [ $BUILD_RC -eq 0 ] && p_builds=true
p_msgdep=false; p_reg=false; p_load=false; p_ran=false; p_pass=false
TESTS_TOTAL=0; TESTS_FAIL=0; COMP_TYPES=""; COMP_LIST=""

if [ -f "$WS/install/setup.bash" ]; then
  set +u
  # shellcheck disable=SC1091
  source "$WS/install/setup.bash"
  set -u

  # 1. the cross-package message field generated with the right type
  IF="$(ros2 interface show battery_msgs/msg/Pack 2>&1)"
  grep -q 'geometry_msgs/Point[[:space:]]\+location\|geometry_msgs/msg/Point[[:space:]]\+location' <<<"$IF" \
    && p_msgdep=true

  # 2. the component is registered where pluginlib/rclcpp_components looks
  COMP_TYPES="$(ros2 component types 2>&1)"
  grep -q 'battery_node::Reporter' <<<"$COMP_TYPES" && p_reg=true

  # 3. it actually loads into a running container. Registration without a
  #    loadable library passes check 2 and fails here.
  timeout 40 ros2 launch battery_node reporter.launch.py >/dev/null 2>&1 &
  LPID=$!
  for _ in $(seq 1 25); do
    COMP_LIST="$(timeout 5 ros2 component list 2>/dev/null)"
    grep -q 'reporter' <<<"$COMP_LIST" && break
    sleep 1
  done
  grep -q 'reporter' <<<"$COMP_LIST" && p_load=true
  kill $LPID 2>/dev/null || true
  wait $LPID 2>/dev/null || true

  # 4/5. tests. `colcon test` exits 0 with zero tests, so count them.
  ( cd "$WS" && colcon test --event-handlers console_direct+ ) >"$TEST_LOG" 2>&1
  TEST_RC=$?
  RES="$( cd "$WS" && colcon test-result --all 2>&1 )"
  # "N tests, M errors, K failures, ..." summed across result files.
  TESTS_TOTAL=$(grep -oE '[0-9]+ test[s]?, ' <<<"$RES" | grep -oE '^[0-9]+' \
                 | awk '{s+=$1} END {print s+0}')
  TESTS_FAIL=$(grep -oE '[0-9]+ (error|failure)[s]?' <<<"$RES" | grep -oE '^[0-9]+' \
                 | awk '{s+=$1} END {print s+0}')
  [ "${TESTS_TOTAL:-0}" -gt 0 ] && p_ran=true
  if [ "${TESTS_TOTAL:-0}" -gt 0 ] && [ "${TESTS_FAIL:-0}" -eq 0 ] && [ $TEST_RC -eq 0 ]; then
    p_pass=true
  fi
fi

{
  printf '{\n'
  printf '  "t7_workspace_found": true,\n'
  printf '  "ws": %s,\n'                       "$(printf '%s' "$WS" | json_escape)"
  printf '  "t7_builds": %s,\n'                "$p_builds"
  printf '  "t7_msg_dep_resolves": %s,\n'      "$p_msgdep"
  printf '  "t7_component_registered": %s,\n'  "$p_reg"
  printf '  "t7_component_loads": %s,\n'       "$p_load"
  printf '  "t7_tests_ran": %s,\n'             "$p_ran"
  printf '  "t7_tests_pass": %s,\n'            "$p_pass"
  printf '  "build_rc": %d,\n'                 "$BUILD_RC"
  printf '  "tests_total": %d,\n'              "${TESTS_TOTAL:-0}"
  printf '  "tests_fail": %d,\n'               "${TESTS_FAIL:-0}"
  printf '  "component_types": %s,\n'          "$(printf '%s' "$COMP_TYPES" | json_escape)"
  printf '  "component_list": %s,\n'           "$(printf '%s' "$COMP_LIST" | json_escape)"
  printf '  "test_tail": %s,\n'                "$(tail -c 1500 "$TEST_LOG" | json_escape)"
  printf '  "build_tail": %s\n'                "$(tail -c 2000 "$BUILD_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"

rm -f "$BUILD_LOG" "$TEST_LOG"
