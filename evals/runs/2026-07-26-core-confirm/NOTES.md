<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Efficiency-axis confirmation — `ros2-core`, 2026-07-26

The [first run](../2026-07-26-core/NOTES.md) evidenced each of six cuts individually
but never measured the reduced body as a whole — the exact gap the redundancy
groups in that same run warned about, just on the cut side instead of the keep
side. This run closes it, and catches a real mistake doing so.

| | |
| :--- | :--- |
| Method | `full` condition only (reads the live `SKILL.md`, so no separate injection step); `naked`/`protocol` reused from the first run — both are context-independent of the skill body |
| Sample | 56 cells at n=8 (all 7 probes) + a targeted top-up to n=15–16 on `tf-lookup` once one check looked off |
| Cost | $0.84 + $0.31 top-up + $0.29 re-verify after the fix = $1.44 |

## Pooled: no regression

| | old-full (50L) | new-full (44L) | naked |
| :--- | ---: | ---: | ---: |
| pooled, 20 checks | 147/157 = 0.936 | 144/159 = 0.906 | 83/154 = 0.539 |

p = 0.405, old vs new-full. The cut body reproduces the effect in aggregate.

## But one check was hiding a mistake

`tf_latest_time` (does the TF lookup ask for the latest transform instead of
timestamping with `get_clock().now()`) moved old 5/6 → new **2/7**, p=0.10 at
n=6–7 — not significant, but the direction and size (83% → 29%) didn't look like
noise. The original ablation had called claim `4:05` (the TF `ExtrapolationException`
symptom row) a clean cut: P(naked)=8/8, Δ=0.00. That measurement was against
*full-minus-this-one-claim* — still 25 other claims in context — not against nothing.

Topped this one probe up to n=16 rather than re-running the whole suite:

| | naked | 44-line full (no row) |
| :--- | ---: | ---: |
| `tf_latest_time` | 16/16 = 1.000 | 6/15 = 0.400 |

p = 0.0017. **With more power, the cut body performs significantly *worse* than
doing nothing at all** on the exact behaviour that row taught. The single-ablation
Δ=0 finding was a false negative from an underpowered comparison, not a correct
verdict — the row is load-bearing, and removing it apparently pushes the model
toward `get_clock().now()` rather than just failing to help.

## Fix and re-verification

Restored the row to `skills/ros2-core/SKILL.md` (44 → 45 lines, 4116 → 4342
chars — still −16% off the original 50/5185). Re-ran `tf-lookup` `full` at n=16
against the restored body:

| | naked | 44-line (broken) | 45-line (restored) |
| :--- | ---: | ---: | ---: |
| `tf_latest_time` | 16/16 | 6/15 | **15/16 = 0.938** |

p = 1.00 vs naked, p = 0.002 vs the broken 44-line version. Fixed.

## What this changes

- `ros2-core` is **45 lines**, not 44. Five lines were genuinely cut, not six.
- The [first run's](../2026-07-26-core/NOTES.md) `4:05` cut entry is wrong; see the
  correction note there.
- The methodological lesson generalizes: a claim's single-ablation Δ=0 is only as
  trustworthy as the power behind it. n=8 detects Δ≥62%; this regression was ~60
  points and still needed n=16 to clear significance against naked. A future cut
  decision this close to the detection floor should get the same top-up before
  shipping, not after.

`ros2-core` moves to ✅ in [`RESULTS.md`](../../RESULTS.md) — both axes now closed:
effect (first run) and efficiency, including the correction this run made.
