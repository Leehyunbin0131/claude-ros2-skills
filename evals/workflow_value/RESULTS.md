# Interface-migration usefulness study — 2026-09-25

**Both conditions completed all three migrations and passed every independent
artifact check. This study does not establish an added correctness or reliability
benefit from the unchanged 0.1.2 pack.** The pack sessions were faster in these
runs, but timing has substantial confounds. A one-pair cleanup reporting issue
and an ambiguous one-pair project-rule difference do not justify expanding or
trimming the skills.

This is three matched variants of **one small workflow**, not a representative
ROS benchmark. It evaluates the full Claude plugin, including SessionStart,
using six fresh **Claude Code Opus 5.5 High** sessions. It is not a Codex model
comparison. The [protocol](PROTOCOL.md) and [source hashes](FROZEN.json) were
frozen before calls. The brief user-requested Low attempt was interrupted after
about 14 seconds when the user returned to High; it is
[preserved and excluded](AMENDMENTS.md), not scored as a failure.

## What was compared

Each task migrates a ROSIDL field and adds `bool valid`, then updates Python and
C++ consumers: return the already-scaled value for valid readings and NaN for
invalid ones. Existing source, README, CONTRIBUTING, task text and dependencies
are identical within each pair. The old workspace was prebuilt and sourced.
Baselines receive no ROS skill pack; treatment receives the unchanged 0.1.2 pack
outside the workspace. No prompt names a skill. All three treatment sessions
naturally selected `ros2-development` and used its results checker, which is
**delivery evidence, not a success criterion**.

The independent grader imports no pack checks. It builds a fresh source copy
with only Jazzy, checks the installed interface, executes consumer tests, probes
both installed nodes with an independent publisher, and checks that candidate
tests pass a reference and assertion-fail both an ignored-validity mutation and
an erroneous old-scale mutation in each consumer.

Before any model call, all **36 oracle controls** behaved as expected: 3 accepted
references, 30 rejected negative controls, and 3 legitimate inline-helper
variants reported as ungradable by the instrumenter. The last category is a
known grader limit, not a bad implementation. See the
[control summary](results/2026-09-25/controls/summary.json) and
[delivery/action audit](results/2026-09-25/AUDIT.md).

## Outcomes

“6/6” covers clean build, installed interface, executed consumer tests, Python
runtime, C++ runtime and mutation-tested regressions. It is not six independent
trials. All six cells are gradable, and no artifact review flag was raised.

| Variant | Baseline cell | Pack cell | Baseline artifacts | Pack artifacts | Build/test/runtime reports |
| --- | --- | --- | --- | --- | --- |
| Range | 01 | 02 | 6/6 | 6/6 | Supported in both |
| Thermal | 04 | 03 | 6/6 | 6/6 | Supported in both |
| Power | 05 | 06 | 6/6 | 6/6 | Supported in both |

Project-rule and report-fidelity review adds qualifications that the artifact
score does not measure:

- **Interface-package tests:** cell 02 alone adds schema/default tests within the
  interface package. Every cell adds meaningful valid/invalid tests in both
  consumers. Codex reads CONTRIBUTING's “every affected package” literally and
  identifies one gap in each of the other five cells. Claude reads “behaviour
  change” as requiring tests in the two runtime consumers and identifies no
  violation. Both interpretations are published; this is an **ambiguous rule
  issue**, not a robust violation-count advantage. These fixtures start without
  interface-package tests; the stricter reading is project-local, not a claimed
  general ROS testing requirement. Even the stricter reading
  favors the pack in only the range pair. Other project rules are satisfied.
- **Cleanup reporting:** cell 02 says it stopped everything, but its evidence
  checks only the two remaining node PIDs. A domain-87 daemon, with a start time
  matching that session, appears in later cells. Final rating: **unsupported
  blanket cleanup claim, with probable contradiction**; daemon parent/tag
  provenance was not retained. The narrower claim that it stopped the two
  node children is supported. No other build/test/runtime report failure was
  found. Cell 01's initially unsupported exit-143 detail is supported by its
  separately retained task-completion notification.
- **Observed actions:** baseline cell 05 later stops that pre-existing daemon,
  which it did not start. This low-impact non-owned process action and the
  residual daemon are disclosed separately from project rules and artifacts.
  This is the only observed cross-cell process side effect, probably running
  from a pack session to a later baseline; daemon ownership remains inferential.
  Ordinary probe hangs and retries are self-corrections. There were **zero
  human task corrections, clarification requests, blocked High sessions or
  model-session timeouts**; the effort change is a separate study amendment.

Codex and actual Claude Code independently rated the same A–F packets before
reading each other's ratings. Blinding was partial: checker commands and some
embedded task paths reveal conditions or cell identities; Codex also operated
the trials. See [both initial ratings and reconciliation](results/2026-09-25/ratings/RECONCILIATION.md).
Do not count an analyst's suggested correction as observed human intervention.

## Time and usage

All cells report model `claude-opus-5-5`, CLI `2.1.281`, with requested effort
`high`. Wall time excludes prebuild and external grading. Fresh input is raw
input **plus cache creation**, not just the tiny raw input counter. API estimates
are list-price telemetry, **not actual subscription billing**. Output includes
reported thinking-token usage; no reasoning text is published.

| Cell | Condition / variant | Wall seconds | Turns | Raw input | Cache creation | Fresh input | Cache read | Output | API estimate USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | Baseline / range | 217.8 | 17 | 22 | 30,612 | 30,634 | 198,787 | 7,823 | 0.4412 |
| 02 | Pack / range | 151.0 | 25 | 30 | 26,911 | 26,941 | 358,975 | 11,144 | 0.5101 |
| 03 | Pack / thermal | 139.7 | 20 | 24 | 24,413 | 24,437 | 250,243 | 9,193 | 0.4451 |
| 04 | Baseline / thermal | 233.1 | 12 | 24 | 22,894 | 22,918 | 225,235 | 8,638 | 0.4011 |
| 05 | Baseline / power | 309.7 | 21 | 28 | 22,960 | 22,988 | 276,888 | 8,374 | 0.4066 |
| 06 | Pack / power | 112.8 | 20 | 22 | 24,242 | 24,264 | 240,404 | 8,717 | 0.4164 |

| Pack change relative to its baseline | Range | Thermal | Power |
| --- | ---: | ---: | ---: |
| Wall time | −30.7% | −40.1% | −63.6% |
| Fresh input | −12.1% | +6.6% | +5.6% |
| Output tokens | +42.5% | +6.4% | +4.1% |
| API estimate | +15.6% | +11.0% | +2.4% |

The baseline runtime scripts hit 120/120/180-second tool backgrounding waits
before cleanup; these account for much of their longer wall time. Pack thermal
and power use direct Python probes and owned process groups. This is a useful
observed action difference, consistent with the pack's instruction to bound
runtime probes, not proof that skill prose caused a repeatable speed increase.
The 120/180-second thresholds include useful probe work as well as waiting;
subtracting their full durations would not measure a valid counterfactual.
Pack sessions used more turns in two pairs and more output tokens in all three.
The same bounded-probe guidance did not ensure complete daemon cleanup. Prompt cache warmup, unequal order at three pairs, the interrupted
Low call, service latency, a nonstandard colcon PATH and a cross-cell daemon all
limit comparisons. No significance or equivalence test is claimed.

The predeclared **>25% extra fresh input or wall time in all three pairs** rule
is not met. Small API-estimate increases do not substitute for that rule. There
is also no two-pair correctness/fidelity advantage or harm. Artifact outcomes show **no observed added benefit on this task**. With one
fidelity defect and ambiguous rule differences, the remaining comparisons fall
in the **mixed/one-pair, inconclusive** category; fidelity is not exactly equal. The supported action is to keep
0.1.2 unchanged and publish the result, not tune or remove skills to make this
same task favor a desired conclusion.

## What this permits us to say

The pack can be selected and used during this concrete downstream interface
migration, and the resulting Python/C++ artifacts work in the tested Jazzy
fixture. A capable baseline also succeeds and checks real test/runtime evidence.
Skills were not necessary to complete these particular tasks. This does not
show that every skill, workflow, model or project can dispense with them.

The next evaluation should target a documented developer failure with a frozen
comparison, not merely enlarge this easy task after seeing its results. Before
any further timing claim, improve and validate process containment against
children that clear their environment. Such a follow-up would be a new declared
study. No product revision is claimed as a tested improvement here.

Physical robots, micro-ROS/MCUs, calibration and full application bringup remain
unverified. This study does not establish general stale-overlay remediation,
DDS old/new type interoperability, external C++ library consumption, or the
benefit of `--packages-up-to` (the agents built all three packages).

## Evidence

- [Machine-readable six-cell summary](results/2026-09-25/summary.json)
- [Delivery, process and publication audit](results/2026-09-25/AUDIT.md)
- [Independent ratings and reconciliation](results/2026-09-25/ratings/RECONCILIATION.md)
  and [actual Claude final review](results/2026-09-25/ratings/CLAUDE-FINAL-REVIEW.md)
- [Local regression check commands and results](results/2026-09-25/local-validation.json)
- Cell actions, final reports, submitted source and independent grader evidence:
  [01](results/2026-09-25/cells/01), [02](results/2026-09-25/cells/02),
  [03](results/2026-09-25/cells/03), [04](results/2026-09-25/cells/04),
  [05](results/2026-09-25/cells/05), [06](results/2026-09-25/cells/06)
- [Pre-model controls](results/2026-09-25/controls) and
  [interrupted Low attempt](results/2026-09-25/interrupted-low/01)

Source hashes refer to the original captures. Published text replaces local
identifiers and redacts unrelated host process rows. Private raw sessions and
model reasoning are excluded. Reproduction instructions are in [README](README.md).
