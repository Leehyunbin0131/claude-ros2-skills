# Nav2 tuning baselines

Load this when behavior is wrong but nothing is crashing — the robot moves, just badly.

Baseline = the shipped defaults in `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml`.
Always diff against that file, not against memory. Change **one** value at a time.

## AMCL

| Param | Baseline | Symptom -> direction |
| :--- | :--- | :--- |
| `alpha1`..`alpha4` (odom noise) | 0.2 each | Pose lags/overtrusts bad odom -> raise toward 0.4. Good wheel odom but pose jitters -> lower toward 0.1. Fix odometry first (`check_odom_direction.py`) — alphas cannot repair inverted/scaled odom. |
| `min_particles` / `max_particles` | 500 / 2000 | Kidnapped-robot recovery poor or large map -> raise max to 5000 (CPU cost is linear). Small static map -> defaults are fine. |
| `update_min_d` / `update_min_a` | 0.25 m / 0.2 rad | Pose updates feel laggy -> lower both; CPU-bound -> raise. |
| `laser_max_beams` | 60 | Localization weak in feature-sparse corridors -> raise to 100-180; CPU-bound -> keep 60. |

## Costmaps

| Param | Baseline | Symptom -> direction |
| :--- | :--- | :--- |
| `resolution` | 0.05 m | Indoor default. Narrow gaps misjudged -> 0.025 (4x memory/CPU). Outdoor/large -> 0.1. |
| `inflation_radius` | 0.55 m | Must exceed robot inscribed radius + margin. Robot hugs obstacles -> raise; can't pass doorways -> lower toward inscribed radius + ~0.1 m. |
| `cost_scaling_factor` | 3.0 | Higher = cost decays faster = paths allowed closer to walls. Too timid in corridors -> raise toward 10; clipping corners -> lower. |
| local costmap size | 3 x 3 m | Faster robots need to see further: >= 2 x (max speed x controller horizon). |

## Controller (MPPI)

Tune ONE critic weight at a time from the shipped defaults:
- Reverses unnecessarily -> raise `PreferForwardCritic.cost_weight`
- Refuses to deviate around obstacles -> lower `PathAlignCritic`

Re-baseline from the defaults file after any Nav2 upgrade — critic defaults shift between releases.

## SLAM (slam_toolbox)

- `resolution: 0.05`
- Clamp `max_laser_range` to the LiDAR's *reliable* range (usually ~80% of datasheet)
- Loop closure misfires in repetitive corridors -> raise `loop_match_minimum_response_fine`
