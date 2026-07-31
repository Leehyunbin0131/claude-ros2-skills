<!-- gazebo-sim ladder rung L3 — the top of a fixed-length ladder. -->

# Ladder gz-L3 — 28/30, ladder exhausted

10 cells, `g3`, **`baseline` only**, n=10, isolated. L3 adds a URDF published on
`/robot_description` and spawned with `ros_gz_sim`, an IMU needing
`gz-sim-imu-system`, sensor frame naming, and `use_sim_time`.

| Check | baseline |
| :--- | ---: |
| `g3_imu_in_ros` | 9/10 |
| `g3_frame_id_is_link` | 9/10 |
| `g3_sim_time` | 10/10 |

Failure threshold is **≤7/10** on a real-outcome check. Nothing came near it.

## The one genuine cell failure

**r3, and only r3** — the same cell fails both `g3_imu_in_ros` and
`g3_frame_id_is_link`, the second because there is no message to read a frame
from. Diagnosed on disk, per rule 6:

- its world **does** load `gz-sim-imu-system`
- its bridge line **is** `/imu@sensor_msgs/msg/Imu[gz.msgs.IMU`, syntactically correct
- but its sensor publishes on the Gazebo topic `/imu/raw`, so the bridge maps a
  Gazebo topic that does not exist

A self-inconsistency inside one cell, not a shared gap. The prompt names ROS
`/imu` explicitly, so grading it is traceable to the frozen text.

One cell in ten is what the threshold calls noise: *"three cells in ten getting
it wrong is a gap; one is noise."*

## `g3_spawned` was removed after the round

Dropping a failing check after seeing it fail is the manufacturing pattern in
reverse, so this is set out in full rather than mentioned.

It never met the standard the other three met. **Before the round it was
recorded as "validated by construction"** — no reference variant ever made it
fail. Three definitions were tried and each asserted something the frozen prompt
does not require:

| Definition | Assumption | What happened |
| :--- | :--- | :--- |
| `>= 2` models | a ground plane exists | 5/10 cells built a world without one |
| URDF robot name appears in the model list | Gazebo's model name equals the URDF robot name | `ros_gz_sim create -name` sets it independently |
| `gz model --list` | the world is named `default` | cells naming their world anything else returned only `ground_plane` |

It is also **redundant**: an IMU publishing from a robot proves that robot is in
the world. Every cell it marked "not spawned" contradicted it by passing
`g3_imu_in_ros`.

Keeping a check whose failures are provably false is worse than removing it. But
this is the weakest link in the round's rigor, and it is recorded that way.

## Verdict: ladder exhausted, `gazebo-sim` is unnecessary

Rule 3 fixes the ladder at three rungs; rule 5 makes an exhausted ladder a
verdict and **forbids a rung 4**.

| Rung | Mechanisms added | Result |
| :--- | :--- | ---: |
| L1 | SDF world, physics system, diff-drive robot, headless run | 40/40 |
| L2 | + `ros_gz_bridge` direction chars, `gpu_lidar` + `gz-sim-sensors-system`, `/clock` | 40/40 |
| L3 | + URDF spawn via `ros_gz_sim`, `gz-sim-imu-system`, frame naming, `use_sim_time` | 28/30 |

**108 of 110 cell-checks, unaided.** An agent with a shell and no skill file
writes a world that runs headless, a diff-drive robot that drives, a bridge with
the right direction characters, a rendering sensor with the system plugin it
needs, `/clock`, a URDF spawned through `ros_gz_sim`, an IMU whose `frame_id` is
the URDF link name, and a node that follows sim time.

Every headline row of `SKILL.md`'s symptom table was tested and none of them was
a thing a cell got wrong:

| Symptom row | Rung | Cells that got it wrong |
| :--- | :--- | ---: |
| bridge direction char (`[` vs `]`) | L2 | 0/10 |
| rendering sensor silent without `gz-sim-sensors-system` | L2 | 0/10 |
| `/clock` not bridged, `use_sim_time` broken | L2, L3 | 0/10 |
| IMU silent without `gz-sim-imu-system` | L3 | 0/10 |
| frame composed as `<model>/<link>/<sensor>` | L3 | 0/10 |

## What is not measured, and stays that way

- **"Robot falls through the ground."** No constructible failing case: deleting
  `<inertial>` leaves the robot driving 1.69 m because SDF supplies a default
  mass, and `/odom`'s planar pose puts z at 0, which protobuf omits.
- **Gazebo Classic confusion.** `SKILL.md` §1 warns against mixing
  `gazebo_ros_pkgs`. No rung created an opportunity to make that mistake.
- **Tuning advice** ("never tune Nav2 solely in sim"). Not a mechanism; nothing
  runs.
