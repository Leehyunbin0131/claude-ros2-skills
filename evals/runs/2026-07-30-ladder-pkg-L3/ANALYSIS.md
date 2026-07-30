# v2 round — `2026-07-30-ladder-pkg-L3`

10 cells graded

## Pass rate per check

| Task | Check | baseline |
| :--- | :--- | ---: |
| `t7` | t7_builds | 10/10 |
| `t7` | t7_component_loads | 10/10 |
| `t7` | t7_component_registered | 10/10 |
| `t7` | t7_first_build_clean | 8/10 |
| `t7` | t7_msg_dep_resolves | 10/10 |
| `t7` | t7_tests_pass | 10/10 |
| `t7` | t7_tests_ran | 10/10 |

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
| `t7` | baseline | Bash (10), Edit (9), Read (5), TaskCreate (7), TaskStop (2), TaskUpdate (7), ToolSearch (8), Write (10) |
