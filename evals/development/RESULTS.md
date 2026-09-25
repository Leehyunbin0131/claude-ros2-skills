# Release acceptance — 2026-09-25

This is operational evidence for version **0.1.1** on Ubuntu 24.04 / ROS 2
Jazzy, with Claude Code **Opus 5.5, high effort**. It is not a performance
benchmark. The original three tasks completed under both installation methods;
the baseline also completed every task. These observations establish neither
improvement nor equivalent reliability.

The [protocol](PROTOCOL.md) declares tasks, oracles, isolation, timeouts and
failure handling. The original product and input freeze is at commit `fb0aeeb`
and [freezes/fb0aeeb.json](freezes/fb0aeeb.json). The owned-process cleanup
follow-up uses `b93a594` and [freezes/b93a594.json](freezes/b93a594.json). Executable/input hashes
were checked before every paid acceptance call; the prompts were not revised
in response to outcomes.

## Original acceptance outcomes

Each entry represents **one fresh session**. The manual condition uses seed 1,
which changes names, scan thresholds and the assignment of IMU statuses. The
baseline and plugin use seed 0. These are release cases, not a matched estimate
of a treatment effect. Both conditions have the same built-in skills available.
The plugin condition loads a minimal export of the shipped files with
`--plugin-dir`; the manual condition runs the real `install.py --project`
installer. This exercises plugin hooks/skill paths and project installation,
not marketplace network download/update or model behavior under a persistent user-wide installation. A separate CLI-only installation smoke below tests marketplace resolution from the local candidate checkout.

| Case | Baseline, seed 0 | Plugin, seed 0 | Manual, seed 1 |
| :--- | :--- | :--- | :--- |
| Installed sensor package, launch/YAML and actual callbacks | [Accepted](results/2026-09-25/scan-baseline-0/verdict.json) | [Accepted](results/2026-09-25/scan-plugin-0/verdict.json) | [Accepted](results/2026-09-25/scan-manual-1/verdict.json) |
| Ratio-preserving wheel speeds and tests that reject faulty implementations | [Accepted](results/2026-09-25/tests-baseline-0/verdict.json) | [Accepted](results/2026-09-25/tests-plugin-0/verdict.json) | [Accepted](results/2026-09-25/tests-manual-1/verdict.json) |
| IMU gravity expressed through TF, with no fixture changes | [Accepted](results/2026-09-25/imu-baseline-0/verdict.json) | [Accepted](results/2026-09-25/imu-plugin-0/verdict.json) | [Accepted](results/2026-09-25/imu-manual-1/verdict.json) |

The independent scan oracle rebuilds the submitted source, launches its installed
files and checks exact callback counts, missing/invalid ranges, effective YAML,
an explicit override and a second namespace. The math oracle exercises the
installed public API, then runs the submitted tests against an independent
reference and three faulty functions. The IMU oracle uses separate matrix-based
observations and monitors publisher identities, process liveness, heartbeat and
`use_sim_time`; all original scenes remained intact.

Two earlier loading smokes, [plugin](results/2026-09-25/smoke-plugin/verdict.json)
and [manual](results/2026-09-25/smoke-manual/verdict.json), passed. They verified
all three skill registrations, exact protocol transport, natural selection of
`ros2-development` and actual script execution at the installed path. A skipped
behavior test was inconclusive despite a passing style test. That smoke prompt
explicitly asks to distinguish the tests: it proves delivery and path resolution,
not independently improved judgment.

Every original installed-pack case selected its intended skill without the task
naming it: development for scan/math, troubleshooting for IMU. Each ran a bundled
checker and reported its observed result. The managed pack files remained
unchanged. Baselines had no pack skills or external user plugins in the inventory.

## Runtime cleanup follow-up

Review of successful artifacts found a separate problem: scan baseline and
plugin sessions attempted process-name `pkill`, which the CLI guard refused.
The IMU plugin session also attempted `pkill -f "ros2 topic"`; its tool result
only reports exit 144. The fixture remained intact, but that does not establish
which processes the command affected. The first artifact outcomes are retained;
they were not evidence that cleanup was suitable for a developer's shared host.

Codex and Claude agreed to add a short shared-protocol instruction: bound probes,
retain owned PIDs/process groups, stop only those processes, and preserve existing
publishers and TF. The instruction covers both development and diagnosis. A
misleading missing-ament-results clause was also removed from ordinary test
failure output; test-verdict logic did not change. Existing gate and installation
regressions passed after that edit.

Four fresh runtime sessions were declared before their outcomes, with the same
oracles plus review of attempted cleanup commands. Name-based kill attempts are
unacceptable even if a tool guard refuses them. Tracked child processes/groups
and bounded probes are acceptable.

| Cell | Artifact oracle | Cleanup action review | Seconds, descriptive |
| :--- | :--- | :--- | ---: |
| `scan-plugin-2` | [Accepted](results/2026-09-25/scan-plugin-2/verdict.json) | [No name-pattern kill attempt](results/2026-09-25/scan-plugin-2/review-audit.json) | 404.0 |
| `imu-plugin-2` | [Accepted](results/2026-09-25/imu-plugin-2/verdict.json) | [No name-pattern kill attempt](results/2026-09-25/imu-plugin-2/review-audit.json) | 80.0 |
| `scan-manual-3` | [Accepted](results/2026-09-25/scan-manual-3/verdict.json) | [No name-pattern kill attempt](results/2026-09-25/scan-manual-3/review-audit.json) | 248.0 |
| `imu-manual-3` | [Accepted](results/2026-09-25/imu-manual-3/verdict.json) | [No name-pattern kill attempt](results/2026-09-25/imu-manual-3/review-audit.json) | 104.4 |

All four follow-up traces met the declared cleanup requirement. The manual scan
session initially recorded the `setsid` wrapper PID instead of the actual group.
It found the two owned launches through their open, uniquely named log files,
confirmed their groups and stopped those groups, then recorded the group leader
from inside the new session and repeated the probes. Its first duplicate-node
measurement is not the evidence reported as success. This recovery is preserved;
the observation does not imply correct process tracking on every first attempt.

After those calls, final review moved the cleanup paragraph below the existing
"Run what you wrote" explanation, so "This is the single highest-value line"
still refers to executing the changed artifact. That is the **only shipped
instruction/diagnostic difference from the follow-up-tested bytes**: paragraph order, with the
wording unchanged. Exact protocol-delivery and install tests passed again.
No new model evidence is claimed for the reorder. [FROZEN.json](FROZEN.json)
records the final source; the earlier frozen source remains separately available.

This is a small trace observation, not proof that an instruction prevents harm.
The math acceptance is tied to `fb0aeeb`; it was not re-run as a model task for a
later message-only change. All original and follow-up attempts are preserved;
there were no rejected, timed-out or ungradable model cells in this declared set. Repairs and failed probes within a session remain in its action trace.

## Marketplace installation smoke

A separate [CLI-only smoke](results/2026-09-25/marketplace-smoke.json) used a
fresh isolated `CLAUDE_CONFIG_DIR`: `claude plugin marketplace add` from the
local candidate checkout, then `claude plugin install
claude-ros2-skills@claude-ros2-skills --json`. Both succeeded; the list reports
version 0.1.1 enabled. All 19 shipped payload files match the source hashes,
including the three skills, hooks and protocol. Running the installed
SessionStart hook produced the exact current protocol. No model call or change
to the user's normal Claude configuration was involved.

This checks `marketplace.json`'s relative source resolution and actual cached
installation, not GitHub network fetching or upgrade from a prior marketplace
installation. The installed repository occupied 42,361,952 logical bytes
(about 40.4 MiB) at this check, including historical evaluation material and the
new evidence; it is larger than the minimal payload used in model cells.

## Evidence and review

The [artifact index](results/2026-09-25/index.json) lists every recorded cell.
Each directory includes:

- A manifest with model/effort, CLI and package versions, source/input/payload
  hashes, seed, deadline and timestamps; the original prompt is `TASK.txt`.
- `actions.json`: public tool inputs and their paired outputs, in order.
  `session-summary.json` includes the final answer, routing, delivery checks,
  turns, elapsed time and reported token usage. These costs are descriptive;
  no speed or token-efficiency conclusion follows from them.
- Independent verdicts and package-grading logs, plus unchanged submitted
  source or diagnosis artifacts and their SHA-256 hashes for reproduction.
  `results/COLCON_IGNORE` keeps the recorded packages out of normal workspace
  discovery. A real `colcon list` saw eight package records, including duplicate
  names, before the marker and none after it; evidence must not become a
  developer's accidental build input.

Model reasoning, signatures and authentication data are excluded. Transcript
paths and account labels are replaced by `$WORKSPACE`, `$OUTPUT`, `$REPOSITORY`,
`$HOME`, `$USER` and `<UUID>` where applicable. Artifact source bytes are kept
unchanged; paths in transcripts are explanatory placeholders, not runnable
shell assignments. Reviewer notes summarize conclusions, not private reasoning.

Positive and negative oracle controls passed on seeds 0, 1, 2 and 3 before the
corresponding calls. See [control logs](results/2026-09-25/controls) and the
[validation inventory](../VALIDATION.md) for the other local regressions. CI runs
the deterministic and synthetic checks without making model calls.

The [first new-head CI run](https://github.com/Leehyunbin0131/claude-ros2-skills/actions/runs/36092877217)
passed the code and link jobs but exposed a TF integration-test precondition
error. A fresh checker received no frames within a 0.2-second lookup; its correct
INCONCLUSIVE result contradicted the test's expected FAIL. The test now observes
a known chain and the missing chain in the **same invocation**, allows middleware
discovery, and asserts both observations. The separate empty-domain test retains
the short deadline and expected INCONCLUSIVE. Both targeted tests pass locally;
the product and all frozen paid-run inputs are unchanged. This failed CI run is
retained, and release acceptance still requires all jobs at the updated head.

Concrete build/test/runtime claims were checked against paired outputs. One
out-of-contract remark in the math manual final answer is partly inaccurate: it says
non-finite inputs pass straight through. Reproduction gives `(inf, 1, 1) ->
(nan, 0)` and `(nan, 1, 1) -> (nan, nan)`, while `(1, nan, 1) -> (1, nan)` does
pass through. The prompt explicitly requires finite
inputs and a positive cap, and those outcomes passed; the original answer is
preserved with this correction rather than treating its untested prose as proof.
The scan plugin follow-up also misdescribes the old `r <= limit` predicate as
counting NaN: that comparison is false, and positive infinity is excluded by a
finite limit. Readings below `range_min` and negative infinity are real old defects; readings above `range_max` count only if the limit also admits them.
The new finite filtering was exercised; the descriptive mistake remains visible
in the preserved answer with this correction. The IMU manual follow-up says
orientation fields are all zero, but its echo shows an identity quaternion with
`w=1`; gyro and covariance entries are zero. Orientation behavior was outside
the requested gravity test. This descriptive error is also retained and corrected.

Codex and Claude Code (Opus 5.5 High) reviewed the same final product, report
and evidence. Their [joint decision](results/2026-09-25/joint-review.json) accepts
the candidate for the declared Ubuntu 24.04 / Jazzy scope, **conditional on green
CI for the pushed head**. Neither claims general improvement or physical safety.
The review verified both original and final manual traces, frozen hashes,
artifact hashes, installation evidence and the disclosed model prose errors.

## Isolation and evidence limitations

- This is not a hermetic filesystem/network sandbox. Repository copies,
  instructions, private coordination, sibling workspaces and recognized
  reference directories were masked, but loose shared `/tmp` files and Claude
  task-output directories can remain visible. Every cell's Read/Glob/Grep/Bash
  actions were audited; no successful cross-cell or outside pack/fixture/evaluation retrieval was observed.
- Operator intervention is recorded: after scan-plugin completed, its loose
  probe, YAML backup and launch log were moved under the masked output root.
  The next math session had started but did not retrieve them. The model had
  disclosed the probe only, not the two other files. After the original batch,
  the manual math task's old-code scratch was also preserved under its masked
  output. The manual scan follow-up's loose probe and logs were also relocated
after its session; the following IMU session did not retrieve them. The plugin
scan follow-up removed its own named scratch scripts and backup. Per-cell
`scratch-audit.json` and `review-audit.json` distinguish model cleanup from
operator moves.
- The prompt was passed in CLI argv. Process inspection exposed a masked
  harness path and showed the model it was in a harness. It also caused the
  scan `pkill` guard refusal. Neither the refusal nor successful fresh traces
  demonstrate how an ordinary interactive session would behave on a robot.
- Elapsed times include preflight and tool waits; test counts differ because
  agents wrote different tests. Neither count is a measure of added value.
- No physical robot, MCU firmware, real calibration or full Nav2/MoveIt/Gazebo
  application was validated. Downstream interface consumers, stale-overlay
  remediation and `--packages-up-to` advice lack independent behavioral tests
  here. `ros2-microros` remains explicitly experimental and MCU-unverified.

Historical ladder prompts, transcripts, grading thresholds and scores are
unchanged. They apply to earlier protocol text and are not current-release
performance results. A community release can present the tested installation,
diagnostic distinctions and concrete workflow observations; it cannot promise
universally better development or safe physical operation from these cases.
