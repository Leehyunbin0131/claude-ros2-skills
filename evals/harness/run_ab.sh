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
          >"$OUT/${TASK}_scenario.log" 2>&1 &
        SCENARIO_PIDS+=($!)
        if [ "$TASK" != tr1 ]; then
          python3 "$REPO/evals/harness/tick_publisher.py" \
            >>"$OUT/${TASK}_scenario.log" 2>&1 &
          SCENARIO_PIDS+=($!)
        fi ;;
    qos1|qos2|qos3) python3 "$REPO/evals/harness/qos_publishers.py" \
          >"$OUT/${TASK}_scenario.log" 2>&1 &
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
          >"$OUT/${TASK}_scenario.log" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    per1|per2) python3 "$REPO/evals/harness/camera_publisher.py" \
          >"$OUT/${TASK}_scenario.log" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
    per3) python3 "$REPO/evals/harness/camera_publisher.py" --depth \
          >"$OUT/${TASK}_scenario.log" 2>&1 &
        SCENARIO_PIDS+=($!) ;;
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
    t6) : ;;
    t7) : ;;
    g1|g2|g3) : ;;
    tr1|tr2|tr3) timeout 25 ros2 service list 2>/dev/null | grep -q slow_check || sleep 3 ;;
    qos1|qos2|qos3) for _ in $(seq 1 20); do
          TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
          case "$TL" in */sensor*) break ;; esac
          sleep 1
        done ;;
    ctl1|ctl2|ctl3|tst1|tst2|tst3|mvt1|mvt2|mvt3) : ;;
    cor1|cor2|cor3|dev1) : ;;
    dev2|dev3) timeout 30 ros2 topic echo /scan --once >/dev/null 2>&1 || true ;;
    per1|per2) timeout 25 ros2 topic echo /camera/image_raw --once >/dev/null 2>&1 || true ;;
    per3) timeout 25 ros2 topic echo /depth/image_raw --once >/dev/null 2>&1 || true ;;
  esac
  echo "scenario for task $TASK up (pids: ${SCENARIO_PIDS[*]})"
}
stop_scenario() {
  # SIGTERM, then SIGKILL. Ten `ros2_control_node` processes from the t1 rounds
  # were found still running long afterwards because this sent only SIGTERM and
  # controller_manager does not act on it. Third instance of the same lesson in
  # this project: `gz sim` ignored SIGTERM in the gazebo rounds, and rclpy inside
  # executor.spin() ignored it in the executor rounds -- where a bare `wait` on
  # the survivor then hung a checker for 4 h 48 m.
  [ ${#SCENARIO_PIDS[@]} -eq 0 ] || kill "${SCENARIO_PIDS[@]}" 2>/dev/null || true
  sleep 2
  [ ${#SCENARIO_PIDS[@]} -eq 0 ] || kill -9 "${SCENARIO_PIDS[@]}" 2>/dev/null || true
  pkill -9 -f '^/opt/ros/jazzy/lib/controller_manager/ros2_control_node' 2>/dev/null || true
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
  case "$TASK" in
    t5|t6|t7|g1|g2|g3|tr1|tr2|tr3|qos1|ctl1|ctl2|ctl3|tst1|tst2|tst3|per1|per2|per3|mvt1|mvt2|mvt3|cor1|cor2|cor3|dev1|dev2|dev3)
      bash "$REPO/evals/harness/${TASK}_check.sh" "$dir" \
        "$OUT/${TASK}-${cell}_check.json" >/dev/null 2>&1 || true ;;
  esac

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
