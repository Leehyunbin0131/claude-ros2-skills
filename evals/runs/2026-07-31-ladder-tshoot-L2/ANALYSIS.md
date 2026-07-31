# v2 round — `2026-07-31-ladder-tshoot-L2`

10 cells graded

## Pass rate per check

| Task | Check | baseline |
| :--- | :--- | ---: |
| `tr2` | tr2_exits_clean | 10/10 |
| `tr2` | tr2_heartbeat_steady | 10/10 |
| `tr2` | tr2_logs_5 | 10/10 |
| `tr2` | tr2_no_hang | 10/10 |

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
| `tr2` | baseline | Bash (10), Edit (1), Read (1), TaskStop (1), ToolSearch (1), Write (10) |
