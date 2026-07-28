# Verification status

**This file is the record of what is finished.** It is the first thing to read
before working on a skill, and the last thing to update after — the final stage of
a verification run writes its own row here, so the record cannot drift from the
runs behind it.

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

| Skill | Status | Evidence |
| :--- | :--- | :--- |
| `ros2-core` | VERIFIED (sonnet re-check) | [2026-07-26 ablation](./runs/2026-07-26-core/NOTES.md) + [confirmation](./runs/2026-07-26-core-confirm/NOTES.md) + [2026-07-28 sonnet re-check](./runs/2026-07-28-core-sonnet/) + [confirmation](./runs/2026-07-28-core-sonnet-confirm/) |
| `ros2-security` | VERIFIED (sonnet re-check) | [2026-07-27 ablation](./runs/2026-07-27-security/NOTES.md) + [2026-07-28 sonnet re-check](./runs/2026-07-28-security-sonnet/) + [confirmation](./runs/2026-07-28-security-sonnet-confirm/) |
| `ros2-testing` | VERIFIED | [2026-07-27 ablation](./runs/2026-07-27-testing/NOTES.md) + [confirmation](./runs/2026-07-27-testing-confirm/NOTES.md) |
| `ros2-package` | VERIFIED | [2026-07-27 ablation](./runs/2026-07-27-package/) + [final confirmation](./runs/2026-07-28-package-final/) |
| `ros2-perception` | VERIFIED | [2026-07-28 ablation](./runs/2026-07-28-perception/) + [confirmation](./runs/2026-07-28-perception-confirm/) + [final](./runs/2026-07-28-perception-final/) |
| `ros2-dev` | IN PROGRESS | — |
| `ros2-troubleshooting` | IN PROGRESS | — |
| `gazebo-sim` | IN PROGRESS | — |
| `ros2-control` | IN PROGRESS | — |
| `ros2-moveit` | IN PROGRESS | — |
| `ros2-microros` | IN PROGRESS | — |

Status vocabulary — a skill is only VERIFIED when **both** axes have passed:

| | Meaning |
| :--- | :--- |
| IN PROGRESS | not yet measured, or measured on one axis only |
| VERIFIED | effect **and** efficiency, at n≥5, with the run linked |
| DID NOT CLEAR | measured and failed — recorded, not hidden |

**No skill has completed verification.** Results are published here per skill as
each one clears both axes — not before, and including the ones that fail.

`ros2-core` is the first skill to clear both axes and shows what a finished row
looks like. Measured at n=8 across 558 cells: the body takes the pass rate from
**0.54 to 0.94** (p<0.0001) pooled over 20 mechanical checks, five lines were cut
as things the model already does unaided (50 → 45 lines), and three behaviours
turned out to be stated redundantly — where removing any single line looks
harmless and removing the group breaks the behaviour.

The confirmation run that closed the efficiency axis caught a sixth candidate cut
as a false negative: single-ablation Δ=0 said "cut," but removing it for real and
re-measuring at higher n showed the reduced body performing *worse than doing
nothing* on the behaviour that line taught (naked 1.00 vs cut 0.40, p=0.0017). The
line was restored before shipping. Detail: [ablation](./runs/2026-07-26-core/NOTES.md),
[confirmation and correction](./runs/2026-07-26-core-confirm/NOTES.md).

Two findings from that run are about the pack rather than the skill:

- **The always-loaded 28-line `CLAUDE.md` protocol did not change generated code
  at all** — 0.56 vs 0.54 against no context, p=0.73.
- **Contamination was looked for and not found.** Adding the protocol on top of
  the body scored 0.92 vs 0.94, p=0.67. Individual checks drop, the aggregate does
  not.

`ros2-security` is the second skill verified, and closes both axes in a single
run: 0.60 → **1.00** (p<0.0001) pooled over 14 checks across 6 claims, and every
ablatable claim came back load-bearing — zero cuts, so the 52-line body is
already the smallest one the harness can find. The same false-negative shape
`ros2-core` hit showed up here too, on the architecture sentence naming which RMW
implementations carry DDS-Security: Δ=+0.25, p=0.467 at n=8 looked like a cut,
and a targeted top-up to n=16 turned it into a real KEEP (p=0.007). Same
contamination check, same result — 1.00 vs 1.00, p=1.00. Detail:
[ablation](./runs/2026-07-27-security/NOTES.md).

`ros2-testing` is the third, and the first run to test more than deletion: every
claim was also tried alone (`only:<id>`, does one line by itself already produce
the effect) and the whole body was tried with its sections reordered
(`reorder:`, does *where* a rule sits change anything). Position turned out to
be a clean null — 52/52 either way, p=1.00, not underpowered, both sides already
at ceiling. Addition turned out to reinforce the deletion story rather than add
a new one: the two redundancy groups' members each reproduced their own effect
alone *and* each measured Δ=0 when singly removed — sufficient alone, unnecessary
once a sibling is present, the two-sided proof of redundancy neither prior run
had. Repeats were kept to n=4 by request, the floor where Fisher's exact can
resolve anything at all — most claims needed a top-up to n=8–16 as a result, and
one showed the same "ablated score below naked" shape investigated twice before;
this time it was noise, not a third hidden regression, but it still took the
top-up to tell the two apart.

Two lines were cut (78 → 76), and getting there surfaced a new failure mode,
distinct from the false negatives the first two runs caught: single-ablating
each cut candidate showed what looked like a real, if borderline, effect — and
both dragged down a check neither one owns. Both symptoms turned out to be
artifacts of the specific state single ablation produces (one row missing from
a six-row table, a shape nothing ships) rather than of the claims themselves —
measuring the real candidate (both rows gone, the actual 76-line body) made
both vanish: 104/104 across all 13 checks, p=1.00 against the pre-cut body.
**When more than one cut is on the table, the state that matters is the one
that will actually ship, not any single-claim reading along the way.** Detail:
[ablation](./runs/2026-07-27-testing/NOTES.md),
[confirmation](./runs/2026-07-27-testing-confirm/NOTES.md).

`ros2-package` is the fourth, and the first to grade one probe against real
ground truth instead of a regex: `pkg-build-ground-truth` actually runs
`colcon build` on the model's generated files in a scratch workspace and checks
`ros2 pkg executables` for the node, rather than pattern-matching the answer.
Against that ground truth the original 126-line, 29-claim body had two real
content gaps, not just cuttable lines: nothing named `package.xml`'s
`<export><build_type>ament_python</build_type></export>` tag or `setup.cfg`'s
`script_dir`/`install_scripts` keys, and generated packages built but the node
was undiscoverable — both confirmed missing against installed packages under
`/opt/ros/jazzy/`, then added as pointer-style corrections and verified at
n=16 (`export_build_type` and `setup_cfg_script_dir` both p<0.002 naked vs
full). Fifteen lines were cut as things the model already produces unaided
(a full CMakeLists.txt/setup.py/rosidl reference block was deliberately kept
regardless of per-clause ceiling effects — structural completeness for a
"copy this shape" reference has value a per-line naked/full test can't see),
taking the body to 16 claims.

Closing the efficiency axis took a failed confirmation attempt before a
correct one. An ad hoc analysis script used to check the confirmation run
tallied per-check results keyed on `(probe, check)` instead of `(probe,
condition, check)`, so `naked`-condition failures silently pooled into the
`full` numbers — producing false regression reports against two of the cut
candidates (a `ModuleNotFoundError` symptom-table row and a "one concern per
package" rule), which were restored on the strength of those reports.
Tracing it down (comparing answer length as a first, discarded hypothesis,
then reading the one flagged failure cell directly and finding the
supposedly-missing content present in the answer) pointed straight at the
scoring bug. Re-run through the project's own `analyze.py` — which has always
keyed correctly — on a fresh n=8 sweep: the reduced 16-claim body still beats
naked significantly on the check the restored lines were meant to drive
(`iface_location_cause` 1/8 naked vs 6/8 full, p=0.041), and every check
compared against the pre-revert 18-claim body shows no significant
difference (p≥0.2, most ≥0.47) — both lines were cut back out. **A hand-rolled
substitute for the project's own analysis tooling reintroduced exactly the
kind of unverified conclusion this whole project exists to catch; use
`analyze.py`, not an inline script, even for a quick confirmation.** Detail:
[initial ablation](./runs/2026-07-27-package/), [content-gap
additions](./runs/2026-07-27-package-additions/), [the miscored confirmation
run](./runs/2026-07-27-package-confirm/), [corrected final
confirmation](./runs/2026-07-28-package-final/).

`ros2-perception` is the fifth, and the cheapest ground truth yet: a C++
compiler. Every snippet the model writes is put through `g++ -fsyntax-only`
against the installed Jazzy headers in about two seconds, no workspace
required — and unlike a regex, a compiler cannot be fooled by code that looks
right. That mattered immediately, because the domain's headline trap is a
header rename that regex grading would have scored either way: Jazzy ships
`cv_bridge/cv_bridge.hpp` and deleted the pre-Jazzy `cv_bridge/cv_bridge.h`.
Unaided, the model writes the deleted spelling **7 times out of 8** and the
code does not compile; with the body, 8/8 compile. Pooled over 19 mechanical
checks the body takes the pass rate from **0.70 to 0.99** (p<10⁻¹³).

The efficiency axis produced an unusually sharp contrast between the two code
blocks sitting side by side in the same section. The `pcl_ros` voxel-filter
block measured 8/8 naked, 8/8 ablated and 8/8 full on *real compilation* — the
model reproduces it perfectly unaided — so it was cut, 23 lines gone (65 → 43).
The `cv_bridge` block one heading above it is one of the strongest KEEPs
measured anywhere in this project. Same section, same language, opposite
verdicts, and only a compiler could tell them apart: this is the evidence gap
that made the equivalent call on `ros2-package` a conservative *keep*, now
closed.

A second cut candidate was cut and then put back. The `pointcloud_to_laserscan`
row looked inert on single ablation (Δ=+0.12, p=1.000, naked already 7/8), but
the confirmation run against the actually-reduced body scored it **5/8 — below
the 8/8 that no body at all achieves**. Reading the failing cells showed why:
with its own row gone, the model reaches for the neighbouring rows' framings
(`frame_id`, TF, QoS) instead of the height band, whereas an empty prompt
leaves it free to answer from its own knowledge. A *thinned* table misleads
where an absent one does not — the same interaction that turned the high-CPU
row from an apparent cut at n=4 into a confirmed KEEP at p=0.007 once a top-up
separated it from the naked ceiling. At p=0.20 the regression is not
significant at the n=8 cap, so the row was restored precautionarily rather than
cut on an unresolved reading, and a third run measured the body that actually
ships: 151/152, p=1.000 against the pre-cut body. **A claim can be inert
against no context and load-bearing against the rest of its own table; only the
shipping state distinguishes the two.** Detail:
[ablation](./runs/2026-07-28-perception/),
[confirmation that caught the regression](./runs/2026-07-28-perception-confirm/),
[final](./runs/2026-07-28-perception-final/).

## Every verdict above is haiku-calibrated, and that is not neutral

All five verified skills were measured on `haiku`. A cross-check of
`ros2-perception` on `sonnet` ([run](./runs/2026-07-28-perception-sonnet/))
shows the target model does not merely need *less* — it needs something
**different**, and the two move in opposite directions:

| Check | haiku naked→full | sonnet naked→full |
| :--- | ---: | ---: |
| `cv_bridge` snippet compiles | 0/8→8/8, p=0.0002 | 6/8→8/8, p=0.47 |
| K vs P matrix row | 0/8→8/8, p=0.0002 | 6/8→7/8, p=1.00 |
| depth/colour registration row | 3/8→8/8, p=0.026 | 8/8→8/8, p=1.00 |
| docs-URL convention | 4/8→8/8, p=0.077 | 1/6→8/8, **p=0.003** |
| `ros2 interface show` habit | 4/8→8/8, p=0.077 | 2/6→8/8, **p=0.015** |

The technical facts lose their effect — a stronger model already knows which
header Jazzy ships and which matrix pairs with which topic. The *navigational*
lines gain it. Capability supplies knowledge; it does not supply the
disposition to build a docs URL from a package name, or to check the local
install instead of answering from memory. That is the project's stated
philosophy — corrections point at authoritative docs rather than handing over
answers — receiving its first direct evidence, and haiku-only measurement was
pointing the other way: it ranked the inline `cv_bridge` block the strongest
KEEP in the run and left both pointers as unresolved "unclear".

So the bias in the record has a known direction: **haiku calibration
over-keeps inlined technical facts and under-values navigational pointers.**
Two caveats on the table above — it is one skill, and two `naked` cells
returned empty answers (correctly scored ungradable, so the docs probe is n=6);
assuming both would have passed, `docs_url` still clears at p=0.026 while
`interface_show` falls to p=0.077.

Nothing above is being retracted on one skill's evidence. What is being
recorded is that the verdicts are conditional on the grading model, that
re-checking a verified skill costs about $1.65 and three minutes, and that
`--models sonnet` belongs in the procedure before any further skill is called
finished.

## Re-checking the five haiku-verified skills on sonnet

Following directly from the caveat above: every previously-verified skill is
being re-swept on `sonnet` and re-cut where the evidence supports it, in the
same order they were originally verified. `ros2-core` is done.

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
question a raw comparison invites: haiku's original `full` was 0.94, this
run's first pass came back 0.89 — worse, on a body that had just been *cut*
for redundancy on a stronger model. Every one of the eight `full`-condition
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
Corrected, `full` moved from 0.89 to 0.95 — at or above haiku's 0.94, which is
the more defensible reading anyway: absolute `full` score is not a portable
cross-model quality metric (checks written against one model's typical output
style don't necessarily fit another's), the real signal is the naked-to-full
gap, and that gap still shrank — +0.40 on haiku (0.54 → 0.94, the 2026-07-26
sweep) against +0.21 on the comparable sonnet sweep (0.748 → 0.954), or +0.27
measured on the shipped 43-line body (0.679 → 0.949) — exactly as the
grading-model switch predicted.

A third candidate — the TF2 symbols bullet — read identically (ceiling
everywhere) but **was not cut**. That single bullet bundles the now-redundant
exception-symbol list with a REP105 frame-convention pointer to
`ros2-troubleshooting` that no check has ever measured; deleting the bullet on
the symbol-list evidence would have silently deleted the pointer too. This is
the same shape the project already applies to reference code blocks (kept in
`ros2-package`/`ros2-perception` past the point individual clauses cleared) —
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

**`ros2-security`**, the smallest skill (6 claims), reversed hardest. The
original haiku pass found *zero* cuttable lines — every claim load-bearing,
including a targeted top-up to n=16 to confirm the architecture sentence
survived. On sonnet, three of the six claims (architecture, the SROS2 CLI code
block, the `policy.xml` block) hit `naked=full=ablate=1.00` on **every one of
their 14 owned checks**, at n=8, no exceptions and no UNDERPOWERED reads — the
cleanest signal measured anywhere in this project. Verified past the regex
before cutting anything this size on a security skill: naked policy-XML
answers were pulled and read whole, reproducing the skill's own example
byte-for-byte including nesting the checks don't verify, and all 8 naked
architecture answers named the untested AES-GCM-GMAC cipher suite unaided.
52 lines cut to 13 (architecture, CLI commands, and the policy block all
removed; only the documentation-pointer section survives), confirmed against
the real shipped body: naked 59/60 vs full 68/69, p=1.000 — indistinguishable.
Detail: [ablation](./runs/2026-07-28-security-sonnet/),
[confirmation](./runs/2026-07-28-security-sonnet-confirm/).

This is not evidence the haiku-era verdict was performed carelessly — it
passed every check this project had at the time. It is the starkest
demonstration yet of the caveat two sections up: a "load-bearing, zero cuts"
result is a fact about the grading model, not about the skill, and the two
can point in opposite directions on the same file.

Closing this run also fixed two bugs the confirmation step itself surfaced.
`_sec_policy_profile_node` required `<profile node=...>` with `node` as the
first attribute; sonnet correctly writes `<profile ns="/" node="...">` just as
often, and the order-sensitive regex scored valid XML `False`. And the
tool-call stub detector (see the sonnet-switch caveat above) kept meeting new
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
| `ros2-core`, `ros2-package`, `ros2-troubleshooting`, `ros2-testing`, `ros2-security`, `ros2-perception`, `ros2-dev`, `gazebo-sim`, `ros2-control`, `ros2-moveit` | `ros2-microros` (`micro-ros-agent` has no apt package — needs the `micro_ros_setup` source build) |

Re-check with `ros2 pkg prefix <pkg>` rather than trusting this table — it is a
snapshot of one machine.

How the runs are set up and re-run: [`README.md`](./README.md).
