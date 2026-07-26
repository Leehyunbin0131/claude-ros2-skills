<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Per-line ablation — `ros2-core`, 2026-07-26

The first run of the efficiency axis: not "do the skills help?" but "does *this
line* help, and is the body the smallest one that produces the effect?"

| | |
| :--- | :--- |
| Method | every claim in the body ablated individually, plus joint ablation of the three redundancy groups; content injected via `--append-system-prompt` so routing is not mixed in; `--tools ""` so the measurement is what the model *writes*, not what it looks up |
| Probes | 7, covering all 26 claims; 20 mechanical checks; prompts never name the rule they test |
| Sample | n=8 per cell, 558 cells, $7.82. Fisher exact two-sided, α=0.05 |
| Grading | 2280/2290 check results gradable; ungradable never counted as a failure |

## Headline

| Comparison | Pass rate | p |
| :--- | :--- | ---: |
| **skill body vs nothing** | 0.54 → **0.94** | **<0.0001** |
| `CLAUDE.md` alone vs nothing | 0.54 → 0.56 | 0.73 |
| body + `CLAUDE.md` vs body alone | 0.94 → 0.92 | 0.67 |

1. **The body works, and the effect is large.** Pooled across all 20 checks.
2. **The always-loaded protocol changes nothing about generated code.** 28 lines
   paid on every session, p=0.73 against no context at all. Its value, if any, is
   not in what the agent writes.
3. **No systematic contamination.** Individual checks drop (`callback_group` 4/8 →
   1/8 when `CLAUDE.md` is added on top of the body), but pooled it is noise. The
   hypothesis that skill content overrides better internal knowledge is **not
   supported** at this sample size.

## Single ablation cannot judge a redundant line

Three behaviours are stated in more than one place. Removing any single member
measured Δ≈0 — which reads as "useless" and is not:

| Group | Each alone | Whole group removed |
| :--- | :--- | :--- |
| bounds: `5:04` rule + `4:07` row | **both Δ=0** | 8/8 → 1/8, Δ=+0.88, p=0.001 |
| QoS: `5:03` + `4:01` + `2:04` | only `5:03` moved (+0.62) | 8/8 → 0/8, Δ=+1.00, p=0.0002 |
| shutdown: `5:05` + `4:08` | only `4:08` moved (+1.00) | 8/8 → 0/8, Δ=+1.00, p=0.0002 |

Cutting the bounds pair on single-ablation evidence would have deleted the rule
that took Task 1 from `0.020 m` to the correct `0.450 m`.

## Cut — model already does it unaided, Δ exactly 0

| Claim | Check | P(naked) | Δ |
| :--- | :--- | ---: | ---: |
| `2:02` odometry/IMU message names | `odom_msg`, `imu_msg` | 7/7, 7/7 | 0.00 |
| `2:03` parameter API names | `param_declare` | 8/8 | 0.00 |
| `4:04` `set_parameters` row | `param_callback` | 8/8 | 0.00 |
| `4:05` TF extrapolation row | `tf_latest_time` | 8/8 | 0.00 |
| `5:01` "never mix ROS 1 syntax" | `no_ros1` | 8/8 | 0.00 |
| `4:03` params-YAML row | `yaml_node_key` | 4/5 | **−0.16** |

Six lines removed: 50 → 44 lines, 5185 → 4116 characters (−21%).

## Keep — load-bearing, significant

| Claim | Check | P(naked) | Δ | p |
| :--- | :--- | ---: | ---: | ---: |
| `4:08` shutdown row | `clean_shutdown` | 0/8 | +1.00 | 0.0002 |
| `4:02` cross-host row | `rmw_impl` | 2/8 | +1.00 | 0.0002 |
| `5:03` QoS rule | `sensor_qos` (scan) | 0/8 | +0.62 | 0.026 |
| `5:03` QoS rule | `sensor_qos` (odom) | 0/7 | +0.88 | 0.001 |
| `4:06` executor row | `multithreaded` | 3/8 | +0.62 | 0.026 |

`5:03` replicates on two independent probes — the only claim measured twice here.

Note `4:02`: the row is load-bearing **only** for naming the RMW implementation
(2/8 → 8/8). Its other two contents, `ROS_DOMAIN_ID` and multicast, are at 8/8
unaided. A row can be worth keeping for one clause out of three.

## What this run does NOT establish

- **The reduced body is unconfirmed.** The cuts are individually evidenced, but
  the 44-line body has not been re-measured as a whole. Until it is, the
  efficiency axis is not closed and `ros2-core` stays 🔄.
- **Symptom rows were graded on code-writing probes.** The symptom table exists
  for diagnosis; only `cross-host-discovery` is a diagnosis probe. Cutting a
  symptom row on code-probe evidence measures the wrong thing, so `4:03`/`4:04`/
  `4:05` were cut on the strength of P(naked)=1.00, not on Δ alone.
- **n=8 detects Δ≥62% only.** Anything smaller is invisible here. `5:05`
  (Δ=+0.25, p=0.47) was left in place for that reason rather than cut.
- **One model, one temperature, tools off.** Whether these verdicts hold with
  tools enabled — where a doc pointer can actually be followed — is untested, and
  that is exactly where the navigational lines would earn their place.

## Harness defects this run exposed

1. **Usage-limit responses were being graded.** 438 cells of the first sweep
   returned `"You've hit your session limit"` as their answer text, and predicates
   scored that `False` — indistinguishable from "the model got it wrong". Fixed:
   a cell with `is_error` or zero cost is recorded as an error and re-run, never
   graded. The fix proved itself when the monthly limit hit mid-run later: 347
   cells were quarantined and retried with no contamination.
2. **No global spend cap.** `--max-budget-usd` is per cell, so a sweep could
   overrun the account it bills. Added `--max-total-usd`, which stops dispatch
   once the running total is reached.
