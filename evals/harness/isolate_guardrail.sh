#!/usr/bin/env bash
# Isolate the cause of the Task 3 `rclcpp.qos`-in-Python regression.
#
# That regression appeared only when the router picked ros2-perception, whose
# code examples are C++ only. Repeating the normal pair does not reliably
# reproduce that routing, so this forces it: every cell gets ros2-perception as
# its ONLY skill. The cells then vary the two candidate fixes independently:
#
#   A control        pre-patch skill, no CLAUDE.md   -> the original failing setup
#   B protocol-only  pre-patch skill + CLAUDE.md     -> does the always-loaded rule alone fix it?
#   C skill-only     patched skill,   no CLAUDE.md   -> does the local symbol name alone fix it?
#   D both           patched skill  + CLAUDE.md      -> the shipped configuration
#
# The pre-patch skill is read out of git (HEAD), so the control is a real
# control rather than the current file.
#
# Usage: ./isolate_guardrail.sh [out-dir] [repeats]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$REPO/evals/runs/$(date +%F)-guardrail/isolated}"
REPEATS="${2:-2}"
MODEL="${MODEL:-haiku}"
SKILL="${SKILL:-ros2-perception}"
PROMPT='My subscriber to `/camera/image_raw` never receives messages, but `ros2 topic hz /camera/image_raw` shows 30 Hz. The code compiles and the node starts fine. What'"'"'s wrong?'

mkdir -p "$OUT"
PRE="$(mktemp -d)/SKILL.md"
git -C "$REPO" show "HEAD:skills/$SKILL/SKILL.md" > "$PRE"

run_cell() {
  local tag="$1" skill_src="$2" want_protocol="$3" dir
  dir="$(mktemp -d "/tmp/iso-${tag}-XXXX")"
  mkdir -p "$dir/.claude/skills/$SKILL"
  cp -r "$REPO/skills/$SKILL/." "$dir/.claude/skills/$SKILL/"
  cp "$skill_src" "$dir/.claude/skills/$SKILL/SKILL.md"   # may be the pre-patch body
  [ "$want_protocol" = yes ] && cp "$REPO/CLAUDE.md" "$dir/"

  ( cd "$dir" && claude -p "$PROMPT" \
      --model "$MODEL" --output-format stream-json --verbose \
      --permission-mode acceptEdits \
      --allowedTools WebFetch WebSearch Read Glob Grep Write Bash \
    ) > "$OUT/${tag}_result.jsonl"
  python3 "$REPO/evals/harness/summarize_run.py" "$OUT/${tag}_result.jsonl" > "$OUT/${tag}_final.md"

  local bad
  bad=$(grep -c 'rclcpp\.' "$OUT/${tag}_final.md" || true)
  printf '  %-22s rclcpp-in-Python: %s\n' "$tag" "$([ "$bad" -gt 0 ] && echo "FAIL ($bad)" || echo OK)"
}

set +u; source /opt/ros/jazzy/setup.bash; set -u
python3 "$REPO/evals/harness/fake_camera_pub.py"    >"$OUT/scenario.log" 2>&1 & P1=$!
python3 "$REPO/evals/harness/reliable_image_sub.py" >>"$OUT/scenario.log" 2>&1 & P2=$!
trap 'kill $P1 $P2 2>/dev/null || true' EXIT INT TERM
timeout 15 ros2 topic echo /camera/image_raw --once >/dev/null 2>&1 || true

for i in $(seq 1 "$REPEATS"); do
  echo "--- repeat $i (only skill: $SKILL) ---"
  run_cell "A-control-$i"       "$PRE"                              no
  run_cell "B-protocol-$i"      "$PRE"                              yes
  run_cell "C-skill-$i"         "$REPO/skills/$SKILL/SKILL.md"      no
  run_cell "D-both-$i"          "$REPO/skills/$SKILL/SKILL.md"      yes
done
