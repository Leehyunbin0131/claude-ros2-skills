# Claude reconciliation: workflow usefulness study (Opus 5.5 High)

Claude Code, Opus 5.5 High. This note is written after both independent ratings were saved.
Neither `claude-value-independent-ratings.md` nor `codex-value-independent-ratings.md` is
modified.

**Sources read (read-only):**
- `codex-value-independent-ratings.md`;
- `value-rater-map.json`: A=03 pack, B=04 base, C=05 base, D=06 pack, E=01 base, F=02 pack;
- `value-session-times.json`;
- `results/2026-09-25/{AUDIT.md, summary.json}`;
- `cells/*/conversation-evidence.json`;
- `AMENDMENTS.md`;
- `interrupted-low/01/{manifest,actions}.json`.

I made no ROS or model calls and edited no code.

**Pairs (seed: baseline / pack):** 0 range E(01)/F(02); 1 thermal B(04)/A(03);
2 power C(05)/D(06).

**Correction to my earlier freeze review.** The frozen grader domains are 225–227, not the
231+seed I suggested before Codex's correction. I accept the recorded values.

## Issue by issue

### 1. E/cell 01 "exit 143": agree, now supported

`cells/01/conversation-evidence.json` contains a non-thinking `system/task_notification`
(status `failed`): "Background command 'Run both monitor nodes…' failed with exit code 143". It
pairs with the backgrounded E14 command. My U rating and Codex's become **S by supplementary
evidence**. The original ratings stay as they were saved. This resolves a packet omission; it does
not correct the model's answer.

### 2. Clarification requests and human follow-ups: agree

- **Checked:** all six `conversation-evidence.json` files. The event types are only
  `assistant_text` and `system/task_notification`, with no user events. No non-final assistant
  text contains a question.
- **Result:** no clarification requests, no blocked sessions, no model-session timeouts, no
  human follow-ups.
- **Not interventions:** tool-command backgrounding (cells 01/04 at 120 s, cell 05 at 180 s) and
  first-attempt PATH failures are self-corrections.
- **The Low interruption** is a study-level intervention outside every scored High task.
  It is correctly excluded and retained.

### 3. F/cell 02 cleanup claim: agree with Codex's final wording

Wording: the blanket "I stopped everything I started, by PID" is **unsupported**, with a
**probable contradiction**; provenance is not proven. My independent label was "probably C".
I accept Codex's phrasing, because there is no retained parent/tag evidence (`env -i` drops
`EVAL_RUN_TAG`).

The circumstantial case is stronger than "timing alone", and the report may state these facts
without claiming proof:

- **Start time:** the domain-87 daemon (PID 256186) started at 17:03, inside cell 02's model
  window (17:01:12–17:03:43).
- **PID order:** its PID follows cell 02's surviving node PIDs (256146/7).
- **Cell 01 excluded:** cell 01 killed its own domain-87 daemon (250945) before 17:00:05.
- **Grader excluded:** the grader uses domains 225–227.
- **Low call excluded:** it started at 17:06:21 and ran only two file-reading actions.

The narrower F sub-claim (two orphaned nodes found and stopped, F22–F23) is supported.

### 4. C/cell 05 stopping the pre-existing daemon: agree

Label it a low-impact, non-owned process action. It is not a project-rule breach and not a
failed implementation.

Add one sentence to the report: this is the only observed cross-cell side effect, and it runs
from a pack cell's residual process to a later baseline cell. It belongs with the
residual-process confound, not with either cell's task outcome.

### 5. Interface-package tests: agree on publishing both readings, with one addition

- **Readings:** my primary reading (runtime behaviour, 0 violations) and Codex's literal reading
  (one gap in each of A–E) are both defensible. Publish both, label the five missing
  interface-package tests an *ambiguous compliance issue*, and do not force agreement.
- **Pair outcome:** under the literal reading, pack is ahead in 1 of 3 pairs only (F vs E). The
  other two pairs tie, because pack cells A and D also lack interface tests. So there is no
  robust advantage, and no claim like "5 vs 2 violations".
- **Addition:** state that a message-only rosidl package commonly has no package-local tests in
  ROS practice. The literal reading is a stricter project-local interpretation, not a claimed ROS
  norm. F's interface test (exact field types plus the `valid` default) is a legitimate extra
  check, not something the rubric proves was required.

### 6. Verification fidelity overall: agree, with one framing correction

- **Agreement:** all six substantiate their build, test and runtime reports with paired outputs
  after their last edits. After item 1, the only remaining fidelity defect is F's blanket
  cleanup claim, which falls in a pack cell. So there is no fidelity benefit, and one pair
  mildly favours baseline on fidelity.
- **Framing correction (disagreement with "mixed/inconclusive" as the headline):** on the
  predeclared *primary* outcomes (artifact and fidelity) the data fits the first frozen rule
  best: equal outcomes, **no observed benefit on this task**. "Inconclusive" belongs only to
  the one-pair secondary differences (interface-test reading, F's overclaim).
- **Why it matters:** labelling the whole study "mixed" suggests competing signals where the
  primary outcomes are simply equal. The resulting action is identical either way.

### 7. Cost and time: agree on the numbers and on no causal claim; the report needs the mechanism and its limits

**Verified from `summary.json`:**
- Pack wall time was lower in all 3 pairs: −30.7%, −40.1%, −63.6%.
- Fresh input (`input_tokens + cache_creation_input_tokens`): −12.1%, +6.6%, +5.6%.
- API cost estimate: +15.6%, +11.0%, +2.4%.
- Output tokens: pack higher in 3/3 (+42%, +6%, +4%).
- Turns: 25 vs 17, 20 vs 12, 20 vs 21.
- The frozen overhead rule (>25% extra fresh input or wall time in all pairs) is **not met**.

**Where I want the report to go further than "confounded":**
- **The wall gap is almost entirely a stall.** All three baseline cells (01, 04, 05) hit a
  120–180 s tool timeout on the same pattern: `kill -INT $P1 $P2; wait` on background jobs.
  Background jobs in a non-interactive shell ignore SIGINT, so the `wait` hangs. The pack cells'
  runtime probes (03, 06, 02) were all bounded, using `timeout …`, `setsid` with signals to the
  process group, or `timeout 120 bash probe.sh` with a trap. None stalled.
- **Without the stall, pack was not faster in two pairs.** The stall (120 s) exceeds the whole
  wall gap in pairs 0 and 1 (67 s, 93 s). Excluding it, pack would not have been faster there.
  Pair 2's gap (197 s) is roughly the 180 s stall plus a retry. Pack cells also used more turns
  in 2/3 pairs and more output tokens in 3/3.
- **The observed behaviour matches the pack's newest instruction.** The pack's shared protocol
  now says "Bound runtime probes with a timeout and keep the PID or process group…". The behaviour
  difference is consistent with it in 3/3 pairs. Report this as a **descriptive,
  hypothesis-generating observation**, not a benefit or a causal effect. It is not a
  predeclared decision criterion. The confounds are n=3 on one workflow, unequal order, cache
  and latency variance, the Low call's cache effects, venv PATH friction, and the residual daemon.
- **The same instruction did not ensure complete cleanup.** F still left a daemon and overclaimed.

### 8. Cleanup practice difference: report it descriptively, not as a benefit

This point is in neither independent rating's scoring.
- **Baselines** found their processes by name-filtered `ps | grep` and then killed explicit
  PIDs. B and E verified ownership by command line; C used a path-scoped `pkill -f`, which may
  match its own shell (Codex's point), and stopped a non-owned daemon.
- **Pack cells** killed only PIDs or process groups they had recorded.
- **Why this is not a benefit:** the protocol has no cleanup dimension, and scoring baselines
  against the treatment's own instruction would be circular.
- **What to publish:** one factual paragraph, including F's leak, so readers see both sides.

### 9. Decision: agree, with wording

- **Product:** keep 0.1.2 unchanged.
- **Skill content:** no expansion. No trimming justified by this study either; the overhead rule
  is not met, and "trimming is a hypothesis" per the frozen rule.
- **Before any new timing study,** predeclare stronger containment:
  - a per-cell PID namespace, so leftovers die with the cell and cells cannot see each other's
    process tables;
  - a cell-reserved ROS domain range, with other domains or daemons blocked or checked;
  - a post-cell residual-process check that does not rely on `EVAL_RUN_TAG`, which `env -i`
    drops.
- **Proposed headline:** "On this interface-migration workflow, both conditions produced
  correct, independently verified artifacts in all 3 pairs, with essentially equal verification
  fidelity. We observed no benefit on primary outcomes, and the overhead criterion was not met.
  One-pair differences are inconclusive. Timing and cost are descriptive only."

## Blockers to publishing the bounded evidence

**None found.**
- My scan of `results/2026-09-25` (8.2 MB) found no username, email, hostname, `sk-ant`/Bearer,
  thinking or signature strings.
- The interrupted Low attempt is retained and excluded, as `AMENDMENTS.md` records.

**Corrections I consider necessary in the planned report** (report text only; no code or reruns):
1. Update E's exit-143 claim to supported, citing the task notification. Keep both original
   ratings visible.
2. Use the primary-outcome framing from item 6 rather than a whole-study "mixed" label.
3. Add the stall mechanism and its limits (item 7): stall ≥ gap in two pairs; the pack used
   more turns and output.
4. Add the cleanup-practice paragraph (item 8) and the cross-cell daemon sentence (item 4).
5. State the F provenance facts (item 3) as circumstantial, not proven.
6. Note the ROS-practice context for interface-package tests (item 5).

**Remaining open disagreement:** only the primary interpretation of the interface-test rule. It
is published as a sensitivity analysis, not resolved. No merge or tag is implied by this
reconciliation.
