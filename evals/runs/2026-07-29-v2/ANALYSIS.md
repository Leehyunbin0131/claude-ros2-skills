# v2 round — `2026-07-29-v2`

45 cells graded

## Pass rate per check

| Task | Check | baseline | scripts-only | skills |
| :--- | :--- | ---: | ---: | ---: |
| `t4` | t4_guards_range | 5/5 | — | 5/5 |
| `t4` | t4_node_runs | 5/5 | — | 5/5 |
| `t1` | t1_correct_type | 5/5 | — | 5/5 |
| `t1` | t1_no_invented_param | 0/5 | — | 3/5 |
| `t1` | t1_searched_or_read | 0/5 | — | 4/5 |
| `t2` | t2_evidence_not_guess | 4/5 | 5/5 | 5/5 |
| `t2` | t2_exit_code_read | 0/5 | 5/5 | 5/5 |
| `t2` | t2_no_ros2_run | — | 5/5 | 5/5 |
| `t2` | t2_ran_script | 0/5 | 5/5 | 5/5 |
| `t3` | t3_asked_before_writing | 4/5 | — | 5/5 |
| `t3` | t3_asked_drive_type | 4/5 | — | 5/5 |
| `t3` | t3_asked_footprint | 4/5 | — | 5/5 |
| `t3` | t3_plugins_real | 0/1 | — | — |
| `t3` | t3_read_shipped_defaults | 1/5 | — | 0/5 |

## Tests

Comparisons and alpha fixed in TASKS.md before the round. `q` is Benjamini-Hochberg across every test here.

| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `t2` | t2_exit_code_read | scripts-only vs baseline | 5/5 | 0/5 | +1.00 | 0.008 | 0.063 | UNDERPOWERED |
| `t2` | t2_ran_script | scripts-only vs baseline | 5/5 | 0/5 | +1.00 | 0.008 | 0.063 | UNDERPOWERED |
| `t1` | t1_searched_or_read | skills vs baseline | 4/5 | 0/5 | +0.80 | 0.048 | 0.254 | UNDERPOWERED |
| `t1` | t1_no_invented_param | skills vs baseline | 3/5 | 0/5 | +0.60 | 0.167 | 0.667 | UNDERPOWERED |
| `t3` | t3_read_shipped_defaults | skills vs baseline | 0/5 | 1/5 | -0.20 | 1.000 | 1.000 | null |
| `t2` | t2_evidence_not_guess | scripts-only vs baseline | 5/5 | 4/5 | +0.20 | 1.000 | 1.000 | null |
| `t3` | t3_asked_before_writing | skills vs baseline | 5/5 | 4/5 | +0.20 | 1.000 | 1.000 | null |
| `t3` | t3_asked_drive_type | skills vs baseline | 5/5 | 4/5 | +0.20 | 1.000 | 1.000 | null |
| `t3` | t3_asked_footprint | skills vs baseline | 5/5 | 4/5 | +0.20 | 1.000 | 1.000 | null |
| `t4` | t4_guards_range | skills vs baseline | 5/5 | 5/5 | +0.00 | 1.000 | 1.000 | null |
| `t4` | t4_node_runs | skills vs baseline | 5/5 | 5/5 | +0.00 | 1.000 | 1.000 | null |
| `t1` | t1_correct_type | skills vs baseline | 5/5 | 5/5 | +0.00 | 1.000 | 1.000 | null |
| `t2` | t2_evidence_not_guess | skills vs scripts-only | 5/5 | 5/5 | +0.00 | 1.000 | 1.000 | null |
| `t2` | t2_exit_code_read | skills vs scripts-only | 5/5 | 5/5 | +0.00 | 1.000 | 1.000 | null |
| `t2` | t2_no_ros2_run | skills vs scripts-only | 5/5 | 5/5 | +0.00 | 1.000 | 1.000 | null |
| `t2` | t2_ran_script | skills vs scripts-only | 5/5 | 5/5 | +0.00 | 1.000 | 1.000 | null |

## Control gate

t4 shows no significant difference between cells — the harness is not tilted toward the skills condition, so the other tasks can be read.

## Tool use per cell

| Task | Cell | Tools seen (cells using each) |
| :--- | :--- | :--- |
| `t1` | baseline | Bash (3) |
| `t1` | skills | Bash (5), Grep (2), Skill (5) |
| `t2` | baseline | Bash (5) |
| `t2` | scripts-only | Bash (5), Read (5), TaskStop (1), ToolSearch (1) |
| `t2` | skills | Bash (5), Grep (1), Read (1), Skill (5) |
| `t3` | baseline | Bash (5), Edit (1), Read (1), ScheduleWakeup (1), TaskCreate (1), ToolSearch (1), Write (1) |
| `t3` | skills | Bash (1), Skill (5) |
| `t4` | baseline | Bash (4), Write (5) |
| `t4` | skills | Bash (5), Skill (5), Write (5) |
