<!-- Round 5. Design, graders, discrimination table and prediction are
     pre-registered in ../../TASKS.md, "T5". -->

# v2 round 5 — `ros2-package`: the build loop reaches every seam unaided

20 cells, `t5` only, `baseline` vs `skills`, n=10, isolated. First of the seven
skills that had no v2 measurement at all.

## The result

**120 out of 120.** Every check, both cells.

| Check | baseline | skills | Δ | q |
| :--- | ---: | ---: | ---: | ---: |
| `t5_builds` | 10/10 | 10/10 | +0.00 | 1.000 |
| `t5_interface_resolves` | 10/10 | 10/10 | +0.00 | 1.000 |
| `t5_run_works` | 10/10 | 10/10 | +0.00 | 1.000 |
| `t5_launch_resolves` | 10/10 | 10/10 | +0.00 | 1.000 |
| `t5_params_installed` | 10/10 | 10/10 | +0.00 | 1.000 |
| `t5_first_build_clean` | 10/10 | 10/10 | +0.00 | 1.000 |

## A total ceiling is exactly when to distrust the grader

The last time this project produced a wall of perfect scores, the cause was a
check written against the file's own phrasing. Three things were done before
reading anything into this one.

**1. The graders were validated against deliberately broken workspaces, before
the round.** Four reference workspaces, one correct and three each carrying one
real packaging defect:

| variant | `builds` | `interface` | `run` | `launch` | `params` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| correct | pass | pass | pass | pass | pass |
| `setup.cfg` deleted | pass | pass | **FAIL** | pass | pass |
| launch/config not in `data_files` | pass | pass | pass | **FAIL** | **FAIL** |
| interfaces in an `ament_python` package | pass | **FAIL** | pass | pass | pass |

Each defect is caught by exactly the check meant to catch it. And **`colcon
build` exits 0 in all four** — the obvious grader, reading the build log, would
have passed every broken package.

**2. The build counts were audited.** If cells had reached a working package by
grinding through failures, `t5_first_build_clean` would show it. It does not:
17 of 20 cells ran `colcon build` exactly once, 3 ran it twice, and **no build
in the round failed.** Nobody iterated into correctness; they wrote it correctly.

**3. Two baseline workspaces were opened on disk** rather than trusted through
the checker. Both have `setup.cfg` with the ROS install paths, the console
script at `install/battery_monitor/lib/battery_monitor/monitor`, and
`monitor.launch.py` plus the config under `share/battery_monitor/`. The wiring
is genuinely right.

The ceiling is real.

## The prediction was wrong, and that is the finding

`TASKS.md` predicted `t5_launch_resolves` and `t5_params_installed` as the place
the cells would separate — `launch/` is not installed by default, and nothing in
the prompt asks the agent to run `ros2 launch` and find out. Baseline scored
10/10 on both.

The reason is visible in the transcripts: asked for a launch file that runs the
node with a config, agents install both, because a launch file they cannot
launch is obviously not the deliverable. The seam is only invisible when you
stop at `colcon build`, and none of them stopped there.

## What this licenses

`ros2-package` is the first of the seven uncovered skills to get a measurement,
and the measurement says its wiring prose is dead weight — **for the seams this
task actually exercised.** Those are, exactly:

| Claim in `SKILL.md` | Exercised by | Result |
| :--- | :--- | :--- |
| `ament_python` needs the `build_type` export in `package.xml` | every cell | 10/10 unaided |
| `setup.cfg` needs `script_dir`/`install_scripts`, or `ros2 run` cannot find the node | `t5_run_works` | 10/10 unaided |
| interfaces require an `ament_cmake` package, with the rosidl depends and `member_of_group` | `t5_interface_resolves` | 10/10 unaided |
| `rosidl_generate_interfaces` first arg starts with the project name | `t5_interface_resolves` | 10/10 unaided |
| launch and config must reach `share/` via `data_files` (the `ament_python` path) | `t5_launch_resolves`, `t5_params_installed` | 10/10 unaided |

Cut — 69 lines to 31. Every one of them is reproduced by an agent with a shell
and no skill.

## What it does not license

Two things in `SKILL.md` §2 look like they were covered and were not. Both stay.

**The `ament_cmake` executable rule.** "Executables must install to
`lib/${PROJECT_NAME}` exactly — that is the only place `ros2 run` looks" was
never exercised: both packages carrying a node here are `ament_python`, and the
`ament_cmake` package has no executable.

**The `install(DIRECTORY ...)` rule.** The measured seam is the `ament_python`
`data_files` path. The sentence in the file is about `ament_cmake`'s
`install(DIRECTORY ...)`, which no cell in this round had to write. It is the
same idea, and that is exactly why it would be easy to cut it on this evidence
and be wrong.

A C++ variant of `t5` settles both in one round. Until then they are unmeasured,
like the doc-entry-point table and the rebuild-and-re-source rule.

**And nothing here transfers to the other six.** This is one skill measured on
one task. `gazebo-sim`, `ros2-perception`, `ros2-core`, `ros2-testing`,
`ros2-dev` and `ros2-troubleshooting` are exactly as unmeasured as they were
before this round.
