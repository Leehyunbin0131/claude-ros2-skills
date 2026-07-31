<!-- Executor ladder rung L3 — top of a fixed-length ladder for ONE sub-topic of
     ros2-troubleshooting (§3C). Rules in ../../LADDER.md. -->

# Executor ladder L3 — 40/40, sub-topic exhausted

10 cells, `tr3`, **`baseline` only**, n=10. Five service calls issued
concurrently from one callback, all awaited, batch under 3 s.

| Check | baseline |
| :--- | ---: |
| `tr3_logs_5` | 10/10 |
| `tr3_exits_clean` | 10/10 |
| `tr3_total_line` | 10/10 |
| `tr3_batch_under_3s` | 10/10 |

**Every cell landed at 2.00 s** — 2.001 to 2.007 — against a hand-written
concurrent reference at 2.017 s and a serialised one at 5.03 s. The scenario
server runs 4 threads, so 2.0 s *is* the floor for five 1 s calls. Ten out of
ten hit the floor exactly. Not one cell serialised.

## The sub-topic ladder, complete

| Rung | Mechanisms added | Result |
| :--- | :--- | ---: |
| L1 | service called from a timer callback | 30/30 |
| L2 | + call moves into a subscription callback, 10 Hz heartbeat must hold | 40/40 |
| L3 | + five calls concurrent, batch under 3 s | 40/40 |

**110 of 110 cell-checks unaided.** At L2, eight of ten cells held a max
heartbeat gap of exactly **0.1 s** — a theoretically perfect 10 Hz while 1 s
calls were in flight. That is correct callback-group use, produced with no
skill file present.

## Verdict: §3C is cut

Rule 5. What was removed from `ros2-troubleshooting`:

- §3.C "Executor Deadlocks & Async Callback Freezes" (symptom / root cause / fix)
- the §5 anti-pattern row for blocking `spin_until_future_complete`
- the decision-tree branch "Node freezes on async call / service?"
- "executor deadlocks" from the frontmatter description

119 → 110 lines. **The rest of the skill is untouched** — that is the point of
laddering a sub-topic rather than a whole file. REP 103/105 frames, lifecycle
states, DDS domain conflicts and the bundled scripts each still need their own
ladder.

## §3C was also factually wrong, which is not why it was cut

Validating the graders showed the file describes the wrong failure:

| Code | What SKILL.md said | What Jazzy does |
| :--- | :--- | :--- |
| nested spin inside a callback | "hangs the entire node" | **`RuntimeError("Executor is already spinning")` in ~1 s.** Loud, immediate |
| `spin_until_future_complete(node, fut)` with no executor arg, node on a MultiThreadedExecutor | not mentioned | **silent hang forever**, no output at all |
| timer + subscription sharing rclpy's default MutuallyExclusive group | not mentioned | **full deadlock** — the response needs the group the blocked callback holds |

So §3C warned about the one case that is now loud and omitted both silent ones.
Recorded because it is true, not as justification: the cut rests on 110/110, and
a correct version of the paragraph would have been cut on the same number.

## A round was lost to the harness, again, to a lesson already learned

The first L3 attempt ran one cell and then sat dead for **4 hours 48 minutes**.
The cell had finished; the checker was blocked on `wait $SRV`. Teardown was
`kill $SRV` (SIGTERM) then `wait $SRV`, and rclpy inside `executor.spin()` does
not reliably act on SIGTERM — so the child stayed alive and `wait` never
returned. `kill_all`, which sends `-9`, ran only after the wait and never got
the chance.

**`gz sim` taught exactly this in the gazebo rounds** — a stray survived `pkill`
for 23 minutes and died only to `-9` — and it was written up at the time. The
lesson was not carried across to the Python scenario servers. Fixed in all three
executor checkers: `kill_all` first, `wait` only to reap.

It was caught by the user asking whether the round was still running, after two
progress reports from me that said it was.
