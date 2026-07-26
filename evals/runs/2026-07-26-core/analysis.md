# Per-claim analysis — `2026-07-26-core`

558 cells, 347 errored, $7.82 spent

## Baselines per check

| Probe | Check | P(naked) | P(protocol) | P(full) | P(shipped) |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `scan-node` | sensor_qos | 0/8 | 0/8 | 8/8 | 8/8 |
| `scan-node` | bounds_filter | 1/8 | 1/8 | 8/8 | 8/8 |
| `scan-node` | nan_handled | 2/8 | 4/8 | 8/8 | 8/8 |
| `scan-node` | clean_shutdown | 0/8 | 0/8 | 8/8 | 6/8 |
| `scan-node` | shutdown_guard | 0/8 | 0/8 | 8/8 | 8/8 |
| `scan-node` | independent_timer | 8/8 | 8/8 | 8/8 | 7/8 |
| `tf-lookup` | tf_exception | 1/8 | 6/8 | 6/8 | 8/8 |
| `tf-lookup` | tf_latest_time | 8/8 | 8/8 | 5/6 | 7/8 |
| `param-runtime` | yaml_node_key | 4/5 | 5/7 | 5/7 | 8/8 |
| `param-runtime` | param_callback | 8/8 | 8/8 | 8/8 | 8/8 |
| `param-runtime` | param_declare | 8/8 | 8/8 | 8/8 | 8/8 |
| `executor-starve` | multithreaded | 3/8 | 1/8 | 8/8 | 8/8 |
| `executor-starve` | callback_group | 0/8 | 0/8 | 4/8 | 1/8 |
| `ros1-leak` | no_ros1 | 8/8 | 8/8 | 8/8 | 8/8 |
| `cross-host-discovery` | domain_id | 8/8 | 8/8 | 8/8 | 8/8 |
| `cross-host-discovery` | rmw_impl | 2/8 | 1/8 | 8/8 | 8/8 |
| `cross-host-discovery` | multicast | 8/8 | 8/8 | 8/8 | 8/8 |
| `odom-imu-yaw` | odom_msg | 7/7 | 8/8 | 8/8 | 8/8 |
| `odom-imu-yaw` | imu_msg | 7/7 | 7/8 | 8/8 | 8/8 |
| `odom-imu-yaw` | sensor_qos | 0/7 | 0/8 | 7/8 | 6/8 |

## Claim verdicts

Δ is P(full) − P(ablate) on the check the claim is supposed to drive. `p` is Fisher exact, two-sided, full vs ablate.

| Claim | Check | P(naked) | P(full) | P(ablate) | Δ | p | Verdict |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `4symptom-root-cause-action:02` | rmw_impl | 0.25 | 1.00 | 0.00 | +1.00 | 0.000 | **KEEP** |
| `4symptom-root-cause-action:06` | multithreaded | 0.38 | 1.00 | 0.38 | +0.62 | 0.026 | **KEEP** |
| `4symptom-root-cause-action:08` | clean_shutdown | 0.00 | 1.00 | 0.00 | +1.00 | 0.000 | **KEEP** |
| `5strict-coding-rules:03` | sensor_qos | 0.00 | 1.00 | 0.38 | +0.62 | 0.026 | **KEEP** |
| `5strict-coding-rules:03` | sensor_qos | 0.00 | 0.88 | 0.00 | +0.88 | 0.001 | **KEEP** |
| `2symbols-to-verify-there-never-write-the:01` | tf_exception | 0.12 | 0.75 | 1.00 | -0.25 | 0.467 | **INERT** |
| `2symbols-to-verify-there-never-write-the:04` | sensor_qos | 0.00 | 1.00 | 1.00 | +0.00 | 1.000 | **INERT** |
| `2symbols-to-verify-there-never-write-the:04` | sensor_qos | 0.00 | 0.88 | 0.83 | +0.04 | 1.000 | **INERT** |
| `4symptom-root-cause-action:01` | sensor_qos | 0.00 | 1.00 | 1.00 | +0.00 | 1.000 | **INERT** |
| `4symptom-root-cause-action:01` | sensor_qos | 0.00 | 0.88 | 0.88 | +0.00 | 1.000 | **INERT** |
| `4symptom-root-cause-action:06` | callback_group | 0.00 | 0.50 | 0.00 | +0.50 | 0.077 | **INERT** |
| `4symptom-root-cause-action:07` | bounds_filter | 0.12 | 1.00 | 1.00 | +0.00 | 1.000 | **INERT** |
| `4symptom-root-cause-action:07` | nan_handled | 0.25 | 1.00 | 1.00 | +0.00 | 1.000 | **INERT** |
| `4symptom-root-cause-action:08` | shutdown_guard | 0.00 | 1.00 | 0.88 | +0.12 | 1.000 | **INERT** |
| `5strict-coding-rules:02` | tf_exception | 0.12 | 0.75 | 0.62 | +0.12 | 1.000 | **INERT** |
| `5strict-coding-rules:04` | bounds_filter | 0.12 | 1.00 | 1.00 | +0.00 | 1.000 | **INERT** |
| `5strict-coding-rules:04` | nan_handled | 0.25 | 1.00 | 1.00 | +0.00 | 1.000 | **INERT** |
| `5strict-coding-rules:05` | clean_shutdown | 0.00 | 1.00 | 0.75 | +0.25 | 0.467 | **INERT** |
| `5strict-coding-rules:05` | shutdown_guard | 0.00 | 1.00 | 1.00 | +0.00 | 1.000 | **INERT** |
| `2symbols-to-verify-there-never-write-the:02` | odom_msg | 1.00 | 1.00 | 1.00 | +0.00 | 1.000 | **CUT** |
| `2symbols-to-verify-there-never-write-the:02` | imu_msg | 1.00 | 1.00 | 1.00 | +0.00 | 1.000 | **CUT** |
| `2symbols-to-verify-there-never-write-the:03` | param_declare | 1.00 | 1.00 | 1.00 | +0.00 | 1.000 | **CUT** |
| `4symptom-root-cause-action:02` | domain_id | 1.00 | 1.00 | 1.00 | +0.00 | 1.000 | **CUT** |
| `4symptom-root-cause-action:02` | multicast | 1.00 | 1.00 | 0.88 | +0.12 | 1.000 | **CUT** |
| `4symptom-root-cause-action:03` | yaml_node_key | 0.80 | 0.71 | 0.88 | -0.16 | 0.569 | **CUT** |
| `4symptom-root-cause-action:04` | param_callback | 1.00 | 1.00 | 1.00 | +0.00 | 1.000 | **CUT** |
| `4symptom-root-cause-action:05` | tf_latest_time | 1.00 | 0.83 | 0.88 | -0.04 | 1.000 | **CUT** |
| `5strict-coding-rules:01` | no_ros1 | 1.00 | 1.00 | 1.00 | +0.00 | 1.000 | **CUT** |

## Redundancy groups — removing the whole group

Every member of these groups measured Δ≈0 alone. That is the signature of redundancy, not of uselessness: cutting them all is only safe if the joint ablation also shows no effect.

| Group | Check | P(full) | P(drop all) | Δ | p | Reading |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| 5strict-coding-rules:03, 4symptom-root-cause-ac:01, 2symbols-to-verify-the:04 | sensor_qos | 8/8 | 0/8 | +1.00 | 0.000 | **the group is load-bearing** — keep at least one member |
| 5strict-coding-rules:04, 4symptom-root-cause-ac:07 | bounds_filter | 8/8 | 1/8 | +0.88 | 0.001 | **the group is load-bearing** — keep at least one member |
| 5strict-coding-rules:04, 4symptom-root-cause-ac:07 | nan_handled | 8/8 | 5/8 | +0.38 | 0.200 | no joint effect — the whole group is a cut candidate |
| 5strict-coding-rules:05, 4symptom-root-cause-ac:08 | clean_shutdown | 8/8 | 0/8 | +1.00 | 0.000 | **the group is load-bearing** — keep at least one member |
| 5strict-coding-rules:05, 4symptom-root-cause-ac:08 | shutdown_guard | 8/8 | 0/8 | +1.00 | 0.000 | **the group is load-bearing** — keep at least one member |

## Interference — ablations that moved a check they do not own

A claim's removal should not disturb an unrelated check. Where it does, 'the effect of line X' is not well defined.

_none — every ablation left the checks it does not own alone._

## Grading coverage

2280/2290 check results were gradable (10 ungradable, never counted as failures).
