# Delivery, action and evidence audit

The primary study has six completed High cells, ordered exactly as in the
[frozen protocol](../../PROTOCOL.md). The single interrupted Low call is
[excluded and retained](../../AMENDMENTS.md). There were no replacement High
cells. Product and frozen evaluator hashes remained unchanged throughout the
High calls; different source commits reflect the recorded effort amendment,
not different task/product/oracle bytes.

## Delivery and contamination

All six init events report `claude-opus-5-5`; the runner passes `--effort high`
and `CLAUDE_CODE_EFFORT_LEVEL=high`. Effort is the requested CLI setting, not a
separately measured amount of model reasoning. Tool inventories and built-in
skills match. Baselines contain no ROS skills; treatment inventories contain
all three shipped ROS skills, the real SessionStart hook returns the exact
protocol, and all three naturally invoke `ros2-development`. Treatment calls
execute the bundled test-results checker. These observations confirm delivery,
not benefit.

All three pair gates match task/source hashes, CLI/dependency versions, settings,
model/effort and frozen sources. The real namespace preflights pass. Paired tool
calls show workspace/package inspection, local dependency inspection, source
edits, builds, tests and runtime probes. No WebFetch, external solution retrieval,
baseline pack retrieval or use of another cell's source is observed. A thermal
cell unsuccessfully tries the masked `~/.colcon/defaults.yaml`. Process-table
queries expose current wrapper/mask paths, which the protocol already disclosed;
no solution text is obtained from them.

The masks are **not complete process isolation**. All models start clean build
shells with `env -i`, which also drops `EVAL_RUN_TAG`. A tag-only empty leftover
list therefore does not prove complete cleanup. The domain-87 ROS daemon with
PID 256186 is still visible in cell 04 action 9 and cell 05 action 16. Its start
time (17:03 local) and PID sequence align with cell 02's runtime CLI queries;
this attribution uses commands/timing, not a retained ownership tag. Cell 02's
final “everything” cleanup claim is broader than its checks of two node PIDs.
Cell 05 later stops the domain-87 daemon (action 20).

This is a disclosed residual-process confound for model runtime/cost comparisons.
No leaked sensor publisher, leaked source solution or wrong runtime values are
observed. Artifact grades remain separate clean builds with independent
publishers in domains 225–227. The six task observations are retained, but this
study does **not** establish fully independent runtime environments or a causal
time advantage. Before another timing study, predeclare stronger per-cell
process containment and test an `env -i` daemon escape; do not silently repair
this completed study or fabricate replacement results.

Models sometimes choose their own local domains (87, 173, 222) rather than the
initial 221–223. Cell 04's 173 is outside the recommended Linux ranges cited in
the protocol, although its recorded probe works here. This is another limit on
operational generalization. Grader domains remain 225–227. No real robot,
hardware driver or motion command was used.

## Actual interventions and self-corrections

The fresh model sessions receive one task each and no human follow-up or answer.
Their non-thinking conversational text contains no clarification request or
blocked task. All six model sessions complete before the 1800-second limit.
The user's temporary effort change is a study-level intervention with a separate
Low attempt; it is not a correction inside any scored High task.

Cells 01 and 04 have runtime commands backgrounded after 120 seconds; cell 05
after 180 seconds. They inspect or rerun their probes and clean up before their
final answers. These are ordinary self-corrections, not model-session timeouts
or observed human corrections. All conditions discover the nonstandard colcon
venv after trying or checking a system-only PATH; timings include that friction.
Cell 02 corrects a temporary probe's `set -u` incompatibility with Jazzy setup.
Cell 05 records a nonzero path-specific `pkill` cleanup command and then reads
all four per-case outputs. Preserve these unsuccessful attempts with the passes.

## Publication and reproducibility

Published files contain paired tool calls/results, final reports, non-thinking
conversation/task-completion evidence, manifests, submitted source, source diffs,
independent grader logs/XML and control evidence. No raw private session JSONL,
model reasoning, authentication files, installed binaries or generated build
products are published. XML under `candidate/build` is test evidence only.

Local home/worktree/cell paths, username and hostname are replaced with stable
placeholders. Twelve unrelated host process rows are explicitly redacted;
study ROS process rows and failure evidence are retained. Square-bracket
placeholders keep XML attributes parseable; all 300 exported XML files and 96
JSON files passed parser checks before the final review note was added.
Credential-pattern scanning is combined with action review. `original-project-sha256.json` hashes
original captured source; exported text may have path/identifier substitutions,
so those hashes are provenance, not a promise of byte identity after redaction.
Recreate fixtures with the frozen source for an executable fresh workspace.

The 36 oracle controls completed before the first model call: three accepted
references, thirty rejected negative controls and three deliberately ungradable
inline-helper variants. Their `source-snapshot.json` was captured during the
control run; file timestamps predate its start and hashes were verified unchanged
at completion. It is not advertised as a cryptographic snapshot taken at launch.
The frozen manifest was committed before the first model call.
