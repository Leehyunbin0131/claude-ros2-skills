#!/usr/bin/env bash
# Run one eval task as a baseline / with-skills A/B pair.
#
#   ./run_ab.sh <task-number> [out-dir]
#
# Both cells get an identical prompt, model, tool allowlist and a fresh working
# directory. The only difference is that the with-skills cell has CLAUDE.md and
# skills/ installed per the Quickstart. stream-json is used in BOTH cells so the
# "verification tools used" column is evidence, not recollection.
#
# Conditions match evals/README.md and the 2026-07-25 container run.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TASK="${1:?usage: run_ab.sh <task-number> [out-dir]}"
OUT="${2:-$REPO/evals/runs/$(date +%F)-native}"
MODEL="${MODEL:-haiku}"

case "$TASK" in
  1) PROMPT='Write a Python node for ROS 2 Jazzy that subscribes to `/scan` (`sensor_msgs/msg/LaserScan`) and logs the minimum range once per second.' ;;
  2) PROMPT='My robot'"'"'s LiDAR is physically mounted upside-down on the back of the chassis, facing backward. Nav2 keeps colliding with obstacles behind the robot. Write the static TF for it and tell me how to confirm the fix.' ;;
  3) PROMPT='My subscriber to `/camera/image_raw` never receives messages, but `ros2 topic hz /camera/image_raw` shows 30 Hz. The code compiles and the node starts fine. What'"'"'s wrong?' ;;
  *) echo "no prompt defined for task $TASK (1-3 supported here; 4-5 are in README.md)" >&2; exit 2 ;;
esac

mkdir -p "$OUT"

# --- live scenario -----------------------------------------------------------
# Each task needs a running system for either cell to be able to verify against
# reality. The same scenario is up for both cells, so the only difference stays
# the skills. Task 2 deliberately publishes ONLY the base tree: writing the
# rear_lidar transform is the agent's job.
SCENARIO_PIDS=()
start_scenario() {
  # setup.bash reads unset vars; -u must be off while sourcing it.
  set +u
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
  set -u
  local pi=3.14159265358979
  case "$TASK" in
    1) python3 "$REPO/evals/harness/fake_scan_pub.py" >"$OUT/t1_scenario.log" 2>&1 &
       SCENARIO_PIDS+=($!) ;;
    2) ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id odom \
         >>"$OUT/t2_scenario.log" 2>&1 & SCENARIO_PIDS+=($!)
       ros2 run tf2_ros static_transform_publisher --frame-id odom --child-frame-id base_link \
         >>"$OUT/t2_scenario.log" 2>&1 & SCENARIO_PIDS+=($!)
       : "$pi" ;;
    3) python3 "$REPO/evals/harness/fake_camera_pub.py" >"$OUT/t3_scenario.log" 2>&1 &
       SCENARIO_PIDS+=($!)
       python3 "$REPO/evals/harness/reliable_image_sub.py" >>"$OUT/t3_scenario.log" 2>&1 &
       SCENARIO_PIDS+=($!) ;;
  esac
  # Block until the system is actually up, instead of sleeping blind.
  case "$TASK" in
    1) timeout 15 ros2 topic echo /scan --once >/dev/null 2>&1 || true ;;
    2) timeout 15 ros2 run tf2_ros tf2_echo odom base_link >/dev/null 2>&1 || true ;;
    3) timeout 15 ros2 topic echo /camera/image_raw --once >/dev/null 2>&1 || true ;;
  esac
  echo "scenario for task $TASK up (pids: ${SCENARIO_PIDS[*]})"
}
stop_scenario() {
  [ ${#SCENARIO_PIDS[@]} -eq 0 ] || kill "${SCENARIO_PIDS[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap stop_scenario EXIT INT TERM

run_cell() {
  local cell="$1" dir
  dir="$(mktemp -d "/tmp/eval-t${TASK}-${cell}-XXXX")"

  if [ "$cell" = "skills" ]; then
    mkdir -p "$dir/.claude/skills"
    cp -r "$REPO"/skills/* "$dir/.claude/skills/"
    cp "$REPO/CLAUDE.md" "$dir/"
  fi

  echo "--- task $TASK / $cell  (model=$MODEL, cwd=$dir)"
  ( cd "$dir" && claude -p "$PROMPT" \
      --model "$MODEL" \
      --output-format stream-json --verbose \
      --permission-mode acceptEdits \
      --allowedTools WebFetch WebSearch Read Glob Grep Write Bash \
    ) > "$OUT/t${TASK}-${cell}_result.jsonl"

  # Final assistant message + the tool names actually invoked, for grading.
  python3 "$REPO/evals/harness/summarize_run.py" \
      "$OUT/t${TASK}-${cell}_result.jsonl" \
      > "$OUT/t${TASK}-${cell}_final.md"

  # Keep whatever files the agent wrote (Task 1 produces a node).
  find "$dir" -maxdepth 1 -type f ! -name CLAUDE.md -exec cp {} "$OUT/" \; 2>/dev/null || true
  echo "    -> $OUT/t${TASK}-${cell}_final.md"
}

start_scenario
run_cell baseline
run_cell skills
stop_scenario

echo
echo "Grade against the Task $TASK checklist in evals/README.md."
