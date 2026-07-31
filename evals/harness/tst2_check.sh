#!/usr/bin/env bash
# Real-outcome checks for the ros2-testing ladder, rung L2.
#
#   ./tst2_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a colcon workspace that builds                 -> tst2_builds
#   a test REGISTERED with the build that runs     -> tst2_test_ran
#   it passing                                     -> tst2_no_failures
#   the node actually launched and talked to       -> tst2_launch_testing
#
# `tst2_launch_testing` is what separates this rung from L1. A unit test that
# imports the node class and calls its callback directly passes the first three
# checks while never launching anything, and the prompt asks for a
# `launch_testing` integration test that asserts on live /in -> /out traffic.
#
# It is graded from the generated test artifacts, not from reading source for
# the word "launch_testing": a `launch_testing` run registers its cases through
# a launch description, and the resulting XML carries the launch-test naming
# that a plain pytest run does not. Both are accepted spellings:
#   * a test target whose name contains the launch-test marker, or
#   * an XML testsuite whose classname/name records a launch_testing case.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * `set -u` + `source setup.bash` aborts on AMENT_TRACE_SETUP_FILES
#   * the Summary: line restates totals -- summing it double-counts every test
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: tst2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: tst2_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

WS=""
while IFS= read -r d; do
  [ -n "$(find "$d/src" -maxdepth 3 -name package.xml -print -quit 2>/dev/null)" ] || continue
  WS="$d"; break
done < <(find "$WORK" -maxdepth 4 -type d -name src -printf '%h\n' 2>/dev/null | sort)

if [ -z "$WS" ]; then
  printf '{"tst2_workspace_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

rm -rf "$WS/build" "$WS/install" "$WS/log"
BUILD_LOG="$(mktemp)"
( cd "$WS" && colcon build --event-handlers console_direct+ ) >"$BUILD_LOG" 2>&1
BUILD_RC=$?

pass_builds=false;  [ $BUILD_RC -eq 0 ] && pass_builds=true
pass_ran=false
pass_nofail=false
pass_launch=false
N_TESTS=0
N_FAIL=0
N_ERR=0

TEST_LOG="$(mktemp)"
RESULT_LOG="$(mktemp)"
if [ $BUILD_RC -eq 0 ]; then
  ( cd "$WS" && timeout 400 colcon test --event-handlers console_direct+ ) >"$TEST_LOG" 2>&1
  ( cd "$WS" && timeout 60 colcon test-result --all ) >"$RESULT_LOG" 2>&1

  read -r N_TESTS N_ERR N_FAIL <<<"$(awk '
    /^Summary:/ { next }
    match($0, /([0-9]+) tests?,/, t) {
      tests += t[1]
      if (match($0, /([0-9]+) errors?,/, e)) errs += e[1]
      if (match($0, /([0-9]+) failures?/, f)) fails += f[1]
    }
    END { printf "%d %d %d", tests+0, errs+0, fails+0 }' "$RESULT_LOG")"

  [ "${N_TESTS:-0}" -ge 1 ] && pass_ran=true
  if [ "${N_TESTS:-0}" -ge 1 ] && [ "${N_FAIL:-0}" -eq 0 ] && [ "${N_ERR:-0}" -eq 0 ]; then
    pass_nofail=true
  fi

  # Did a launch test actually run?
  #
  # The launch_testing pytest plugin wraps the whole launch-test MODULE into a
  # single case whose `name` equals the last segment of its `classname`, while
  # an ordinary pytest case carries the test function's own name. Verified on
  # this install against both references before the rung ran:
  #
  #   launch_testing  classname="echo_pkg.test.test_echo_launch"
  #                   name="test_echo_launch"            -> equal
  #   plain pytest    classname="echo_pkg.test.test_echo_unit"
  #                   name="test_callback_republishes"   -> different
  #
  # This reads what the build produced, not the cell's source, so any spelling
  # that genuinely launches the node counts. Its one limit, stated rather than
  # hidden: a plain test function named exactly after its module would also
  # match. Nothing in the frozen prompt encourages that, and the alternative --
  # grepping the source for "launch_testing" -- would pass a file that imports
  # it and never launches anything, which is the failure this check exists for.
  LT_HITS=$(find "$WS/build" -name '*.xml' -print0 2>/dev/null \
    | xargs -0 -r python3 -c '
import re, sys, xml.etree.ElementTree as ET
n = 0
for p in sys.argv[1:]:
    try:
        root = ET.parse(p).getroot()
    except Exception:
        continue
    for tc in root.iter("testcase"):
        cls = tc.get("classname") or ""
        name = tc.get("name") or ""
        if cls and name and cls.rsplit(".", 1)[-1] == name:
            n += 1
print(n)
' 2>/dev/null | awk '{s+=$1} END {print s+0}')
  [ "${LT_HITS:-0}" -ge 1 ] && pass_launch=true
fi

{
  printf '{\n'
  printf '  "tst2_workspace_found": true,\n'
  printf '  "ws": %s,\n'                   "$(printf '%s' "$WS" | json_escape)"
  printf '  "tst2_builds": %s,\n'          "$pass_builds"
  printf '  "tst2_test_ran": %s,\n'        "$pass_ran"
  printf '  "tst2_no_failures": %s,\n'     "$pass_nofail"
  printf '  "tst2_launch_testing": %s,\n'  "$pass_launch"
  printf '  "n_tests": %d,\n'              "${N_TESTS:-0}"
  printf '  "n_failures": %d,\n'           "${N_FAIL:-0}"
  printf '  "n_errors": %d,\n'             "${N_ERR:-0}"
  printf '  "build_rc": %d,\n'             "$BUILD_RC"
  printf '  "test_result": %s,\n'          "$(tail -c 800 "$RESULT_LOG" | json_escape)"
  printf '  "build_tail": %s\n'            "$(tail -c 1200 "$BUILD_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"

rm -f "$BUILD_LOG" "$TEST_LOG" "$RESULT_LOG"
