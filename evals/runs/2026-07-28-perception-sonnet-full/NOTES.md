<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-perception` verified on sonnet — 2026-07-28

The smallest skill measured (43 lines, 11 claims) and the one where the ceiling
problem was expected to be worst. It was — most of the body is at ceiling — but
the run also produced **the two strongest KEEP verdicts in the project**, and
they are the only two claims where q cleared the significance bar at all.

| | |
| :--- | :--- |
| Method | n=4 sweep, three targeted top-ups to n=10, an authored `variant:` rewrite, then a confirmation run on the shipped body |
| Probes | 6, covering all 11 claims. `perc-cv-bridge-cpp` and `perc-pcl-cpp` are not regex-graded: `_compiles_cpp()` runs `g++ -fsyntax-only` over the answer's C++ against every per-package include dir under `/opt/ros/jazzy` |
| Spend | 192-cell sweep $4.69, top-ups $0.61, variant $2.52, confirmation $2.23 — $10.05 total |
| Outcome | 43 -> 38 lines, `naked` 0.849 vs `full` 0.987 on the shipped body |

## Axis 1

Pooled over all 19 checks on the shipped 38-line body at n=8:
**`naked` 118/139 = 0.849, `full` 150/152 = 0.987.**

The prediction going in was that this skill would be the hardest to measure,
because a cross-check on the old body had `naked` at 0.908 — only 9 points of
room. That held: 10 of 16 claim-check pairs came back
`naked = full = ablate = 1.00`, and no amount of extra sampling would move them.

## Axis 2: almost everything at ceiling, and two claims that are not

Two claims cleared the corrected significance bar. Nothing else in this project
has.

| Claim | Check | naked | full | ablate | q |
| :--- | :--- | ---: | ---: | ---: | ---: |
| K-vs-P symptom row | k_vs_p_cause | 0.90 | 1.00 | **0.00** | 0.000 |
| docs-URL convention | docs_url | 0.25 | 1.00 | 0.30 | 0.025 |

**The K-vs-P row is the strongest result measured here, and its shape matters
more than its size.** Removing it does not return the model to its unaided
answer — unaided it is already right 9 times out of 10. Removing it drives the
check to **zero**. The ablated answers explain the symptom as box-coordinate
scaling ("boxes are in `vision_msgs` normalized/pixel coordinates from one image
resolution but drawn on a differently-scaled image") instead of as a camera
matrix mix-up. With the rest of the table present but that row gone, the model
reaches for a neighbouring row's framing and produces a confident wrong answer.
This is the "inert against nothing, load-bearing against its own table" pattern
in its sharpest form yet, and it is the second time a cut judged against
`naked` alone would have removed a line that actively prevents a wrong answer.

Checked against ground truth before trusting it: `ros2 interface show
sensor_msgs/msg/CameraInfo` documents `K` as "the intrinsic camera matrix for
the raw (distorted) images" and `P` as specifying "the intrinsic (camera) matrix
of the processed (rectified) image". The skill's line is correct and the
ablated answers are wrong.

The docs-URL line is the other survivor, at `naked` 0.25. Unaided, sonnet does
not build `https://docs.ros.org/en/jazzy/p/<package>/` from a package name; it
looks for a URL it remembers. This is the navigational-pointer effect the
earlier model cross-check predicted, now confirmed with a proper ablation rather
than inferred from a baseline comparison.

Three claims stayed **UNDERPOWERED** and were kept: the QoS symptom row on one
of its four checks (Δ=+0.25), and the `cv_bridge` code block on both `compiles`
and `cvbridge_hpp` (Δ=+0.30, `naked` 0.70). That last one is the Jazzy
`cv_bridge/cv_bridge.hpp` spelling — the model writes the pre-Jazzy `.h` form
about 30% of the time unaided, which the compile grader catches and no regex
over the answer text would.

## What was cut, and why it is a real cut this time

Five of seven symptom rows: encoding exception, depth units, depth
registration, `pointcloud_to_laserscan` height band, compressed transport. All
at `naked = full = ablate = 1.00`.

The joint ablation of the encoding + depth-units pair was also clean, which by
the rule established on `ros2-testing` normally means "merge, not delete". It
does not here, and the difference is worth stating precisely: on `ros2-testing`
the jointly-ablatable group had `naked` at **0/8** — the lines were saying one
true thing redundantly, and the model could not supply it. Here `naked` is
**1.00**. A clean joint ablation means merge when the model cannot produce the
content unaided, and means delete when it can. The joint result alone does not
distinguish those; the naked baseline does.

Verified past the regex before cutting: the naked depth-encoding answers were
read whole. They give `16UC1` as millimetres and `32FC1` as metres, explain why
cv_bridge cannot convert single-channel depth to a 3-channel colour encoding,
and reach for `passthrough` — with a fallback of printing `msg.encoding` when
that still fails. That is understanding, not pattern-matching.

## The rewrite

The compressed body keeps the doc pointers, the `cv_bridge` block (UNDERPOWERED,
not a cut), the QoS row and the K-vs-P row, and drops the other five symptom
rows. Saved as
[`../../variants/ros2-perception/compressed.md`](../../variants/ros2-perception/compressed.md),
measured against the live body at n=8: **tied on all 19 checks**, largest
deviation -0.12 at p=1.000, both compile graders unchanged. 43 -> 38 lines.

The gain is small because the file was already small. No prose-for-example
substitution was attempted here: the one code block in the file is not at
ceiling, so there was nothing to test that hypothesis against.

## Run health

5 cells errored — four `no-model-response` and one timeout, four of them in the
`protocol` condition, which no verdict depends on. 44 of 591 check results were
ungradable (7.4%), concentrated in `perc-docs-lookup` and `perc-qos-silent`.
The pre-flight stub check was run against `perc-docs-lookup` specifically
because the earlier cross-check showed it was the most stub-prone probe — the
correction to the mistake made on `ros2-package`, where the most convenient
probe was sampled instead of the most at-risk one. It came back clean at 2/2,
and the sweep's rate stayed low enough not to starve any comparison.
