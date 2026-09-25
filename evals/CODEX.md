# Codex compatibility — 0.1.2

Codex can install this pack as native local skills, alongside the existing
Claude Code support. This is compatibility evidence on Ubuntu 24.04 / ROS 2
Jazzy, not a model-performance comparison or a hardware validation.

## Delivery

`python3 scripts/install.py --agent codex --project /path/to/workspace` installs
all three skills under `.agents/skills`; `--user` uses `~/.agents/skills`.
These are the [documented Codex locations](https://learn.chatgpt.com/docs/build-skills).
The default agent remains Claude, so existing installer commands keep working.
Each Codex copy preserves the source frontmatter and embeds the shared
`CLAUDE.md` protocol before the skill body. It arrives on skill activation,
not through a session-start hook. No AGENTS.md or Codex configuration is changed.
Resource/script bytes are shared, and the same installer ownership, conflict
and rollback checks apply to both targets.

Source skill examples now resolve a shell variable from the loaded skill's
absolute path instead of requiring Claude's skill-directory substitution.
The ROS Python implementations and shared protocol text are unchanged. The
earlier [Claude acceptance](development/RESULTS.md) applies to its recorded
source snapshots; no new Claude behavioral run is claimed for the path wording.
The attempted Claude peer review hit the session limit before reviewing this
change. Codex completed the implementation and review alone, as authorized.

## Checks performed

- **22 offline installation tests passed:** project/user targeting, preserved
  user/global instructions, coexistence, conflicts before writes, symlink/path
  protection, rollback and executable installed helpers. User scope was tested
  with a temporary home substitute; normal user configuration was not modified.
- **Native discovery passed** using Codex CLI `0.155.0-alpha.16.4` and its local
  app server. All three project skills were enabled and discoverable from both
  the project root and a nested directory, including a path containing spaces.
  Run `python3 tests/test_codex_discovery.py` to repeat this optional, no-model
  check. It skips when the Codex CLI is unavailable; it is not a CI prerequisite.
- All three rendered skills passed the skill frontmatter validator. Existing
  diagnostic, test-result, installer-runner and evaluation-harness regressions
  passed. CI continues to run the real colcon/ament and synthetic ROS suites.

## Actual Codex observations

Two fresh `codex exec` sessions used project installation, the bundled CLI's
default model, `--ignore-user-config`, ephemeral sessions, workspace-write
sandboxing with network access, and a 540-second deadline per call. No explicit
model/effort override was provided; the JSON event stream did not record the
resolved model identity, so these cases must not be attributed to a named model.
ROS was sourced and the existing isolated pytest 7.4.4/colcon environment was
available. The task prompts did not name a skill. Both sessions read their
installed SKILL.md (including the shared protocol), executed the bundled checker
at its installed path, and left the installed pack unchanged.

| Task | Observed result | Independent check |
| :--- | :--- | :--- |
| Wheel-speed library and meaningful regression tests | Selected `ros2-development`; old behavior failed five cases, corrected library passed ten; built and exercised the installed library | Fresh rebuild, installed API checks, reference implementation and three faulty implementations [passed](development/results/2026-09-25-codex/tests/verdict.json) |
| Live IMU/TF diagnosis | Selected `ros2-troubleshooting`; observed pass, fail and inconclusive for three synthetic streams | Matrix-based oracle matched all statuses; publisher identities, heartbeat, TF and simulation-time settings were [preserved](development/results/2026-09-25-codex/imu/verdict.json) |

The IMU session first encountered a read-only ROS log directory, then received
no messages in its initial sandboxed probes. It moved logging into the workspace
and eventually set `FASTDDS_BUILTIN_TRANSPORTS=UDPv4` and
`ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` for its own probes. The second setting
**broadens discovery**. Its final diagnosis passed, but this is not a successful
demonstration of localhost-only sandbox connectivity. Do not treat widening
discovery as a required install step or a general workaround. The graph and
permission boundary must suit the user's environment; unavailable data remains
inconclusive. The failed probes and environment changes remain in the evidence.
An unavailable pre-build `ament_python` prefix lookup in the library session is
also retained; the later build and installed-library checks succeeded.

Evidence directories contain the original prompts, sanitized tool commands with
their outputs, final answers, source/payload hashes, independent verdicts and
unchanged source artifacts. [Library evidence](development/results/2026-09-25-codex/tests/manifest.json)
and [IMU evidence](development/results/2026-09-25-codex/imu/manifest.json) are
separate from the previous Claude runs. Failed probes inside each session were
not removed. Private model reasoning and authentication data are excluded.
The containing results directory has COLCON_IGNORE, so generated packages do
not enter a user's normal colcon discovery.

These sessions are narrow observations, with shared local runtime and filesystem
visibility, not a hermetic benchmark. No speed, reliability improvement, or
equivalence to Claude follows. User-wide model activation, other Codex versions,
remote/cloud hosts, full Nav2/MoveIt/Gazebo applications, physical robots and MCU
firmware remain unvalidated. micro-ROS is discoverable but still experimental.
