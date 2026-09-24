#!/usr/bin/env bash
# Run a command with this repository -- every copy of it that can be found --
# and the host's own Claude instructions hidden from it.
#
#   ./isolate_cell.sh <workdir> <command...>
#   ./isolate_cell.sh --check [workdir]    # build and verify the isolation, run nothing
#
# Why. In round 2 a `baseline` cell globbed $HOME, found this repository, and
# read evals/DESIGN.md and evals/harness/fake_imu_pub.py -- the eval design and
# the scenario source, which states the planted answer outright. That leak
# happened to strengthen the baseline, so the result survived, but a `skills`
# cell reading the task list would learn exactly which graders score it. Every
# round after that one runs through here.
#
# What is hidden is decided by isolation.py (read its docstring): every git
# worktree of this checkout, copies a bounded scan of $HOME and /tmp recognises,
# EVAL_MASK_PATHS, the host's ~/.claude instruction dirs, and instruction files
# in the workdir's ancestors. It refuses outright when managed policy is present
# or a mask would hide the workdir or Claude's credentials.
#
# How. An unprivileged mount namespace (`unshare --map-root-user --mount`) in
# which each hidden path has an empty file or directory bind-mounted over it.
# Outside the namespace nothing changes. No root, no container runtime.
#
# The agent runs as the ORIGINAL uid. `--map-root-user` alone runs it as uid 0
# of the user namespace, and that root owns the mount namespace: it can simply
# `umount` a mask and read what is under it. A second, nested user namespace
# maps the original uid back and holds no capability over those mounts.
# `--check` proves both: it tries the unmount as the agent would, and fails if
# that works.
#
# HOME is deliberately left alone. An earlier version pointed it at the cell
# directory to hide the repo from a plain `ls ~`, and that broke authentication
# for every cell -- `claude` keeps its credentials under $HOME, so all 20 cells
# of a round returned "Not logged in" and were scored as real answers.
#
# NOT a sandbox, and not claimed to be one. The agent keeps the network (the
# repository is public; a WebFetch can read it), the process table (`ps` shows
# harness paths), and every file outside the masks. analyze_v2.py's isolation
# section detects repository content arriving in a cell; nothing here prevents
# a determined read.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

MODE=run
CLEAN_WORKDIR=""
if [ "${1:-}" = "--check" ]; then
  MODE=check
  WORKDIR="${2:-}"
  if [ -z "$WORKDIR" ]; then
    WORKDIR="$(mktemp -d /tmp/iso-check-XXXX)"
    CLEAN_WORKDIR="$WORKDIR"
  fi
  set -- true
else
  WORKDIR="${1:?usage: isolate_cell.sh <workdir> <command...> | --check [workdir]}"
  shift
  [ $# -gt 0 ] || { echo "isolate_cell.sh: no command given" >&2; exit 2; }
fi
[ -d "$WORKDIR" ] || { echo "isolate_cell.sh: workdir $WORKDIR does not exist" >&2; exit 2; }
WORKDIR="$(cd "$WORKDIR" && pwd -P)"

if ! command -v unshare >/dev/null 2>&1; then
  echo "isolate_cell.sh: unshare not available -- REFUSING to run unisolated." >&2
  echo "A round measured without isolation is not comparable to one with it." >&2
  exit 3
fi
# Captured, not piped into `grep -q`: under pipefail that races (see README).
UNSHARE_HELP="$(unshare --help 2>&1)"
case "$UNSHARE_HELP" in
  *--map-user*) ;;
  *) echo "isolate_cell.sh: this unshare has no --map-user (util-linux >= 2.38)," >&2
     echo "so the agent would run as root of its namespace and could unmount the" >&2
     echo "masks. REFUSING. Ubuntu 24.04 ships util-linux 2.39." >&2
     exit 3 ;;
esac

TMPD="$(mktemp -d /tmp/iso-mask-XXXX)"
cleanup() {
  rm -rf "$TMPD"
  [ -z "$CLEAN_WORKDIR" ] || rmdir "$CLEAN_WORKDIR" 2>/dev/null || true
}
trap cleanup EXIT

LIST="$TMPD/masks"
python3 "$HERE/isolation.py" plan --repo "$REPO" --workdir "$WORKDIR" > "$LIST"
rc=$?
[ "$rc" -eq 0 ] || exit "$rc"
mkdir "$TMPD/src"

# Inside the namespace: mask, verify every mask, then drop back to our uid.
read -r -d '' INNER <<'EOS'
set -uo pipefail
list=$1 src=$2 workdir=$3 uid=$4 gid=$5 mode=$6 probe=$7
shift 7
n=0
while read -r kind path; do
  [ -n "$kind" ] || continue
  n=$((n + 1))
  if [ "$kind" = d ]; then mkdir -p "$src/m$n"; else : > "$src/m$n"; fi
  mount --bind "$src/m$n" "$path" \
    || { echo "isolate_cell.sh: could not mask $path" >&2; exit 4; }
done < "$list"
while read -r kind path; do
  [ -n "$kind" ] || continue
  if [ "$kind" = d ]; then
    [ -z "$(ls -A "$path" 2>/dev/null)" ] \
      || { echo "isolate_cell.sh: $path is still visible after masking" >&2; exit 4; }
  elif [ -s "$path" ]; then
    echo "isolate_cell.sh: $path still has content after masking" >&2; exit 4
  fi
done < "$list"
cd "$workdir" || exit 5
if [ "$mode" = check ]; then
  exec unshare --map-user="$uid" --map-group="$gid" -- bash -c "$probe" _ "$uid" "$list"
fi
# stdin from /dev/null: `claude -p` otherwise waits on it inside the
# namespace, warns, and produces a stub. Another round lost to this.
exec unshare --map-user="$uid" --map-group="$gid" -- "$@" </dev/null
EOS

# What --check runs as the agent would: right uid, and no way back under a mask.
read -r -d '' PROBE <<'EOS'
uid=$1 list=$2
[ "$(id -u)" = "$uid" ] \
  || { echo "isolate_cell.sh: the agent would run as uid $(id -u), not $uid" >&2; exit 4; }
while read -r kind path; do
  [ "$kind" = d ] || continue
  if umount "$path" 2>/dev/null || umount -l "$path" 2>/dev/null; then
    echo "isolate_cell.sh: the agent could unmount the mask on $path" >&2; exit 4
  fi
  [ -z "$(ls -A "$path" 2>/dev/null)" ] \
    || { echo "isolate_cell.sh: $path is visible to the agent" >&2; exit 4; }
done < "$list"
echo "isolation ok: $(awk 'END {print NR}' "$list") path(s) masked, agent uid $(id -u)"
EOS

unshare --map-root-user --mount -- bash -c "$INNER" _ \
  "$LIST" "$TMPD/src" "$WORKDIR" "$(id -u)" "$(id -g)" "$MODE" "$PROBE" "$@"
rc=$?
[ "$MODE" = check ] && [ "$rc" -eq 0 ] && sed 's/^/  masked: /' "$LIST"
exit $rc
