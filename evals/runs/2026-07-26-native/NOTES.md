<!-- Detailed write-up for this run. The summary that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Native-install run — 2026-07-26 (Tasks 1–3, live `/opt/ros/jazzy`)

Roadmap item 3: the three remaining tasks, measured against a live install for
the first time. No container this time — `ros-jazzy-ros-base` installed natively
on Ubuntu 24.04 (WSL2), which satisfies the same grading criterion (the agent can
read the real install and actually run nodes). Artifacts under
[`runs/2026-07-26-native/`](./); the harness that produced
them is committed in [`harness/`](../../harness/) so the pairs are re-runnable.

| | |
| :--- | :--- |
| Harness | CLI 2.1.220, `claude -p`, `--output-format stream-json` in **both** cells (so "tools used" is counted from the transcript, not recalled), `acceptEdits`, `--allowedTools WebFetch WebSearch Read Glob Grep Write Bash`, fresh `mktemp -d` per cell |
| Model | `haiku` in both cells |
| Environment | native `ros-jazzy-ros-base`, `rmw_fastrtps_cpp`, 194 packages |
| Live scenario | up for both cells: a BEST_EFFORT `/scan` publisher (Task 1), `map→odom→base_link` only (Task 2 — writing the sensor TF is the agent's job), a 30 Hz BEST_EFFORT camera + default-RELIABLE subscriber (Task 3) |
| Sample size | **n=1 per cell**, same disclosed conflict of interest as above |

## Task 1 — `/scan` monitor, graded by running it

Both agents wrote a node; both nodes were then run for 6 s against the live
publisher. The scan contains `inf`, `nan`, a below-`range_min` value (0.02) and
an above-`range_max` value (99.0); **the correct in-bounds minimum is 0.45 m.**

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| Subscription QoS | ❌ `create_subscription(..., 10)` → RELIABLE | ✅ `qos_profile_sensor_data` |
| **Messages actually received** | ❌ **zero.** rclpy itself logged `New publisher discovered on topic '/scan', offering incompatible QoS. No messages will be received from it. Last incompatible policy: RELIABILITY` | ✅ receives at 5 Hz |
| Reported minimum | — (never received; logged `Awaiting first scan message...` every second) | ⚠️ **`0.020 m` — wrong**, the below-`range_min` reading |
| `range_min`/`range_max` bounds filter | ❌ absent (`r > 0 and r != inf`) | ❌ absent (`not float('inf') == r`) |
| `nan` handling | ✅ incidentally excluded by `r > 0` | ❌ `nan` passes the filter |
| Independent 1 Hz timer | ✅ | ✅ |
| Says something when no data | ✅ | ✅ |
| Turns / cost / tool calls | 2 / $0.0307 / 1 | 4 / $0.0344 / 2 (`Skill: ros2-core`, `Write`) |

**Honest read: skills win the decisive bit and both fail the numeric one.** Only
the with-skills node connects at all — that is the difference between a working
sensor pipeline and a node that will never fire, and it is what the skill's QoS
rule exists to produce. But neither node filters against `range_min`/`range_max`,
so the with-skills node confidently reports `0.020 m` instead of `0.45 m`. The
baseline's identical bug is merely invisible because it never receives data.

**One nuance worth stating precisely.** The QoS failure is silent *at the DDS
level*, which is where it matters — but it is not necessarily silent in the logs.
This baseline logs on a timer, so it repeats `Awaiting first scan message...`
forever, and Jazzy's rclpy prints an incompatible-QoS warning of its own. The
argument for the skill's QoS rule rests on the middleware behavior (zero messages
delivered), not on the claim that nothing is printed.

## Task 2 — inverted LiDAR TF

Graded on the transcript **and** by publishing each agent's transform verbatim
and running the diagnostic on it ([`t2_agent_output_check.log`](./t2_agent_output_check.log)).

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| Asks about the physical mounting before writing | ❌ answered in one turn | ✅ **asked the back-distance / offset question first**, before emitting the transform |
| RPY encodes roll≈180° **and** yaw≈180° | ✅ | ✅ |
| REP 105 parent/child (`base_link` → sensor) | ✅ | ✅ |
| Published output flagged by `check_tf_tree.py` | ✅ both roll and yaw flagged | ✅ both flagged |
| Jazzy argument form | ✅ named args | ⚠️ named args in the launch file, but the "one-liner" uses the **positional form**, which the install answers with `[WARN] Old-style arguments are deprecated` |
| Invented symbols | ❌ a `static_transforms:` YAML schema no core node consumes | ❌ **`ros2 run ros2_troubleshooting_helpers check_tf_tree.py` — no such package** (`ros2 pkg prefix` → `Package not found`) |
| Physical-confirmation advice | ⚠️ RViz, but a **PointCloud2** display for a LiDAR | ✅ `tf2_echo` + a **LaserScan** display + "points should wrap around the back" |
| Turns / cost / tool calls | 1 / $0.0254 / **0** | 3 / $0.0475 / 1 (`Skill: ros2-troubleshooting`) |

**The gate fired, and the skills still hallucinated.** The behavioral win is
real and reproducible — with skills the agent stopped and asked for the mounting
geometry, which is the checklist's first item and the thing that prevents 200
wrong lines. But the same answer invented a package name **for the skill's own
script**, and told the user the check "should show RPY matching your physical
mount without flagging ~180° as suspicious" — the opposite of what the script
does (it flags ~180° every time, by design). A skill that ships tooling has to
state how to invoke it, or the model will invent a plausible `ros2 run`.

## Task 3 — silent QoS mismatch

The premise was made real first: `ros2 topic hz /camera/image_raw` reported
**30.000 Hz** while the RELIABLE subscriber logged `images received: 0`
([`t3_hz.log`](./t3_hz.log),
[`t3_sub.log`](./t3_sub.log)).

| Check | Baseline | With skills |
| :--- | :--- | :--- |
| Names reliability mismatch as prime suspect, first attempt | ✅ | ✅ |
| Recommends inspecting real endpoint QoS | ✅ `ros2 topic info --verbose` | ✅ `ros2 topic info -v` |
| **Actually inspected the live system** | ❌ 0 tool calls | ❌ loaded the skill, then answered — never ran the command it recommended |
| Fix uses a real QoS API | ✅ | ✅ |
| Factual accuracy of the QoS claim | ✅ | ❌ calls the default `(Reliable, **Transient Local**)`; the installed default is RELIABLE + **VOLATILE** (`QoSProfile(depth=10)` → `RELIABLE`, `VOLATILE`) |
| Turns / cost / tool calls | 1 / $0.0194 / 0 | 3 / $0.0271 / 1 (`Skill: ros2-core`) |

**Honest read: a tie the skills slightly lost.** Diagnosis is the one thing haiku
already knows cold — this is the single most-written-about ROS 2 failure, so both
cells nailed it in one turn. The with-skills cell added a wrong durability claim
and, despite a live reproduction sitting right there with `Bash` allowed,
recommended a command it did not run. Task 3 as written cannot separate the
conditions; a fair version would have to require the answer be *demonstrated*
against the live endpoints, not asserted.

## Verification scripts — the FAIL path, first time

Every previous live run of `check_qos_compat.py` returned PASS. The Task 3
scenario produced its first real failure:

```
[FAIL] fake_camera_pub -> reliable_image_sub
       reliability: publisher offers BEST_EFFORT, subscriber requests RELIABLE —
       subscriber will receive NOTHING; use qos_profile_sensor_data or a
       BEST_EFFORT subscription for sensor streams
exit code = 1
```

`check_tf_tree.py` was also tested for **specificity**, not just sensitivity: run
against a tree carrying both an inverted rear sensor and a correctly-mounted
forward one, it flagged the first for roll and yaw and left the second alone
([`t2_tf_check.log`](./t2_tf_check.log)).

## What this run establishes

1. **Tasks 1–3 now have live-install measurements.** Roadmap item 3 is closed;
   every task in the suite has been run against a real ROS 2 install.
2. **The QoS result is now a runtime fact, not a code review.** The baseline node
   received zero messages from a publisher visibly running at 5 Hz, and the
   middleware said why. This is the repo's central claim and it reproduces.
3. **The pre-write gate reproduces too** — third independent run in which the
   with-skills agent asked for physical/geometric facts before writing.
4. **Skills do not stop hallucination; they move it.** Two invented symbols in
   with-skills output across three tasks (`ros2_troubleshooting_helpers`, a wrong
   default durability), one of them about the repo's own tooling. Routing to docs
   raises the floor; it does not make the model correct.
5. **On tasks the model already knows, skills cost ~1.4× and buy little.**
   Baseline total $0.0755 vs with-skills $0.1090 across the three pairs. Task 3
   is the clear case: same answer, more money, one extra error.

## Follow-ups this run created

**Read the tables above as measurements of the skills as they were *before* these
fixes.** Everything marked applied below landed after the run, in the same commit
as this write-up; whether the fixes work is an open question until Tasks 1–3 are
re-run.

- ✅ **Applied.** `ros2-troubleshooting` §1a now gives the literal invocation
  (`python3 <skill-dir>/scripts/<name>.py`) and names `ros2 run
  ros2_troubleshooting_helpers` as a known failure mode. A skill that ships a
  script must state how to run it, or the model invents a package.
- ✅ **Applied.** `ros2-core` now carries the bounds rule as both a
  symptom→cause→action row and a strict rule: a `LaserScan` reading is usable only
  when finite **and** within `[range_min, range_max]`. "Filter `inf`" is what the
  model already does, and it produces a confidently wrong minimum.
- ✅ **Applied.** `ros2-core` gained the shutdown pattern — both agents' nodes died
  with `rcl_shutdown already called` / `ExternalShutdownException` on SIGTERM.
- ✅ **Applied.** `ros2-troubleshooting` now states that `check_tf_tree.py` always
  prints the `VERIFY PHYSICALLY` advisory for a ~180° roll or yaw, even when the
  mounting is intentional — the with-skills run told the user the opposite.
- ⏳ **Open.** Task 3's checklist should require a *demonstrated* inspection, not a
  recommended one, or it will keep scoring as a tie.
- ⏳ **Open.** Re-run Tasks 1–3 against the patched skills. The specific
  regressions to watch: does the Task 1 node now filter bounds, and does the
  Task 2 answer stop inventing a package?

---
