# v2 round — `2026-07-30-v2-t5-package`

20 cells graded

## Pass rate per check

| Task | Check | baseline | skills |
| :--- | :--- | ---: | ---: |
| `t5` | t5_builds | 10/10 | 10/10 |
| `t5` | t5_first_build_clean | 10/10 | 10/10 |
| `t5` | t5_interface_resolves | 10/10 | 10/10 |
| `t5` | t5_launch_resolves | 10/10 | 10/10 |
| `t5` | t5_params_installed | 10/10 | 10/10 |
| `t5` | t5_run_works | 10/10 | 10/10 |

## Tests

Comparisons and alpha fixed in TASKS.md before the round. `q` is Benjamini-Hochberg across every test here.

| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `t5` | t5_builds | skills vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |
| `t5` | t5_first_build_clean | skills vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |
| `t5` | t5_interface_resolves | skills vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |
| `t5` | t5_launch_resolves | skills vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |
| `t5` | t5_params_installed | skills vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |
| `t5` | t5_run_works | skills vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |

## Control gate

t4 was not run in this round. The gate was cleared in the round that established the harness; a narrow follow-up inherits that rather than re-paying for it.


## Isolation

No cell reached the repository. Isolation held.

## Tool use per cell

| Task | Cell | Tools seen (cells using each) |
| :--- | :--- | :--- |
| `t5` | baseline | Bash (10), Edit (6), Read (4), TaskCreate (3), TaskUpdate (3), ToolSearch (3), Write (10) |
| `t5` | skills | Bash (10), Edit (8), Read (7), Skill (10), TaskCreate (2), TaskUpdate (2), ToolSearch (2), Write (10) |
