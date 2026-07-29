# v2 round — `2026-07-30-v2-t1`

20 cells graded

## Pass rate per check

| Task | Check | baseline | scripts-only | skills |
| :--- | :--- | ---: | ---: | ---: |
| `t1` | t1_correct_type | 10/10 | — | 10/10 |
| `t1` | t1_no_invented_param | 3/10 | — | 6/10 |
| `t1` | t1_searched_or_read | 3/10 | — | 10/10 |

## Tests

Comparisons and alpha fixed in TASKS.md before the round. `q` is Benjamini-Hochberg across every test here.

| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `t1` | t1_searched_or_read | skills vs baseline | 10/10 | 3/10 | +0.70 | 0.003 | 0.009 | **SIGNIFICANT** |
| `t1` | t1_no_invented_param | skills vs baseline | 6/10 | 3/10 | +0.30 | 0.370 | 0.555 | UNDERPOWERED |
| `t1` | t1_correct_type | skills vs baseline | 10/10 | 10/10 | +0.00 | 1.000 | 1.000 | null |

## Control gate

t4 was not run in this round. The gate was cleared in the round that established the harness; a narrow follow-up inherits that rather than re-paying for it.


## Isolation

No cell reached the repository. Isolation held.

## Tool use per cell

| Task | Cell | Tools seen (cells using each) |
| :--- | :--- | :--- |
| `t1` | baseline | Bash (8), Glob (1), ToolSearch (3), WebFetch (3), WebSearch (3) |
| `t1` | skills | Bash (10), Grep (2), Read (1), Skill (10), TaskStop (1), ToolSearch (1) |
