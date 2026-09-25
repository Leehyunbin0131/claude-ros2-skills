# Independent review and reconciliation

The independent [Codex rating](CODEX.md) was saved before Codex read the actual
[Claude Opus 5.5 High rating](CLAUDE.md). Both are retained unchanged apart from
publication redaction. Claude then read Codex's rating and supplemental evidence
and wrote a [reciprocal reconciliation](CLAUDE-RECONCILIATION.md). These reviewer
calls are distinct from the six fresh test-model sessions and are not included
in trial cost/timing.

| Packet | Cell | Condition / variant |
| --- | --- | --- |
| A | 03 | Pack / thermal |
| B | 04 | Baseline / thermal |
| C | 05 | Baseline / power |
| D | 06 | Pack / power |
| E | 01 | Baseline / range |
| F | 02 | Pack / range |

Packets hide condition names and supplied instruction bodies, but checker paths,
Skill-like actions and embedded task paths still reveal conditions/cell IDs.
Codex operated the calls and already knew conditions. Neither reviewer claims
perfect blinding. Cross-packet process observations further expose ordering.

## Resolved and retained differences

| Issue | Independent ratings | Reconciled treatment |
| --- | --- | --- |
| Build, actual tests, Python/C++ runtime | Both supported all six | Unchanged: all six substantiate these observations; independent artifact grades are a separate dimension. |
| Cell 01 exit-143 detail | Both unsupported in the limited packet | Supported by the original non-thinking task notification, now published in cell 01 conversation evidence. This corrects a packet omission, not the task model's answer. |
| Cell 02 “stopped everything” | Codex unsupported; Claude probably contradicted | Unsupported blanket claim, with probable contradiction from later process listings/timing. Node-child cleanup supported. No retained parent/tag proof, so no confirmed daemon attribution. |
| Interface-package tests absent in five cells | Codex: one literal rule gap per cell; Claude: zero under runtime-behavior reading | Keep both interpretations. Ambiguous compliance issue. Only cell 02 adds interface tests, so the stricter interpretation favors pack in one pair only. Other rules satisfied. |
| Cell 05 stops pre-existing domain-87 daemon | Claude explicitly flags non-owned stop; Codex's first note only flags cleanup weakness | Include the non-owned action and residual-process confound. Do not invent a project rule, failed artifact or treatment advantage from it. |
| Actual interventions | No request/block/timeout seen; both noted packet omissions | Original non-thinking progress contains no clarification requests; fresh wrappers supplied no human follow-ups. Six complete High sessions; Low interruption is separate. |

Both agree on the product decision: **keep 0.1.2 unchanged; no expansion or
trimming justified by this study; no established added correctness/reliability
benefit; no causal speedup claim**. Before another timing study, predeclare and
validate process containment against children that clear the environment.

Claude's reconciliation preferred the “equal primary outcomes / no observed
benefit” category. Codex retains the explicit qualification that fidelity is not
exactly equal: one pack cell has an unsupported cleanup claim. The report leads
with equal successful **artifacts**, then applies the frozen one-pair/mixed rule
to remaining differences. This preserves the actual defect rather than erasing
it as “essentially equal”; both readings lead to the same product action.

Claude also proposed subtracting the 120/180-second backgrounding thresholds to
explain hypothetical no-stall speed. Codex does not use that counterfactual:
those intervals include useful probe execution, so their entire duration is not
measured idle time. The report describes observed cleanup stalls and bounded
probe practices without an adjusted timing score. Similarly, it describes the
fixture's absent interface-test infrastructure without asserting a general ROS
norm about which packages need tests.

## Evidence details

Cell 02's window is 17:01:12–17:03:43 local. PID 256186 starts at 17:03 and follows
its node PIDs 256146/256147. Cell 01's own domain-87 daemon PID 250945 was killed
before 17:00:05. Graders use domains 225–227, and the Low call starts at 17:06:21.
This is strong circumstantial evidence, not direct retained parentage. Later
observations are cell 04 action 9 and cell 05 action 16; cell 05 action 20 stops
the daemon. See [session times](../session-times.json) and [audit](../AUDIT.md).

The original ratings include more fine-grained factual/advisory claims than the
report's build/test/runtime/cleanup families. No single aggregate score is
computed from different numbers of prose claims. Advice about user shells,
external binaries or DDS old/new type matching is not upgraded into observed
verification.
