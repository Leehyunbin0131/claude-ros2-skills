# Verification status

**Nothing is currently verified.** The measurement round that produced the
previous table has been deleted, and the criterion it used has been replaced.

## What happened

The first round asked: *does the model produce this behaviour without the file?*
It answered that question carefully — 5,156 graded cells across nine skills —
using a harness that ran every cell single-turn with tools disabled.

Tools-off is a requirement of per-claim ablation: an agent with tools reads the
real file, so ablating a line from its context proves nothing. The mistake was
letting that constraint define the project. **Nobody ships an agent that cannot
look anything up**, so "the model does not know this unaided" is not the same as
"the skill earns its place", and the numbers systematically overstated what the
files were buying.

The criterion is now: **a skill supplies what the agent cannot reach on its own**
— with the model's knowledge, web search, and a live install all available. See
[`DESIGN.md`](./DESIGN.md), written before any v2 measurement.

## What survived the reset

| | |
| :--- | :--- |
| All 23 run directories, all authored variants, every VERIFIED status | **deleted** — they answer the old question, and a KEEP does not transfer to the new one |
| Every CUT already applied to a skill file | **kept** — one-way logic: content the model produces without tools it certainly produces with them, so those cuts are conservative under the stricter rule |
| Two facts verified against the install | **kept** — properties of Jazzy, not of any harness (below) |
| Harness code and the real-outcome graders | **kept** — v2 needs them |
| Method failures in [`FINDINGS.md`](./FINDINGS.md) | **kept** — lessons about measuring, not about skills |

### The two install-verified facts

Both were found by asking the model cold and checking its answer against
`/opt/ros/jazzy/`, and both are now in the shipped skills:

- Jazzy's `diff_drive_controller` subscribes to `geometry_msgs/msg/TwistStamped`
  only, and has **no `use_stamped_vel` parameter** — the model prescribes one
  4 times out of 4. (`diff_drive_controller_parameters.hpp` declares 23
  parameters; none is that.)
- Jazzy replaced `/servo_node/start_servo` (`std_srvs/srv/Trigger`) with
  `/servo_node/switch_command_type` (`moveit_msgs/srv/ServoCommandType`). The
  model prescribes the removed service 4 times out of 4, and the skill used to
  agree with it.

## Status

| Skill | Status |
| :--- | :--- |
| `ros2-core`, `ros2-package`, `ros2-testing`, `ros2-perception`, `ros2-troubleshooting`, `ros2-control`, `ros2-moveit`, `ros2-dev`, `gazebo-sim` | NOT VERIFIED — awaiting v2 |
| `ros2-microros` | OUT OF SCOPE — no `micro_ros_agent` or `micro_ros_setup` in apt for Jazzy; needs a multi-repository source build |

`ros2-security` was deleted during the first round because the model reproduced
all of it unaided, including details no check tested. That decision was already
the one resting on an argument rather than a number, and v2 is the setting that
can actually test it — a file of documentation pointers cannot pay off in a
harness with no second turn and no tool to follow a link with.

## Reading order

- [`DESIGN.md`](./DESIGN.md) — the criterion and the v2 plan. Start here.
- [`TASKS.md`](./TASKS.md) — the four v2 tasks, their graders, and what was
  decided in advance so it cannot be adjusted after seeing numbers.
- [`FINDINGS.md`](./FINDINGS.md) — what the first round taught, including what
  it got wrong. Read the "what we got wrong" half.
- [`PROCEDURE.md`](./PROCEDURE.md) — step-by-step, being rewritten for v2.
- [`harness/README.md`](./harness/README.md) — the tools.
