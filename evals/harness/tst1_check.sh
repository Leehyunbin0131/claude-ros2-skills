#!/usr/bin/env bash
# Real-outcome checks for the ros2-testing ladder, rung L1.
#
#   ./tst1_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a colcon workspace that builds            -> tst1_builds
#   a pytest REGISTERED with the build        -> tst1_test_ran
#   the test passing                          -> tst1_no_failures
#
# `tst1_test_ran` is the check this rung exists for. Verified on this install
# before the rung ran: a package whose test file exists but is not wired into
# the build exits `colcon test` with code 0 and reports 0 tests. A grader that
# only read the exit code would pass a workspace that runs no tests at all --
# which is why the test COUNT is graded, not the return code.
#
# Everything is re-run by the grader from a clean build tree, so an incremental
# build that only works the second time is not a build.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * `set -u` + `source setup.bash` aborts on AMENT_TRACE_SETUP_FILES
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: tst1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: tst1_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

# --- locate the workspace ----------------------------------------------------
WS=""
while IFS= read -r d; do
  [ -n "$(find "$d/src" -maxdepth 3 -name package.xml -print -quit 2>/dev/null)" ] || continue
  WS="$d"; break
done < <(find "$WORK" -maxdepth 4 -type d -name src -printf '%h\n' 2>/dev/null | sort)

if [ -z "$WS" ]; then
  printf '{"tst1_workspace_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

# --- clean rebuild -----------------------------------------------------------
rm -rf "$WS/build" "$WS/install" "$WS/log"
BUILD_LOG="$(mktemp)"
( cd "$WS" && colcon build --event-handlers console_direct+ ) >"$BUILD_LOG" 2>&1
BUILD_RC=$?

pass_builds=false;  [ $BUILD_RC -eq 0 ] && pass_builds=true
pass_ran=false
pass_nofail=false
N_TESTS=0
N_FAIL=0
N_ERR=0

TEST_LOG="$(mktemp)"
RESULT_LOG="$(mktemp)"
if [ $BUILD_RC -eq 0 ]; then
  ( cd "$WS" && timeout 300 colcon test --event-handlers console_direct+ ) >"$TEST_LOG" 2>&1
  ( cd "$WS" && timeout 60 colcon test-result --all ) >"$RESULT_LOG" 2>&1

  # colcon test-result --all prints lines like
  #   build/pkg/pytest.xml: 3 tests, 0 errors, 0 failures, 0 skipped
  # Sum them. A workspace with nothing registered prints no such line at all.
  # Skip the trailing "Summary:" line -- it restates the same totals, and
  # summing both double-counted every workspace (a 1-test package reported 2).
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
fi

{
  printf '{\n'
  printf '  "tst1_workspace_found": true,\n'
  printf '  "ws": %s,\n'                 "$(printf '%s' "$WS" | json_escape)"
  printf '  "tst1_builds": %s,\n'        "$pass_builds"
  printf '  "tst1_test_ran": %s,\n'      "$pass_ran"
  printf '  "tst1_no_failures": %s,\n'   "$pass_nofail"
  printf '  "n_tests": %d,\n'            "${N_TESTS:-0}"
  printf '  "n_failures": %d,\n'         "${N_FAIL:-0}"
  printf '  "n_errors": %d,\n'           "${N_ERR:-0}"
  printf '  "build_rc": %d,\n'           "$BUILD_RC"
  printf '  "test_result": %s,\n'        "$(tail -c 800 "$RESULT_LOG" | json_escape)"
  printf '  "build_tail": %s\n'          "$(tail -c 1200 "$BUILD_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"

rm -f "$BUILD_LOG" "$TEST_LOG" "$RESULT_LOG"
