#!/usr/bin/env bash
# Real-outcome checks for gazebo-sim ladder rung L1 (evals/LADDER.md).
#
#   ./g1_check.sh <cell-workdir> <out.json>
#
# L1's mechanisms and the check that catches each:
#
#   valid SDF                          -> g1_sdf_valid   (`gz sdf --check`)
#   the world actually runs headless   -> g1_sim_runs
#   diff-drive plugin wired to joints  -> g1_topics_present, g1_robot_moves
#   joints the plugin names really exist -> g1_robot_moves
#
# DROPPED CHECK, recorded rather than quietly omitted: "robot falls through the
# ground" is in SKILL.md's symptom table and is NOT measured here. Two reasons,
# both found while validating the graders:
#   * /odom carries the planar pose, so z is always 0 -- and protobuf text
#     format omits zero-valued fields, so there is nothing to read.
#   * the obvious defect for it does not work. Deleting <inertial> from the
#     wheels leaves the robot driving 1.69 m, because SDF supplies a default
#     mass and unit inertia.
# A grader with no constructible failing case is not a grader. That symptom row
# stays unmeasured at L1.
#
# NOTE on a rejected reference variant: deleting <inertial> from the wheels does
# NOT break this. SDF supplies a default mass and unit inertia, so the robot
# still drives 1.69 m. The discriminating defect is a DiffDrive plugin naming
# joints that do not exist -- the plugin loads, odometry publishes, and nothing
# moves.
#
# ------------------------------------------------------------------------
# THE RENDER ENGINE IS FORCED TO `ogre`, DELIBERATELY.
#
# On this machine `ogre2` -- which is Gazebo's default AND what
# skills/gazebo-sim/SKILL.md tells you to write -- segfaults under
# --headless-rendering, inside Ogre::Hlms::createDatablock. Topics get
# advertised and then the process dies with no data.
#
# Leaving that in place would fail every cell for a reason that has nothing to
# do with the agent's SDF, and the round would look like "the model cannot make
# Gazebo sensors work". That is a manufactured gap. `gz sim --render-engine
# ogre` overrides whatever the SDF asks for (verified: a world requesting ogre2
# runs fine under the flag), so the machine stops being a variable and the
# check measures the wiring.
#
# The ogre2 crash is recorded in LADDER.md as an environment fact. It is NOT a
# rung mechanism and no cell is scored on it.
# ------------------------------------------------------------------------
set -uo pipefail

WORK="${1:?usage: g1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: g1_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

# The agent chooses the filename. Take the SDF that declares a <world>.
WORLD=""
while IFS= read -r f; do
  grep -q '<world' "$f" 2>/dev/null || continue
  WORLD="$f"; break
done < <(find "$WORK" -maxdepth 4 -name '*.sdf' -o -maxdepth 4 -name '*.world' 2>/dev/null | sort)

if [ -z "$WORLD" ]; then
  printf '{"g1_world_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export GZ_PARTITION="g1check$$"

p_sdf=false; p_runs=false; p_topics=false; p_moves=false
CHECK_OUT="$(gz sdf --check "$WORLD" 2>&1)"
grep -q '^Valid\.' <<<"$CHECK_OUT" && p_sdf=true

SIM_LOG="$(mktemp)"
gz sim -s -r --headless-rendering --render-engine ogre "$WORLD" >"$SIM_LOG" 2>&1 &
SIM=$!

TOPICS=""
for _ in $(seq 1 25); do
  TOPICS="$(timeout 5 gz topic -l 2>/dev/null)"
  grep -q '/odom' <<<"$TOPICS" && break
  kill -0 $SIM 2>/dev/null || break
  sleep 1
done

kill -0 $SIM 2>/dev/null && p_runs=true
# `gz topic -l` lists advertised topics only -- a subscribe-only /cmd_vel does
# not appear, which is why this checks the odometry the plugin publishes. The
# command path is what g1_robot_moves is for.
grep -q '/odom' <<<"$TOPICS" && p_topics=true

pose_of() {  # forward position x from one /odom sample, or "nan"
  timeout 8 gz topic -e -t /odom -n 1 2>/dev/null \
    | python3 -c '
import re,sys
t=sys.stdin.read()
m=re.search(r"position\s*\{(.*?)\}", t, re.S)
if not m:
    print("nan"); raise SystemExit
# protobuf text format omits zero-valued fields, so an absent x means 0.0 --
# not missing data. Only an absent position block is missing data. An earlier
# version also lost the exponent on values like -1.47e-17 by excluding "-"
# from the number class, which made a stationary robot read as no data.
mm=re.search(r"x:\s*(-?[0-9.]+(?:[eE][-+]?[0-9]+)?)", b if (b:=m.group(1)) else "")
print(mm.group(1) if mm else "0")'
}

X0=nan; X1=nan
if $p_runs; then
  X0="$(pose_of)"
  # Drive forward for ~4 s of sim time. Continuous publishing: a single
  # --once is routinely lost before discovery completes.
  ( for _ in $(seq 1 40); do
      gz topic -t /cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.4}' >/dev/null 2>&1
      sleep 0.1
    done ) &
  PUB=$!
  sleep 5
  X1="$(pose_of)"
  kill $PUB 2>/dev/null || true
  wait $PUB 2>/dev/null || true

  # Forward at least 15 cm of the ~2 m the command should produce. The
  # reference world reaches 1.69 m; a DiffDrive plugin naming joints that no
  # <joint> declares reaches nothing, with the world loaded and /odom publishing.
  V="$(mktemp)"
  python3 -c '
import sys, math
x0, x1 = (float(v) if v not in ("nan", "") else math.nan for v in sys.argv[1:3])
moved = (not math.isnan(x0)) and (not math.isnan(x1)) and (x1 - x0) > 0.15
open(sys.argv[3], "w").write(str(int(moved)))' "$X0" "$X1" "$V"
  [ "$(cat "$V")" = 1 ] && p_moves=true
  rm -f "$V"
fi

# gz sim ignores SIGTERM headless -- a stray was found alive 23 minutes after
# its cell ended, surviving pkill and dying only to -9. Leftovers leak into
# `gz topic -l` and can make a later check read a simulation nobody is driving.
kill $SIM 2>/dev/null || true
sleep 2
kill -9 $SIM 2>/dev/null || true
wait $SIM 2>/dev/null || true
pkill -9 -f '^gz sim' 2>/dev/null || true

{
  printf '{\n'
  printf '  "g1_world_found": true,\n'
  printf '  "world": %s,\n'          "$(printf '%s' "$WORLD" | json_escape)"
  printf '  "g1_sdf_valid": %s,\n'   "$p_sdf"
  printf '  "g1_sim_runs": %s,\n'    "$p_runs"
  printf '  "g1_topics_present": %s,\n' "$p_topics"
  printf '  "g1_robot_moves": %s,\n' "$p_moves"
  printf '  "pose_x": "%s -> %s",\n' "$X0" "$X1"
  printf '  "topics": %s,\n'         "$(printf '%s' "$TOPICS" | json_escape)"
  printf '  "sdf_check": %s,\n'      "$(printf '%s' "$CHECK_OUT" | json_escape)"
  printf '  "sim_tail": %s\n'        "$(tail -c 1500 "$SIM_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$SIM_LOG"
