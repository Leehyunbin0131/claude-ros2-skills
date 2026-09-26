# Evidence Handoff Reference

This reference describes the optional evidence tracking workflow used when preparing a task handoff between sessions, agents, or human developers.

## Purpose

When concluding a task or handing it off, unverified assertions ("tests passed", "package built cleanly") often force the recipient to rerun all checks.

The optional `evidence.py` tool provides a lightweight snapshot mechanism to verify whether monitored workspace inputs and environment variables have changed at handoff time.

- Using this tool does not guarantee freshness, nor does it prove that an agent generates higher quality code.
- It records and compares snapshots; it does not execute or re-run user commands.

## Workflow

### 1. Begin Evidence Capture

Prepare the shell environment and workspace first. The `--workspace` flag identifies the root directory for snapshot relative paths; it does not change the caller's working directory. Likewise, source the intended ROS underlay and overlay before invoking `begin` so the captured parent-shell environment reflects the intended execution conditions:

```bash
# 1. Enter the workspace and source the intended ROS environment
cd /path/to/workspace
source /opt/ros/jazzy/setup.bash

# ROS2_SKILL_DIR is an example shell variable set by the agent to the loaded skill directory.
ROS2_SKILL_DIR="/absolute/path/to/ros2-development"

# 2. Begin evidence capture
python3 "${ROS2_SKILL_DIR}/scripts/evidence.py" begin \
  --workspace "/path/to/workspace" \
  --output "/tmp/evidence-task-123" \
  --scope "drive_limits regression-test invocation" \
  --command "colcon test --packages-select drive_limits --return-code-on-test-failure --python-testing pytest" \
  --watch src
```

- `--workspace`: Absolute root directory of the colcon workspace. Must be an existing directory (passing a non-directory file or non-existent path is rejected as invalid/incomplete).
- `--output`: A fresh directory for metadata and snapshots. Must not be located inside any watched path. A `COLCON_IGNORE` file is created inside to prevent colcon package indexing.
- `--scope`: The caller-declared intent (such as recording a test invocation), not a proven verification claim.
- `--command`: The exact command displayed for human review.
- `--watch`: Paths to monitor relative to workspace root (defaults to `src`). Specifying `--watch` replaces the default completely; list all desired paths explicitly when watching multiple locations.
  - **Watched paths must exist at `begin`**: Specifying a non-existent path causes `begin` to fail.
  - **Watch selection principles**: A build step modifies `install/`; therefore, when recording a build command, watch `src` only. When verifying an already-built artifact during runtime or test execution, watch `src` plus the specific built file (e.g., `install/my_pkg/share/my_pkg/config/limits.yaml`).
  - **Avoid watching entire install trees under `--symlink-install`**: When `colcon build --symlink-install` is used, installation trees frequently contain directory symlinks, which the tool rejects. Narrow monitoring to specific installed files. File symlinks pointing to regular files within the workspace are permitted and hashed by target content.
  - **Keep watched trees idle during recording**: File scans are sequential; avoid writing to watched paths while `begin` or `finish` is capturing snapshots.

*Exclusions: `.git`, `__pycache__`, and `*.pyc` are automatically excluded.*

*Limits: The 16 MiB size limit applies strictly to `manifest.json` and `command.log`. Monitored workspace input files are streamed through cryptographic hashing and have no file size ceiling.*

### 2. Run the Verification Command

The caller executes the command in their own environment. Direct file redirection is recommended:

```bash
colcon test --packages-select drive_limits --return-code-on-test-failure --python-testing pytest > /tmp/evidence-task-123/command.log 2>&1
rc=$?
```

- **Save `rc=$?` immediately**: Capture the exit code right after the command.
- **Do not use `cmd && finish`**: If the command fails, `&&` skips `finish`, losing the failure log and exit code.
- **Avoid `| tee`**: Piping through `tee` without `pipefail` masks non-zero exit codes.

*Note on test verification*: `evidence.py` records command execution facts and snapshot states; it does **not** evaluate JUnit test XMLs or detect zero-test runs. To verify that tests actually executed and passed without silent skips, combine this command with `check_test_results.py --require-test`.

### 3. Finish Evidence Capture

Record the execution outcome and finalize the snapshot via atomic replacement:

```bash
# When recording a completed command execution, --exit-code and --log are both required:
python3 "${ROS2_SKILL_DIR}/scripts/evidence.py" finish /tmp/evidence-task-123 \
  --exit-code "$rc" \
  --log /tmp/evidence-task-123/command.log
```

If execution was blocked or timed out, specify `--outcome timeout` or `--outcome unavailable` instead of `--exit-code`. In these non-exit cases, `--log` is optional; omitting it stores an empty log and sets `log_source` to `null`.

### 4. Inspect at Handoff

The incoming collaborator inspects the evidence directory from their intended environment:

```bash
python3 "${ROS2_SKILL_DIR}/scripts/evidence.py" inspect /tmp/evidence-task-123 \
  --workspace "/path/to/workspace"
```

The inspection outputs a JSON object with keys:
- `record_status`: `"consistent"`, `"changed"`, or `"incomplete"`. (Note: `"open"` is returned only by `begin`, never by `inspect`).
- `declared`: Caller-declared attributes: `command`, `outcome`, `exit_code`, `log_source`, and `scope`.
- `observed`: Tool-observed states:
  - `watch`: Monitored paths.
  - `changes`: List of detected differences, prefixed by phase:
    - `between-snapshots:...`: Differences detected between `begin` and `finish` (recorded execution interval).
    - `since-finish:...`: Differences detected between `finish` and current inspection time.
  - `reasons`: Diagnostic explanation notes.
  - `environment_provenance`: Summary of parent-shell environment variables captured during `begin`. In `keys_present_at_begin`, "present" indicates only that the environment variable was set (including if set to an empty string); it does not validate variable content.
- `limits`: Boundary reminders.

#### Inspect Return Codes
- **`0` (Consistent)**: Monitored files and relevant environment variables match the snapshot; the log file is intact.
- **`1` (Changed)**: Monitored files or environment variables were modified between snapshots (between `begin` and `finish`) or after `finish`.
- **`2` (Incomplete)**: The directory is missing metadata, was not finalized, log file is missing or altered, `--workspace` is not a directory, or recorded with `timeout` / `unavailable`.

*The `inspect` exit code evaluates artifact consistency only. A command with `exit_code: 1` (e.g., a failing test) will still produce an `inspect` exit code of `0` if the record is intact.*

## Handoff Review Principles

When reviewing or receiving recorded evidence:

1. **Stay within the declared scope**: Evaluate the handoff strictly against the caller-declared scope and watched paths. Do not automatically expand a standalone fixture or focused script check into an unrequested full colcon package build or workspace refactoring.
2. **Environment snapshot boundaries**: `environment_provenance` reflects parent-shell variables captured at `begin`. Variables marked unset or `null` in the tool's snapshot shell do not prove that internal subshells or sourced scripts lacked those variables.
3. **Environment differences do not mean source defects**: An environment mismatch (`changed:environment:...`) indicates that the current inspect shell has different ROS configuration or paths than the recording shell. It reflects changed observation context, not a source code bug or robot failure. When environment differences appear, verify whether `inspect` was run in the intended ROS setup.

## Concrete Limits

1. **Declared vs. Observed Distinction**: The command, outcome, exit code, log, and scope are caller-declared inputs. They are not digitally signed or attested by the tool. Observed data is limited strictly to filesystem hashes and specific ROS environment variables.
2. **Sequential Scans (Not Filesystem Atomic)**: File scans are sequential; changes occurring during snapshot creation may result in partial state capture. Keep watched trees idle during capture.
3. **Pre-execution Blindness**: The tool cannot determine whether the command was executed before `begin`.
4. **Intermediate Changes (ABA Problem)**: If a file was altered and restored to its original content before `inspect`, the hash matches. Intermediate changes are not detected.
5. **No Whole-Robot Health Claim**: A return code of `0` confirms only that watched files match the snapshot. It does not establish robot health or functional correctness.
6. **No Automatic Graph Crawling**: Dependencies outside declared `--watch` paths (underlays, system packages) are not tracked.
