# Claude final release review: workflow-value study (read-only)

Claude Code, Opus 5.5 High. Checkout `[HOME]/Development/claude-ros2-team/codex`, branch
`codex/workflow-value`, HEAD 5fab133 plus the uncommitted report/evidence files.

I read:
- `RESULTS.md`, `ratings/RECONCILIATION.md`, `AUDIT.md`;
- the README/CONTRIBUTING diffs, the `ci.yml` diff and `value-final-validation.json`;
- the control summaries.

I made no model calls, ran no ROS or test suites, changed no code and edited no ratings.

**Verdict: no blockers to opening a new PR (no merge, no tag).** The accepted state is
conditional on the new PR's CI being green, including the new seed-0 oracle-control step (see N1).

## The two reciprocal corrections

1. **"Fidelity is not exactly equal."** **Accepted.**
   - Cell 02's unsupported blanket cleanup claim is a real fidelity defect.
   - Leading with equal correct artifacts and no established gain, then applying the frozen
     one-pair/mixed rule to the remaining differences, is more faithful than my "essentially
     equal" wording. My reconciliation's category preference is preserved as a record, and I
     withdraw it as the headline.
2. **No subtraction of the 120/180 s windows.** **Accepted.**
   - Those windows include real probe work: node start, sleeps and publishes. The idle
     fraction was not measured.
   - My "excluding the stall, pack was not faster in two pairs" was an unmeasured
     counterfactual and should not be published.
   - The report's formulation is correct: it describes the stalls, pack's extra turns and output,
     and the bounded probes, with no adjusted timing score.
3. **Interface tests described per fixture, not as a general ROS norm.** **Accepted.** My
   ROS-practice remark was uncited and is correctly omitted.

**No remaining substantive disagreement** on the report's claims.

## Checks performed

| Area | Result |
| :--- | :--- |
| Product unchanged | `git diff 1227c3d` over `skills/`, `hooks/`, `.claude-plugin/`, `CLAUDE.md`, `scripts/`, `tests/`: empty; plugin version 0.1.2 |
| Frozen evaluator | All 30 `FROZEN.json` hashes match the current working-tree bytes. The 36 pre-model controls therefore apply to the code being published. |
| Controls | `controls/summary.json` matches the reported 3 accepted / 30 rejected / 3 ungradable. `crash_tests` also sets `needs_review`, because the injected crash makes colcon exit 3 and both mutant runs count as incomplete. This is exactly the declared "mutant-only crash → no kill + review" rule, not a bug. |
| Report support | Checked against `summary.json` and cell evidence: 6/6 artifacts per cell; wall −30.7/−40.1/−63.6%; fresh input −12.1/+6.6/+5.6%; output +42.5/+6.4/+4.1%; API estimate +15.6/+11.0/+2.4%; overhead rule not met. Also verified: cell 01 exit 143 in the task notification; zero clarification requests or human follow-ups; the cell 02 daemon timing; cell 05's non-owned stop; the Low call at 17:06:21 with two read actions. "Pack thermal and power use … owned process groups" correctly excludes the range pack cell, which used a timeout-bounded CLI script. |
| Audit honesty | `AUDIT.md` states that masks are not complete process isolation, and that `env -i` drops `EVAL_RUN_TAG`, so an empty tag-based leftover list does not prove cleanup. It discloses the cross-cell domain-87 daemon as a residual-process confound, and says the study does not establish independent runtime environments or a causal time advantage. It proposes containment for future studies without retrofitting this trial. No exhaustive isolation or causal-gain claim was found in RESULTS, the READMEs or AUDIT. |
| Ratings preservation | `ratings/CLAUDE.md` and `ratings/CLAUDE-RECONCILIATION.md` are byte-identical to my coordination files; `CODEX.md` is identical to Codex's. |
| Privacy | Scan of `results/2026-09-25` found no username, email, hostname, credentials, thinking or signature. The only hit is my own reconciliation sentence naming the `sk-ant` pattern: a false positive. |
| Colcon discovery | `results/COLCON_IGNORE` covers the 18 evidence `package.xml` files. |
| Links | 30 Markdown files (READMEs, CONTRIBUTING, `evals/workflow_value/**`): no broken relative links |
| CI paths and dependencies | Covered below. |

**CI detail.**
- **Unit job.** It runs `workflow_value/test_runner.py` and `test_oracle.py`. Without ROS, the
  `Controls` class skips, and the pure tests (including the output-inside-workspace guard) need no
  ROS.
- **ROS job.** It adds `ros-jazzy-ament-cmake-gtest` and `ros-jazzy-rosidl-default-generators`,
  and runs `WV_ORACLE_CONTROLS=1 WV_SEEDS=0` controls. In that container:
  - `grade.py` falls back from the absent `/tmp/…venv` to the apt `colcon` on `/usr/bin`;
  - the probe uses `sys.executable`;
  - `rclcpp`, `std_msgs` and `rclpy` come with ros-base.
- **Validation.** `value-final-validation.json` shows all 16 local commands at return code 0.

## Nonblocking notes (do not rewrite the frozen trial)

- **N1. The new CI step is unproven in CI.** Its first run happens in the PR, on apt pytest and
  colcon in the container; local runs used the venv. The logic and bytes match the passing local
  controls, but a container-specific failure must be fixed and re-reviewed before merge. It must
  not be silently skipped.
- **N2. compileall reaches evidence.** CI's `compileall … evals/workflow_value` also compiles
  model-written sources under `results/`. It passes today, but a future evidence file with a
  syntax error would fail CI for non-product reasons. Consider `-x '/results/'` in a later change.
- **N3. Wording nit.** `evals/workflow_value/README.md` says the runner "verifies isolation".
  Suggested wording: "verifies the mount-mask/private-/tmp preflight (not process isolation)",
  matching AUDIT. It is documentation for future runs, not a data claim.
- **N4. Carried-forward grader limit** (already disclosed earlier, never triggered in this study):
  `copy_project` follows symlinks, so a dangling symlink would raise rather than produce an
  ungradable verdict. The runner records a missing verdict. It does not affect these data.

## Current-code bugs

**None found that invalidate data or require a fix before the PR.**

The daemon escape and residual process are infrastructure weaknesses. They are disclosed for
future studies and correctly not patched into this frozen trial.

## Independent conclusion

The publishable claim is bounded and supported:
- In one small interface-migration workflow (3 pairs, Opus 5.5 High), both conditions produced
  correct, independently verified artifacts.
- Verification reports were supported except for one pack-side blanket cleanup claim.
- The interface-test compliance difference is ambiguous and at most one pair.
- The pack runs were faster, with confounds, and cost slightly more on the API estimate.
- No added correctness or reliability benefit, and no causal speedup, is established.
- Keeping 0.1.2 unchanged is the correct action.

Open the PR; merge only after green CI and owner decision.
