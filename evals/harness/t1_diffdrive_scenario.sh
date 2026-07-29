#!/usr/bin/env bash
# Live diff_drive_controller for v2 Task 1, on mock hardware.
#
#   ./t1_diffdrive_scenario.sh up      # bring up, stay running (Ctrl-C to stop)
#   ./t1_diffdrive_scenario.sh check   # bring up, self-test, tear down, exit 0/1
#
# Why this exists: Task 1 asks the agent why publishing to /cmd_vel does not
# move a diff-drive robot. Grading that on a real outcome -- "does the command
# you gave actually produce wheel velocity" -- needs a controller that really
# runs. mock_components/GenericSystem plus controller_manager gives one with no
# robot and no Gazebo.
#
# Everything here was read off the installed packages, not from memory:
#   * mock_components/GenericSystem is the only mock system plugin registered
#     in this install.
#   * Jazzy's controller_manager takes robot_description from a TOPIC, not a
#     parameter, so robot_state_publisher has to be up first. Passing it as a
#     parameter leaves controller_manager waiting forever.
#   * diff_drive_controller subscribes on <ns>/cmd_vel with TwistStamped only.
set -uo pipefail

MODE="${1:-up}"
DIR="$(mktemp -d /tmp/t1-ddrive-XXXX)"
PIDS=()

cleanup() {
  [ ${#PIDS[@]} -eq 0 ] || kill "${PIDS[@]}" 2>/dev/null || true
  sleep 1
  [ ${#PIDS[@]} -eq 0 ] || kill -9 "${PIDS[@]}" 2>/dev/null || true
  rm -rf "$DIR"
}
trap cleanup EXIT INT TERM

cat > "$DIR/robot.urdf" <<'URDF'
<?xml version="1.0"?>
<robot name="dd">
  <link name="base_link"/>
  <link name="lw"/><link name="rw"/>
  <joint name="left_wheel_joint" type="continuous">
    <parent link="base_link"/><child link="lw"/><axis xyz="0 1 0"/>
    <origin xyz="0 0.15 0"/>
  </joint>
  <joint name="right_wheel_joint" type="continuous">
    <parent link="base_link"/><child link="rw"/><axis xyz="0 1 0"/>
    <origin xyz="0 -0.15 0"/>
  </joint>
  <ros2_control name="mock" type="system">
    <hardware><plugin>mock_components/GenericSystem</plugin></hardware>
    <joint name="left_wheel_joint">
      <command_interface name="velocity"/>
      <state_interface name="position"/><state_interface name="velocity"/>
    </joint>
    <joint name="right_wheel_joint">
      <command_interface name="velocity"/>
      <state_interface name="position"/><state_interface name="velocity"/>
    </joint>
  </ros2_control>
</robot>
URDF

cat > "$DIR/ctl.yaml" <<'YAML'
controller_manager:
  ros__parameters:
    update_rate: 50
    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
    diff_drive_controller:
      type: diff_drive_controller/DiffDriveController
diff_drive_controller:
  ros__parameters:
    left_wheel_names: ["left_wheel_joint"]
    right_wheel_names: ["right_wheel_joint"]
    wheel_separation: 0.30
    wheel_radius: 0.05
    base_frame_id: base_link
    cmd_vel_timeout: 10.0
YAML

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

# robot_description must be on the topic before controller_manager starts.
ros2 run robot_state_publisher robot_state_publisher "$DIR/robot.urdf" \
  >"$DIR/rsp.log" 2>&1 &
PIDS+=($!)

for _ in $(seq 1 20); do
  ros2 topic list 2>/dev/null | grep -qx /robot_description && break
  sleep 0.5
done

ros2 run controller_manager ros2_control_node \
  --ros-args --params-file "$DIR/ctl.yaml" >"$DIR/cm.log" 2>&1 &
PIDS+=($!)

for _ in $(seq 1 40); do
  ros2 control list_controllers >/dev/null 2>&1 && break
  sleep 0.5
done

timeout 30 ros2 run controller_manager spawner joint_state_broadcaster >>"$DIR/cm.log" 2>&1
timeout 30 ros2 run controller_manager spawner diff_drive_controller  >>"$DIR/cm.log" 2>&1

if ! ros2 control list_controllers 2>/dev/null | grep -q 'diff_drive_controller.*active'; then
  echo "SCENARIO FAILED: diff_drive_controller not active" >&2
  tail -n 20 "$DIR/cm.log" >&2
  exit 2
fi
echo "scenario up: diff_drive_controller active on mock hardware"
ros2 control list_controllers 2>/dev/null

if [ "$MODE" = "up" ]; then
  echo "Ctrl-C to stop."
  wait
  exit 0
fi

# --- check mode: prove the scenario discriminates ---------------------------
# A plain Twist must NOT move the wheels; a TwistStamped must. If both move it
# or neither does, the task cannot be graded on a real outcome and we want to
# know that here rather than mid-round.
read_vel() {
  timeout 5 ros2 topic echo /joint_states --once 2>/dev/null \
    | python3 -c "
import sys,re
t=sys.stdin.read()
m=re.search(r'velocity:\s*\n((?:\s*-\s*[-\d.e+]+\n)+)', t)
print(max(abs(float(x)) for x in re.findall(r'-?\d+\.?\d*(?:e[-+]?\d+)?', m.group(1)))
      if m else 0.0)
"
}

# Publish continuously, not --once: a one-shot publisher is routinely lost
# before discovery completes, and diff_drive_controller stops on cmd_vel_timeout
# anyway. Each burst is killed before the next starts.
timeout 6 ros2 topic pub -r 20 /diff_drive_controller/cmd_vel \
  geometry_msgs/msg/Twist "{linear: {x: 0.5}}" >/dev/null 2>&1 &
PUB=$!; sleep 3
PLAIN="$(read_vel)"
kill $PUB 2>/dev/null; sleep 2

timeout 6 ros2 topic pub -r 20 /diff_drive_controller/cmd_vel \
  geometry_msgs/msg/TwistStamped "{header: {frame_id: base_link}, twist: {linear: {x: 0.5}}}" >/dev/null 2>&1 &
PUB=$!; sleep 3
STAMPED="$(read_vel)"
kill $PUB 2>/dev/null

echo "plain Twist    -> max |wheel velocity| = $PLAIN"
echo "TwistStamped   -> max |wheel velocity| = $STAMPED"

python3 - "$PLAIN" "$STAMPED" <<'PY'
import sys
plain, stamped = float(sys.argv[1]), float(sys.argv[2])
if stamped > 0.1 and plain < 0.01:
    print("DISCRIMINATES: TwistStamped moves the wheels, plain Twist does not.")
    raise SystemExit(0)
print(f"DOES NOT DISCRIMINATE (plain={plain}, stamped={stamped}) — "
      "t1_command_runs cannot be graded on this scenario.")
raise SystemExit(1)
PY
