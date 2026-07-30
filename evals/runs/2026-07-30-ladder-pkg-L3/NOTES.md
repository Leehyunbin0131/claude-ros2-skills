<!-- Ladder rung L3 for ros2-package — the top of a fixed-length ladder.
     Rung, graders and rules frozen in ../../LADDER.md before any cell ran. -->

# Ladder L3 — the ladder is exhausted at ceiling

10 cells, `t7`, **`baseline` only**, n=10, isolated.

L3 adds a `.msg` field typed by `geometry_msgs/Point`, a composable node
registered through `rclcpp_components` and **loaded into a live container**, and
a test that `colcon test` has to actually run.

## The result

| Check | baseline |
| :--- | ---: |
| `t7_builds` | 10/10 |
| `t7_msg_dep_resolves` | 10/10 |
| `t7_component_registered` | 10/10 |
| `t7_component_loads` | 10/10 |
| `t7_tests_ran` | 10/10 |
| `t7_tests_pass` | 10/10 |
| `t7_first_build_clean` | **8/10** |

Every real-outcome check is at ceiling. The failure threshold fixed in
`LADDER.md` is **≤ 7/10 on a real-outcome check**; nothing came near it.

## The first non-ceiling number in three rungs, diagnosed

`t7_first_build_clean` is 8/10 — two cells' first `colcon build` failed. Rule 6
requires diagnosing that mechanically rather than reading a story into it. The
two failures are **unrelated**:

| cell | first-build failure | fixed by |
| :--- | :--- | :--- |
| r6 | `package.xml` declared `<depend>rclcpp_components</depend>` *and* `<exec_depend>` for it. `catkin_pkg` rejects it: "The generic dependency on 'rclcpp_components' is redundant with: exec_depend" | build 2 of 2 |
| r7 | the gtest target did not link the component library — `undefined reference to battery_node::Reporter::Reporter` | build 2 of 2 |

Two different one-off mistakes, both **loud** — a validation error and a linker
error, each printed with the exact cause — and both corrected on the next build.
That is ordinary iteration, not a shared gap. If seven cells had failed the same
way, this would be the content to write.

## The verdict: `ros2-package` is unnecessary

Rule 3 fixed the ladder at three rungs. Rule 5: an exhausted ladder is a verdict,
and **adding a rung 4 is forbidden.** The rule exists precisely for this moment —
climbing until the answer is the one you wanted is search dressed as measurement.

Across the three rungs: **19 real-outcome checks, n=10 each, 190 cell-checks, no
failure below ceiling.** An agent with a shell and no skill file, on this
install, writes:

- an `ament_python` package whose console script `ros2 run` can find
- an `ament_cmake` package whose executable installs to `lib/${PROJECT_NAME}`
- `launch/` and `config/` installed so `ros2 launch` and `get_package_share_directory` resolve them
- a launch file that includes another package's launch file
- `.msg` and `.srv` generation, including a field typed by another package's message
- a composable node registered and **loaded into a running container**
- a test `colcon test` actually runs and passes

That is the entire subject of the skill.

### Which of the 31 remaining lines this rests on

Stated exactly, because "the ladder said so" is not a per-line measurement:

| Lines | Content | Basis |
| :--- | :--- | :--- |
| §2, 6 lines | `lib/${PROJECT_NAME}`, `install(DIRECTORY ...)`, `ament_package()` last | **measured 10/10 unaided** at L2 and L3, and checked on disk in all 10 L2 cells |
| §3, 3 lines | rebuild **and** re-source before concluding something is broken | every rung required it; 30/30 cells |
| §1, 9 lines | documentation entry points, "read a working installed package and copy its structure" | **never graded directly.** Removed on rule 5, not on its own number |
| 13 lines | frontmatter, title, framing | scaffolding |

§1 is the one part going out on the ladder verdict rather than on a measurement
of itself. `REDUCTION.md` already flagged doc-entry-point tables as the least
certain cut in the pack; that is still true here.

## A limit worth stating

Each rung's prompt names the **requirement** — "must be loadable into an
`rclcpp_components` container", "at least one test that `colcon test` runs and
passes" — and never the **wiring**. It does not mention
`rclcpp_components_register_node`, the `PLUGIN` argument, where the library
installs, `DEPENDENCIES` in `rosidl_generate_interfaces`, or that a gtest target
has to link the library under test. The wiring is what the skill claims to supply
and what the graders test, so naming the goal is correct design: a task that hid
the goal would measure requirement-guessing instead.

What the ladder therefore does **not** answer: whether the agent would propose
composition, or a test, unprompted. That is a different question, and it is not
one `ros2-package` claims to answer.
