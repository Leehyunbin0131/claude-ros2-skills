# v2 round — `2026-07-31-ladder-gz-L3`

10 cells graded

## Pass rate per check

| Task | Check | baseline |
| :--- | :--- | ---: |
| `g3` | g3_frame_id_is_link | 9/10 |
| `g3` | g3_imu_in_ros | 9/10 |
| `g3` | g3_sim_time | 10/10 |

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
| `g3` | baseline | Bash (10), Edit (4), Grep (1), Read (5), TaskOutput (1), ToolSearch (5), WebFetch (2), WebSearch (4), Write (10) |
