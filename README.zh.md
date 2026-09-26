<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy skills for Claude Code and Codex" width="100%"/>

**情境化封装 ROS 2 验证工具、工作流与交接证据。**

[English](README.md) | [한국어](README.ko.md) | **中文** | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

</div>

适用于 **Ubuntu 24.04 / ROS 2 Jazzy** 的三个 Claude Code 与 Codex 技能：开发软件包、核实测试与安装产物、诊断运行时故障。

本项目遵循 [Agent Skills 规范](https://agentskills.io/home)，将领域知识、开发工作流与可执行诊断工具打包。我们并不声称提高前沿大模型的固有代码生成能力，而是探索一个工程设计假设：**通过封装特定环境的证据检查和结构化交接记录，能否减少会话间验证歧义与上下文交接成本。** 虽然各工具的独立功能已在测试环境中通过验证，但**降低交接成本或提高整体开发生产率仍属未经证实的假设。**

## 快速上手

支持自动技能发现（skill discovery）。

**Codex — 安装到现有项目：**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# 用户全局安装：
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

技能安装在 Codex 目录（`<project>/.agents/skills` 或 `~/.agents/skills`），并在使用技能时加载共享[验证协议](CLAUDE.md)。保留现有配置与其他技能。

**Claude Code — 插件安装：**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

## 技能列表

| 技能 | 适用场景 | 提供内容 |
| :--- | :--- | :--- |
| [ros2-development](skills/ros2-development/SKILL.md) | 创建或修改软件包、节点、接口、launch、配置及测试 | 依赖感知构建、安装产物验证、检测空测试运行、用于任务交接的自选证据跟踪工具 |
| [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md) | 运行时的发布者、回调、TF、IMU 或里程计异常 | 4 个可执行诊断脚本，以及坐标系（REP 103/105）、QoS、实机标定参考资料 |
| [ros2-microros](skills/ros2-microros/SKILL.md) | MCU 通信、Agent、rclc、消息内存 | 源码索引与故障诊断指南；**未经 MCU 实机验证** |

## 可执行验证与证据工具

脚本存放在各技能目录下。示例中的 `ROS2_SKILL_DIR` 是由智能体内部设置为已加载技能目录的示例变量，不需要用户手动输入。

| 脚本 | 目的与检查的证据 |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py` | 检查新 colcon 报告中实际执行并通过的测试（排除空测试） |
| `ros2-development/scripts/evidence.py begin / finish / inspect` | **可选（opt-in）工作流**：记录调用方声明的命令元数据并比对工作区文件哈希与选定环境变量值，支持任务交接 |
| `ros2-troubleshooting/scripts/check_qos_compat.py --topic /scan` | 发布者/订阅者端点间的 Jazzy QoS 兼容性 |
| `ros2-troubleshooting/scripts/check_tf_tree.py --sensors laser_frame,imu_link` | TF 树连通性与实机对比用的安装 RPY 欧拉角 |
| `ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data` | 静止水平放置时转换至 `--base base_link` 的重力向量 |
| `ros2-troubleshooting/scripts/check_odom_direction.py --topic /odom` | 观察到的实际移动前后的新里程计方向 |

**诊断脚本退出代码：0 通过，1 失败，2 无法断定或请求无效。**
**证据检查（inspect）退出代码：0 一致 (Consistent)，1 已变更 (Changed)，2 不完整 (Incomplete)。**
证据工具严格区分调用方声明的结果与工具观察到的文件哈希。它不会自动运行或重跑用户命令，不保证新鲜度或不存在中间篡改，也不证明整个机器人的健康状态。详见 [docs/DESIGN.md](docs/DESIGN.md)。

## 验证与证据边界

退出码：0 通过，1 失败，2 无法判定或请求无效。数据缺失、NaN、未知 QoS、缺失 TF、样本少于 2 个、样本偏差过大（>1.5 m/s²，可通过 --max-variation 调整）或没有执行测试不能视为成功。PASS 仅评估通过已声明 TF 或显式对齐假设（--assume-aligned）后水平基座坐标系中测得的 +Z 重力；二者均不能证明物理静止，且重力不能验证 yaw。里程计检查只验证方向，不验证距离标定。运行时检查不发布运动命令。

CI 涵盖安装保持、代码有效性、真实 Python/CMake 和 ament 测试用例，以及合成 Jazzy 发布订阅与判定逻辑。

在过往 Claude Code Opus 5.5 High 会话中，技能与基线在相同任务上均通过。在接口迁移实验（[RESULTS.md](evals/workflow_value/RESULTS.md)）中，技能组虽记录到更短耗时，但受限于小样本与缓存等混淆因素，**并未因果证明能带来速度提升、可靠性增强或编码能力改进。**该历史 0.1.2 研究未评估 0.2.0 版本新增的交接工具。

物理机器人、MCU 固件以及完整的 Nav2/MoveIt 应用仍属未验证范围。

## 贡献与许可

[CONTRIBUTING.md](CONTRIBUTING.md) · [evals/AUTHORING.md](evals/AUTHORING.md) · [Apache-2.0](LICENSE).
