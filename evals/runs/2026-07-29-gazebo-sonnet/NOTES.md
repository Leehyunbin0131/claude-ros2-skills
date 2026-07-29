<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# `gazebo-sim` measured on sonnet — 2026-07-29

First suite written under the check-anchoring rule added to `PROCEDURE.md` the
same day, and the first one to come back at **`full` below 1.000** — because the
grader is a real parser rather than a search for the file's own words.

**File unchanged at 85 lines. No claim cleared q<0.05.**

| | |
| :--- | :--- |
| Method | pre-measurement, n=4 sweep, baseline topped up to n=10, three targeted ablate top-ups |
| Probes | 4 new, 13 checks, covering 18/18 claims |
| Spend | $7.70 |
| Outcome | `naked` 80/113 = 0.708 vs `full` 123/126 = 0.976 |

## A real-outcome grader, and what it changed

`sdf_parses` hands the answer's XML to the installed `gz sdf --check` from
`gz_tools_vendor`. Two things had to be established before it could be trusted:

- **It discriminates.** `gz sdf --check` prints `Valid.` even for unknown tags,
  so the exit code alone says nothing. It does emit
  `Warning [...] not defined in SDF` per bogus element, and that is the signal
  the check reads. Verified: the skill's own diff-drive and lidar blocks parse
  clean; the same blocks with `<samples>` misspelled `<sampels>` do not.
- **Everything else it looks for exists in the install**, not just in the file:
  `libgz-sim8-diff-drive-system.so`, `-sensors-system` and `-imu-system` all
  ship, `gpu_lidar` is a real sensor type in `gz sdf --describe`, and
  `<gz_frame_id>` — absent from the SDF spec and easy to assume invented — is
  used inside `<sensor>` by the shipped
  `nav2_minimal_tb3_sim/urdf/gz_waffle.sdf.xacro`.

The result is the first `full` under 1.000 in three skills: **0.976**. The
parser fails roughly one answer in six even with the file in context, which is
what a check that cannot be satisfied by wording looks like.

Split the same way as the earlier audit:

| Check group | naked | full |
| :--- | ---: | ---: |
| anchored to the install or the parser | 0.742 | **0.972** |
| echoing the file's phrasing | 0.500 | 1.000 |

The phrasing group still reads 1.000. The anchored group does not. Same run,
same answers.

## Nothing cleared the bar, and it was not chased

Six claims came back UNDERPOWERED, two of them at **q=0.055** — the IMU world
plugin (`naked` 0.12, `full` 1.00, `ablate` 0.40) and `<gz_frame_id>`
(`naked` 0.75, `full` 1.00, `ablate` 0.25). Both would likely cross 0.05 with
another top-up.

They were not topped up further. q=0.055 and q=0.05 are not meaningfully
different, and sampling until a number crosses a threshold is how a result gets
manufactured rather than measured. Recorded as UNDERPOWERED, which is what they
are.

The real signals worth naming even unconfirmed: unaided, sonnet names the
`gz-sim-imu-system` world plugin **1 time in 8**, bridges `/clock` with
`use_sim_time` **2 times in 8**, and reaches for `ros2 pkg prefix ros_gz_bridge`
**1 time in 10**. Those are the parts of this file with headroom.

## No rewrite was attempted

There is compressible mass on paper — the bridge-syntax line, `gz sim --version`
and both plugin filenames all sit at `naked` 0.89–1.00. But `sdf_parses` scores
**0.00 when the diff-drive block is ablated** against 0.83 with it (Δ=+0.83,
q=0.143): removing the worked SDF example is what makes the model's own SDF stop
parsing. Underpowered, but pointed in one direction, and it points at exactly
the block a compression would delete. After the three rejected
`ros2-troubleshooting` rewrites, spending to confirm a warning the data has
already given would be the wrong call.

## Two grader bugs, both caught before they reached a verdict

**The wrapper nested fragments wrongly.** `<plugin>` belongs to `<model>` and
`<sensor>` inside `<link>`; the first draft put everything inside `<link>`, so
correct plugin blocks parsed as invalid. Caught in the pre-flight stub check
when `full` scored below `naked` — a shape that is almost always the
instrument, not the content.

**Elided illustrations were graded as wrong answers.** `full` answers tend to
give a whole `<model>` or `<world>` with `...` standing in for the rest. That is
not complete SDF and cannot be parsed, but it is not a wrong answer either. The
check now returns ungradable for any fragment containing an elision marker and
wraps `<model>`/`<world>` roots directly. Fixed with `runner.py regrade` against
stored answers: 10 of 767 results changed, no re-run, no spend.

Both are the same failure this project keeps meeting from new angles — a
non-answer scored as a wrong answer, deflating whichever baseline it lands in.
