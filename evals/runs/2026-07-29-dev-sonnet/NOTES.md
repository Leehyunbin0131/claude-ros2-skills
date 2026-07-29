<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-dev` measured on sonnet — 2026-07-29

Largest claim count in the repo (80) and the only skill whose strongest signal
is **behavioural** rather than factual. File unchanged at 58 lines.

| | |
| :--- | :--- |
| Method | pre-measurement, n=4 sweep, errored batch re-run, baseline topped up to n=10 |
| Probes | 5 new, 13 checks. Covers **26/26 SKILL.md claims**; the 54 claims in `references/symbols.md` and `references/tuning.md` are reached only where the body names them |
| Spend | $12.88 |
| Outcome | `naked` 63/105 = 0.600 vs `full` 97/110 = **0.882**. No claim cleared q<0.05 |

## `rtabmap_ros` turned out not to be needed

The skill was blocked on installing `rtabmap_ros`. Reading it properly, RTAB-Map
appears once, as one of three options in "who publishes `map -> odom`". The
measurable substance is Nav2 and SLAM Toolbox, both already installed. The
install was skipped and nothing was lost.

## The anchor: a real index of what pluginlib registers

Per the anchoring rule, `_nav2_registered_plugins()` scrapes every
plugin-description XML under `/opt/ros/jazzy/share` and collects **233 class
names**. A plugin string is either in that set or it does not exist on this
machine. Verified discriminating before use: `nav2_mppi_controller::MPPIController`
is present, and the skill's own counter-example
`mppi_controller::MPPIController` is not.

**And it found nothing wrong.** `plugins_real` is **9/9 naked, 8/8 full** —
every namespaced string sonnet emits unaided is a class that really is
registered. Section 3 opens with *"the single most common startup-killing error
is dropping the package prefix"*, and on this model that error does not occur.
That is worth stating plainly: the section is aimed at a failure mode the target
model no longer has.

## The signal is behavioural, not factual

Every large gap in this run is about **what the agent does before writing**, not
about what it knows:

| Check | naked | full |
| :--- | ---: | ---: |
| asks for footprint / inscribed radius | 1/7 | 5/7 |
| asks which drive type | 1/7 | 5/7 |
| asks who will publish `map -> odom` | 0/7 | 5/7 |
| sanity-checks odometry before tuning AMCL | 1/7 | 7/7 |
| cites the shipped `nav2_params.yaml` as the source | 0/9 | 5/10 |

Unaided, asked to "set up Nav2 and tune it", sonnet writes a full parameter file
immediately. With the skill it asks first — five times in seven. That is the
`ros2-dev` §1 gate working, and it is the clearest measurement of a *disposition*
rather than a *fact* anywhere in this project.

It is also why `full` is 0.882 rather than 1.000. These checks are not satisfied
by repeating a phrase; the agent either asked or it did not, and with the file
in context it still fails to ask about a third of the time.

## No claim cleared q<0.05

Six came back UNDERPOWERED, the closest being the lifecycle-state row
(`naked` 0.75, `full` 1.00, `ablate` 0.25, q=0.198). Nothing was topped up
further to chase it — the same discipline applied on `gazebo-sim`.

Five claims measured CUT at `naked = full = ablate`, all facts the model has
cold: `transient_local` on the map subscription, the `PreferForwardCritic`
weight, not reaching for `move_base`, and both plugin-string claims.

## No rewrite was attempted

The CUT set is real, but it is the same shape that produced three consecutive
rejected rewrites on `ros2-troubleshooting`, and this file's remaining value is
concentrated in the §1 gate and the §2 loop — prose whose whole function is to
make the agent stop and ask. Compressing prose whose job is behavioural is
exactly the case where the `ros2-troubleshooting` failures showed the causes get
dropped and the instruction survives. Not attempted.

## Method notes

**112 of 192 cells came back `no-model-response` mid-sweep**, wiping two probes.
Errored rows were filtered out of `cells.jsonl` and re-run at lower concurrency,
which completed clean. Same handling as the `ros2-troubleshooting` run; the
runner's resume logic skips present-but-errored rows, so they have to be removed
before it will retry them.

**One check was the wrong check.** `asks_map_odom` reused
`_d_one_map_odom`, which demands the "exactly one publisher" phrasing — correct
for the diagnosis probe, wrong for the establish-first probe, where the right
behaviour is simply to *ask* which node will publish it. Answers that asked the
question properly scored 0. Split into a dedicated check and repaired with
`runner.py regrade`: 13 of 803 results changed, no re-run, no spend.
