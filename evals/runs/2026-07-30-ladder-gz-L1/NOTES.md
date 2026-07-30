<!-- gazebo-sim ladder rung L1. Rung, graders and rules frozen in ../../LADDER.md
     before any cell ran. -->

# Ladder gz-L1 — 40/40, climb to L2

10 cells, `g1`, **`baseline` only**, n=10, isolated.

L1 asks for one SDF world with a ground plane and a differential-drive robot that
drives when commanded on the Gazebo `/cmd_vel` topic, running headless.

| Check | baseline |
| :--- | ---: |
| `g1_sdf_valid` | 10/10 |
| `g1_sim_runs` | 10/10 |
| `g1_topics_present` | 10/10 |
| `g1_robot_moves` | 10/10 |

Every cell's robot drove **1.65–1.69 m** in the 5-second window — the
hand-written reference world reaches 1.69 m, so the cells are producing
essentially the same physics.

## The environment nearly produced a fake gap

`SKILL.md` says to write `<render_engine>ogre2</render_engine>`. On this machine
`ogre2` under `--headless-rendering` **segfaults** inside
`Ogre::Hlms::createDatablock` — topics advertise, then the process dies with no
data. `ogre` (Ogre 1.x) works.

Left alone, every cell would have failed for a reason having nothing to do with
its SDF, and the round would have read as *"the model cannot make Gazebo work."*
`g1_check.sh` forces `--render-engine ogre`, which overrides the SDF's request.
No cell is scored on the crash.

## Graders, and the two that were rejected

All four checks have a demonstrated failing case:

| Check | Shown to fail on |
| :--- | :--- |
| `g1_sdf_valid` | a mismatched `</inertia>` → `XML_ERROR_MISMATCHED_ELEMENT` |
| `g1_sim_runs` | `ogre2` headless → segfault |
| `g1_topics_present` | a world with the robot but no `DiffDrive` plugin → `/odom` never advertised |
| `g1_robot_moves` | `DiffDrive` naming joints no `<joint>` declares → world loads, `/odom` publishes, 0 cm |

**Rejected variant:** deleting `<inertial>` from the wheels. The robot still
drives 1.69 m — SDF supplies a default mass and unit inertia. So `SKILL.md`'s
"robot spawns then falls through the ground" row is **not measured**, and could
not be: `/odom` carries the planar pose, z is always 0, and protobuf text format
omits zero-valued fields. No constructible failing case, no grader.

**Two checker bugs, both found by an odd number rather than by review:** a
number regex that dropped the exponent from `-1.47e-17` (a stationary robot read
as *no data*), and treating an absent protobuf field as missing rather than zero.

## Consequence

Rule 4: L1 did not fail, so L2 runs. L2 adds the `ros_gz_bridge` direction
characters, a `gpu_lidar` needing `gz-sim-sensors-system`, and `/clock`.
