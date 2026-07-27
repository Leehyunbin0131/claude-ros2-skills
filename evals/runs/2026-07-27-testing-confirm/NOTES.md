<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Efficiency-axis confirmation — `ros2-testing`, 2026-07-27

Closes the gap the [ablation run](../2026-07-27-testing/NOTES.md) left open: two
claims (`4symptom:03`, `4symptom:04`) were candidates for cutting, but
single-ablating each one *individually* — the only measurement available before
this run — was messier than a clean Δ=0.00: one showed its own check landing on
the naked baseline (a real-looking effect, just short of p<0.05), and both
dragged down an unrelated check in the same probe, an artifact of the
odd five-of-six-row table that single ablation produces and no shipped version
would ever contain. This run measures the state that actually matters — both
rows gone, the real 76-line body — instead of trusting what the single-ablation
table implied about it. Separate run directory because `full` reads the live
`SKILL.md`, and the ablation run's `cells.jsonl` already had `full` cells
recorded against the pre-cut 78-line version — same-directory resume would have
skipped them as "already done."

| | |
| :--- | :--- |
| Method | `full`/`naked` only, all 4 probes, against the post-cut `SKILL.md` |
| Sample | n=8, 64 cells, $0.58 |

## Result: no regression, on any check

| | old-full (78L, from the ablation run) | new-full (76L) | naked |
| :--- | ---: | ---: | ---: |
| pooled, 13 checks | 124/124 = 1.000 | 104/104 = 1.000 | 49/101 = 0.485 |

p = 1.00, old vs new. Per-check breakdown of the new body — every one of the 13
checks, including the two the cut rows used to own, at ceiling:

`hang_cause` 8/8, `ci_cause` 8/8, and all 11 other checks 8/8.

The single-ablation artifact does not survive into the real, symmetric,
six-minus-two body: `qos_test_cause` and `simtime_cause` — the two checks that
looked disturbed when only one of the two rows was removed — are both 8/8 here,
matching every other check. Whatever made the asymmetric intermediate table
misbehave is specific to that never-shipped state, not to the content that
`SKILL.md` actually ships.

`ros2-testing` closes both axes in [`RESULTS.md`](../../RESULTS.md) on the
strength of this run plus the [ablation run](../2026-07-27-testing/NOTES.md).
