# Verification status

**This file is the record of what is finished.** It is the first thing to read
before working on a skill, and the last thing to update after — the final stage of
a verification run writes its own row here, so the record cannot drift from the
runs behind it.

For *how* to run a verification — the steps, in order, in plain language —
see **[`PROCEDURE.md`](./PROCEDURE.md)**. For the tools themselves, see
[`harness/README.md`](./harness/README.md).

## What "verified" means here

A skill is not verified because it is correct. Correct is the floor. It is
verified when both of these are answered:

- **Effect** — does it change what the agent produces on a task that exercises
  *its own* content, measured against a live ROS 2 Jazzy install?
- **Efficiency** — is this body the *smallest* one that produces that effect?
  Fewer tokens and less text may buy the same result, and until that is tested,
  "the agent used it" is only half an answer.

Both are measured by A/B runs graded mechanically — does the symbol exist in the
install, does the command succeed when re-run, does the generated node print the
right number against a live publisher — not by review.

## Status

The two axes are **ordered**, and axis 1 gates axis 2: if the shipped body does
not beat `naked`, "which line is load-bearing" is not a question worth asking —
the answer is to delete the file, not to trim it. The effect column below is
that gate, measured on the *shipped* body in each skill's confirmation run, so
it cannot drift away from what actually ships.

| Skill | Effect (naked → full, shipped body) | Status | Evidence |
| :--- | :--- | :--- | :--- |
| `ros2-core` | 0.689 → 0.949 | VERIFIED | [ablation](./runs/2026-07-28-core-sonnet/) + [confirmation](./runs/2026-07-28-core-sonnet-confirm/) |
| `ros2-testing` | 0.786 → 1.000 | VERIFIED | [ablation](./runs/2026-07-28-testing-sonnet/NOTES.md) + [rewrite comparison](./runs/2026-07-28-testing-variant/) + [confirmation](./runs/2026-07-28-testing-confirm-sonnet/) |
| `ros2-package` | 0.863 → 0.953 | VERIFIED | [ablation](./runs/2026-07-28-package-sonnet/NOTES.md) + [rewrite comparison](./runs/2026-07-28-package-variant/) + [confirmation](./runs/2026-07-28-package-confirm-sonnet/) |
| `ros2-perception` | 0.849 → 0.987 | VERIFIED | [ablation](./runs/2026-07-28-perception-sonnet-full/NOTES.md) + [rewrite comparison](./runs/2026-07-28-perception-variant2/) + [confirmation](./runs/2026-07-28-perception-confirm-sonnet/) |
| `ros2-dev` | 0.600 → 0.882 | IN PROGRESS | [ablation](./runs/2026-07-29-dev-sonnet/NOTES.md) — 26/26 body claims, 54 reference claims sampled, no claim cleared q<0.05 |
| `ros2-troubleshooting` | 0.795 → 1.000 *(install-verified checks: 0.051 → 0.982)* | VERIFIED | [ablation](./runs/2026-07-28-troubleshooting-sonnet/NOTES.md) + 3 rejected rewrites ([1](./runs/2026-07-28-troubleshooting-variant/), [2](./runs/2026-07-28-troubleshooting-variant2/), [3](./runs/2026-07-28-troubleshooting-variant3/)) |
| `gazebo-sim` | 0.708 → 0.976 *(parser/install-anchored checks: 0.742 → 0.972)* | IN PROGRESS | [ablation](./runs/2026-07-29-gazebo-sonnet/NOTES.md) — 18/18 claims, no claim cleared q<0.05 |
| `ros2-control` | 0.696 → 1.000 *(install-verified checks: 0.444 → 1.000)* | VERIFIED | [ablation](./runs/2026-07-29-control-sonnet/NOTES.md) + [rewrite](./runs/2026-07-29-control-variant/) + [confirmation](./runs/2026-07-29-control-confirm/) |
| `ros2-moveit` | 0.470 → 1.000 *(install-verified checks: 0.083 → 1.000)* | VERIFIED | [ablation](./runs/2026-07-29-moveit-sonnet/NOTES.md) |
| `ros2-microros` | — | OUT OF SCOPE | no `micro_ros_agent` or `micro_ros_setup` in apt; needs a source build. Excluded by instruction |

Status vocabulary — a skill is only VERIFIED when **both** axes have passed:

| | Meaning |
| :--- | :--- |
| IN PROGRESS | not yet measured, measured on one axis only, or measured over only part of the body — the evidence column says which |
| VERIFIED | effect **and** efficiency, at n≥5, with the run linked |
| OUT OF SCOPE | cannot be measured on this machine without work disproportionate to the question; the reason is stated in the evidence column |
| DID NOT CLEAR | measured and failed axis 1 — the body does not beat an empty context, so there is no effect for axis 2 to apportion. Recorded, not hidden |

Every row is measured on **`sonnet`**, the model these skills actually ship
against. An earlier pass graded on `haiku`; those verdicts were discarded
rather than carried forward, because a `KEEP` from a smaller model does not
transfer upward — see [`PROCEDURE.md`](./PROCEDURE.md). Skills whose only
evidence was haiku-era are back to IN PROGRESS until they are re-swept.

**No skill has completed verification.** Results are published here per skill as
each one clears both axes — not before, and including the ones that fail.

## Why the record starts on sonnet

An earlier round of this work graded every skill on `haiku`. Those runs and
their verdicts have been removed rather than kept as history, because they
were actively misleading to read: a `KEEP` from a smaller model does not
transfer to a larger one, and the two disagree in a *direction*, not at random.

A cross-check of `ros2-perception` measured on both
([run](./runs/2026-07-28-perception-sonnet/)) is what established this. The
technical facts lost their effect on the bigger model — it already knows which
header Jazzy ships and which matrix pairs with which topic — while the
*navigational* lines gained it: the docs-URL convention went from p=0.077 on
haiku to **p=0.003** on sonnet, and the "check the local install" habit from
p=0.077 to **p=0.015**. Capability supplies knowledge; it does not supply the
disposition to build a docs URL from a package name or to verify against the
install instead of answering from memory.

So haiku calibration **over-keeps inlined technical facts and under-values
navigational pointers** — precisely inverting this project's stated philosophy,
which is that a correction should point at the authoritative doc rather than
hand over the answer. Keeping those verdicts on the page would have meant
publishing conclusions whose most likely error mode was known and unfixed.
The one direction that does transfer is CUT: if a smaller model does not need
a line, a larger one will not either.

`ros2-package` and `ros2-perception` had no evidence left once the haiku runs
were removed; both have since been re-swept on sonnet.

## Skills verified on sonnet

**`ros2-core`**: n=4 sweep, n=8 top-up on every ambiguous claim, one probe
(`tf-lookup`) got a joint-ablation condition it should have had from the start
(below) before any cut was decided, then a `naked`/`full` confirmation against
the real reduced body — 487 ablation cells plus 111 confirmation cells, $14.58
total (plus $2.71 on an exploratory naked/full probe run, discarded once the
per-claim sweep made it redundant). Two more lines cut (45 → 43): the TF-exception-catching rule and the TF
`ExtrapolationException` symptom row, both `naked=full=ablate=1.00` on sonnet
with no redundancy partner once tested. Confirmation: `tf_exception` and
`tf_latest_time` both 8/8 before and after, pooled across all 19 checks
95.4% → 94.9%, not significant (p=0.36).

Those pooled numbers are after a second bug fix, found by asking a plain
question the numbers invited: this run's first pass came back at `full` 0.89,
lower than the earlier grading pass on the same body, which should not happen
on a body that had just been *cut* for redundancy. Every one of the eight `full`-condition
failures behind that number turned out to be the same artifact: sonnet reaches
for a tool this tools-off harness has turned off ("I'll check the current
directory structure first... **Tool: bash**") and, finding nothing, stops
before answering — a non-answer, not a wrong one. Two checks
(`param_callback`, `param_declare`) additionally bypassed the `code()`/`prose()`
extraction helpers and regexed the raw answer directly, so a stub that merely
*mentioned* `add_on_set_parameters_callback` while trying to look it up had
been scored a pass. Fixed in both extraction helpers behind a length-gated
marker detector, verified against every sampled stub format (30/33 caught
directly; the remaining 3 already graded correctly some other way) with zero
new false passes or fails introduced — every changed grade moved to
*ungradable*, never invented one. A `runner.py regrade` subcommand now
re-applies current check functions to a run's stored answers without
re-spending anything; both `ros2-core` sonnet runs were regraded in place.
Corrected, `full` moved from 0.89 to 0.95. The lesson is not the number but
what the discrepancy was worth: an absolute `full` score is not a portable
quality metric — checks written against one model's typical output style do
not necessarily fit another's — so the signal to trust is the naked-to-full
gap, +0.21 on the ablation sweep (0.748 → 0.954) and +0.27 on the shipped
43-line body (0.679 → 0.949). Chasing a raw score that looked wrong is what
surfaced the bug; treating it as the metric would have hidden it.

A third candidate — the TF2 symbols bullet — read identically (ceiling
everywhere) but **was not cut**. That single bullet bundles the now-redundant
exception-symbol list with a REP105 frame-convention pointer to
`ros2-troubleshooting` that no check has ever measured; deleting the bullet on
the symbol-list evidence would have silently deleted the pointer too. This is
the same shape the project already applies to reference code blocks (kept
past the point individual clauses cleared) —
here for the first time on a single line rather than a whole block. Splitting
the bullet so each half can be judged on its own is future work, not done.

Fixing the probes surfaced a bug older than this re-check. `probes.py`'s claim
ID constants for `ros2-core` (9 of 16) and `ros2-testing` (4 of 6) had gone
stale: the confirmation commits that cut each skill (`d647ed8`, `f152b08`)
renumbered sections, and the constants were never updated to match. Every
`ablate:<id>` condition on the affected IDs either targeted the wrong line or,
where the old number no longer existed at all, crashed with `KeyError`. Neither
skill's original confirmation run caught this because both were `naked`-vs-
`full` only, which never touches a per-claim ID — this sonnet re-sweep is the
first full per-claim ablation run against either skill's *shipped* body since
the cuts that broke the mapping. Both are fixed and every suite's claim IDs are
now checked to resolve before spending on a sweep.

The `tf-lookup` probe also had a real gap independent of the stale-ID bug: two
different claims (the TF-catch rule and the TF2 symbols bullet) both drove its
`tf_exception` check with no `joint=` declaration between them — exactly the
redundancy-pair blind spot the project's own methodology (see below) exists to
catch, just never applied to this one probe. Added before either claim was cut.

The sonnet re-checks also surfaced two grading bugs worth recording, because
both scored *correct* answers as failures and neither was visible in the
aggregate. One check was order-sensitive on XML attributes — it demanded a
particular attribute first, and sonnet writes them in a different but equally
valid order just as often, so real answers scored `False`. And the tool-call
stub detector (see the sonnet-switch caveat above) kept meeting new
renderings it didn't cover — an icon glyph in front of "Tool:", then
`**Tool Call:**` with a space instead of an underscore — each one scoring a
hard `False` on a real question instead of ungradable until caught. Both
narrow, anchored patterns were replaced with one loose match (the word `Tool`
followed by a colon within 20 characters, case-sensitive so lowercase mentions
in ordinary prose are never swept up), checked against the full corpus of
already-graded `True` answers across every stored run before trusting it:
one flagged "false positive" turned out to be the same class of bug again — a
negative-form check (`no_python_qos_in_cpp`, true whenever the wrong syntax is
*absent*) trivially passing a stub that never answered at all.

**`ros2-testing`** produced the most useful method result so far. Axis 1 is the
strongest measured anywhere: on the shipped body at n=8, `naked` 77/101 = 0.762 against `full`
104/104 = 1.000. Two checks carry most of that gap — `writer_create_topic` is
**0/8 unaided**, because sonnet reaches for the templated
`writer.write(msg, topic, time)` overload and never registers the topic, and
`simtime_cause` is 4/8, connecting "rosbag playback produces no callbacks" to
`use_sim_time`/`--clock` only half the time.

Axis 2 is where the interesting part is. The n=4 sweep returned CUT on 12 of 16
claim-check pairs, plus two declared redundancy groups whose joint ablations
came back at Δ=0 — the colcon block, its prose, and two symptom rows (4 claims);
and the `launch_testing` example plus its `ReadyToTest()` explanation (2 claims).
Reading that as "delete six claims" would have been wrong, and the targeted
top-ups proved it: the same claims that looked inert under ablation include the
one scoring 0/8 naked. **Jointly ablatable is not the same as unnecessary.**
What a clean joint ablation actually reports is that those lines say the same
thing more than once — which argues for merging them, not for dropping them.

So they were merged by hand and the rewrite was measured rather than assumed:
[`variants/ros2-testing/compressed.md`](./variants/ros2-testing/compressed.md),
four claims about `colcon test` collapsed to one sentence and the 23-line
`launch_testing` example plus its explanation collapsed to one sentence, run
against the live body at n=8. **Tied on all 13 checks, 8/8 versus 8/8, p=1.000
everywhere**, so the adoption rule (on a tie the smaller body wins) took it:
76 lines to 42. Detail: [re-check](./runs/2026-07-28-testing-sonnet/NOTES.md),
[rewrite comparison](./runs/2026-07-28-testing-variant/),
[confirmation](./runs/2026-07-28-testing-confirm-sonnet/).

The finding worth carrying forward is what the merged prose did to the answers.
Working from one sentence of description instead of a worked example, the
variant's `launch_testing` answers included `@pytest.mark.launch_test`,
`proc_info.assertWaitForStartup`, `proc_output.assertWaitFor`, and the
`add_launch_test()` CMake call — none of which the deleted example showed, all
four verified present in the local Jazzy install. The checks score those answers
identically, so the measurement is a tie; read whole, the shorter body is
better. **A worked example appears to act as a ceiling**: the model reproduces
it and stops. Naming the concept and leaving the code to the model got more
correct API surface, not less. That is a hypothesis from one probe, not a law,
but it is the first concrete reason found in this project to prefer prose over
an example, and it is directly testable on the remaining skills.

**`ros2-package`** is the largest skill measured (115 lines, 16 claims) and the
only one with a grader that runs a real build. It ended at **115 lines to 69**,
again by rewriting rather than deleting, and it produced two results the other
skills could not.

First, the real-build probe was at ceiling in *every* condition — `naked` 4/4 on
both "does `colcon build` succeed" and "does `ros2 pkg executables` list the
node". Sonnet writes a working `ament_python` package unaided, including the
`data_files` resource-index entry, the `<export><build_type>` tag and the
`setup.cfg` install paths. The last two were content *added* to this skill in an
earlier pass precisely because they were missing from the model's output; they
are no longer missing. Content can expire, and only re-measurement finds out.

Second, the run is the clearest case yet of a probe rather than a skill setting
the measurement floor. 113 of 1000 check results were ungradable (11%, the
highest here), all tool-call stubs, all correctly scored ungradable rather than
wrong. The first hypothesis was that a line in the body sends the model looking
at the install; that was checked and **rejected** — the rate tracks the probe,
not the content. Every condition of `pkg-interfaces` runs 0.27–0.30 while seven
other probes sit near zero, and `protocol` (`CLAUDE.md` alone, which says to
verify against the local install) runs 0.28. The consequence is concrete: four
interface claims stayed UNDERPOWERED with deltas as large as +0.80 because
`full` could only be graded 3 times in 10, and they were kept rather than cut,
which is what UNDERPOWERED is for.

One claim is worth naming for its shape. `setup.cfg`'s install path measured
`naked` 0.75, `full` 1.00, `ablate` **0.67** — removing the line scores *below*
having no file at all, because the surrounding text then points at an install
path nothing explains. Cutting on the naked baseline would have been wrong here;
the comparison that decides a cut is full-with-line against full-without-line.
Detail: [ablation](./runs/2026-07-28-package-sonnet/NOTES.md),
[rewrite comparison](./runs/2026-07-28-package-variant/),
[confirmation](./runs/2026-07-28-package-confirm-sonnet/).

The rewrite tested the `ros2-testing` hypothesis on a second skill and it held:
the `ament_cmake` reference block (six checks, all at ceiling) and the
`ament_python` `data_files`/`entry_points` block were replaced by two prose
sentences naming only the facts that matter, and the compressed body tied `full`
on all 27 checks at n=8 — including both real-build checks. Two skills is not
proof, but "try prose before assuming the code block is doing the work" now has
evidence from more than one place.

**`ros2-perception`** is the smallest skill (43 lines) and was expected to be
the hardest to measure — a cross-check had `naked` at 0.908, leaving nine points
of room. That held: ten of sixteen claim-check pairs came back
`naked = full = ablate = 1.00` and no sampling would move them. It also produced
**the only two claims in this project that clear the corrected significance
bar.** 43 lines to 38, `naked` 0.849 vs `full` 0.987 on the shipped body.

| Claim | Check | naked | full | ablate | q |
| :--- | :--- | ---: | ---: | ---: | ---: |
| K-vs-P symptom row | k_vs_p_cause | 0.90 | 1.00 | **0.00** | 0.000 |
| docs-URL convention | docs_url | 0.25 | 1.00 | 0.30 | 0.025 |

The K-vs-P row matters for its shape more than its size. Unaided the model is
already right nine times in ten, so by the naked baseline the line looks
redundant. Removing it drives the check to **zero** — the ablated answers
explain "detection boxes drawn at wrong image positions" as box-coordinate
scaling rather than as a camera-matrix mix-up, borrowing a neighbouring row's
framing to produce a confident wrong answer. A line can be nearly invisible
against an empty prompt and still be the only thing standing between the rest of
its table and a plausible error. Checked against ground truth before it was
trusted: the installed `sensor_msgs/msg/CameraInfo` documents `K` as the
intrinsic matrix for raw images and `P` as the one for rectified images, exactly
as the skill says.

The docs-URL line is the navigational-pointer effect confirmed properly for the
first time. At `naked` 0.25, sonnet does not build
`https://docs.ros.org/en/jazzy/p/<package>/` from a package name unaided; it
reaches for a URL it remembers. That was previously inferred from a baseline
comparison across grading models — here it is a direct ablation.

This run also sharpened the merge-versus-delete rule from `ros2-testing`. The
encoding + depth-units pair ablated jointly clean, which normally reads as
"merge, not delete". It does not here, and the distinguishing fact is the naked
baseline: on `ros2-testing` the jointly-ablatable group sat at **0/8** unaided —
the lines said one true thing redundantly and the model could not supply it. Here
`naked` is **1.00**. **A clean joint ablation means merge when the model cannot
produce the content unaided, and delete when it can. The joint result alone does
not distinguish those.** Five of seven symptom rows were cut on that basis, after
reading the naked answers whole to confirm the model really does know
`16UC1`-is-millimetres, `32FC1`-is-metres and `passthrough` rather than merely
matching the pattern. Detail:
[ablation](./runs/2026-07-28-perception-sonnet-full/NOTES.md),
[rewrite comparison](./runs/2026-07-28-perception-variant2/),
[confirmation](./runs/2026-07-28-perception-confirm-sonnet/).

**`ros2-troubleshooting`** is the largest skill (119 lines, 50 claims) and the
first with no pre-existing probes. All 50 claims were measured. **Nothing was
cut**, and the reason is not the one this section originally gave — see the
correction below, which is the more useful finding.

Probe design started from a measurement rather than from the file. Asked cold,
sonnet diagnoses the silent-QoS case and reaches for `ros2 topic info -v`
unprompted, works the inverted-drive bug layer by layer, and gives the
`ROS_DOMAIN_ID` range as **0-232 with the 0-101 ephemeral-port caveat and the
`7400 + 250*id` arithmetic** — a superset of what the skill says.

**Axis 1 has to be read in two halves, not pooled.** The file's two parts behave
completely differently:

| | naked | full |
| :--- | ---: | ---: |
| Shipped-scripts section (1a) | 4/80 = **0.050** | 109/111 = 0.982 |
| Everything else (42 claims) | 70/88 = **0.795** | 92/92 = 1.000 |
| Pooled | 74/168 = 0.440 | 201/203 = 0.990 |

The pooled 0.440 is not a summary of this skill, it is an artifact of how many
checks point at each half. Roughly half the graded baseline cells belong to
probes whose checks ask for filenames that exist nowhere but this repository, so
`naked` there is structurally near zero. The honest reading: the scripts section
is worth a great deal, the rest is worth about +0.20 over an unaided model.

Five claims cleared q<0.05, all in the scripts section. The sharpest is
`advisory_not_verdict`, at **1.00 unaided and 0/7 ablated**: asked cold the
model reasons correctly that a `VERIFY PHYSICALLY` advisory on a deliberately
inverted mount is not a verdict, and given the rest of the skill with that one
line removed it stops. The surrounding text creates a wrong expectation that
only that line corrects.

### Correction: three rewrites were rejected, and not for the reason first recorded

Three compressed rewrites were authored and all three lost a check
significantly, so none shipped. The first write-up concluded that per-claim
`CUT` verdicts had been wrong — that each rewrite had removed a line which was
secretly load-bearing. **Re-reading the three variant runs side by side rather
than each against `full` alone shows that is true for only one of the three.**

| Check | `full` | v1 (topic absent) | v2 (terse summary added) | v3 (more added) |
| :--- | ---: | ---: | ---: | ---: |
| `tf2_echo` | 8/8 | **2/6** | 7/8 | 13/14 |
| `domain_default` | 15/16 | 8/8 | **7/16** | 16/16 |
| `single_thread` | 16/16 | 7/8 | 13/16 | **9/16** |

`tf2_echo` behaves as first described: the line was dropped, the check
collapsed, restoring the line fixed it. The other two do the opposite.
`domain_default` scored a clean 8/8 in the variant that omitted DDS content
**entirely**, and only broke in the next variant, which still omitted it but had
gained an unrelated summary section. `single_thread` got monotonically *worse*
as content about it was added back.

The mechanism is visible in the text. The `single_thread` check looks for the
words `single-threaded`. The shipped body explains the cause — *"a
single-threaded executor cannot process service responses while executing a
blocking callback"* — while the rewrite compressed it to *"needs a
`MultiThreadedExecutor` plus a `ReentrantCallbackGroup`"*, which is the fix with
the cause deleted. The model followed the shorter framing and produced the fix
without the cause.

**A terse summary of a topic can be worse than both the full treatment and
saying nothing at all.** Omit a topic and the model answers from its own
knowledge, completely. Summarise it badly and the summary becomes the frame the
answer is built on, and whatever the summary dropped is dropped from the answer
too. That is a sharper and more actionable finding than "the content is
mutually reinforcing", which is what was recorded first.

So what is established is **"these three rewrites failed"**, not "this file
cannot be compressed". The failures trace to how the rewrites were written —
they kept actions and discarded causes — not to a property of the file. A
compression that preserves the causal explanations was never tried, and the
skill ships unchanged at 119 lines either way. Detail:
[run notes](./runs/2026-07-28-troubleshooting-sonnet/NOTES.md).

The miss is worth naming as a method failure: each variant was compared only
against `full`, never against the other variants, so three runs each produced
"another CUT-verdict line broke" and the pattern looked like confirmation. Two
of the three numbers contradict that reading and the contradiction was sitting
in data already collected.

**`ros2-control`** is the first skill where the pre-measurement found a place
the model is **reliably wrong** rather than a place it is already right, and
that changed what the run was for. 70 lines to 46, with one line *added*.
`naked` 0.679 vs `full` 1.000 on the shipped body.

Asked cold why an active `diff_drive_controller` ignores `/cmd_vel`, sonnet
correctly diagnoses a `Twist`/`TwistStamped` mismatch and then, **4 times out of
4**, prescribes `use_stamped_vel` — a parameter that does not exist. Verified
against the install before acting: `diff_drive_controller_parameters.hpp`
declares 23 parameters and none is that; `diff_drive_controller.hpp` has a
single `Subscription<TwistStamped>` and no plain-`Twist` path; the string
appears nowhere under `/opt/ros/jazzy/`. The skill said nothing about it. A
symptom row naming the `TwistStamped`-only subscription and warning off the
invented parameter was added **before** the sweep, since ablation can only
measure lines that exist — and it measured **KEEP at q=0.050** (`naked` 0.00,
`full` 1.00, `ablate` 0.30, n=10).

This is the counterpart to the `ros2-package` finding that content expires.
Content can also be *missing in a way ablation cannot see*: a per-claim sweep
scores the lines that are there and is silent about the confident, repeatable
error sitting where a line should be. The only thing that surfaces it is asking
the model the question cold and checking its answer against the install.

The rewrite followed the compression rules collected after the
`ros2-troubleshooting` failures. Both code blocks were at ceiling and became two
prose paragraphs, the `joint_state_broadcaster` row folded into one of them
rather than being said twice, and section 5 *gained* two causal clauses the
original left implicit — keep the reason, not just the instruction. Tied on all
14 checks at n=8, three slightly better. Detail:
[run notes](./runs/2026-07-29-control-sonnet/NOTES.md).

One check bug worth recording because it is the same shape as before. The
negative check for the invented parameter searched for the string and failed any
answer containing it — including answers naming it *to warn the reader off*,
which is what the skill asks for. `full` read 0/4 while all four answers were
correct. It now fails only when the parameter is prescribed, and was fixed with
`runner.py regrade` against stored answers: 18 of 583 results changed, no re-run,
no spend.

**`ros2-moveit`** produced the highest ratio of load-bearing content measured
here — **five KEEP verdicts at q<0.05 against one CUT** — and went one step
past the `ros2-control` finding. There the skill was *silent* about a place the
model is confidently wrong. Here the skill was **repeating the model's error**.

Jazzy redesigned MoveIt Servo: `moveit_msgs` ships `ServoCommandType.srv`
(`JOINT_JOG=0`, `TWIST=1`, `POSE=2`) and there is no Trigger-shaped servo
service left in the installed `moveit_msgs/srv/`. Asked cold, sonnet prescribes
the removed `/servo_node/start_servo` with `std_srvs/srv/Trigger` **4 times out
of 4** — and this skill's own row said "call the servo start trigger service",
the same dead Humble/Iron interface. The row was rewritten against the installed
`.srv` before the sweep and both its checks came back KEEP: `no_start_servo` at
`naked` 0.00 / `full` 1.00 / `ablate` 0.00, q=0.007.

**A skill can be a liability rather than merely inert.** Ablation cannot see
this: measuring a wrong line only shows whether the model repeats it, and it
does, so the line scores as load-bearing either way. Only asking the model cold
and checking the answer against the install separates "this line is working"
from "this line and the model are wrong together".

`naked` 0.433 vs `full` 1.000 at n=10. The other KEEPs are ordinary technical
content rather than repo-local facts, which is new: missing `joint_limits.yaml`
velocity/acceleration limits (q=0.007), TRAC-IK/PickIK over default KDL
(q=0.033), and the `.hpp` header comment on the code block (q=0.033) — unaided
the model writes the deprecated `.h` spelling three times in four, and since
both headers ship in Jazzy nothing errors and nothing warns. Same silent-
wrongness as the `cv_bridge` header in `ros2-perception`. Detail:
[run notes](./runs/2026-07-29-moveit-sonnet/NOTES.md).

No rewrite was attempted. With five KEEPs and one CUT in 60 lines there is no
ceiling mass to compress, and after the three rejected `ros2-troubleshooting`
rewrites, spending to confirm that was not worth it.

## A `full` score of 1.000 is a statement about the checks, not the skill

Three skills in a row came back at `full` = **1.000** — `ros2-troubleshooting`,
`ros2-control`, `ros2-moveit`. Those are exactly the three whose probes were
written from scratch for this project, by reading the skill and then writing
checks that look for what it says. The four skills with older probes sit at
0.949-1.000 with real misses in them. That is not a coincidence and it is not
the skills getting better.

**A check derived from the file measures whether the model repeats the file.**
The file says X, the model with the file in context says X, the check looks for
X. `full` → 1.000 is close to an identity for that construction, and it says
nothing about whether the answer is any good. It also fails correct answers
worded differently — an answer choosing `BiTRRT` for a stated reason scores as a
miss against a check that greps for `RRTConnect`.

Splitting each of those three suites into checks anchored to something
**outside** the file — a `.srv` that exists in the install, a header that ships
at that path, a script present in this repository — and checks that only echo
the file's own phrasing:

| Skill | Check group | naked | full |
| :--- | :--- | ---: | ---: |
| `ros2-moveit` | install-verified | **0.083** | 1.000 |
| `ros2-moveit` | file phrasing | 0.627 | 1.000 |
| `ros2-control` | install-verified | **0.444** | 1.000 |
| `ros2-control` | file phrasing | 0.833 | 1.000 |
| `ros2-troubleshooting` | install/repo-verified | **0.051** | 0.982 |
| `ros2-troubleshooting` | file phrasing | 0.795 | 1.000 |

`full` is 1.000 in both groups; the groups differ entirely in `naked`. **The
trustworthy half of the comparison is `naked`** — it is what the model does with
no help, and no amount of check-wording bias can inflate it. The install-verified
findings survive intact: the model really does prescribe a removed servo service
4/4 unaided, really does invent `use_stamped_vel`, really does write the
deprecated `cv_bridge`/MoveIt `.h` headers. What does not survive is reading
`full` = 1.000 as "the skill makes the model perfect".

`PROCEDURE.md` now ranks check anchors — a real build or run first, an
install-verified fact second, the file's own phrasing last and flagged as such —
and the status table above carries the install-verified split for the three
affected skills.

### A stub shape that was being scored as a wrong answer

Found in the same audit. Answers rendered as a bare tool call with a shell
argument — `Bash(grep -n -i "tolerance" skills/ros2-moveit/SKILL.md)`, sometimes
followed by a *fabricated* result block citing a line number the file does not
have — were not matched by the stub detector and were graded `False` instead of
ungradable, deflating whichever baseline they landed in. The detector now covers
the bare `Tool(arg)` form and every stored run was regraded: 97 check results
changed across 16 runs, no re-run and no spend. Effect on the headline numbers
was small and only ever moved `naked` up: `ros2-moveit` 0.433 → 0.470,
`ros2-control` 0.679 → 0.696, `ros2-testing` 0.762 → 0.786. Not the explanation
for the 1.000s, which is the check-design problem above.

**`gazebo-sim`** is the first suite written under the check-anchoring rule, and
the first to return **`full` below 1.000**. That is the point of it.

`sdf_parses` hands the answer's XML to the installed `gz sdf --check`. The
grader had to be shown to discriminate first: `gz sdf --check` prints `Valid.`
even for unknown tags, so the exit code says nothing, but it emits
`Warning [...] not defined in SDF` per bogus element — the skill's own blocks
parse clean, the same blocks with `<samples>` misspelled do not. Everything else
the suite looks for was confirmed in the install rather than in the file:
`libgz-sim8-diff-drive-system.so` and friends ship, `gpu_lidar` is a real sensor
type, and `<gz_frame_id>` — absent from the SDF spec, so easy to assume invented
— is used inside `<sensor>` by the shipped `nav2_minimal_tb3_sim` waffle model.

| Check group | naked | full |
| :--- | ---: | ---: |
| anchored to the parser or the install | 0.742 | **0.972** |
| echoing the file's phrasing | 0.500 | 1.000 |

The phrasing group still reads 1.000; the anchored group does not. Same run,
same answers. A check that cannot be satisfied by wording fails about one answer
in six even with the file in context, which is what the earlier three suites
were unable to show.

**No claim cleared q<0.05, and that was not chased.** Two sat at q=0.055 — the
`gz-sim-imu-system` world plugin (`naked` 0.12) and `<gz_frame_id>` (`ablate`
0.25) — and both would probably cross with another top-up. Sampling until a
number crosses a threshold manufactures a result rather than measuring one, so
they are recorded as UNDERPOWERED. Unconfirmed but worth naming: unaided, sonnet
names the IMU world plugin 1 time in 8, bridges `/clock` with `use_sim_time` 2
in 8, and reaches for `ros2 pkg prefix ros_gz_bridge` 1 in 10.

No rewrite was attempted. There is compressible mass on paper, but `sdf_parses`
scores **0.00 with the diff-drive block ablated** against 0.83 with it — removing
the worked SDF example is what makes the model's own SDF stop parsing. That is
underpowered, and it points directly at the block a compression would delete.
Detail: [run notes](./runs/2026-07-29-gazebo-sonnet/NOTES.md).

**`ros2-dev`** has the largest claim count (80, of which 26 are the body and 54
live in `references/`) and is the only skill whose strongest signal is
**behavioural** rather than factual. `naked` 0.600 vs `full` 0.882 — the second
suite in a row where `full` lands well short of 1.000, for the same reason:
these checks cannot be satisfied by repeating a phrase.

The planned blocker turned out not to exist. `rtabmap_ros` was never installed
because RTAB-Map appears once in the whole file, as one of three options in "who
publishes `map -> odom`". The measurable substance is Nav2 and SLAM Toolbox,
both already present.

The anchor is a real index: every plugin-description XML under
`/opt/ros/jazzy/share`, **233 registered class names**. A plugin string is in
that set or it does not exist here. Verified discriminating —
`nav2_mppi_controller::MPPIController` is present, the skill's own
counter-example `mppi_controller::MPPIController` is not. **And it found nothing
wrong**: 9/9 naked, 8/8 full. Section 3 opens with "the single most common
startup-killing error is dropping the package prefix", and on this model that
error does not occur. The section targets a failure mode the target model no
longer has.

What does move is what the agent does *before* writing:

| Check | naked | full |
| :--- | ---: | ---: |
| asks for footprint / inscribed radius | 1/7 | 5/7 |
| asks which drive type | 1/7 | 5/7 |
| asks who will publish `map -> odom` | 0/7 | 5/7 |
| sanity-checks odometry before tuning AMCL | 1/7 | 7/7 |
| cites the shipped `nav2_params.yaml` | 0/9 | 5/10 |

Asked cold to "set up Nav2 and tune it", sonnet writes a full parameter file
immediately. With the skill it asks first, five times in seven. That is the §1
gate working, and it is the clearest measurement of a **disposition** rather
than a fact anywhere in this project — as well as the reason `full` is 0.882:
with the file in context the agent still fails to ask about a third of the time.

No claim cleared q<0.05; the closest was the lifecycle row at q=0.198, and it
was not chased. No rewrite was attempted: this file's remaining value is
concentrated in prose whose whole job is to make the agent stop and ask, which
is precisely the content the `ros2-troubleshooting` rewrites destroyed by
keeping instructions and dropping reasons. Detail:
[run notes](./runs/2026-07-29-dev-sonnet/NOTES.md).

**`ros2-microros` is out of scope.** Neither `micro_ros_agent` nor
`micro_ros_setup` exists in apt for Jazzy — only peripheral packages
(`micro-ros-msgs`, `micro-ros-diagnostic-bridge`) — so measuring it would need a
multi-repository source build. Excluded by instruction rather than left as
pending work.

## The efficiency axis rests on an assumption that had never been measured

Every cut in this project has been justified as "the model already does this
unaided" — a real, tested claim. But the *reason to bother cutting at all* is
a second, separate claim that was never itself tested: that leaving inert
content in also costs something on the effect axis, not just in tokens. On
2026-07-28 that assumption was checked directly: `evals/variants/ros2-perception/bloated.md`
takes the verified `ros2-perception` body and adds five paragraphs of
plausible, on-topic, but genuinely untested filler (general node hygiene,
a generic debugging workflow, general performance notes) — +85% by length
(43 → 80 lines), with every already-tested line left character-for-character
identical. Run through all 19 checks across all 6 probes at n=8 on sonnet
([run](./runs/2026-07-28-perception-bloat-test/)): **19/19 checks scored
identically, 8/8 = 8/8 on every one.** Average per-cell API cost was not
measurably different either ($0.0169 vs $0.0152 — noise, not a real gap).

Scoped claim, not a general one: one skill, one model, one style of filler
(readable, plausible, on-topic, generic-advice-shaped), at +85% on a 43-line
base. It does not show bloat is free at every scale — `ros2-troubleshooting`
at 119 lines or `ros2-dev` at 191 could plausibly behave differently, and
genuinely irrelevant or contradictory padding was not tested. What it does
show: the strong version of "cut it, it's hurting correctness" is not
supported by this evidence, at this scale, on this model. The remaining
grounds for cutting inert content are real but different ones — token cost at
scale, and every stale-reference bug this session found living in content
nobody was reading closely because it wasn't earning its place — not "it
measurably degrades the answer," which was the framing every prior cut in
this project implicitly leaned on without checking.

Interim measurements are deliberately not published. An earlier round of this work
produced a plausible conclusion from a single run that a controlled re-run then
disconfirmed; publishing partial results invites exactly that error to spread
before it can be caught.

## Before measuring a skill: is it even runnable here?

The effect axis needs the skill's packages actually installed — a skill whose
first instruction is "read the installed defaults" cannot be measured where those
defaults do not exist. Re-checked on the eval machine 2026-07-28, after Nav2,
Gazebo, ros2_control, MoveIt and the perception stack were installed:

| Runnable now | Blocked until installed |
| :--- | :--- |
| `ros2-core`, `ros2-package`, `ros2-troubleshooting`, `ros2-testing`, `ros2-perception`, `ros2-dev`, `gazebo-sim`, `ros2-control`, `ros2-moveit` | `ros2-microros` (`micro-ros-agent` has no apt package — needs the `micro_ros_setup` source build) |

Re-check with `ros2 pkg prefix <pkg>` rather than trusting this table — it is a
snapshot of one machine.

How the runs are set up and re-run: [`README.md`](./README.md).
