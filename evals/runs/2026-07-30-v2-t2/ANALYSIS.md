# v2 round — `2026-07-30-v2-t2`

20 cells graded

## Pass rate per check

| Task | Check | baseline | scripts-only | skills |
| :--- | :--- | ---: | ---: | ---: |
| `t2` | t2_evidence_not_guess | 9/10 | 10/10 | — |
| `t2` | t2_exit_code_read | 0/10 | 10/10 | — |
| `t2` | t2_no_ros2_run | 1/1 | 10/10 | — |
| `t2` | t2_ran_script | 1/10 | 10/10 | — |

## Tests

Comparisons and alpha fixed in TASKS.md before the round. `q` is Benjamini-Hochberg across every test here.

| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `t2` | t2_exit_code_read | scripts-only vs baseline | 10/10 | 0/10 | +1.00 | 0.000 | 0.000 | **SIGNIFICANT** |
| `t2` | t2_ran_script | scripts-only vs baseline | 10/10 | 1/10 | +0.90 | 0.000 | 0.000 | **SIGNIFICANT** |
| `t2` | t2_evidence_not_guess | scripts-only vs baseline | 10/10 | 9/10 | +0.10 | 1.000 | 1.000 | null |
| `t2` | t2_no_ros2_run | scripts-only vs baseline | 10/10 | 1/1 | +0.00 | 1.000 | 1.000 | null |

## Control gate

t4 was not run in this round. The gate was cleared in the round that established the harness; a narrow follow-up inherits that rather than re-paying for it.


## Tool use per cell

| Task | Cell | Tools seen (cells using each) |
| :--- | :--- | :--- |
| `t2` | baseline | Bash (10), Read (2) |
| `t2` | scripts-only | Bash (10), Read (10) |
