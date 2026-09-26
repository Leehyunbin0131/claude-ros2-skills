# Design Note: Evidence Tracking and Handoff Workflow

This document records the architectural decisions, discussion rationale, and operational boundaries for evidence tracking and task handoff in `claude-ros2-skills`.

## 1. Context and Philosophy

In accordance with the [Agent Skills standard](https://agentskills.io/home), skills in this repository are structured modular directories containing contextual knowledge, workflow guidance, and executable tools.

This project does not claim to improve the intrinsic code generation capabilities of frontier language models. Instead, it tests an engineering hypothesis: **packaging environment-specific evidence checks and structured handoff records can reduce verification ambiguity and context-transfer overhead between sessions, agents, and human developers.**

Tool functionality (parsers, diagnostics, exit codes, and snapshot hashing) is tested and verified on isolated test fixtures. However, **reduced handoff cost and overall developer productivity gains remain unproven hypotheses.**

Collaborative roles during design and implementation:
- **Codex**: System architecture and CLI implementation.
- **DeepSeek (deepseek-flash)**: Critique, edge-case analysis, and independent contract testing.
- **Gemini 3.8 (gemini-3.8-flash)**: Documentation, protocol refinement, and multilingual synchronization.

## 2. Decision Rationale & Architectural Tradeoffs

The architecture was finalized through technical evaluation between Codex and DeepSeek:

1. **Subprocess Execution Wrapper vs. Caller Execution**
   - *Proposal (Codex)*: Implement an active runner sub-command that executes the target command inside a monitored subprocess.
   - *Counterargument (DeepSeek - Accepted)*: Wrapping arbitrary shell commands, interactive tools, ROS launch environments, and custom permission environments introduces severe fragility (signal handling, TTY allocation, environment inheritance, and security sandboxing complications).
   - *Decision*: Discard the runner wrapper. The caller (developer or agent) executes commands directly using their established shell/tooling conventions and captures the raw log and exit code. The tool records and verifies snapshots without executing or re-running user commands.

2. **Automatic Colcon Dependency Closure vs. Explicit Watch Paths**
   - *Proposal (DeepSeek)*: Automatically resolve colcon package dependency graphs, build trees, and install spaces across multi-package workspaces.
   - *Counterargument (Codex - Accepted)*: Parsing CMake, ament, and Python dependency closures statically or at runtime is error-prone, fragile across diverse ROS distributions, and introduces unnecessary token and runtime cost.
   - *Decision*: DeepSeek withdrew the automatic colcon closure proposal. The tool relies on explicit watch paths (`--watch`, defaulting to `src`). Callers monitoring a build watch `src` only (as builds alter `install/`), while callers verifying an already-built artifact monitor specific built files explicitly.

3. **Snapshot Differences & Incomplete Semantics (DeepSeek Critiques Evaluated)**
   - *Proposal F1 (DeepSeek - Rejected)*: Treat differences between `before` and `after` snapshots as `incomplete` rather than `changed`.
     - *Rationale*: A modification occurring between `begin` and `finish` is an observed modification of watched artifacts during execution. The existing contract classification (`changed: 1`, prefixed with `between-snapshots:`) is preserved.
   - *Proposal F2 (DeepSeek - Rejected)*: Ignore shell environment differences during `inspect`.
     - *Rationale*: Environment variables directly alter compiler flags, ROS domains, DDS middleware, and prefix paths. If an incoming collaborator runs `inspect` in a shell with divergent ROS configuration, reporting `changed: 1` (prefixed with `since-finish:environment:`) correctly highlights that observation conditions differ. The solution is to inspect from the intended shell environment, not to suppress environmental visibility. Environment differences reflect changed context, not code defects.

4. **Decoupled JSON Manifest and Storage Architecture**
   - A standardized directory layout was adopted: `manifest.json`, `command.log`, and `COLCON_IGNORE`, finalized via atomic temporary file replacement.
   - The 16 MiB size limit applies strictly to `manifest.json` and `command.log`. Monitored workspace files are streamed for hashing and have no size ceiling. Full environment dumps are avoided; only relevant ROS configuration keys are recorded.
   - When recording non-exit outcomes (`timeout` or `unavailable`), `--log` is optional; omitting it stores an empty log and sets `log_source: null`. For completed commands (`--exit-code`), `--log` remains strictly required.

## 3. The Evidence Tool Interface

The evidence recording mechanism is an **opt-in workflow tool** located at `<skill>/scripts/evidence.py`. Automatic skill discovery across assistants remains active; only the evidence recording workflow is selective.

For the operational step-by-step procedure, command guidelines, and symlink handling, refer directly to [skills/ros2-development/references/handoff.md](../skills/ros2-development/references/handoff.md).

### Core CLI Contract

```bash
# 1. Initialize recording (returns record_status: "open", exit code 0)
python3 "${ROS2_SKILL_DIR}/scripts/evidence.py" begin \
  --workspace /path/to/workspace \
  --output /tmp/evidence-run-001 \
  --scope "drive_limits regression-test invocation" \
  --command "colcon test --packages-select drive_limits --return-code-on-test-failure --python-testing pytest" \
  --watch src

# 2. Caller execution (caller's own shell/tool)
colcon test --packages-select drive_limits --return-code-on-test-failure --python-testing pytest > /tmp/evidence-run-001/execution.log 2>&1
rc=$?

# 3. Finalize recording
python3 "${ROS2_SKILL_DIR}/scripts/evidence.py" finish /tmp/evidence-run-001 \
  --exit-code "$rc" \
  --log /tmp/evidence-run-001/execution.log

# 4. Inspect recorded evidence
python3 "${ROS2_SKILL_DIR}/scripts/evidence.py" inspect /tmp/evidence-run-001 \
  --workspace /path/to/workspace
```

### Inspect JSON Structure and Exit Codes

`inspect` outputs a JSON structure containing:
- `record_status`: `"consistent"`, `"changed"`, or `"incomplete"`. (`"open"` is returned only by `begin`).
- `declared`: Caller-declared attributes: `command`, `outcome` (`"exited"`, `"timeout"`, or `"unavailable"`), `exit_code`, `log_source`, and `scope` (the caller-defined intent).
- `observed`: Tool-observed states:
  - `watch`: Monitored paths.
  - `changes`: Differences detected, prefixed by `between-snapshots:` (execution interval) or `since-finish:` (post-execution).
  - `reasons`: Diagnostic notes.
  - `environment_provenance`: Summary of parent-shell environment variables captured during `begin`. In `keys_present_at_begin`, "present" indicates only that the environment variable was set (including if empty), not that its value was valid.
- `limits`: Explicit boundary reminders and non-guarantees.

#### Exit Codes for `inspect`
- **`0` (Consistent)**: Monitored files and relevant environment variables match the recorded snapshot; log file is intact.
- **`1` (Changed)**: Files under watched paths or environment variables were modified between snapshots (between `begin` and `finish`) or after `finish`.
- **`2` (Incomplete)**: The directory is missing metadata, was not finalized, log file is missing or altered, `--workspace` is not a directory, or recorded with `timeout` / `unavailable`.

*The `inspect` exit code evaluates artifact consistency only. A command with `exit_code: 1` (a failed test) can still produce a perfectly consistent record (`inspect` returns `0`).*

## 4. Verification Boundaries & Known Limits

1. **Strict Separation of Declared vs. Observed**: Caller-declared results (`command`, `outcome`, `exit_code`, `log_source`, and `scope`) are unverified inputs provided by the caller. Hash records provide no cryptographic authenticity or provenance guarantee for the declared command.
2. **Not an Atomic Filesystem Snapshot**: File scans are performed sequentially; filesystem changes occurring during scanning are not guaranteed to be captured atomically. Monitored inputs should remain idle while recording.
3. **Pre-execution Blindness**: The tool cannot determine whether the command was executed before `begin` was invoked.
4. **Reverted Changes (ABA Problem)**: If a file was modified during execution and subsequently reverted to its exact original byte state, hash comparisons will not detect the intermediate modification.
5. **No Guarantee of Whole-System Health**: An `inspect` status of `0` confirms only that watched files match the snapshot. It does not prove that the robot is operational or free of defects.
6. **No Automatic Graph Crawling**: The tool monitors only explicitly declared watch paths. Dependencies outside declared `--watch` paths (underlays, system packages) are not tracked.
