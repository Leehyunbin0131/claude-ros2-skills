# v2 round — `2026-07-30-ladder-gz-L2`

10 cells graded

## Pass rate per check

| Task | Check | baseline |
| :--- | :--- | ---: |
| `g2` | g2_clock_in_ros | 10/10 |
| `g2` | g2_ros_cmd_moves | 10/10 |
| `g2` | g2_scan_360 | 10/10 |
| `g2` | g2_scan_in_ros | 10/10 |

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
| `g2` | baseline | Bash (10), Edit (10), Read (5), ScheduleWakeup (1), TaskCreate (4), TaskUpdate (4), ToolSearch (5), WebFetch (1), Write (10) |
