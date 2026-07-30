# v2 round — `2026-07-30-v2-t1-claudemd`

20 cells graded

## Pass rate per check

| Task | Check | baseline | claude-md-only |
| :--- | :--- | ---: | ---: |
| `t1` | t1_correct_type | 10/10 | 10/10 |
| `t1` | t1_no_invented_param | 4/10 | 6/10 |
| `t1` | t1_searched_or_read | 2/10 | 10/10 |

## Tests

Comparisons and alpha fixed in TASKS.md before the round. `q` is Benjamini-Hochberg across every test here.

| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `t1` | t1_searched_or_read | claude-md-only vs baseline | 10/10 | 2/10 | +0.80 | 0.001 | 0.002 | **SIGNIFICANT** |
| `t1` | t1_no_invented_param | claude-md-only vs baseline | 6/10 | 4/10 | +0.20 | 0.656 | 0.984 | null |
| `t1` | t1_correct_type | claude-md-only vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |

## Control gate

t4 was not run in this round. The gate was cleared in the round that established the harness; a narrow follow-up inherits that rather than re-paying for it.


## Isolation

No cell reached the repository. Isolation held.

## Tool use per cell

| Task | Cell | Tools seen (cells using each) |
| :--- | :--- | :--- |
| `t1` | baseline | Bash (9), ToolSearch (1), WebFetch (1) |
| `t1` | claude-md-only | Bash (10), Glob (2), Grep (2), Read (1), ToolSearch (4) |
