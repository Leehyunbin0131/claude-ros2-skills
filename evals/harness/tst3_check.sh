#!/usr/bin/env bash
# Real-outcome checks for the ros2-testing ladder, rung L3.
#
#   ./tst3_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a colcon workspace that builds        -> tst3_builds
#   a test registered and actually run    -> tst3_test_ran
#   it passing                            -> tst3_no_failures
#   a rosbag2 bag written by the test     -> tst3_bag_written
#
# `tst3_bag_written` is the rung. The prompt asks the test to record `/ticks`
# into a bag PROGRAMMATICALLY (not by shelling out to `ros2 bag record`) and
# then read it back. A test that asserts on live topic traffic and never
# touches rosbag2 passes the first three checks; a real one leaves a bag on
# disk with a metadata file and a storage file in it.
#
# Graded by OBSERVING rosbag2 being driven at runtime, not by finding a bag
# left on disk and not by grepping the source.
#
# Leftover artifacts were the first design and they were wrong: every cell in
# the first L3 round wrote its bag to `tempfile.mkdtemp()` and removed it in
# tearDown -- correct practice, and nothing in the prompt asks for the bag to
# survive. All six were scored 0 while their tests passed.
#
# A source grep is equally wrong in the other direction: it would pass a test
# that imports rosbag2_py and records nothing, which is the exact failure this
# check exists for.
#
# So a `sitecustomize.py` on PYTHONPATH wraps `SequentialWriter.open` and
# `SequentialReader.open` to append to a marker file. The marker records that
# the test actually opened a bag for writing, wherever it put it and however
# soon it deleted it.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * the Summary: line restates totals -- summing it double-counts every test
#   * `set -u` + `source setup.bash` aborts on AMENT_TRACE_SETUP_FILES
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: tst3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: tst3_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

WS=""
while IFS= read -r d; do
  [ -n "$(find "$d/src" -maxdepth 3 -name package.xml -print -quit 2>/dev/null)" ] || continue
  WS="$d"; break
done < <(find "$WORK" -maxdepth 4 -type d -name src -printf '%h\n' 2>/dev/null | sort)

if [ -z "$WS" ]; then
  printf '{"tst3_workspace_found": false}\n' > "$OUT"
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
pass_bag=false
N_TESTS=0
N_FAIL=0
N_ERR=0
N_BAGS=0
BAG_PATH="-"

TEST_LOG="$(mktemp)"
RESULT_LOG="$(mktemp)"
# Marker file: only bags created after this point count, so a bag left behind by
# an earlier cell cannot be credited to this one.
STAMP="$(mktemp)"

# Runtime observation, independent of where the bag goes or whether it
# survives. A background watcher polls for bag directories while the test runs.
# A bag must exist between being written and being read back, so a 0.2 s poll
# sees it even when the test removes it in tearDown.
#
# Monkey-patching rosbag2_py from a sitecustomize was tried first and rejected:
# replacing a method on the pybind11 type aborts the interpreter (SIGABRT,
# exit -6), and swapping the module attribute for a subclass did not take.
TMPROOT="$(mktemp -d)"
BAGWATCH="$(mktemp)"
# Watch for the STORAGE file, not metadata.yaml: rosbag2 writes the metadata
# only when the writer is closed, so a test that reads the bag back and deletes
# it leaves a window of a fraction of a second. The .db3/.mcap exists from
# writer.open onward -- the whole recording period -- which is comfortably
# longer than the poll interval.
( while :; do
    find "$WS" "$TMPROOT" -maxdepth 6 \( -name '*.db3' -o -name '*.mcap' \) \
      2>/dev/null >>"$BAGWATCH"
    sleep 0.1
  done ) &
WATCH=$!

N_READS=0
if [ $BUILD_RC -eq 0 ]; then
  ( cd "$WS" && TMPDIR="$TMPROOT" \
      timeout 600 colcon test --event-handlers console_direct+ ) >"$TEST_LOG" 2>&1
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

  kill -9 $WATCH 2>/dev/null || true
  N_BAGS=$(sort -u "$BAGWATCH" 2>/dev/null | awk 'END {print NR+0}')
  BAG_PATH="$(sort -u "$BAGWATCH" 2>/dev/null | head -1)"
  [ -n "$BAG_PATH" ] || BAG_PATH="-"
  [ "${N_BAGS:-0}" -ge 1 ] && pass_bag=true

fi

{
  printf '{\n'
  printf '  "tst3_workspace_found": true,\n'
  printf '  "ws": %s,\n'                 "$(printf '%s' "$WS" | json_escape)"
  printf '  "tst3_builds": %s,\n'        "$pass_builds"
  printf '  "tst3_test_ran": %s,\n'      "$pass_ran"
  printf '  "tst3_no_failures": %s,\n'   "$pass_nofail"
  printf '  "tst3_bag_written": %s,\n'   "$pass_bag"
  printf '  "n_tests": %d,\n'            "${N_TESTS:-0}"
  printf '  "n_failures": %d,\n'         "${N_FAIL:-0}"
  printf '  "n_errors": %d,\n'           "${N_ERR:-0}"
  printf '  "n_bag_dirs_seen": %d,\n'    "${N_BAGS:-0}"
  printf '  "bag_path": %s,\n'           "$(printf '%s' "$BAG_PATH" | json_escape)"
  printf '  "build_rc": %d,\n'           "$BUILD_RC"
  printf '  "test_result": %s,\n'        "$(tail -c 800 "$RESULT_LOG" | json_escape)"
  printf '  "build_tail": %s\n'          "$(tail -c 1200 "$BUILD_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"

kill -9 $WATCH 2>/dev/null || true
rm -rf "$BUILD_LOG" "$TEST_LOG" "$RESULT_LOG" "$STAMP" "$BAGWATCH" "$TMPROOT"
