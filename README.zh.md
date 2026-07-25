<div align="center">

<img src="assets/hero.png" alt="claude-ros2-skills — 面向 ROS 2 Jazzy 的抗幻觉 Claude Code 技能" width="100%"/>

**面向 ROS 2 Jazzy Jalisco 机器人开发的 Claude Code Skills。**

抗幻觉参考技能 — 每个技能都路由到官方文档，而不是猜测 API 名称。

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

[English](README.md) | [한국어](README.ko.md) | **中文** | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

<sub>🌐 本文档为机器翻译。原文请参阅 [English](README.md)。</sub>

| 技能 | 常驻路由器 | 文档链接（CI 检查） | 机器人地面真值检查 | 评估：写前验证 |
| :---: | :---: | :---: | :---: | :---: |
| **11 个** | **26 行** | **38 个** | **4 个脚本** | **0/3 → 3/3** |

</div>

---

## 目录

- [为什么存在](#为什么存在)
- [有何不同](#有何不同)
- [实测评估](#实测评估)
- [快速开始](#快速开始)
- [技能列表](#技能列表)
- [验证脚本](#验证脚本)
- [工作原理](#工作原理)
- [更新](#更新)
- [贡献](#贡献)
- [许可证](#许可证)

## 为什么存在

日志只能证明系统是*一致的*，而永远无法证明它是*正确的* — 而智能体默认没有理由去怀疑一个自洽的叙事。有两种失败模式反复出现：

| 失败模式 | 表面症状 | 实际原因 |
| :--- | :--- | :--- |
| **错误的地面真值** | `/cmd_vel` 前进，`/odom` 前进，所有话题正常 — 机器人却在**倒着开** | 静态 TF 声明与传感器实际安装方向相反；下游一切都*基于错误的变换*正确计算，因此没有任何矛盾 |
| **错误的时代** | 代码评审通过，运行时死在一个"听起来合理"的方法上 | 智能体依赖记忆中 Foxy/Humble 时代的训练数据；该 API 在 Jazzy 中已重命名或从未存在 |

两者都源于信任*看起来*权威的东西，而不是核对地面真值。`ros2-troubleshooting` 强制在信任话题之前先做物理检查（推一推机器人、echo 原始 TF、确认 IMU 重力）。其余每个技能把同样的规则应用到代码上：类名、消息、参数一律对照官方 Jazzy 文档或 `/opt/ros/jazzy/` 验证 — 绝不凭记忆。

## 有何不同

大多数机器人技能包把 API 知识固化进技能文件。生态一旦移动，每一段固化的代码片段都会变成可能悄悄腐烂的"事实"。本仓库押注于完全相反的方向：

| | 内容密集型技能包 | **claude-ros2-skills** |
| :--- | :--- | :--- |
| 知识所在 | 固化在技能文件中，**每技能 400–1,800 行** | 路由到官方文档；技能正文 **~60 行**，大块细节放在 `references/`，**仅在需要时**读取 |
| 常驻上下文 | 完整 SKILL.md | **26 行**路由器 |
| Jazzy API 变更时 | 片段悄悄腐烂；需要永远做文档回归测试 | 腐烂面缩小为链接 + 符号名 — **38 个链接**每周 CI 检查（仅存活性），死链即构建失败 |
| 验证方式 | 静态 / 基于日志 | **物理层面**：IMU 重力、推动测试、TF 安装 vs 真实硬件、DDS QoS 匹配 |
| 发行版声明 | 示例只针对一个却标注"支持 4 个" | **仅 Jazzy**，开门见山 |

坦率地说明取舍：对于官方文档薄弱的主题（DDS 厂商调优、PREEMPT_RT 内部机制），内容密集型技能包可能更适合你。本仓库只为一件事优化 — 把"看似可信却在 Jazzy 上跑不起来的代码"的概率降到最低。

## 实测评估

是测量结果，不是口头主张 — 但有一点需要公开：运行与评分由仓库作者自己的智能体会话完成，并非独立第三方。所有产物均已提交，供第三方重新评分。相同的提示词在全新的 headless Claude Code 会话中分别以安装/不安装技能运行（每组使用相同模型）；输出逐符号对照锁定的 Jazzy 源码评分。

| 结果 | 无技能 | 有技能 |
| :--- | ---: | ---: |
| 错误/虚构的 Nav2 MPPI 键 (haiku，重跑) | **~30 个** — 完全没有 `critics:` 列表，无法启动 | **~16–20 个** — 插件字符串、`motion_model`、命名空间均正确 |
| 真实 BEST_EFFORT LiDAR 上 `/scan` 回调触发 (sonnet) | **永不触发** — 错误默认 QoS，无声失败 | **正常触发** |
| 写代码前做了验证的运行 | **0 / 3** | **3 / 3** |

完整评分表、条件和所有生成产物：[`evals/RESULTS.md`](./evals/RESULTS.md) · 协议与检查清单：[`evals/README.md`](./evals/README.md) — 目前每格 n=1；欢迎提交附带评分记录的 PR。

<details>
<summary>这些数字意味着什么</summary>

两个值得命名的模式：在强模型上，技能把"大概率正确"变成"经验证正确"；在小模型上，技能是"无法启动的配置"与"正确配置"之间的差别。而在一次验证工具不可用的运行中，加载技能的智能体**拒绝输出未经验证的参数**而不是去猜 — 基线则根本没意识到自己什么都没核对过。

</details>

## 快速开始

**方式 A — 插件市场（推荐）：**

```
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

更新通过 `/plugin marketplace update` 获取。

**方式 B — 手动复制：**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git

# 项目级（仅此项目）
mkdir -p your-project/.claude/skills
cp -r claude-ros2-skills/skills/* your-project/.claude/skills/
cp claude-ros2-skills/CLAUDE.md your-project/

# 或用户级（所有项目）
mkdir -p ~/.claude/skills
cp -r claude-ros2-skills/skills/* ~/.claude/skills/
```

重启 Claude Code（或开启新会话）即可加载技能。

## 技能列表

| 技能 | 路径 | 覆盖范围 |
| :--- | :--- | :--- |
| **ros2-core** | `skills/ros2-core/SKILL.md` | rclcpp、rclpy、TF2、EKF 里程计、QoS 配置、参数 |
| **ros2-package** | `skills/ros2-package/SKILL.md` | `ros2 pkg create`、CMakeLists/setup.py 接线、colcon 构建与 source、自定义接口 |
| **ros2-dev** | `skills/ros2-dev/SKILL.md` | Nav2（AMCL、代价地图、MPPI/Smac）、SLAM Toolbox、RTAB-Map、Isaac ROS |
| **gazebo-sim** | `skills/gazebo-sim/SKILL.md` | Gazebo Harmonic、ros_gz_bridge、ros_gz_sim、SDFormat 建模 |
| **ros2-control** | `skills/ros2-control/SKILL.md` | ros2_control 硬件抽象、控制器管理器、URDF 标签 |
| **ros2-moveit** | `skills/ros2-moveit/SKILL.md` | MoveIt 2、MoveGroup C++/Python API、IK 求解器、OMPL、MoveIt Servo |
| **ros2-perception** | `skills/ros2-perception/SKILL.md` | image_transport、cv_bridge、vision_msgs、depth_image_proc、PCL |
| **ros2-testing** | `skills/ros2-testing/SKILL.md` | launch_testing、gtest/pytest、rosbag2 C++/Python API、ros2trace |
| **ros2-microros** | `skills/ros2-microros/SKILL.md` | micro-ROS Agent、rclc 客户端 API、自定义传输、静态内存 |
| **ros2-security** | `skills/ros2-security/SKILL.md` | SROS2、PKI 密钥库生成、访问控制、DDS Security |
| **ros2-troubleshooting** | `skills/ros2-troubleshooting/SKILL.md` | REP 103/105 地面真值 TF 树、LiDAR/IMU 对齐、反幻觉 |

## 验证脚本

这些脚本捆绑在 `ros2-troubleshooting` 技能内（`skills/ros2-troubleshooting/scripts/`），因此随任何安装方式一同分发。它们把物理检查变成可运行的通过/失败事实（需要已 source 的 ROS 2 环境；退出码 0 = PASS，1 = FAIL，2 = 无数据）：

| 脚本 | 验证内容 |
| :--- | :--- |
| `check_imu_gravity.py` | 机器人静止时 → 重力应为 **+Z** 轴上约 +9.81 m/s²（REP 103）。捕捉装反或旋转安装的 IMU。 |
| `check_odom_direction.py` | 向前推机器人 → 里程计位移应沿航向为正。捕捉反转的电机、编码器或 TF。 |
| `check_tf_tree.py` | 确认 `map→odom→base_link` 可解析；以 RPY 角度打印每个传感器安装并标记约 180° 的声明，以便与物理安装对比。 |
| `check_qos_compat.py` | 检查话题上每对发布者/订阅者是否符合 DDS 匹配规则的 QoS 兼容。捕捉"话题显示 30 Hz 但我的回调从不触发"的无声失败（BEST_EFFORT 发布 vs RELIABLE 订阅，以及 durability/deadline/liveliness 不匹配）。 |

纯判定逻辑无需 ROS 即可单元测试（`python3 skills/ros2-troubleshooting/scripts/test_checks.py`），并在每次推送时于 CI 中运行。

## 工作原理

```mermaid
flowchart LR
    A["你的请求"] --> B["CLAUDE.md<br/>26 行路由器，<br/>无 API 细节"]
    B --> C["skills/&lt;name&gt;/SKILL.md<br/>文档链接 +<br/>已验证的符号名"]
    C --> D["官方 Jazzy 文档<br/>或 /opt/ros/jazzy/"]
    D --> E["代码"]
```

`CLAUDE.md` 从不内联 API 细节 — 它只负责路由。每个 `SKILL.md` 都是官方文档链接加精确类/消息/参数名的轻量目录，因此 Claude 是在验证而不是猜测。参见 [`CLAUDE.md`](./CLAUDE.md)。

## 更新

```bash
cd claude-ros2-skills
git pull
cp -r skills/* ~/.claude/skills/   # 或你项目的 .claude/skills/
```

## 贡献

简版规则 — 技能保持为文档链接目录（不是教程），每个符号都对照 Jazzy 文档或 `/opt/ros/jazzy/` 验证，脚本的纯逻辑保持无需 ROS 即可单元测试。完整规则、技能/脚本检查清单和 issue 模板：[`CONTRIBUTING.md`](./CONTRIBUTING.md)。

## 许可证

Apache-2.0 — 参见 [LICENSE](./LICENSE)。
