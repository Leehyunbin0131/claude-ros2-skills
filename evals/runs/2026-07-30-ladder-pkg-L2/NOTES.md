<!-- Ladder rung L2 for ros2-package. Rung and rules frozen in ../../LADDER.md
     before any cell ran. -->

# Ladder L2 — `ros2-package`: 70/70, climb to L3

10 cells, `t6`, **`baseline` only**, n=10, isolated. Rungs run baseline only:
the question is whether the model reaches it at all, and a real outcome answers
that without a comparison cell.

L2 adds a C++ `ament_cmake` package **with an executable**, a `.srv` consumed
from both C++ and Python, and a launch file that **includes another package's
launch file**. It exists because L1 left the `lib/${PROJECT_NAME}` install rule
and `install(DIRECTORY ...)` unexercised — L1 had no C++ executable.

## The result

**70 out of 70.**

| Check | baseline |
| :--- | ---: |
| `t6_builds` | 10/10 |
| `t6_srv_resolves` | 10/10 |
| `t6_cpp_run_works` | 10/10 |
| `t6_py_run_works` | 10/10 |
| `t6_composed_launch` | 10/10 |
| `t6_service_available` | 10/10 |
| `t6_first_build_clean` | 10/10 |

## Audited before being believed

Same three checks as L1, because a total ceiling is when to distrust the grader.

**Graders validated against broken references before the rung ran.** A correct
workspace, one with the C++ executable installed to `bin/`, one with the C++
`launch/` never installed. Each defect caught by exactly the check meant to
catch it; **both build with rc=0**.

**No build failed.** 6 cells ran `colcon build` once, 4 ran it twice, zero
failures across the round. Nobody iterated into correctness.

**Every cell's C++ executable is at `install/battery_cpp/lib/battery_cpp/guard`**
— checked on disk, all 10. That is verbatim the rule still shipped in
`SKILL.md` §2, produced unaided by every cell.

## Consequence

Rule 4: stop at the first rung that **fails**. L2 did not fail, so L3 runs, and
L2's outcome is recorded rather than acted on.

The two claims L1 left unexercised are now exercised and are **reachable**. They
are still in the file, because cutting them belongs to the reduction step, not
to a rung that was climbing past them. What L2 removes is the excuse for keeping
them.
