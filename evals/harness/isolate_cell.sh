#!/usr/bin/env bash
# Run a command with this repository hidden from it.
#
#   ./isolate_cell.sh <workdir> <command...>
#
# Why. In round 2 a `baseline` cell globbed $HOME, found this repository, and
# read evals/DESIGN.md and evals/harness/fake_imu_pub.py -- the eval design and
# the scenario source, which states the planted answer outright. That leak
# happened to strengthen the baseline, so the result survived, but a `skills`
# cell reading TASKS.md would learn exactly which graders score it. Every round
# after that one runs through here.
#
# How. An unprivileged mount namespace (`unshare --map-root-user --mount`) with
# an empty directory bind-mounted over the repo path. Inside the namespace the
# repo looks empty; outside, nothing changed. No root, no container runtime.
#
# HOME is also pointed at the cell directory, so the obvious discovery path --
# listing the home directory -- finds only the cell's own files.
#
# Verify it works before trusting a round:
#   ./isolate_cell.sh /tmp ls /home/hyunlee/home/claude-ros2-skills
# should print nothing.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:?usage: isolate_cell.sh <workdir> <command...>}"
shift
[ $# -gt 0 ] || { echo "no command given" >&2; exit 2; }

if ! command -v unshare >/dev/null 2>&1; then
  echo "isolate_cell.sh: unshare not available -- REFUSING to run unisolated." >&2
  echo "A round measured without isolation is not comparable to one with it." >&2
  exit 3
fi

EMPTY="$(mktemp -d /tmp/iso-empty-XXXX)"
chmod 555 "$EMPTY"

# The command runs as the *original* user inside the namespace: --map-root-user
# only maps uid 0 for the mount call. Everything the agent does is still
# unprivileged, and /opt/ros and the cell directory are untouched.
unshare --map-root-user --mount -- bash -c '
  set -uo pipefail
  mount --bind "$1" "$2" || { echo "isolate_cell.sh: bind-mount failed" >&2; exit 4; }
  # Drop back to the invoking user inside the namespace.
  export HOME="$3"
  cd "$3" || exit 5
  shift 3
  exec "$@"
' _ "$EMPTY" "$REPO" "$WORKDIR" "$@"
rc=$?
rmdir "$EMPTY" 2>/dev/null || true
exit $rc
