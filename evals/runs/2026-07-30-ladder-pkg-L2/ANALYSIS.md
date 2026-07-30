# v2 round — `2026-07-30-ladder-pkg-L2`

10 cells graded

## Pass rate per check

| Task | Check | baseline |
| :--- | :--- | ---: |
| `t6` | t6_builds | 10/10 |
| `t6` | t6_composed_launch | 10/10 |
| `t6` | t6_cpp_run_works | 10/10 |
| `t6` | t6_first_build_clean | 10/10 |
| `t6` | t6_py_run_works | 10/10 |
| `t6` | t6_service_available | 10/10 |
| `t6` | t6_srv_resolves | 10/10 |

## Tests

Comparisons and alpha fixed in TASKS.md before the round. `q` is Benjamini-Hochberg across every test here.

| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |

## Control gate

t4 was not run in this round. The gate was cleared in the round that established the harness; a narrow follow-up inherits that rather than re-paying for it.


## Isolation

No cell reached the repository. Isolation held.

## Tool use per cell

| Task | Cell | Tools seen (cells using each) |
| :--- | :--- | :--- |
| `t6` | baseline | Bash (10), Edit (9), Read (6), TaskCreate (6), TaskUpdate (6), ToolSearch (6), Write (10) |
