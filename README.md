<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy skills for Claude Code and Codex" width="100%"/>

**ROS 2 development with evidence that the result works.**

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

**English** | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

</div>

Three skills for **Claude Code and Codex**, targeting **Ubuntu 24.04 / ROS 2 Jazzy**: develop packages,
verify tests and installed behaviour, and diagnose runtime faults. The goal is
less time spent correcting plausible code that was never exercised. This pack
supplies targeted workflows and executable checks, not a replacement for the
workspace's conventions or the installed ROS documentation.

## Quickstart

Choose your assistant. For Claude Code, choose either plugin or manual installation.

**Codex — native skills for an existing project:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# Alternative: install for this user across all projects
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

The [Codex skill locations](https://learn.chatgpt.com/docs/build-skills) are
`<project>/.agents/skills` and `~/.agents/skills` for these two scopes. Choose one
scope to avoid duplicate skill names. Each installed Codex skill includes the
shared [verification protocol](CLAUDE.md), loaded when that skill is used.
No Claude hooks or rules are required. Existing `AGENTS.md`, `CLAUDE.md`, Codex
configuration and unrelated skills are preserved; local edits stop an update.
Start a new Codex session in the target workspace. To select a skill explicitly
in Codex CLI or the IDE, use `$ros2-development` or `$ros2-troubleshooting`.
In the desktop skill picker, select the same skill by name.

Live ROS checks also need access to the intended ROS graph. In a restricted
Codex environment, a denied ROS log directory can be redirected with
`ROS_LOG_DIR` to a writable workspace directory. Discovered topics with no
received messages can reflect sandbox/DDS transport constraints. Keep the
workspace's domain and discovery scope; widening discovery to `SUBNET` is not a
general installation fix. Report unavailable observations as inconclusive.
See the [observed Codex runtime limitations](evals/CODEX.md).

**Plugin — from a Claude Code session:**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Start a new session. A `SessionStart` hook loads the [protocol](CLAUDE.md);
plugin-root `CLAUDE.md` is not automatically loaded on its own. The default user
scope applies to all projects. Prefer a project install when you want it limited
to a ROS workspace.

**Claude Code manual — into an existing project:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --project /path/to/your-workspace
# Alternative: install for this user across all projects
# python3 claude-ros2-skills/scripts/install.py --user
```

The installer copies the three skills and `.claude/rules/ros2-verification.md`.
It preserves existing `CLAUDE.md` files and unrelated skills, refuses to overwrite
local edits, and reports retired skill directories for manual review. Restart
Claude Code afterwards. ROS, colcon and robot drivers are not installed by this
pack; install the dependencies needed by your workspace. For these checks on an
existing Jazzy installation:

```bash
sudo apt install python3-colcon-common-extensions python3-pytest \
  ros-jazzy-tf2-ros ros-jazzy-sensor-msgs ros-jazzy-nav-msgs
source /opt/ros/jazzy/setup.bash
```

Prefer Ubuntu/Jazzy's test-tool versions or a separately verified environment.
The tested Jazzy `launch_testing` plugin fails to start with pytest 9; our
ROS-sourced checks use Ubuntu's pytest 7.4.4. A runner crash is not evidence that
the implementation's assertions failed.

## Skills

| Skill | When it helps | What it adds |
| :--- | :--- | :--- |
| [ros2-development](skills/ros2-development/SKILL.md) | Creating or modifying packages, nodes, interfaces, launch/config and tests | Dependency-aware builds, installed-artifact verification, a check that rejects empty/all-skipped test runs |
| [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md) | A live publisher, callback, TF, IMU or odometry behaves incorrectly | Four executable diagnostics and focused frame, runtime and calibration references |
| [ros2-microros](skills/ros2-microros/SKILL.md) | MCU transport, agent, rclc or message memory work | Source pointers and troubleshooting guidance; **not MCU-validated** |

Both assistants can select a skill from its description. To request it explicitly, mention
its name in your task. Examples:

- “Use ros2-development to add a service to this existing Jazzy package. Build
  its consumers, run the relevant tests, and show that the installed node works.”
- “Use ros2-troubleshooting: `/scan` publishes, but my node's callback never
  fires. Find the incompatible endpoints and verify the correction.”
- “The robot is level but its IMU is mounted upside down. Check gravity using
  the declared TF; distinguish a correct mounting transform from a real error.”

Specify hardware versus simulation and the workspace when known. The agent
should establish genuinely missing robot geometry or existing publishers before
making assumptions about them.

## Verification scripts

Scripts ship with their skill. Resolve `scripts/` from the absolute directory
of the loaded `SKILL.md`, not the current working directory. The examples use
`ROS2_SKILL_DIR`, a shell variable you set to that directory. They are Python
files, not ROS packages to invoke with `ros2 run`.

| Script | Evidence it checks |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py <results> --packages <name>` | Check executed, passing cases in fresh colcon reports; use `--require-test PACKAGE::test_name` for the changed behaviour, since linters alone can otherwise pass |
| `ros2-troubleshooting/scripts/check_qos_compat.py --topic /scan` | Native Jazzy QoS compatibility for discovered publisher/subscriber pairs |
| `ros2-troubleshooting/scripts/check_tf_tree.py --sensors laser_frame,imu_link` | TF connectivity and mounting RPY for physical comparison; an unusual angle is an advisory |
| `ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data` | Gravity at rest on level ground, transformed into `--base base_link`; missing TF is inconclusive, and gravity cannot establish yaw |
| `ros2-troubleshooting/scripts/check_odom_direction.py --topic /odom` | Fresh odometry before and after an externally observed movement; direction only, not distance calibration |

**Exit codes: 0 PASS, 1 FAIL, 2 INCONCLUSIVE or invalid request.** Missing data,
NaN, unavailable IMU fields, unknown QoS, no executed tests and insufficient
motion must not become successful verification. The runtime scripts require a
sourced Jazzy environment. They do not publish motion commands; the odometry
check relies on movement performed outside the script. A check proves only the
property it observes, not the correctness of the whole robot.

## How it works

```mermaid
flowchart LR
    A[Development request] --> B[Protocol: verify local facts]
    B --> C[ros2-development: build and test]
    B --> D[ros2-troubleshooting: runtime evidence]
    C --> E[Installed behaviour and observed result]
    D --> E
    E --> F[Correct the defect and repeat the relevant check]
```

The protocol covers development across packages, Nav2, MoveIt and ros2_control;
the focused skills add procedures and tools when those are useful. We do not
restore large domain manuals merely to increase the skill count. The new
`ros2-development` workflow addresses a concrete gap: a successful test command
can report **zero tests**. In the real package fixture, that command returns 0
while the bundled evidence check returns 2.

## Validation and evidence limits

CI checks installation/update preservation, Python and shell code, deterministic
verdicts, real Python/CMake and ament test wrappers, synthetic Jazzy pub/sub and
TF, and independent acceptance-oracle controls. Commands are in
[CONTRIBUTING.md](CONTRIBUTING.md).

Real Claude Code **Opus 5.5 High** sessions completed three targeted workflows
under both plugin and manual installation: a namespaced sensor package with
installed YAML/launch, meaningful wheel-speed tests, and live IMU/TF diagnosis.
Both loading smokes verified protocol delivery and actual bundled-script use.
The three baseline sessions also passed: the observed task outcomes were the
same. This is **one run per method and task, not evidence of a performance gain
or equivalent reliability**. Follow-up runtime sessions review owned-process
cleanup after a focused instruction fix; all attempts and limits are in the
[release acceptance report](evals/development/RESULTS.md).

Codex support is tracked separately in the [Codex compatibility report](evals/CODEX.md).
Earlier Claude observations are not Codex performance evidence. The Codex installer
embeds the protocol on skill activation; it does not install a session-wide hook.

Physical robots, MCU firmware, calibration and full Nav2/MoveIt/Gazebo
applications remain unverified. Downstream interface consumers, stale-overlay
remediation and `--packages-up-to` guidance also need independent behavioral
validation beyond these cases.

## Evals

[CAPABILITIES.md](evals/CAPABILITIES.md) preserves historical scores and reconciles
them with committed verdicts. Some reported scores cannot be reproduced because
transcripts or re-grades are missing; they are not evidence that all domain
knowledge is unnecessary. We do not advertise those scores as current results.

New skills should improve a real development task. Reproducible failure fixtures
support tool correctness; before claiming an agent performance gain, compare
matched tasks with and without the change. See [authoring criteria](evals/AUTHORING.md)
and the [evaluation method](evals/LADDER.md).

## Updating

For a plugin installation:

```bash
claude plugin update claude-ros2-skills@claude-ros2-skills
```

For a manual installation, pull the repository and rerun the same installer
command. Local edits are preserved by refusing the update until you review the
conflict. Include `--agent codex` when updating Codex. Start a new session in the
corresponding assistant afterwards.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Correctness fixes, useful development
workflows and reproducible counterexamples are welcome. Keep historical
transcripts intact and distinguish observed results from hypotheses.

## License

[Apache-2.0](LICENSE).
