# The difficulty ladder

How to find what the model cannot reach, without manufacturing it.

## Why this replaces the audit

Rounds 1–5 asked one question: *does the shipped line change anything?* That
question can only ever delete. Five rounds produced two keeps and 40 deleted
lines, and the two keeps were a bundled script and one paragraph of
`CLAUDE.md` — nothing that any `SKILL.md` says.

But a skill scoring 120/120 against no-skill on `t5` does not mean packaging is
easy. It means **that task** was inside what the model reaches unaided. The
useful question is the other one:

> **Where does the model stop being able to do this on its own?**

Find that point, and the content to write is whatever is on the far side of it.
Never find it, and the skill really is unnecessary. Either answer is a result.

## The thing that would make this worthless

Raising difficulty until the model fails is trivially easy. Any skill can be
"proved necessary" by asking for something absurd. A ladder that stops when the
answer is the one you wanted is not measurement — it is search dressed as
measurement, and it is a more seductive version of the error that caused the
reverted reduction.

Six rules, all fixed before any rung of a ladder runs.

1. **The whole ladder is written first.** Every rung, in full prompt text, before
   any cell runs. A written rung is frozen — it cannot be edited after it has
   been run, not even for a typo that changes nothing.

2. **Rungs are defined by mechanisms added, not by difficulty felt.** Each rung
   names the specific things it adds — a second build system, an interface that
   depends on another package's interface, a component registration, a test that
   must pass. "Harder" is not a definition. If you cannot list what a rung adds
   as a set of mechanisms, it is not a rung.

3. **The ladder has a fixed length: three rungs per skill.** Decided here, once,
   for every skill.

4. **Stop at the first rung that fails.** Not the rung with the biggest effect.
   If L2 fails, L3 is not run — the gap is at L2 and that is where the content
   gets written.

5. **An exhausted ladder is a verdict, not a prompt to extend it.** Baseline at
   ceiling through L3 means the skill is unnecessary and gets cut. **Adding a
   rung 4 is forbidden.** This is the rule the whole document exists for.

6. **The failure must be diagnosed mechanically.** Which real-outcome check
   dropped, in how many cells, and what the cells actually produced on disk. Not
   a story read out of transcripts.

## What a rung is

A task with **real-outcome graders only** — something built, run, or checked by
a tool, never a phrasing match. Rungs run **`baseline` only**, n=10: the question
is whether the model reaches it, and a real outcome answers that without a
comparison cell. That also halves the cost of climbing.

**Failure threshold, fixed:** a rung fails if any real-outcome check comes back
**≤ 7/10**. Three cells in ten getting it wrong is a gap; one is noise.

**Every rung's graders are validated against deliberately broken reference
material before the rung runs.** A grader that has only seen good answers is not
validated. This has already caught one design that would have passed three
broken packages, because all three exit `colcon build` with code 0.

## What happens after a rung fails

Finding the gap is half of it. The other half is finding out whether text fixes
it.

1. **Diagnose.** Which check, how many cells, what they produced.
2. **Write the smallest line** that addresses exactly that. Not the topic — the
   failure.
3. **Verify the line, on the same rung, n=10:** `baseline` vs
   `baseline + that line`. Nothing else installed. This is the only comparison
   in the new method, and it tests one line at a time.
4. **The line ships only if the check it targets moves significantly.** If it
   does not, text is not the fix. The gap may need a bundled script — that is
   category 2, the one thing already measured to work (round 2, q<0.001) — or it
   may not be fixable, which is also worth writing down.

A line that fails step 4 is not shipped with an argument attached. That is how
622 lines happened.

### `patch` must not contain `CLAUDE.md`

The `patch` cell installs the candidate line **and nothing else** — no
`CLAUDE.md`, no other skill, no scripts. This is not a detail; it is the one way
phase 2 can go wrong, and it has already gone wrong once at task level.

`run_ab.sh`'s `skills` cell copies `CLAUDE.md` in alongside the skills, and
`CLAUDE.md` contains, verbatim, several of the behaviours the graders measure:

| `CLAUDE.md` says | which is the grader |
| :--- | :--- |
| "Do NOT answer ... from memorized knowledge ... verify against local `/opt/ros/jazzy/`" | `t1_searched_or_read` |
| "Ask when the request doesn't say" | `t3_asked_before_writing` |
| "Report what you actually observed — a build succeeding, `ros2 topic echo` showing data, a check script passing" | `t2_exit_code_read`, and the shape of `t5`/`t6` |

Round 4 caught this for `t1` and had to retract an attribution. **The flaw is
systemic, not a `t1` quirk.** It did not produce a false published claim
elsewhere — `t3` was null, round 2's `t2` comparison had no `CLAUDE.md` in either
cell, and `t5` was 120/120 in both — but every one of those was luck, not design.

A `patch` cell that shipped `CLAUDE.md` would make every candidate line look
effective, because `CLAUDE.md` would be doing the work. Any future condition that
needs `CLAUDE.md` present must have it present in **both** cells.

## The ladders

Three rungs per skill, all written before running. `L1` for `ros2-package` is
`t5`, already run.

### `ros2-package` — **LADDER EXHAUSTED AT CEILING, SKILL DELETED**

19 real-outcome checks across three rungs, n=10 each, 190 cell-checks, nothing
below ceiling. Rule 5 fired and the file was removed. The only non-ceiling number
in the whole ladder was `t7_first_build_clean` at 8/10, and the two failures were
unrelated one-offs — a redundant `<depend>` that `catkin_pkg` rejects out loud,
and a gtest target that did not link the library under test — both fixed on the
next build. Diagnosis in
[`runs/2026-07-30-ladder-pkg-L3/NOTES.md`](./runs/2026-07-30-ladder-pkg-L3/NOTES.md).

| Rung | Mechanisms added | Status |
| :--- | :--- | :--- |
| **L1** | `ament_python` node package; `ament_cmake` interface package with one `.msg`; launch file; params file | **run — 10/10 on all six checks** |
| **L2** | + a C++ node package (`ament_cmake` with an executable, which L1 never had); + a `.srv` consumed by both the C++ and the Python node; + a launch file that includes the other package's launch file | **run — 70/70** |
| **L3** | + a message field typed by another package's message (`DEPENDENCIES`); + a composable node registered through `rclcpp_components` and loaded into a container at launch; + a `colcon test` that must pass | **run — every real outcome 10/10** |

L2 exists because L1 left two claims in the file unexercised — the `ament_cmake`
`lib/${PROJECT_NAME}` install rule and `install(DIRECTORY ...)` — for the
specific reason that L1 had no C++ executable. That is a mechanism gap, not a
difficulty preference, which is what rule 2 requires.

**L2's graders, validated before the rung ran** (`t6_check.sh`), against a
correct workspace and two carrying one real defect each:

| variant | `builds` | `srv` | `cpp_run` | `py_run` | `composed` | `service` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| correct | pass | pass | pass | pass | pass | pass |
| C++ installed to `bin/` | pass | pass | **FAIL** | pass | FAIL | FAIL |
| C++ `launch/` not installed | pass | pass | pass | pass | **FAIL** | FAIL |

Both defects **build with rc=0**, as at L1. The two leave different signatures,
which is what makes rule 6 possible:

- `cpp_run_works` fails → wrong install destination
- `cpp_run_works` passes but `composed_launch` fails → `launch/` never installed

**L3's graders, validated before the rung ran** (`t7_check.sh`):

| variant | `builds` | `msg_dep` | `comp_reg` | `comp_loads` | `tests_ran` | `tests_pass` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| correct | pass | pass | pass | pass | pass | pass |
| component never registered | pass | pass | **FAIL** | FAIL | pass | pass |
| no test wired | pass | pass | pass | pass | **FAIL** | FAIL |

All three build rc=0, as at L1 and L2.

**`t7_tests_ran` is separate from `t7_tests_pass` because `colcon test` exits 0
when there are no tests.** Confirmed on the `no_tests` reference workspace: rc=0,
`tests_total=0`. "The tests pass" is not a claim until something has been shown
to run — the same class of silent success as a packaging defect that builds
clean, and a grader that only read `colcon test`'s exit code would have called
an empty test suite a pass.

### A silent failure found while building the L2 fixtures

Not part of any rung, recorded because it is a real property of this install and
was found the hard way. The first L2 reference workspace scored 2/6 on the
*correct* variant. The cause was in the fixture, not the checker: its
`package.xml` files were missing
`<export><build_type>ament_cmake</build_type></export>`.

Without that export, colcon identifies the package as **catkin**, generates
catkin-style environment hooks, and **never puts the package on
`AMENT_PREFIX_PATH`**. Consequences, in order of how much they mislead:

- `colcon build` exits **0** and reports the package finished.
- The files are all installed, in the right places.
- `ros2 interface show <pkg>/...` says `Unknown package`.
- `ros2 run <pkg> <exe>` says `Package not found`, with the executable sitting
  at `install/<pkg>/lib/<pkg>/<exe>`.

It is not a rung mechanism because `ros2 pkg create --build-type ament_cmake`
writes the export, so a task cannot force an agent into it without asking for
something artificial. It is exactly the shape of thing this project is looking
for, and it is here so it is not lost.

### The remaining six

Ladders get written when each skill's turn comes, under the same six rules, and
before any of its cells run. Recorded here as they are written so the order
cannot be rearranged after the fact.

### `gazebo-sim`

All three prompts written and frozen 2026-07-30 in `run_ab.sh` before any cell
ran. **`g2` and `g3` have no checker yet, deliberately** — rule 4 stops at the
first rung that fails, so their harness is built only if the rung below passes.
Freezing the prompts now is what stops the ladder being reshaped after a result.

| Rung | Mechanisms added | Status |
| :--- | :--- | :--- |
| **L1** (`g1`) | SDF world authoring; `gz-sim-physics-system`; a diff-drive robot with joints; `gz-sim-diff-drive-system` wired to those joints; headless `gz sim -s -r` | **run — 40/40**, every robot drove 1.65–1.69 m |
| **L2** (`g2`) | + `ros_gz_bridge parameter_bridge` with correct direction characters; + a `gpu_lidar`, which needs `gz-sim-sensors-system` in the world; + `/clock` bridged | **run — 40/40** (after a grader fix; see below) |
| **L3** (`g3`) | + URDF published on `/robot_description` and spawned with `ros_gz_sim`; + `gz-sim-imu-system`; + sensor `frame_id` matching the URDF link name rather than `<model>/<link>/<sensor>`; + `use_sim_time` actually following sim time | running |

**L1's graders, validated before the rung ran** (`g1_check.sh`). Every check has
a demonstrated failing case — the standard, since a grader with no constructible
failure is not a grader:

| Check | Shown to fail on |
| :--- | :--- |
| `g1_sdf_valid` | a mismatched `</inertia>` — `XML_ERROR_MISMATCHED_ELEMENT` (found by breaking the fixture accidentally) |
| `g1_sim_runs` | `ogre2` headless on this machine: segfault in `Ogre::Hlms::createDatablock` |
| `g1_topics_present` | a world with the robot but no `DiffDrive` plugin — `/odom` never advertised |
| `g1_robot_moves` | `DiffDrive` naming joints no `<joint>` declares: world loads, `/odom` publishes, robot moves 0 cm |

#### The environment nearly manufactured a gap

`skills/gazebo-sim/SKILL.md` tells you to write
`<render_engine>ogre2</render_engine>`. On this machine, **`ogre2` under
`--headless-rendering` segfaults**: the sensor topics get advertised, then the
process dies inside Ogre with no data. `ogre` (Ogre 1.x) works — 60 lidar ranges
and IMU samples, no crash.

Had the checker run the agent's world as written, **every cell would have failed
for a reason with nothing to do with its SDF**, and the round would have read as
"the model cannot make Gazebo sensors work." That is a fabricated gap, and it is
the same class of error as grading against a document instead of an outcome.

`g1_check.sh` therefore forces `--render-engine ogre`, which overrides whatever
the SDF asks for (verified: a world requesting `ogre2` runs fine under the flag).
The machine stops being a variable. **No cell is scored on the crash**, and the
crash is recorded here as an environment fact rather than smuggled in as a
finding.

From L2 up the checker has to execute the agent's own `bringup.sh`, so it cannot
pass the flag on its own command line, and there is no environment variable for
it (`GZ_SIM_RENDER_ENGINE_PATH` is a plugin search path, not a selection).
[`harness/gzshim/gz`](./harness/gzshim/gz) is prepended to `PATH` instead and
appends `--render-engine ogre` to any `gz sim` invocation. Verified to win even
when the caller passes `--render-engine ogre2` explicitly *and* the SDF requests
ogre2: 60 lidar ranges, no crash.

#### `g2` and `g3` were revised before either ran, and here is exactly why

Both originally ended "Give me the exact commands to bring it all up." That is
not mechanically gradable — the checker would have had to parse free-form
commands out of a transcript, which is the kind of judgement this project keeps
out of graders. Both now ask for a `bringup.sh` the checker can execute. **The
mechanism set is unchanged**; only the delivery format is.

Rule 1 freezes a rung once it *has run*. Fixing a gradability flaw found while
building the checker — the same stage that turned up the ogre2 crash — is
allowed. Changing a rung after seeing a result is not, and this is recorded so
the difference stays checkable.

**L3's graders, validated before the rung ran** (`g3_check.sh`):

| variant | `spawned` | `imu_in_ros` | `frame_id_is_link` | `sim_time` | measured `frame_id` |
| :--- | :---: | :---: | :---: | :---: | :--- |
| correct | pass | pass | pass | pass | `imu_link` |
| no `gz-sim-imu-system` | pass | **FAIL** | FAIL | pass | `` |
| no `<gz_frame_id>` | pass | pass | **FAIL** | pass | **`imubot/base_link/imu_sensor`** |
| `/clock` not bridged | pass | pass | pass | **FAIL** | `imu_link` |

The third row confirms `SKILL.md`'s claim **literally**: without `<gz_frame_id>`
Gazebo composes the frame as `<model>/<link>/<sensor>`, and the measured value is
exactly that. `g3_frame_id_is_link` compares against the link names parsed out of
the cell's own URDF, not against a fixed string.

`g3_sim_time` runs a real ROS node with `use_sim_time:=true` and reads its clock.
Sim time starts near zero and wall time is ~1.75e18 ns, so the two can never be
confused; the correct reference reported `SIMTIME 12655000000`.

`g3_spawned` passed in all four variants. A bring-up that never publishes
`/robot_description` would fail it, but that variant was not run — validated by
construction, and recorded as such rather than implied.

#### L2 almost failed for the wrong reason — the most instructive episode here

`g2_ros_cmd_moves` first graded **6/10**, under the pre-registered ≤7/10 failure
threshold. That is the ladder announcing a gap. It was the grader.

The four "failing" cells reported `nan -> nan`, not `0 -> 0`. `nan` is not "the
robot stayed still" — it is "no odometry was read at all". Those four were
exactly the cells that left `<odom_topic>` out of the DiffDrive plugin, so
gz-sim used its default `/model/<name>/odometry`. **The `g2` prompt never asked
for the topic to be called `/odom`** (`g1`'s did). They did what was asked and
the checker could not see it. Re-graded from the preserved workspaces after
switching to discovery **by message type**: 40/40.

The grader defects found on this rung, all by a number looking odd rather than
by review:

| # | Defect | Left in place |
| :--- | :--- | :--- |
| 1 | range parser expected inline `[a, b, c]`; `ros2 topic echo` prints a YAML block sequence | every cell fails |
| 2 | odometry topic hardcoded to `/odom` | **4/10 false gap** |
| 3 | `pkill -f "gz sim"` matches any command line containing that string, including the wrapper shell | kills its own parent |
| 4 | a cell's `bringup.sh` leaves `gz sim` alive after the session; strays leak into `gz topic -l` | reads a simulation nobody is driving |
| 5 | **`gz sim` ignores SIGTERM headless** — a stray survived 23 minutes and `pkill`, dying only to `kill -9` | cleanup silently does nothing |
| 6 | **`set -o pipefail` + `grep -q`** — `grep -q` exits on match, SIGPIPEs the producer, `pipefail` reports the pipeline as failed | success read as failure |

Number 6 is the one to remember: `cmd | grep -q PATTERN` can exit **non-zero on
a match**, and it is racy, so it passed standalone and failed inside the checker.
Capture first, then match.

**The rule that saved this round is not one of the six above.** It was refusing
a failure that arrived in a convenient shape. To a threshold, `nan` and `0` are
both "did not move"; only one of them is a finding.

#### One symptom row L1 cannot measure, stated rather than skipped

"Robot spawns then falls through the ground" is in `SKILL.md`'s symptom table and
is **not** graded. `/odom` carries the planar pose, so z is always 0 — and
protobuf text format omits zero-valued fields, so there is nothing to read. Worse,
the obvious defect does not work: deleting `<inertial>` from the wheels leaves the
robot driving 1.69 m, because SDF supplies a default mass and unit inertia. No
constructible failing case means no grader, so that row stays unmeasured.

| Skill | Ladder |
| :--- | :--- |
| `ros2-troubleshooting` | not yet written |
| `ros2-perception` | not yet written |
| `ros2-core` | not yet written |
| `ros2-testing` | not yet written |
| `ros2-dev` | not yet written |
| `ros2-moveit` | not yet written |

## What the files become

The current shape of a `SKILL.md` — architecture paragraph, documentation entry
point table, symptom/cause/action table, tuning baselines — is a textbook's
shape. Five rounds say a textbook is what the model already has.

New content is written in one shape only:

```
## <the failing case, in one line>

**Measured:** <check> failed <n>/10 unaided, at ladder rung <L>.
<The minimum thing to do differently.>
```

Two kinds of content do **not** get written, because they have been measured and
belong elsewhere:

- **Documentation entry points.** No measured effect anywhere.
- **"Verify against the install before writing it."** Round 4: `CLAUDE.md` alone
  produces this 10/10, and adding all ten skills on top moves nothing. It stays
  in `CLAUDE.md`, once.

Existing files are **not** rewritten into this shape ahead of their ladder.
Converting ten files on the strength of a method that has produced one measured
gap so far would be the reverted reduction again, with better prose.
