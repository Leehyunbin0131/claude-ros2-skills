<!-- gazebo-sim ladder rung L2. Read the second half first: this round's real
     subject is the grader, not the model. -->

# Ladder gz-L2 — 40/40, and a rung that almost failed for the wrong reason

10 cells, `g2`, **`baseline` only**, n=10, isolated. L2 adds `ros_gz_bridge`
direction characters, a `gpu_lidar` needing `gz-sim-sensors-system`, and
`/clock`. Each cell writes the world **and** a `bringup.sh` the checker runs.

| Check | baseline |
| :--- | ---: |
| `g2_scan_in_ros` | 10/10 |
| `g2_scan_360` | 10/10 |
| `g2_clock_in_ros` | 10/10 |
| `g2_ros_cmd_moves` | 10/10 |

Rule 4: L2 did not fail, so L3 runs.

---

## The first grading said 6/10, and it was wrong

`g2_ros_cmd_moves` came back **6/10** — under the pre-registered failure
threshold of ≤7/10. That is the ladder announcing a gap: the point where content
gets written into the skill.

**It was the checker.** The four "failing" cells reported `nan -> nan`, not
`0 -> 0`. `nan` does not mean the robot stayed still; it means **no odometry was
read at all.**

| cell | odometry topic it used | first grading | regrade |
| :--- | :--- | :--- | :--- |
| r1 | `/model/diffbot/odometry` | FAIL | **pass** |
| r2 | `/model/diff_drive_robot/odometry` | FAIL | **pass** |
| r6 | `/model/diff_drive_robot/odometry` | FAIL | **pass** |
| r8 | `/model/vehicle/odometry` | FAIL | **pass** |
| the other six | `/odom` | pass | pass |

The four are exactly the cells that did not set `<odom_topic>` in the DiffDrive
plugin, so gz-sim used its default `/model/<name>/odometry`. **The `g2` prompt
never asked for the topic to be called `/odom`** — `g1`'s did, `g2`'s does not.
Those cells did precisely what was asked and the grader could not see it.

A manufactured gap, at the exact rung where the ladder was looking for one, in
the direction the experimenter would have found most interesting. Nothing in the
pass rate looked wrong; only `nan` instead of `0` gave it away.

The fix: **discover the odometry topic by message type (`gz.msgs.Odometry`),
never by name.** The cells were re-graded from their preserved workspaces — the
artifacts are untouched, only the measurement changed.

## Six grader defects, and what each would have produced

Every one of them was found by a number looking odd, not by reading the code.

| # | Defect | Left in place |
| :--- | :--- | :--- |
| 1 | range parser expected an inline `[a, b, c]`; `ros2 topic echo` prints a YAML **block sequence** | every cell fails |
| 2 | odometry topic hardcoded to `/odom`, which the prompt never required | **4/10 false gap** |
| 3 | `pkill -f "gz sim"` matches any process whose command line contains that string — including the wrapper shell | kills its own parent |
| 4 | a cell's `bringup.sh` leaves `gz sim` running after the session ends; strays leak into `gz topic -l` (19 topics for a 10-topic world) | reads a simulation nobody is driving |
| 5 | **`gz sim` ignores SIGTERM headless.** A stray was found alive 23 minutes after its cell, surviving `pkill`, dying only to `kill -9` | cleanup silently does nothing |
| 6 | **`set -o pipefail` + `grep -q`** | success reported as failure |

Number 6 is the one worth remembering. `cmd | grep -q PATTERN` exits *non-zero
on a match*: `grep -q` returns as soon as it matches, the producer gets SIGPIPE,
and `pipefail` propagates that. It is racy — short output finishes before `grep`
exits — so it passed standalone and failed inside the checker, which cost more
time than the other five together. Capture first, match on the string.

## What this round is actually evidence for

Two things, and the second matters more.

**The model reaches L2 unaided.** Ten of ten cells produced a world plus a
bring-up where ROS 2 sees a 360-ray `LaserScan` with finite ranges, sees
`/clock`, and drives the robot by publishing `Twist` on `/cmd_vel`. Both
headline rows of `SKILL.md`'s symptom table — the missing
`gz-sim-sensors-system` and the reversed bridge direction character — were
things no cell got wrong.

**A ladder is only as honest as its grader.** The rule that saved this round was
not one of the six in `LADDER.md`; it was refusing to accept a failure that
arrived in a convenient shape. `nan` and `0` are both "did not move" to a
threshold, and only one of them is a finding.
