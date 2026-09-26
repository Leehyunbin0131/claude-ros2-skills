# 用运行证据支持 ROS 2 开发

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

适用于 Ubuntu 24.04 / ROS 2 Jazzy 的三个 Claude Code 和 Codex 技能：开发软件包、核实测试与安装产物、诊断运行故障。保留项目现有约定，按需要查阅官方文档。

## 安装

### Codex 安装

在克隆仓库后运行以下命令。项目安装使用 `.agents/skills`；使用 `--user` 代替 `--project` 可安装到 `~/.agents/skills`。每个 Codex 技能包含共享验证协议，在使用技能时读取。保留现有 `AGENTS.md`、`CLAUDE.md` 和配置。安装后在工作区启动新会话。CLI/IDE 可用 `$ros2-development` 明确调用。Codex 的验证范围见 [兼容性记录](evals/CODEX.md)。下面的插件与默认手动命令用于 Claude Code。

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

### Claude Code

选择一种安装方式。在 Claude Code 会话中安装插件：

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

也可安装到已有项目：

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --project /path/to/your-workspace
# --user: alternative to --project
```

重启会话后生效。插件通过 SessionStart 钩子加载协议；用户级安装影响所有项目。手动安装保留现有 CLAUDE.md 和其他技能，将协议放入 .claude/rules/ros2-verification.md；遇到本地修改时拒绝覆盖。ROS、colcon 和驱动需自行准备。

## 技能

- [ros2-development](skills/ros2-development/SKILL.md): 软件包、节点、接口、launch/config 和测试开发；检查每个软件包是否确实执行了测试。
- [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md): 四项可执行诊断：QoS、TF、IMU 和里程计方向，以及坐标系和标定参考。
- [ros2-microros](skills/ros2-microros/SKILL.md): MCU、代理、rclc 和内存指导。尚未在 MCU 上验证。

在任务中明确写出技能名，例如：“使用 ros2-development 修改此 Jazzy 软件包，构建依赖并验证已安装节点和实际执行的测试。”

## 验证与限制

退出码：0 通过，1 失败，2 无法判定或请求无效。数据缺失、NaN、未知 QoS、缺失 TF、样本少于 2 个、样本偏差过大（>1.5 m/s²，可通过 --max-variation 调整）或没有执行测试不能视为成功。PASS 仅评估通过已声明 TF 或显式对齐假设（--assume-aligned）后水平基座坐标系中测得的 +Z 重力；二者均不能证明物理静止，且重力不能验证 yaw。里程计检查只验证方向，不验证距离标定。运行时检查不发布运动命令。

CI 覆盖安装保护、判定逻辑、真实临时 Python/CMake 软件包构建与测试、合成 Jazzy 通信和 TF，以及评估工具。Opus 5.5 High 在插件和手动安装下完成了三个任务；基线也全部完成。每种方式、每个任务仅观察一次，详见[验证记录](evals/development/RESULTS.md)。这些检查证明工具行为，不证明代理能力提升。实体机器人和 MCU 仍需单独验证。

后续[接口迁移对照研究](evals/workflow_value/RESULTS.md)用 Opus 5.5 High 比较了三个含 Python/C++ 消费者的变体。基线与技能组的六个结果均通过独立验证；报告准确性、规则歧义和进程残留另行记录。尚未证实额外的可靠性收益或因果性的提速，技能保持 0.1.2。

历史成绩存在缺失记录和无法复现的重新评分；不将其宣传为当前性能。 [CAPABILITIES.md](evals/CAPABILITIES.md).

## 更新

手动安装请拉取仓库后重跑相同安装命令；插件使用以下命令。更新后重启会话。

```bash
claude plugin update claude-ros2-skills@claude-ros2-skills
```

[完整使用流程与证据范围 (English)](README.md) · [贡献指南](CONTRIBUTING.md) · [Apache-2.0](LICENSE).
