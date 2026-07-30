#!/usr/bin/env bash
# Run one eval task as a baseline / with-skills A/B pair.
#
#   ./run_ab.sh <t1|t2|t3|t4> [out-dir]
#   CELLS="baseline scripts-only skills" ./run_ab.sh 2 out/
#
# Both cells get an identical prompt, model, tool allowlist and a fresh working
# directory. The only difference is that the with-skills cell has CLAUDE.md and
# skills/ installed per the Quickstart. stream-json is used in BOTH cells so the
# "verification tools used" column is evidence, not recollection.
#
# Conditions match evals/README.md and the 2026-07-25 container run.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TASK="${1:?usage: run_ab.sh <t1|t2|t3|t4> [out-dir]}"
OUT="${2:-$REPO/evals/runs/$(date +%F)-native}"
MODEL="${MODEL:-haiku}"

# v2 tasks. Prompts are verbatim from evals/TASKS.md -- if they diverge, TASKS.md
# is the source of truth. t1-t3 target one category each from DESIGN.md; t4 is
# the null control and must show no difference between cells.
case "$TASK" in
  t1) PROMPT='I have a diff-drive robot running `ros2_control` on ROS 2 Jazzy with `diff_drive_controller` active and its interfaces claimed. Publishing to `/cmd_vel` does nothing — the wheels never turn and nothing errors. Find out why and give me a command that actually moves it.' ;;
  t2) PROMPT='My robot'"'"'s EKF odometry drifts and sometimes spins on the spot. Every topic looks healthy and nothing errors. I think the IMU is mounted wrong but I want evidence, not a hunch. Settle it.' ;;
  t3) PROMPT='Set up Nav2 on my ROS 2 Jazzy robot and tune it so it navigates well. Go ahead.' ;;
  t4) PROMPT='Write a Python node for ROS 2 Jazzy that subscribes to `/scan` (`sensor_msgs/msg/LaserScan`) and logs the minimum range once per second.' ;;
  t5) PROMPT='On ROS 2 Jazzy, create a colcon workspace in the current directory with two packages. `battery_monitor_msgs` defines `msg/Cell.msg` with fields `string id` and `float32 voltage`. `battery_monitor` is a Python package with a node `monitor` that publishes `battery_monitor_msgs/msg/Cell` on `/cells` at 1 Hz, plus `launch/monitor.launch.py` that starts the node with `config/monitor.yaml`. Build the workspace.' ;;
  *) echo "unknown task: $TASK (expected t1|t2|t3|t4|t5)" >&2; exit 2 ;;
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
    t1) bash "$REPO/evals/harness/t1_diffdrive_scenario.sh" up \
          >"$OUT/${TASK}_scenario.log" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    t2) python3 "$REPO/evals/harness/fake_imu_pub.py" \
          >"$OUT/${TASK}_scenario.log" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    t3) : ;;  # Nav2 config task; nothing to bring up, the install is the system
    t4) python3 "$REPO/evals/harness/fake_scan_pub.py" \
          >"$OUT/${TASK}_scenario.log" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    t5) : ;;  # packaging task; the deliverable is a buildable workspace
  esac
  # Block until the system is actually up, instead of sleeping blind.
  case "$TASK" in
    t1) for _ in $(seq 1 60); do
          ros2 control list_controllers 2>/dev/null | grep -q 'diff_drive_controller.*active' && break
          sleep 1
        done ;;
    t2) timeout 20 ros2 topic echo /imu/data --once >/dev/null 2>&1 || true ;;
    t3) : ;;
    t4) timeout 20 ros2 topic echo /scan --once >/dev/null 2>&1 || true ;;
    t5) : ;;
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
  dir="$(mktemp -d "/tmp/eval-${TASK}-${cell}-XXXX")"

  # Three conditions. `scripts-only` ships the bundled scripts WITHOUT any
  # SKILL.md or CLAUDE.md, so a task about those scripts measures what the
  # skill *text* buys rather than what shipping the files buys -- without it
  # that comparison is a tautology, since an agent that globs finds the scripts
  # either way. See evals/TASKS.md, Task 2.
  case "$cell" in
    skills)
      mkdir -p "$dir/.claude/skills"
      cp -r "$REPO"/skills/* "$dir/.claude/skills/"
      cp "$REPO/CLAUDE.md" "$dir/"
      ;;
    scripts-only)
      local s
      for s in "$REPO"/skills/*/scripts; do
        [ -d "$s" ] || continue
        mkdir -p "$dir/scripts"
        cp -r "$s"/* "$dir/scripts/"
      done
      ;;
    # `CLAUDE.md` and nothing else. The `skills` cell ships both CLAUDE.md and
    # skills/, so round 3's t1_searched_or_read result (3/10 -> 10/10, q=0.009)
    # could belong to either. CLAUDE.md's opening paragraph is itself an
    # instruction to verify against /opt/ros/jazzy, which is exactly the
    # behaviour that grader measures. This cell separates them.
    claude-md-only)
      cp "$REPO/CLAUDE.md" "$dir/"
      ;;
    baseline) ;;
    *) echo "unknown cell: $cell" >&2; return 2 ;;
  esac

  echo "--- task $TASK / $cell  (model=$MODEL, cwd=$dir)"
  # Every cell runs with this repository hidden. Round 2 caught a baseline cell
  # reading evals/DESIGN.md and the scenario source, which names the planted
  # answer; see evals/harness/isolate_cell.sh. Rounds before that fix are not
  # comparable to rounds after it.
  bash "$REPO/evals/harness/isolate_cell.sh" "$dir" \
    claude -p "$PROMPT" \
      --model "$MODEL" \
      --output-format stream-json --verbose \
      --permission-mode acceptEdits \
      --allowedTools WebFetch WebSearch Read Glob Grep Write Bash \
    > "$OUT/${TASK}-${cell}_result.jsonl"

  # Final assistant message + the tool names actually invoked, for grading.
  python3 "$REPO/evals/harness/summarize_run.py" \
      "$OUT/${TASK}-${cell}_result.jsonl" \
      > "$OUT/${TASK}-${cell}_final.md"

  # T5's graders are all real outcomes and have to run against the workspace
  # the cell left behind: a clean rebuild, then `ros2 run` / `ros2 launch` /
  # `ros2 interface show`. Run it here, while $dir still exists, and keep the
  # verdict next to the transcript. Every one of the packaging defects this
  # task is about builds cleanly, so reading the build log is not enough --
  # see the discrimination table in t5_check.sh.
  if [ "$TASK" = t5 ]; then
    bash "$REPO/evals/harness/t5_check.sh" "$dir" "$OUT/${TASK}-${cell}_check.json" \
      >/dev/null 2>&1 || true
  fi

  # Keep whatever files the agent wrote (Task 1 produces a node).
  find "$dir" -maxdepth 1 -type f ! -name CLAUDE.md -exec cp {} "$OUT/" \; 2>/dev/null || true
  echo "    -> $OUT/${TASK}-${cell}_final.md"
}

start_scenario
for cell in ${CELLS:-baseline skills}; do
  run_cell "$cell"
done
stop_scenario

echo
echo "Grade with: python3 evals/harness/grade_v2.py $TASK <result.jsonl>"
