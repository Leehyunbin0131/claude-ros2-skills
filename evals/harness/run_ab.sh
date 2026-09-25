#!/usr/bin/env bash
# Run one eval task: one cell per condition, each against its own live scenario.
#
#   MODEL=sonnet CELLS=baseline ./run_ab.sh <task> <out-dir>
#   MODEL=sonnet CELLS="baseline scripts-only skills" ./run_ab.sh t2 out/
#   ./run_ab.sh --preflight [task]      # every refusal check, no scenario, no model call
#
# Every cell gets an identical prompt, model, tool allowlist and a fresh working
# directory; the conditions differ only in what is copied into it (see
# run_cell). stream-json is recorded in every cell so tool use is evidence, not
# recollection. A ladder round is ten invocations, one per rep directory:
#
#   for i in $(seq 1 10); do
#     MODEL=sonnet CELLS=baseline ./run_ab.sh ctl1 ../runs/<round>/ctl1/r$i
#   done
#
# Fails closed before any model call (see preflight): MODEL must be named
# explicitly, isolation must verify, no other eval run may be active, and no ROS
# stack this harness did not start may be running on the host -- cells execute
# model-written ROS code and checkers publish commands.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HARNESS/../.." && pwd)"
PREFLIGHT_ONLY=""
if [ "${1:-}" = "--preflight" ]; then
  PREFLIGHT_ONLY=1
  shift
  set -- "${1:-t4}" "(preflight: nothing is written)"
fi
TASK="${1:?usage: run_ab.sh <task> <out-dir> | --preflight [task]}"
OUT="${2:?usage: run_ab.sh <task> <out-dir> -- name the round directory explicitly}"
# No default. It used to be haiku, which this project found does not transfer
# to the model it ships against; every committed sweep ran sonnet (the model id
# each transcript's init event records).
MODEL="${MODEL:-}"

# The prompts below are FROZEN (evals/LADDER.md rule 1) and are the record: the
# TASKS.md they were first written in is not in this repository. t4 is the
# null control and must show no difference between cells.
case "$TASK" in
  t1) PROMPT='I have a diff-drive robot running `ros2_control` on ROS 2 Jazzy with `diff_drive_controller` active and its interfaces claimed. Publishing to `/cmd_vel` does nothing — the wheels never turn and nothing errors. Find out why and give me a command that actually moves it.' ;;
  t2) PROMPT='My robot'"'"'s EKF odometry drifts and sometimes spins on the spot. Every topic looks healthy and nothing errors. I think the IMU is mounted wrong but I want evidence, not a hunch. Settle it.' ;;
  t3) PROMPT='Set up Nav2 on my ROS 2 Jazzy robot and tune it so it navigates well. Go ahead.' ;;
  t4) PROMPT='Write a Python node for ROS 2 Jazzy that subscribes to `/scan` (`sensor_msgs/msg/LaserScan`) and logs the minimum range once per second.' ;;
  t5) PROMPT='On ROS 2 Jazzy, create a colcon workspace in the current directory with two packages. `battery_monitor_msgs` defines `msg/Cell.msg` with fields `string id` and `float32 voltage`. `battery_monitor` is a Python package with a node `monitor` that publishes `battery_monitor_msgs/msg/Cell` on `/cells` at 1 Hz, plus `launch/monitor.launch.py` that starts the node with `config/monitor.yaml`. Build the workspace.' ;;
  # t6 is ladder rung L2 for ros2-package (evals/LADDER.md). FROZEN 2026-07-30
  # before any cell ran: this text must not change, per LADDER.md rule 1.
  t6) PROMPT='On ROS 2 Jazzy, create a colcon workspace in the current directory with three packages. `battery_msgs` defines `msg/Cell.msg` (`string id`, `float32 voltage`) and `srv/SetLimit.srv` (request `float32 max_voltage`, response `bool accepted`). `battery_cpp` is a C++ package with an executable node `guard` that provides the `SetLimit` service on `/set_limit`. `battery_py` is a Python package with a node `monitor` that publishes `battery_msgs/msg/Cell` on `/cells` at 1 Hz and calls `/set_limit` once at startup. `battery_cpp` has `launch/guard.launch.py` starting `guard`; `battery_py` has `launch/system.launch.py` which includes `battery_cpp`'"'"'s launch file and also starts `monitor` with `config/monitor.yaml`. Build the workspace.' ;;
  # t7 is ladder rung L3 for ros2-package (evals/LADDER.md). FROZEN 2026-07-30
  # before any cell ran: this text must not change, per LADDER.md rule 1.
  t7) PROMPT='On ROS 2 Jazzy, create a colcon workspace in the current directory with two packages. `battery_msgs` defines `msg/Pack.msg` with fields `string id`, `float32 voltage`, and `geometry_msgs/Point location`. `battery_node` is a C++ package containing a composable node class `battery_node::Reporter` that subscribes to `/packs` (`battery_msgs/msg/Pack`) and logs the voltage; it must be loadable into an `rclcpp_components` container at runtime, and `launch/reporter.launch.py` must bring up a container with it loaded. `battery_node` must also have at least one test that `colcon test` runs and passes. Build the workspace and run the tests.' ;;
  # gazebo-sim ladder (evals/LADDER.md). All three prompts FROZEN 2026-07-30
  # before any cell ran, per LADDER.md rule 1. g2/g3 have no checker yet: rule 4
  # says stop at the first rung that fails, so their harness is built only if the
  # rung below them passes. The prompts are frozen now so the ladder cannot be
  # reshaped after seeing a result.
  g1) PROMPT='On ROS 2 Jazzy with Gazebo Harmonic, write a single SDF world file in the current directory containing a ground plane and a differential-drive robot. The robot must drive: publishing a `gz.msgs.Twist` with positive `linear.x` on the Gazebo topic `/cmd_vel` has to move it forward, and it must publish odometry on the Gazebo topic `/odom`. The world has to run headless with `gz sim -s -r`. No ROS bridge is needed for this task.' ;;
  # g2/g3 REVISED 2026-07-30, before any cell of either ran, and recorded in
  # LADDER.md. The frozen text ended "Give me the exact commands to bring it all
  # up", which is not mechanically gradable -- the checker would have had to
  # parse free-form commands out of a transcript. Asking for `bringup.sh`
  # instead gives the checker an entry point it can execute. The mechanism set
  # is unchanged. Fixing a gradability flaw before running is allowed; changing
  # a rung after seeing a result is not.
  g2) PROMPT='On ROS 2 Jazzy with Gazebo Harmonic, in the current directory build an SDF world with a differential-drive robot carrying a 360-sample GPU lidar, plus whatever is needed to drive and read it from ROS 2. Also write `bringup.sh` in the current directory that starts everything in the background and returns; it does not need to clean up. After `bash bringup.sh`, from ROS 2 I must be able to: see `sensor_msgs/msg/LaserScan` with 360 finite ranges on `/scan`, see `rosgraph_msgs/msg/Clock` on `/clock`, and move the robot by publishing `geometry_msgs/msg/Twist` on the ROS topic `/cmd_vel`.' ;;
  g3) PROMPT='On ROS 2 Jazzy with Gazebo Harmonic, in the current directory create a robot described as a URDF that is published on `/robot_description` and spawned into a running Gazebo world with `ros_gz_sim`. The robot carries an IMU. Also write `bringup.sh` in the current directory that starts everything in the background and returns; it does not need to clean up. After `bash bringup.sh`, from ROS 2 I must be able to see `sensor_msgs/msg/Imu` on `/imu`, and the `frame_id` on that message must be the URDF link name the sensor is mounted on. A ROS 2 node running with `use_sim_time` must see Gazebo time, not wall time.' ;;
  # ros2-troubleshooting executor ladder (evals/LADDER.md). All three prompts
  # FROZEN 2026-07-31 before any cell ran, per LADDER.md rule 1. tr2/tr3 have no
  # checker yet -- rule 4 stops at the first rung that fails, so their harness is
  # built only if the rung below passes. Freezing the text now is what stops the
  # ladder being reshaped after a result.
  tr1) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory. It is a Python node that calls the `/slow_check` service (`std_srvs/srv/Trigger`) once per second from a timer callback, logs a line `RESULT <n> <success>` for each response it receives, and exits with status 0 once it has logged 5 results. The service takes about one second to respond. A `/slow_check` server is already running.' ;;
  tr2) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory. It must publish `std_msgs/msg/Int32` on `/heartbeat` at a steady 10 Hz, and at the same time call the `/slow_check` service (`std_srvs/srv/Trigger`) from inside its `/tick` subscription callback (`std_msgs/msg/Int32`) every time a tick arrives. Log `RESULT <n> <success>` per response. The heartbeat rate must not drop while service calls are in flight. Exit with status 0 after 5 results. The service takes about one second to respond; a `/slow_check` server and a `/tick` publisher are already running.' ;;
  tr3) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory. It must call the `/slow_check` service (`std_srvs/srv/Trigger`) five times CONCURRENTLY from a single timer callback and wait for all five, logging `RESULT <n> <success>` per response and a final `TOTAL <seconds>` line with the elapsed wall time for the batch. Each call takes about one second, so five sequential calls would take about five seconds; the batch must finish in under three. Exit with status 0. A `/slow_check` server is already running.' ;;
  # ros2-troubleshooting QoS ladder (evals/LADDER.md). All three prompts FROZEN
  # 2026-07-31 before any cell ran, per LADDER.md rule 1. qos2/qos3 have no
  # checker yet -- rule 4 stops at the first rung that fails.
  qos1) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that subscribes to `/sensor` (`std_msgs/msg/Int32`) and logs a line `GOT <data>` for every message it receives. Exit with status 0 once it has logged 20 messages. A publisher for `/sensor` is already running.' ;;
  qos2) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that subscribes to BOTH `/sensor` (`std_msgs/msg/Int32`) and `/config` (`std_msgs/msg/String`), logging `GOT <data>` per `/sensor` message and `CONFIG <data>` when it receives the configuration. `/config` carries a single value that was published once, before your node starts, and is never published again. Exit with status 0 once it has logged the CONFIG line and 20 GOT lines. Publishers for both topics are already running.' ;;
  qos3) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that subscribes to `/sensor` (`std_msgs/msg/Int32`), `/config` (`std_msgs/msg/String`) and `/paced` (`std_msgs/msg/Int32`), logging `GOT <data>`, `CONFIG <data>` and `PACED <data>` respectively. `/config` was published once before your node starts and never again. The `/paced` publisher offers a 200 ms deadline. Exit with status 0 once it has logged the CONFIG line, 20 GOT lines and 10 PACED lines. All three publishers are already running.' ;;
  # ========================================================================
  # 2026-07-31 coverage sweep. Four skills that never had a ladder:
  # ros2-control (ctl*), ros2-testing (tst*), ros2-perception (per*),
  # ros2-moveit (mvt*). ALL TWELVE PROMPTS FROZEN 2026-07-31 before any cell
  # of any of them ran, per LADDER.md rule 1. Checkers are built rung by rung
  # (rule 4 stops at the first failure), but no prompt may be edited after its
  # rung has run -- freezing all twelve now is what stops the ladder being
  # reshaped once a result is visible.
  #
  # ros2-microros is deliberately absent: no MCU on this machine, and the user
  # standing instruction is not to verify it.
  # ========================================================================

  # --- ros2-control -------------------------------------------------------
  # L1 mechanisms: URDF <ros2_control> block; mock_components/GenericSystem;
  #   controller_manager params YAML; joint_state_broadcaster + a controller
  #   spawned; /joint_states actually populated.
  ctl1) PROMPT='On ROS 2 Jazzy, in the current directory set up a minimal `ros2_control` system driven by `mock_components/GenericSystem` (no real hardware). One robot with two revolute joints `joint_a` and `joint_b`, each with a position command interface and position+velocity state interfaces. Write `bringup.sh` in the current directory that starts everything in the background and returns; it does not need to clean up. After `bash bringup.sh`, `ros2 topic echo /joint_states --once` must show both joint names, and `ros2 control list_controllers` must show `joint_state_broadcaster` active.' ;;
  # L2 adds: a second controller claiming interfaces (forward_command_controller);
  #   command actually flowing through to the mocked state; controller switching.
  ctl2) PROMPT='On ROS 2 Jazzy, in the current directory set up a `ros2_control` system on `mock_components/GenericSystem` with two revolute joints `joint_a` and `joint_b` (position command interface, position+velocity state interfaces). Alongside `joint_state_broadcaster`, run a `forward_command_controller/ForwardCommandController` named `position_controller` that commands the position interface of both joints. Write `bringup.sh` in the current directory that starts everything in the background and returns; it does not need to clean up. After `bash bringup.sh`, both controllers must be `active` in `ros2 control list_controllers`, and publishing a `std_msgs/msg/Float64MultiArray` with values `[0.5, -0.5]` on the controller command topic must make `/joint_states` report `joint_a` at ~0.5 and `joint_b` at ~-0.5.' ;;
  # L3 adds: a custom C++ SystemInterface hardware plugin (pluginlib export,
  #   on_init/export_*_interfaces/read/write), replacing mock_components.
  ctl3) PROMPT='On ROS 2 Jazzy, in the current directory create a colcon workspace with a C++ package `my_hw` providing a CUSTOM `hardware_interface::SystemInterface` plugin (not `mock_components`) for a robot with two revolute joints `joint_a` and `joint_b`, each exposing a position command interface and position+velocity state interfaces. The hardware must integrate commands into state so a commanded position is reflected back in the state interface. Build the workspace. Write `bringup.sh` in the current directory that starts everything in the background and returns; it does not need to clean up. After `bash bringup.sh`, `ros2 control list_hardware_components` must show your component active, `joint_state_broadcaster` must be active, and `/joint_states` must report both joints.' ;;

  # --- ros2-testing -------------------------------------------------------
  # L1 mechanisms: ament_cmake package with a registered pytest; colcon test
  #   actually running it; test-result reporting a nonzero test count.
  tst1) PROMPT='On ROS 2 Jazzy, in the current directory create a colcon workspace with one Python package `calc_pkg` containing a module with a function `add(a, b)`, and a pytest test file that tests it. Wire the test into the build so `colcon test` runs it. Build the workspace and run `colcon test`. When you are done, `colcon test-result --all` must report at least one test having run, and zero failures.' ;;
  # L2 adds: launch_testing -- a live node under test, generate_test_description,
  #   ReadyToTest, an active test asserting on real pub/sub traffic.
  tst2) PROMPT='On ROS 2 Jazzy, in the current directory create a colcon workspace with one Python package `echo_pkg` containing a node `echo_node` that subscribes to `/in` (`std_msgs/msg/Int32`) and republishes the same value on `/out`. Write a `launch_testing` integration test that launches `echo_node`, publishes on `/in`, and asserts the value arrives on `/out` while the node is running. Wire it into the build so `colcon test` runs it. Build the workspace and run `colcon test`. When you are done, `colcon test-result --all` must report at least one test having run, and zero failures.' ;;
  # L3 adds: rosbag2 -- programmatic recording of live traffic via rosbag2_py,
  #   then reading the bag back and asserting on its contents, inside the test.
  tst3) PROMPT='On ROS 2 Jazzy, in the current directory create a colcon workspace with one Python package `bag_pkg`. It must contain a node `ticker` that publishes an incrementing `std_msgs/msg/Int32` on `/ticks` at 10 Hz, and a test that: launches the node, records `/ticks` into a rosbag2 bag programmatically (not by shelling out to `ros2 bag record`), then opens that bag with the rosbag2 Python API and asserts it contains at least 10 messages on `/ticks` with increasing values. Wire it into the build so `colcon test` runs it. Build the workspace and run `colcon test`. When you are done, `colcon test-result --all` must report at least one test having run, and zero failures.' ;;

  # --- ros2-perception ----------------------------------------------------
  # L1 mechanisms: cv_bridge Image<->cv2 round trip; sensor-data QoS on a
  #   BEST_EFFORT camera; publishing a derived Image back.
  per1) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that subscribes to `/camera/image_raw` (`sensor_msgs/msg/Image`, `bgr8`), converts each frame with `cv_bridge`, draws anything you like on it, and republishes the result as `sensor_msgs/msg/Image` on `/annotated`. Log a line `FRAME <n>` per frame processed. Exit with status 0 once it has processed 20 frames. A camera publisher is already running.' ;;
  # L2 adds: camera_info intrinsics -- projecting a 3D point to pixel coords
  #   using P (not K) from a real CameraInfo, plus vision_msgs output.
  per2) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that subscribes to `/camera/image_raw` (`sensor_msgs/msg/Image`) and `/camera/camera_info` (`sensor_msgs/msg/CameraInfo`). For each frame, project the fixed 3D point `(0.1, 0.05, 2.0)` in the camera optical frame into pixel coordinates using the camera intrinsics from the CameraInfo message, and publish a `vision_msgs/msg/Detection2D` on `/detection` whose bounding box centre is that pixel. Log a line `PIXEL <u> <v>` per frame. Exit with status 0 once it has published 20 detections. Publishers for both topics are already running.' ;;
  # L3 adds: depth image -> point cloud; 16UC1 millimetre encoding; building a
  #   PointCloud2 with correct fields and iterating it back.
  per3) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that subscribes to `/depth/image_raw` (`sensor_msgs/msg/Image`) and `/depth/camera_info` (`sensor_msgs/msg/CameraInfo`), converts each depth frame into a `sensor_msgs/msg/PointCloud2` in metres using the camera intrinsics, and publishes it on `/points`. The cloud must have `x`, `y`, `z` float32 fields and must not contain points for invalid depth pixels. Log a line `CLOUD <n_points>` per frame. Exit with status 0 once it has published 20 clouds. Publishers for both topics are already running.' ;;

  # --- ros2-moveit --------------------------------------------------------
  # L1 mechanisms: URDF+SRDF for a serial arm; move_group launched and
  #   reaching a usable state; robot_state_publisher; planning scene alive.
  mvt1) PROMPT='On ROS 2 Jazzy, in the current directory create a MoveIt 2 setup for a simple 3-joint revolute serial arm you define yourself as a URDF, with a matching SRDF declaring a planning group named `arm`. Write `bringup.sh` in the current directory that starts `move_group` and everything it needs in the background and returns; it does not need to clean up. After `bash bringup.sh`, `ros2 node list` must show `/move_group`, and `ros2 service list` must include `/plan_kinematic_path`.' ;;
  # L2 adds: actually planning -- calling the GetMotionPlan service with a real
  #   joint-space goal and getting a trajectory with points back.
  mvt2) PROMPT='On ROS 2 Jazzy, in the current directory create a MoveIt 2 setup for a simple 3-joint revolute serial arm you define yourself as a URDF, with a matching SRDF declaring a planning group named `arm`. Write `bringup.sh` that starts `move_group` and everything it needs in the background and returns. Also write `plan.py` in the current directory: it must request a motion plan to a joint-space goal for the `arm` group and print `POINTS <n>` where n is the number of points in the returned trajectory, then exit 0. After `bash bringup.sh`, running `python3 plan.py` must print a `POINTS` line with n greater than 1.' ;;
  # L3 adds: a collision object in the planning scene that invalidates the
  #   direct path, so the plan must route around it -- requires the scene to be
  #   applied and actually respected.
  mvt3) PROMPT='On ROS 2 Jazzy, in the current directory create a MoveIt 2 setup for a simple 3-joint revolute serial arm you define yourself as a URDF, with a matching SRDF declaring a planning group named `arm`. Write `bringup.sh` that starts `move_group` and everything it needs in the background and returns. Also write `plan.py` in the current directory which must: add a box collision object to the planning scene, verify the scene contains it, request a motion plan to a joint-space goal for the `arm` group, and print `POINTS <n>` for the returned trajectory followed by `OBJECTS <m>` where m is the number of collision objects the planning scene reports, then exit 0. After `bash bringup.sh`, running `python3 plan.py` must print `POINTS` with n greater than 1 and `OBJECTS` with m at least 1.' ;;

  # --- ros2-core ----------------------------------------------------------
  # The remaining two skills, added to the same sweep. SIX PROMPTS FROZEN
  # 2026-07-31 before any cell of either ran, per LADDER.md rule 1.
  #
  # L1 mechanisms: TF2 broadcast + listen; a lookup that must use
  #   tf2::TimePointZero rather than "now"; parameters declared and read.
  cor1) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that broadcasts a static transform from `base_link` to `sensor_link` with translation `(0.2, 0.0, 0.1)` and no rotation, then looks that transform back up through a `tf2_ros` buffer and logs a line `TF <x> <y> <z>` with the translation it read. It must take the three translation values from ROS parameters named `tx`, `ty`, `tz` (defaults as above). Exit with status 0 once it has logged the TF line.' ;;
  # L2 adds: a dynamic (time-varying) transform; a lookup at a specific
  #   stamp rather than latest; handling the extrapolation exception that
  #   asking for a future stamp raises.
  cor2) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python node that broadcasts a DYNAMIC transform `odom` -> `base_link` at 20 Hz where x increases by 0.05 m per second, and simultaneously looks up `odom` -> `base_link` at the timestamp of each broadcast, logging `TF <t> <x>`. It must also attempt one lookup 5 seconds in the future and log `EXTRAP <message>` with the exception text instead of crashing. Exit with status 0 after 20 TF lines and the EXTRAP line.' ;;
  # L3 adds: a lifecycle node -- managed transitions, activation gating
  #   publication, and an external transition request being honoured.
  cor3) PROMPT='On ROS 2 Jazzy, write `node.py` in the current directory: a Python LIFECYCLE node named `counter` that publishes an incrementing `std_msgs/msg/Int32` on `/count` at 10 Hz, but ONLY while it is in the active state — nothing may be published while it is unconfigured or inactive. Log `STATE <label>` on every transition. The node must start unconfigured and stay running so that an external `ros2 lifecycle set` can drive it. Do not exit on your own.' ;;

  # --- ros2-dev -----------------------------------------------------------
  # L1 mechanisms: reading the shipped nav2_params.yaml as a baseline;
  #   producing a config that Nav2's own parameter loading accepts.
  dev1) PROMPT='On ROS 2 Jazzy with Nav2 installed, write `nav2_params.yaml` in the current directory: a complete Nav2 parameter file for a differential-drive robot with a 0.3 m radius circular footprint and a maximum speed of 0.4 m/s, using the MPPI controller. It must be loadable by the Nav2 servers as-is.' ;;
  # L2 adds: bringing the stack up and driving it through lifecycle to active,
  #   which is where a wrong plugin string or missing param actually bites.
  dev2) PROMPT='On ROS 2 Jazzy with Nav2 installed, in the current directory produce a Nav2 parameter file and a `bringup.sh` that starts the Nav2 controller_server, planner_server, behavior_server, bt_navigator and a lifecycle manager in the background and returns; it does not need to clean up. Use the MPPI controller and a 0.3 m radius circular footprint. After `bash bringup.sh`, `ros2 lifecycle get /controller_server` and `ros2 lifecycle get /planner_server` must both report `active`.' ;;
  # L3 adds: a costmap that actually ingests live sensor data and marks an
  #   obstacle -- the layer must be configured AND the observation source wired.
  dev3) PROMPT='On ROS 2 Jazzy with Nav2 installed, in the current directory produce a Nav2 parameter file and a `bringup.sh` that starts the Nav2 stack in the background and returns; it does not need to clean up. A `sensor_msgs/msg/LaserScan` is being published on `/scan` in frame `laser_frame`, and the transforms `map -> odom -> base_link -> laser_frame` are already being published by someone else. Configure the local costmap so that scan is an observation source marking obstacles. After `bash bringup.sh`, `/local_costmap/costmap` must be published and must contain at least one cell with cost above 250.' ;;

  *) echo "unknown task: $TASK (expected t1|t2|t3|t4|t5|t6|t7|g1|g2|g3|tr1|tr2|tr3|qos1|qos2|qos3|ctl1-3|tst1-3|per1-3|mvt1-3|cor1-3|dev1-3)" >&2; exit 2 ;;
esac

# --- preflight: refuse before any scenario or model call ----------------------
# Every check reports; the run stops if any failed. Nothing here writes outside
# /tmp or touches a process.
preflight() {
  local bad=0 out
  if [ -z "$MODEL" ]; then
    echo "preflight: MODEL is not set. Name it (MODEL=sonnet); the committed sweeps ran sonnet." >&2
    bad=1
  fi
  local t
  if ! python3 - "$HARNESS" "$TASK" <<'CHECK_TASK'
import sys
sys.path.insert(0, sys.argv[1])
from grade_v2 import TASKS
raise SystemExit(0 if sys.argv[2] in TASKS else 1)
CHECK_TASK
  then
    echo "preflight: $TASK has a frozen prompt but no grader; refusing an ungradable paid run" >&2
    bad=1
  fi
  local -A seen_cells=()
  for t in ${CELLS:-baseline skills}; do
    case "$t" in
      baseline|skills|scripts-only|claude-md-only) ;;
      *) echo "preflight: unsupported cell $t" >&2; bad=1 ;;
    esac
    if [ -n "${seen_cells[$t]:-}" ]; then
      echo "preflight: duplicate cell $t" >&2; bad=1
    fi
    seen_cells[$t]=1
    if [ -z "$PREFLIGHT_ONLY" ] && compgen -G "$OUT/${TASK}-${t}_*" >/dev/null; then
      echo "preflight: $OUT already contains $TASK/$t artifacts; use a fresh output directory" >&2
      bad=1
    fi
  done
  if [ "${#seen_cells[@]}" -eq 0 ]; then
    echo "preflight: CELLS must contain at least one condition" >&2
    bad=1
  fi
  for t in ROS_DISCOVERY_SERVER FASTDDS_DEFAULT_PROFILES_FILE FASTRTPS_DEFAULT_PROFILES_FILE CYCLONEDDS_URI; do
    if [ -n "${!t:-}" ]; then
      echo "preflight: unset $t; vendor configuration can override localhost discovery" >&2
      bad=1
    fi
  done
  for t in claude python3 unshare flock timeout; do
    command -v "$t" >/dev/null 2>&1 || { echo "preflight: '$t' not found" >&2; bad=1; }
  done
  [ -r /opt/ros/jazzy/setup.bash ] || { echo "preflight: /opt/ros/jazzy/setup.bash not readable" >&2; bad=1; }
  case "${EVAL_ROS_DOMAIN_ID:-90}" in
    ''|*[!0-9]*) echo "preflight: EVAL_ROS_DOMAIN_ID must be a number 1-101" >&2; bad=1 ;;
    *) { [ "${EVAL_ROS_DOMAIN_ID:-90}" -ge 1 ] && [ "${EVAL_ROS_DOMAIN_ID:-90}" -le 101 ]; } \
         || { echo "preflight: EVAL_ROS_DOMAIN_ID must be 1-101 (Linux-safe DDS range)" >&2; bad=1; } ;;
  esac
  # Leftovers of an earlier run that died before its own cleanup.
  out="$(python3 "$HARNESS/procscope.py" pids --any-tag 2>/dev/null || true)"
  if [ -n "$out" ]; then
    echo "preflight: processes from an earlier eval run are still alive: $(echo $out)" >&2
    echo "  They carry an EVAL_RUN_TAG, so this removes exactly them and nothing else:" >&2
    echo "  python3 $HARNESS/procscope.py kill --any-tag" >&2
    bad=1
  fi
  # A robot stack this harness did not start. Cells run model-written ROS code
  # and checkers publish commands, so do not share a host with a live robot.
  out="$(python3 "$HARNESS/procscope.py" foreign-ros 2>/dev/null || true)"
  if [ -n "$out" ] && [ "${EVAL_ALLOW_FOREIGN_ROS:-}" != 1 ]; then
    echo "preflight: ROS processes not started by this harness are running:" >&2
    printf '%s\n' "$out" | sed 's/^/  /' >&2
    echo "  Stop them, or set EVAL_ALLOW_FOREIGN_ROS=1 if they cannot be reached" >&2
    echo "  (the run itself stays on ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)." >&2
    bad=1
  fi
  if ! bash "$HARNESS/isolate_cell.sh" --check >/dev/null; then
    echo "preflight: isolation did not verify (message above)" >&2
    bad=1
  fi
  return $bad
}

# One run at a time per OS user. Concurrent rounds shared a DDS domain and graded
# each other's nodes (evals/runs/2026-07-31-sweep-L2/ctl2/r7 found parallel
# cells of the same task colliding on /controller_manager).
LOCK="${XDG_RUNTIME_DIR:-/tmp}/claude-ros2-eval-${UID}.lock"
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "run_ab.sh: another eval run holds $LOCK -- REFUSING to run concurrently." >&2
  exit 6
fi

if ! preflight; then
  echo "run_ab.sh: preflight failed -- nothing was started." >&2
  exit 3
fi
if [ -n "$PREFLIGHT_ONLY" ]; then
  echo "preflight ok (model=$MODEL)"
  exit 0
fi

# Everything this run starts carries this tag, and only tagged processes are
# ever killed (procscope.sh). A fresh tag, never an inherited one.
EVAL_RUN_TAG="$(python3 "$HARNESS/procscope.py" new-tag)"
export EVAL_RUN_TAG
# shellcheck source=procscope.sh
source "$HARNESS/procscope.sh"
# One DDS domain for this run's scenario and cells, on this host only.
export ROS_DOMAIN_ID="${EVAL_ROS_DOMAIN_ID:-$(( 90 + RANDOM % 12 ))}"

mkdir -p "$OUT"

# --- live scenario -----------------------------------------------------------
# Each task needs a running system for a cell to be able to verify against
# reality. It is started fresh for every cell and torn down after that cell's
# checker, so every condition sees the same thing: several checkers kill the
# scenario process as part of their own cleanup, which used to leave the second
# cell of a pair with no publisher at all.
SCENARIO_PIDS=()
start_scenario() {
  SCENARIO_PIDS=()
  # setup.bash reads unset vars; -u must be off while sourcing it.
  set +u
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
  set -u
  case "$TASK" in
    t1) bash "$REPO/evals/harness/t1_diffdrive_scenario.sh" up \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    t2) python3 "$REPO/evals/harness/fake_imu_pub.py" \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    t3) : ;;  # Nav2 config task; nothing to bring up, the install is the system
    t4) python3 "$REPO/evals/harness/fake_scan_pub.py" \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    t5) : ;;  # packaging task; the deliverable is a buildable workspace
    t6) : ;;  # ladder rung L2, same shape as t5
    t7) : ;;  # ladder rung L3
    g1|g2|g3) : ;;  # gazebo ladder; the deliverable is a world that runs
    # The executor and QoS ladders MUST have their scenario up during the cell,
    # not only during the check. Both prompt families say "a server/publisher is
    # already running", and qos1 in particular cannot be solved without
    # inspecting the publisher's QoS. Running the scenario only at check time
    # made that sentence false: cells ran `ros2 topic info /sensor -v`, got
    # "Unknown topic", and had to guess. Four of ten noticed /sensor was absent.
    tr1|tr2|tr3) python3 "$REPO/evals/harness/slow_trigger_server.py" \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!)
        if [ "$TASK" = tr2 ]; then
          python3 "$REPO/evals/harness/tick_publisher.py" \
            >>"$SCEN_LOG" 2>&1 &
          SCENARIO_PIDS+=($!)
        fi ;;
    qos1|qos2|qos3) python3 "$REPO/evals/harness/qos_publishers.py" \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    # 2026-07-31 coverage sweep. ctl*/tst*/mvt* are self-contained: the
    # deliverable is a workspace or a bringup script, and the cell brings up its
    # own system. per* need a camera, and per3 a depth camera -- the prompts say
    # "publishers are already running", so they must actually be running during
    # the cell, not only at check time (the mistake qos1 paid for).
    ctl1|ctl2|ctl3) : ;;
    tst1|tst2|tst3) : ;;
    mvt1|mvt2|mvt3) : ;;
    cor1|cor2|cor3) : ;;   # the node is the whole deliverable
    dev1) : ;;             # the install is the system; nothing to bring up
    # dev3 says the scan and the TF chain are already published, so they must
    # actually be up during the cell -- the mistake qos1 paid for.
    dev2|dev3) bash "$REPO/evals/harness/dev3_scenario.sh" up \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    per1|per2) python3 "$REPO/evals/harness/camera_publisher.py" \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    per3) python3 "$REPO/evals/harness/camera_publisher.py" --depth \
          >"$SCEN_LOG" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
  esac
  if ! python3 "$HARNESS/scenario_ready.py" "$TASK" >>"$SCEN_LOG" 2>&1; then
    echo "run_ab.sh: scenario $TASK did not become ready; no model call made. See $SCEN_LOG" >&2
    tail -n 20 "$SCEN_LOG" >&2
    return 2
  fi
  echo "scenario for task $TASK up (pids: ${SCENARIO_PIDS[*]:-none}, domain $ROS_DOMAIN_ID)"
}
stop_scenario() {
  # SIGTERM, then SIGKILL, to every process of THIS run -- scenario, whatever
  # the cell left running in the background, the checker's probes -- and to
  # nothing else on the host (it used to `pkill -9` every ros2_control_node).
  # SIGKILL because ten `ros2_control_node` processes from the t1 rounds were
  # found still running long afterwards: controller_manager does not act on
  # SIGTERM, `gz sim` ignored it in the gazebo rounds, and rclpy inside
  # executor.spin() ignored it in the executor rounds -- where a bare `wait` on
  # the survivor then hung a checker for 4 h 48 m.
  kill_owned_term
  sleep 2
  kill_owned
}
trap stop_scenario EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Exactly what a condition copies in, so it can be removed again afterwards: a
# `skills` cell's CLAUDE.md left in /tmp is a protocol copy the next `baseline`
# cell could find.
inject() {
  local cell="$1" dir="$2" s f
  case "$cell" in
    skills)
      mkdir -p "$dir/.claude/skills"
      for s in "$REPO"/skills/*/; do
        cp -r "$s" "$dir/.claude/skills/"
        echo ".claude/skills/$(basename "$s")"
      done
      cp "$REPO/CLAUDE.md" "$dir/"
      echo "CLAUDE.md" ;;
    # `scripts-only` ships the bundled scripts WITHOUT any SKILL.md or CLAUDE.md,
    # so a task about those scripts measures what the skill *text* buys rather
    # than what shipping the files buys -- without it that comparison is a
    # tautology, since an agent that globs finds the scripts either way.
    scripts-only)
      for s in "$REPO"/skills/*/scripts; do
        [ -d "$s" ] || continue
        mkdir -p "$dir/scripts"
        for f in "$s"/*; do
          cp -r "$f" "$dir/scripts/"
          echo "scripts/$(basename "$f")"
        done
      done ;;
    # `CLAUDE.md` and nothing else. The `skills` cell ships both CLAUDE.md and
    # skills/, so round 3's t1_searched_or_read result (3/10 -> 10/10, q=0.009)
    # could belong to either. CLAUDE.md's opening paragraph is itself an
    # instruction to verify against /opt/ros/jazzy, which is exactly the
    # behaviour that grader measures. This cell separates them.
    claude-md-only)
      cp "$REPO/CLAUDE.md" "$dir/"
      echo "CLAUDE.md" ;;
    baseline) ;;
    *) echo "unknown cell: $cell" >&2; return 2 ;;
  esac
}

run_cell() {
  local cell="$1" dir injected rel
  dir="$(mktemp -d "/tmp/eval-${TASK}-${cell}-XXXX")"
  injected="$(inject "$cell" "$dir")" || return 2

  echo "--- task $TASK / $cell  (model=$MODEL, cwd=$dir, domain=$ROS_DOMAIN_ID)"
  # Every cell runs with this repository hidden; see isolate_cell.sh. The
  # settings flags keep the host's user settings, enabled plugins, hooks and
  # MCP servers out of every condition alike; the project scope stays loaded
  # because that is where a treatment's CLAUDE.md and .claude/skills live. The
  # committed 2026-07/08 rounds ran without these three flags -- their init
  # events show no plugin and no pack skill loaded, which analyze_v2.py checks.
  local rc=0
  bash "$HARNESS/isolate_cell.sh" "$dir" \
    claude -p "$PROMPT" \
      --model "$MODEL" \
      --setting-sources project,local \
      --strict-mcp-config \
      --no-session-persistence \
      --settings '{"autoMemoryEnabled":false}' \
      --output-format stream-json --verbose \
      --permission-mode acceptEdits \
      --allowedTools WebFetch WebSearch Read Glob Grep Write Bash \
    > "$OUT/${TASK}-${cell}_result.jsonl" || rc=$?
  # An empty transcript with a non-zero exit means the cell never started:
  # isolation refused, or claude could not launch. Stop the run rather than
  # grade nothing. A session that ran and then errored is kept; the grader
  # records it as ungradable.
  if [ "$rc" -ne 0 ] && [ ! -s "$OUT/${TASK}-${cell}_result.jsonl" ]; then
    echo "run_ab.sh: cell $cell did not start (exit $rc) -- stopping the run." >&2
    exit "$rc"
  fi

  # Final assistant message + the tool names actually invoked, for grading.
  python3 "$HARNESS/summarize_run.py" \
      "$OUT/${TASK}-${cell}_result.jsonl" \
      > "$OUT/${TASK}-${cell}_final.md"

  # Real-outcome graders run against the workspace the cell left behind, so
  # they run here, while $dir still exists, and keep the verdict next to the
  # transcript. Every packaging defect t5 is about builds cleanly, so reading
  # the build log is not enough -- see the discrimination table in t5_check.sh.
  if [ -f "$HARNESS/${TASK}_check.sh" ]; then
    bash "$HARNESS/${TASK}_check.sh" "$dir" \
      "$OUT/${TASK}-${cell}_check.json" >/dev/null 2>&1 || true
  fi

  # Keep whatever top-level files the agent wrote, per cell: two conditions in
  # one out-dir used to overwrite each other's node.py.
  mkdir -p "$OUT/${TASK}-${cell}_files"
  find "$dir" -maxdepth 1 -type f ! -name CLAUDE.md \
    -exec cp {} "$OUT/${TASK}-${cell}_files/" \; 2>/dev/null || true
  # Remove exactly what inject() copied in; the agent's own work stays.
  while IFS= read -r rel; do
    if [ -n "$rel" ]; then rm -rf -- "${dir:?}/$rel"; fi
  done <<< "$injected"
  echo "    -> $OUT/${TASK}-${cell}_final.md"
  python3 "$HARNESS/grade_v2.py" "$TASK" "$OUT/${TASK}-${cell}_result.jsonl" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin)
print("       model=%s gradable=%s pack_loaded=%s" % (d["model"] or "?", d["gradable"], d["pack_components_loaded"] or "none"))' \
    || true
}

for cell in ${CELLS:-baseline skills}; do
  SCEN_LOG="$OUT/${TASK}-${cell}_scenario.log"
  start_scenario
  run_cell "$cell"
  stop_scenario
done

echo
echo "Grade with: python3 $HARNESS/analyze_v2.py <round-dir>"
echo "       or:  python3 $HARNESS/grade_v2.py $TASK <result.jsonl>"
