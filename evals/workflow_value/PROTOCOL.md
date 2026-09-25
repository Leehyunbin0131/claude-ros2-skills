# Workflow usefulness study: interface migration

This protocol is written before the first evaluation call. It evaluates the
shipped **0.1.2 pack**, including its SessionStart protocol, against no pack.
It does not measure skill prose alone. No product change is made before data.
The existing release-acceptance records remain unchanged.

## Question and scope

Does the pack improve artifacts, verification fidelity, or effort when a capable
model changes an existing ROS 2 Jazzy interface and its Python and C++ consumers?
This workflow was selected because `ros2-development` claims to support interface
changes and downstream verification. Three parameterized variants of this one
workflow are not a representative sample of ROS development or three independent
application domains. Hardware, micro-ROS, and full application bringup are excluded.

## Conditions and inputs

Six fresh Claude Code sessions use `claude-opus-5-5`, effort `high`, without a
fallback or inherited review conversation. Run sequentially:

| Cell | Variant | Condition |
| --- | --- | --- |
| 01 | 0: range | baseline |
| 02 | 0: range | pack |
| 03 | 1: thermal | pack |
| 04 | 1: thermal | baseline |
| 05 | 2: power | baseline |
| 06 | 2: power | pack |

Each receives byte-identical task and project source/documents within its pair.
The runner also supplies the same empty `colcon-defaults.yaml` and generated-file
`.gitignore`, and commits these initial files in a new local fixture repository.
The ignored `.colcon/` state is generated later, not committed project content.
The workspace has three packages: a ROSIDL message, an ament_python consumer, and
an ament_cmake C++ consumer. Both consumers have existing tests and public
`normalize` helpers. Migrate a reading to an SI-unit field and add `valid`:
valid readings pass through and invalid readings produce NaN. Existing helper
interfaces, node entrypoints, and topics are documented project contracts.
A normal CONTRIBUTING file gives all project rules equally: clean-checkout CI,
regression tests, source-only edits, and changelog maintenance. No requirement is
reserved for the pack condition and no user prompt names a skill.

Each workspace is built from the old source before the session. The initial
shell has Jazzy and this workspace sourced, as the prompt states. This permits
ordinary stale-consumer mistakes but does not guarantee stale artifacts:
rebuilding the same installation can update it in place. No package rename or
assumed DDS type-hash failure is part of the task.

The pack is exported outside the workspace. The corresponding empty directory
exists in baseline. Only the treatment is passed to `--plugin-dir`. Natural skill
selection is observed, never required for artifact success. No credit is given
for our checker, a preferred command, or an exact answer format.

Tools, settings, timeout (1800 seconds), and local dependencies are identical.
Model cells use domains 221–223 and graders use 225–227. These are distinct and
within the documented Linux domain range for the default ephemeral ports
([Jazzy documentation source](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Concepts/Intermediate/About-Domain-ID.rst)).
Memory, synced skills/plugins, external MCPs, and host instructions are excluded.
A mount namespace masks repository copies, controls, prior cells, transcripts,
and host instruction sources while preserving authentication. Each cell gets a
private `/tmp`; only the predeclared Python runtime is exposed read-only there.
The agent runs as the original UID without authority to remove the masks.
Preflight must verify this before a model call. The pack, workspace source, and
protocol/runner/oracle are hashed. Cells never overwrite previous attempts.

This is contamination control, not a security sandbox: network, process table,
and unmasked host paths remain available. Audit paired tool calls/results for
outside solutions or pack retrieval in baseline. An externally contaminated or
incorrectly delivered cell is invalid and retained, not silently counted as a
model failure or dropped. Correct infrastructure before a labeled replacement;
never tune task/rubric/product using a replacement's desired outcome.
The CLI prompt and wrapper/mask paths remain visible in process arguments in
both conditions; this can also trigger CLI guards against broad process kills.
Both conditions also expose the ownership tag, effort variable, and empty
`ROS_STATIC_PEERS` in their environment. Pair identity (task/project hashes,
model/effort, settings and dependency versions) is checked before the second
model call of each pair.

## Independent grading

The grader does not import or execute pack checks. Rebuild the final source in a
new directory with only the Jazzy underlay, then evaluate:

1. All three packages build; installed interface contains the new fields and
   excludes the old field.
2. Both consumers' tests actually execute without failure or skips substituting
   for behavior coverage.
3. Both installed nodes produce the specified readings and NaN from an
   independent publisher. Runtime checks are bounded and clean up owned PIDs.
4. Candidate regression tests accept an independent reference implementation and
   reject two compiling/importable implementations: one ignores `valid`; the
   other incorrectly applies the old unit conversion to the new field. Both
   consumers must reject both mutations. Require real assertion failures, not
   missing results, build errors, or test-runner crashes. The existing public
   helper boundary enables mutation.

Before any model call, for **each** variant, validate the reference solution and
negative controls: unchanged starter, interface-only migration, missed Python
consumer, missed C++ consumer, C++ node bypassing its helper, valid-only tests,
invalid-only tests, and vacuous regression tests. A harness failure blocks calls
until fixed. Product/task/rubric changes after the freeze require a new declared
study. The clean copies retain legitimate project-root source/configuration
files as well as `src/`; generated build/install/log/cache directories are excluded.
Additional controls ensure exceptions/crashes do not count as assertion-based
mutation kills, and a legitimate inline C++ helper that the instrumenter cannot
replace is reported as ungradable, rather than as a candidate defect.
An assertion kill requires a completed mutant run (colcon exit 0 or 1), a test
that passes the independent reference, and an assertion failure rather than an
exception, missing-result placeholder, or crash. A mutant-only timeout or crash
counts as no assertion kill and requires analyst review; it is not silently
converted to a pass. An incomplete instrumented reference or instrumentation
build failure makes the cell ungradable for this dimension. Invariant failures
across all instrumented modes are disclosed and require review.

Record analyst-assessed project-rule violations separately from automated flags
and diffs. Normal build/install outputs are
expected; creating them is not a forbidden generated-file edit. Count intentional
manual edits or using installed/generated files as the submitted implementation,
not every changed build byte. Judge necessary dependency changes on their merits.

Split the final report into verification claims. Classify each as supported,
unsupported, or contradicted, using paired action/output evidence after the last
relevant edit. Valid incremental rebuilds count; a fresh clean build is required
only to support an explicit clean-build claim. The external clean oracle is a
separate dimension. Record undisclosed artifact failures and explicitly admitted
verification limits. Runtime success does not prove whole-system correctness.

Codex and Claude independently rate claims and rules before reconciling. Hide
condition labels/pack names where feasible; tool behavior can still reveal them,
so do not claim perfect blinding. Publish disagreements and resolutions. An
analyst's defect/correction list is **not** observed human intervention. Separately
record actual clarification requests, blocked sessions, and timeouts. Do not
fabricate user corrections for these unattended sessions.

## Cost and decision rules

Report per cell: actual model/effort/CLI, wall time, turns, uncached input,
cache creation/read, output tokens, and API-reported cost estimate if available.
For the pairwise cost rule, uncached input means `input_tokens` plus
`cache_creation_input_tokens`; report those two raw counters and
`cache_read_input_tokens` separately as well. Missing usage is unavailable,
not zero. A pair with missing usage cannot satisfy the token-based rule.
Subscription billing is not inferred from that estimate. Prebuild and external
grading time are excluded from model wall time. Prompt cache warmup, unequal
order at n=3, build caching, and service latency limit time comparisons. There
is no significance test, representative benchmark claim, or equivalence claim.

- Equal artifact/fidelity outcomes and similar cost: no observed benefit in this
  task; do not expand the skill. Trimming is a hypothesis, not proven improvement.
- Equal outcomes and >25% extra uncached input or wall time in **all three pairs**:
  descriptive overhead without observed benefit. Diagnose from actions; a trim
  or narrower trigger needs fresh predeclared follow-up variants before claiming
  improvement. Timing alone remains noisy.
- Baseline defects or false/undisclosed verification claims avoided by treatment
  in at least two pairs: descriptive value on this workflow only.
- Treatment worse on primary outcomes in at least two pairs: highlight harm and
  diagnose before changing content.
- Mixed/one-pair differences: inconclusive; no skill change justified by this
  study alone. Crossing decision categories is reported rather than flattened
  into one score.

Preserve every attempt and failed check. If usage ends, retain available data,
continue analysis alone, and mark missing cells/review as incomplete; do not
replace Opus with another model without a new explicit declaration.
