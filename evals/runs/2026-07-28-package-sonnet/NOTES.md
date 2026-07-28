<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `ros2-package` verified on sonnet — 2026-07-28

The largest skill measured so far (115 lines, 16 claims) and the only one with a
grader that runs a real build instead of a regex. **115 lines to 69**, and as
with `ros2-testing`, the reduction came from rewriting rather than deleting.

| | |
| :--- | :--- |
| Method | n=4 sweep (`naked`/`protocol`/`full`/`shipped`, every claim ablated singly and `only:`), targeted top-ups on the two unresolved groups, an authored `variant:` rewrite, then a confirmation run on the shipped body |
| Probes | 8, covering all 16 claims. `pkg-build-ground-truth` is not regex-graded: it unpacks the model's files into a scratch workspace, runs `colcon build`, and checks `ros2 pkg executables` lists the node |
| Spend | 280-cell sweep $6.79, top-ups $0.78, variant $3.08, confirmation $2.07 — $12.72 total |
| Outcome | 115 -> 69 lines, `naked` 0.844 vs `full` 0.953 on the shipped body |

## Axis 1

Pooled over all 27 checks on the shipped 69-line body at n=8:
**`naked` 157/186 = 0.844, `full` 202/212 = 0.953.** The gap is the smallest of
the three skills verified so far (`ros2-testing` 0.762 -> 1.000, `ros2-core`
0.689 -> 0.949), which is what a high unaided baseline looks like: sonnet
already writes correct package wiring most of the time.

The single strongest signal in the run is `iface_location_cause` — **1/4 naked,
4/4 full**. Unaided, sonnet does not reliably know that custom interfaces cannot
live in an `ament_python` package. That one fact is most of what this skill is
buying.

The ground-truth probe was at ceiling in every condition: `naked` 4/4 on both
`builds_clean` and `exe_discoverable`. Sonnet writes a working `ament_python`
package with no help at all — correct `data_files` resource-index entry,
correct `<export><build_type>`, correct `setup.cfg` install paths. Those last
two were content *added* to this skill in an earlier pass because they were
missing; the model now supplies them unaided.

## Axis 2: five claims at ceiling, four that only looked ambiguous

Nine of nineteen claim-check pairs came back at `naked = full = ablate = 1.00`:
the scaffolding block, the entire `ament_cmake` reference block (six checks, all
of them), the `ament_python` `data_files`/`entry_points` block, the
`<export><build_type>` prose, the colcon build/source block, and the
launch-not-installed symptom row.

Four came back **UNDERPOWERED**, and none of them were cut:

| Claim | Check | naked | full | ablate | Δ |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `interfaces:04` | verify_cmd | 0.67 | 1.00 | 0.20 | +0.80 |
| `interfaces:02` | rosidl_generate | 0.67 | 1.00 | 0.50 | +0.50 |
| `ament-python:03` | setup_cfg_script_dir | 0.75 | 1.00 | 0.67 | +0.33 |
| `interfaces:03` | iface_xml_tags | 0.67 | 1.00 | 0.75 | +0.25 |

`setup_cfg_script_dir` is worth naming separately: `ablate` (0.67) scores
*below* `naked` (0.75). That is the shape where a line is inert against an empty
prompt and load-bearing against the rest of its own section — removing it leaves
the surrounding text pointing at an install path it no longer explains. Cutting
on the naked baseline would have been the wrong call, and this run did not make
it.

## Why these stayed underpowered: the probe provokes the stubs

113 of 1000 check results were ungradable — 11%, by far the highest rate in any
run here. All of them were tool-call stubs, correctly scored ungradable rather
than wrong, and they are not evenly spread:

| Condition | Stub rate |
| :--- | ---: |
| `only:`/`ablate:` on interface claims | 0.27 – 0.30 |
| `protocol` (CLAUDE.md only) | 0.28 |
| `full` | 0.17 |
| `naked` | 0.10 |

The first read was that the skill body causes it — that some line tells the
model to go check the install and it stalls with tools off. That is wrong, and
worth recording as a rejected hypothesis: the rate tracks the **probe**, not the
content. Every condition of `pkg-interfaces` is high and every condition of the
other seven probes is at or near zero. `protocol` being high fits the same
explanation — `CLAUDE.md` says to verify against the local install, and with
tools off that instruction produces a stall rather than an answer.

The practical consequence is that `pkg-interfaces` effectively ran at n=3 on
`full` despite ten repeats. A top-up to `--repeats 10` on the four interface
claims bought only a few gradable cells. Pushing further would cost more than
the question is worth when the answer is already "do not cut", so the four
claims are recorded as UNDERPOWERED and kept.

## The rewrite

The `ament_cmake` block (6 checks at ceiling) and the `ament_python` block
(2 checks at ceiling) were the two largest chunks of the file. Following the
finding from `ros2-testing` — a worked example seems to cap what the model
produces — both were replaced with prose naming only the facts that matter:
the exact `lib/${PROJECT_NAME}` destination, that `launch/` and `params/` are
not installed by default, that `ament_package()` comes last, and that
`package.xml` needs the `ament_python` export tag. The scaffolding block, the
colcon block and the symptom row were dropped outright. The `setup.cfg` block
and the whole interfaces section were left untouched.

Saved as
[`../../variants/ros2-package/compressed.md`](../../variants/ros2-package/compressed.md)
and measured against the live body at n=8: **tied on all 27 checks**, including
both real-build checks, largest deviation -0.25 at p=1.000 on the
stub-starved interfaces probe. On a tie the smaller body wins, so 69 lines
shipped.

## Verified past the regex before cutting

The `ament_cmake` block was the biggest single cut, so its `naked` answers were
read whole rather than trusted to the checks. They produce
`install(TARGETS ... DESTINATION lib/${PROJECT_NAME})`,
`ament_target_dependencies`, `install(DIRECTORY launch DESTINATION
share/${PROJECT_NAME})` and `ament_package()` last — and both the `lib/<pkg>`
layout and `ament_target_dependencies` were confirmed present in the local Jazzy
install (`/opt/ros/jazzy/lib/<pkg>/`,
`share/ament_cmake_target_dependencies/cmake/ament_target_dependencies.cmake`)
rather than assumed.

## Method notes

**Stub-checking one probe is not stub-checking the sweep.** The pre-flight check
was run against `pkg-build-ground-truth`, which came back clean at 4/4 — and
that probe turned out to be the *least* stub-prone of the eight. The probe that
mattered was never sampled. Check the probe whose prompt most invites a lookup,
not the one that is most convenient to check.

**Claim ids shifted again**, as expected this time rather than by surprise: the
rewrite dropped four claims and merged a section, moving every section number
below the doc pointers. All twelve `C_PKG_*` constants were stale afterwards and
were re-mapped before the confirmation run; four are now `None`. The constant
names deliberately no longer match the digits in their ids and the comment in
`probes.py` says so, since the mismatch reads as a bug.
