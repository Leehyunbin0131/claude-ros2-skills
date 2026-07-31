#!/usr/bin/env bash
# Real-outcome checks for the ros2-dev ladder, rung L2.
#
#   ./dev2_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   the Nav2 stack brought up from a bringup.sh -> dev2_servers_up
#   controller_server driven to active          -> dev2_controller_active
#   planner_server driven to active             -> dev2_planner_active
#
# L1 only needed a parameter file the servers accept. Here the stack must
# actually reach `active`, which is where a lifecycle manager that does not
# cover every server, or a plugin that fails on configure, finally shows.
#
# Both `active` checks read `ros2 lifecycle get` rather than the bringup log:
# a bringup that prints "started" proves nothing, and a server can sit in
# `unconfigured` forever while every process looks healthy.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * the cell may set its own ROS_DOMAIN_ID (correct practice) -- adopt it
#   * the cell has already run its bringup, so kill the `ros2 launch` wrapper
#     too or a re-entrancy guard skips the relaunch and nothing starts
#   * `pkill -f "$BDIR"` matches this checker's own command line -- exclude self
#     and every ancestor, or it kills itself mid-run
#   * lifecycle servers ignore SIGTERM -- kill -9, never `wait` on them
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: dev2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: dev2_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"dev2_bringup_found": false}\n' > "$OUT"
  exit 0
fi
BDIR="$(dirname "$BRINGUP")"

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f 'controller_server' 2>/dev/null || true
  pkill -9 -f 'planner_server' 2>/dev/null || true
  pkill -9 -f 'behavior_server' 2>/dev/null || true
  pkill -9 -f 'bt_navigator' 2>/dev/null || true
  pkill -9 -f 'lifecycle_manager' 2>/dev/null || true
  if [ -n "${BDIR:-}" ]; then
    local skip=" $$ " p=$PPID
    while [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null; do
      skip="$skip$p "
      p="$(awk '{print $4}' "/proc/$p/stat" 2>/dev/null)"
    done
    local pid
    for pid in $(pgrep -f "$BDIR" 2>/dev/null || true); do
      case "$skip" in *" $pid "*) continue ;; esac
      kill -9 "$pid" 2>/dev/null || true
    done
  fi
}
kill_all
sleep 1

# Nav2's costmaps refuse to ACTIVATE without a TF chain -- verified here: with
# no transforms the lifecycle manager logs "Failed to change state for node:
# controller_server" after 60 s and the server sits at `inactive [2]` forever.
# The scenario has to run on THIS checker's domain, so start it here rather
# than relying on the one run_ab.sh brought up for the cell.
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$HARNESS/dev3_scenario.sh" up >/dev/null 2>&1 &
SCENARIO=$!
for _ in $(seq 1 25); do
  TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
  case "$TL" in */scan*) break ;; esac
  sleep 1
done

BRING_LOG="$(mktemp)"
( cd "$BDIR" && timeout 240 bash ./bringup.sh ) >"$BRING_LOG" 2>&1
BRING_RC=$?

adopt_domain_from() {
  local pid d
  pid="$(pgrep -f "$1" | head -1)"
  [ -n "$pid" ] || return 0
  d="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null \
       | awk -F= '$1=="ROS_DOMAIN_ID" {print $2; exit}')"
  [ -n "$d" ] && export ROS_DOMAIN_ID="$d"
  return 0
}
adopt_domain_from 'controller_server'

SERVERS_UP=false
for _ in $(seq 1 25); do
  NL="$(timeout 5 ros2 node list 2>/dev/null || true)"
  case "$NL" in *controller_server*) SERVERS_UP=true; break ;; esac
  sleep 1
done

# Poll for `active`: a lifecycle manager takes time to walk every server up,
# and bringup.sh is allowed to return before it finishes.
CS_STATE="-"
PS_STATE="-"
# Bounded so scenario + bringup + these polls cannot outlast the caller's
# timeout and leave no verdict on disk at all.
for _ in $(seq 1 20); do
  CS_STATE="$(timeout 5 ros2 lifecycle get /controller_server 2>&1 | head -1)"
  PS_STATE="$(timeout 5 ros2 lifecycle get /planner_server 2>&1 | head -1)"
  # `inactive` contains `active` as a substring, so an unanchored match
  # reported a server sitting in `inactive [2]` as active. Compare the first
  # field exactly.
  if printf '%s' "$CS_STATE" | awk '$1=="active" {f=1} END {exit !f}' \
     && printf '%s' "$PS_STATE" | awk '$1=="active" {f=1} END {exit !f}'; then
    break
  fi
  sleep 2
done

CS_ACTIVE=false
PS_ACTIVE=false
printf '%s' "$CS_STATE" | awk '$1=="active" {f=1} END {exit !f}' && CS_ACTIVE=true
printf '%s' "$PS_STATE" | awk '$1=="active" {f=1} END {exit !f}' && PS_ACTIVE=true

kill_all
kill -9 $SCENARIO 2>/dev/null || true
pkill -9 -f 'dev3_scenario' 2>/dev/null || true

p_up=false;  $SERVERS_UP && p_up=true
p_cs=false;  $CS_ACTIVE && p_cs=true
p_ps=false;  $PS_ACTIVE && p_ps=true

{
  printf '{\n'
  printf '  "dev2_bringup_found": true,\n'
  printf '  "bringup": %s,\n'                 "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "dev2_servers_up": %s,\n'         "$p_up"
  printf '  "dev2_controller_active": %s,\n'  "$p_cs"
  printf '  "dev2_planner_active": %s,\n'     "$p_ps"
  printf '  "cs_state": %s,\n'                "$(printf '%s' "$CS_STATE" | json_escape)"
  printf '  "ps_state": %s,\n'                "$(printf '%s' "$PS_STATE" | json_escape)"
  printf '  "bringup_rc": %d,\n'              "$BRING_RC"
  printf '  "bringup_tail": %s\n'             "$(tail -c 1200 "$BRING_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BRING_LOG"
