# v2 round — `2026-07-31-ladder-tshoot-L3`

10 cells graded

## Pass rate per check

| Task | Check | baseline |
| :--- | :--- | ---: |
| `tr3` | tr3_batch_under_3s | 10/10 |
| `tr3` | tr3_exits_clean | 10/10 |
| `tr3` | tr3_logs_5 | 10/10 |
| `tr3` | tr3_total_line | 10/10 |

## Tests

Comparisons and alpha fixed in TASKS.md before the round. `q` is Benjamini-Hochberg across every test here.

| Task | Check | Comparison | higher | lower | Δ | p | q | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |

## Control gate

t4 was not run in this round. The gate was cleared in the round that established the harness; a narrow follow-up inherits that rather than re-paying for it.


## Isolation

**5 of 10 cells reached the repository** — these have seen the eval design and/or a scenario source, which names the planted answer. Reported, not averaged away:

- `r1/tr3-baseline_result.jsonl` — 2 tool call(s)
- `r2/tr3-baseline_result.jsonl` — 1 tool call(s)
- `r4/tr3-baseline_result.jsonl` — 2 tool call(s)
- `r7/tr3-baseline_result.jsonl` — 2 tool call(s)
- `r9/tr3-baseline_result.jsonl` — 1 tool call(s)

Run through `isolate_cell.sh` to close this.

## Tool use per cell

| Task | Cell | Tools seen (cells using each) |
| :--- | :--- | :--- |
| `tr3` | baseline | Bash (10), Edit (2), Read (2), Write (10) |
