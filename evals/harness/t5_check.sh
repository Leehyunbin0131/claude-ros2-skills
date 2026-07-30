#!/usr/bin/env bash
# Real-outcome checks for T5 (ros2-package). Run against whatever the cell left
# behind, in a shell that has seen only /opt/ros/jazzy and the agent's own
# install tree.
#
#   ./t5_check.sh <cell-workdir> <out.json>
#
# Every check here is a real outcome, not a phrasing match. The wiring claims in
# skills/ros2-package/SKILL.md all fail *silently at build time* and only show
# up when you try to use the package -- which is exactly why grading has to run
# the thing rather than read the CMakeLists.
#
# Verified to discriminate before being trusted (2026-07-30, this install):
#
#   setup.cfg present -> script installs to lib/<pkg>/monitor -> `ros2 run` works
#   setup.cfg absent  -> colcon build STILL EXITS 0
#                        script installs to bin/monitor
#                        `ros2 run` -> "No executable found"
#
# So `t5_builds` alone cannot see the defect and `t5_run_works` can. A grader
# that only checked the build would have passed the broken package.
set -uo pipefail

WORK="${1:?usage: t5_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: t5_check.sh <cell-workdir> <out.json>}"

PKG="battery_monitor"
MSGPKG="battery_monitor_msgs"
IFACE="$MSGPKG/msg/Cell"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

# --- locate the workspace ----------------------------------------------------
# The agent chooses where to put it. A workspace root is a directory with a
# src/ containing at least one package.xml. Deepest-first so a nested ws wins
# over the cell dir itself.
WS=""
while IFS= read -r d; do
  [ -n "$(find "$d/src" -maxdepth 3 -name package.xml -print -quit 2>/dev/null)" ] || continue
  WS="$d"; break
done < <(find "$WORK" -maxdepth 4 -type d -name src -printf '%h\n' 2>/dev/null | sort)

if [ -z "$WS" ]; then
  printf '{"t5_workspace_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

# --- 1. clean rebuild --------------------------------------------------------
# From scratch: a build that only succeeds incrementally is not a build.
rm -rf "$WS/build" "$WS/install" "$WS/log"
BUILD_LOG="$(mktemp)"
( cd "$WS" && colcon build --event-handlers console_direct+ ) >"$BUILD_LOG" 2>&1
BUILD_RC=$?

pass_builds=false;    [ $BUILD_RC -eq 0 ] && pass_builds=true
pass_iface=false
pass_run=false
pass_launch=false
pass_params=false

if [ -f "$WS/install/setup.bash" ]; then
  set +u
  # shellcheck disable=SC1091
  source "$WS/install/setup.bash"
  set -u

  # --- 2. the custom interface actually generated ----------------------------
  IF_OUT="$(ros2 interface show "$IFACE" 2>&1)"
  if [ $? -eq 0 ] \
     && grep -q 'string[[:space:]]\+id' <<<"$IF_OUT" \
     && grep -q 'float32[[:space:]]\+voltage' <<<"$IF_OUT"; then
    pass_iface=true
  fi

  # --- 3. `ros2 run` finds the executable ------------------------------------
  # This is the check that catches a missing setup.cfg / wrong install()
  # destination. "No executable found" is the exact failure it exists for.
  RUN_OUT="$(timeout 12 ros2 run "$PKG" monitor 2>&1)"
  if ! grep -qi 'no executable found\|package .* not found\|No such file' <<<"$RUN_OUT"; then
    pass_run=true
  fi

  # --- 4. the launch file was installed into share/ --------------------------
  # `launch/` is not installed by default. If the agent forgot the
  # install(DIRECTORY launch ...) / data_files entry, the file exists in src/
  # and `ros2 launch` cannot see it.
  # Two conditions, because "ros2 launch printed no not-found error" alone
  # would also pass a launch that died for an unrelated reason: the file must
  # be in the install tree AND ros2 launch must resolve it.
  LA_INSTALLED=false
  find "$WS/install" -path "*share/$PKG/*" -name 'monitor.launch.py' \
       -print -quit 2>/dev/null | grep -q . && LA_INSTALLED=true
  LA_OUT="$(timeout 20 ros2 launch "$PKG" monitor.launch.py 2>&1)"
  if $LA_INSTALLED \
     && ! grep -qi 'file .* was not found\|no such file\|package .* not found\|not found in' <<<"$LA_OUT"; then
    pass_launch=true
  fi

  # --- 5. the params file reached share/ too ---------------------------------
  if find "$WS/install" -path "*share/$PKG/*" \( -name '*.yaml' -o -name '*.yml' \) \
       -print -quit 2>/dev/null | grep -q .; then
    pass_params=true
  fi
fi

{
  printf '{\n'
  printf '  "t5_workspace_found": true,\n'
  printf '  "ws": %s,\n'        "$(printf '%s' "$WS" | json_escape)"
  printf '  "t5_builds": %s,\n'             "$pass_builds"
  printf '  "t5_interface_resolves": %s,\n' "$pass_iface"
  printf '  "t5_run_works": %s,\n'          "$pass_run"
  printf '  "t5_launch_resolves": %s,\n'    "$pass_launch"
  printf '  "t5_params_installed": %s,\n'   "$pass_params"
  printf '  "build_rc": %d,\n'              "$BUILD_RC"
  printf '  "build_tail": %s\n'             "$(tail -c 2000 "$BUILD_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"

rm -f "$BUILD_LOG"
