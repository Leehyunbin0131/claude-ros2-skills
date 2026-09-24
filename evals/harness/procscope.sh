# shellcheck shell=bash
# Sourced by run_ab.sh and every *_check.sh. Two things, both about not reaching
# past this eval run:
#
#   * Processes. `kill_owned PATTERN...` kills only processes carrying this
#     run's EVAL_RUN_TAG (see procscope.py). The checkers used to run
#     `pkill -9 -f robot_state_publisher` and friends, which kill every matching
#     process on the host -- a live robot's stack included.
#   * The ROS graph. Discovery is kept on this machine
#     (ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; Jazzy's default is SUBNET), so a
#     cell told to "give me a command that actually moves it" cannot reach a
#     robot elsewhere on the LAN, and no checker probe can either.
#
# A checker run by hand outside run_ab.sh gets a fresh tag, so it cleans up only
# what it started itself. To re-grade a cell's leftovers, export the run's
# EVAL_RUN_TAG first.

_PROCSCOPE_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/procscope.py"

if [ -z "${EVAL_RUN_TAG:-}" ]; then
  EVAL_RUN_TAG="$(python3 "$_PROCSCOPE_PY" new-tag)"
fi
export EVAL_RUN_TAG
export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-LOCALHOST}"
# Static peers are contacted whatever the discovery range says.
unset ROS_STATIC_PEERS

kill_owned()      { python3 "$_PROCSCOPE_PY" kill --signal KILL "$@" || true; }
kill_owned_term() { python3 "$_PROCSCOPE_PY" kill --signal TERM "$@" || true; }
owned_pids()      { python3 "$_PROCSCOPE_PY" pids "$@"; }

# The cell's bringup may set its own ROS_DOMAIN_ID -- correct practice, and
# invisible unless we ask -- so read it back off a process that bringup started.
# Only OUR processes are considered: an unscoped `pgrep -f ros2_control_node`
# could adopt the domain of someone else's live controller_manager, and ctl2's
# probe then publishes position commands on it.
adopt_domain_from() {
  local pid d
  pid="$(owned_pids "$1" 2>/dev/null | head -1)"
  [ -n "$pid" ] || return 0
  d="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null \
       | awk -F= '$1=="ROS_DOMAIN_ID" {print $2; exit}')"
  [ -n "$d" ] && export ROS_DOMAIN_ID="$d"
  return 0
}
