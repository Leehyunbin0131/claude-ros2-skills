<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy skills for Claude Code and Codex" width="100%"/>

**ROS 2 検証ツール、ワークフロー、引き継ぎ証拠のコンテキストに応じたパッケージング。**

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | **日本語** | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

</div>

**Ubuntu 24.04 / ROS 2 Jazzy** を対象とした Claude Code および Codex 向けの3つのスキルを提供します：パッケージ開発、テストとインストール成果物の検証、実行時障害の診断。

本リポジトリは、[Agent Skills 標準](https://agentskills.io/home) に準拠し、ドメイン知識、開発ワークフロー、実行可能な診断ツールをパッケージングします。先端言語モデル本来のコーディング能力向上を主張するのではなく、**環境固有の証拠確認と構造化された引き継ぎ記録により、検証の曖昧さやセッション間の引き継ぎコストを削減できるかを探る設計仮説**に基づいています。ツール自体の機能はテストフィクスチャで確認されていますが、**引き継ぎコストの削減や総合的な生産性の向上は未検証の仮説です。**

## クイックスタート

自動スキル検出（skill discovery）を標準でサポートしています。

**Codex — プロジェクトへのインストール:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# ユーザー全体のインストール:
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

Codexのスキル配置先（`<project>/.agents/skills` または `~/.agents/skills`）に配置され、共通の [検証プロトコル](CLAUDE.md) が各スキルに含まれます。既存の設定や他のスキルは保持されます。

**Claude Code — プラグインインストール:**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

## スキル一覧

| スキル | 用途 | 提供内容 |
| :--- | :--- | :--- |
| [ros2-development](skills/ros2-development/SKILL.md) | パッケージ、ノード、インターフェース、launch、設定、テストの開発 | 依存関係を考慮したビルド、インストール成果物の検証、空テスト実行の検出、引き継ぎのためのオプトイン証拠追跡ツール |
| [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md) | トピック、コールバック、TF、IMU、オドメトリの実行時障害 | 4つの実行可能診断ツール、座標系（REP 103/105）、QoS、実機キャリブレーション参照 |
| [ros2-microros](skills/ros2-microros/SKILL.md) | MCU通信、エージェント、rclc、メッセージメモリ | ソース参照および診断ガイダンス（**MCU実機未検証**） |

## 実行可能検証および証拠ツール

各スクリプトはスキル内に配置されています。例にある `ROS2_SKILL_DIR` はエージェントがロードされたスキルのディレクトリに内部設定する変数であり、ユーザーに入力を求めるものではありません。

| スクリプト | 目的と確認証拠 |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py` | 新規colcon結果から実際に実行・成功したテストを確認（空テストの排除） |
| `ros2-development/scripts/evidence.py begin / finish / inspect` | **オプトインワークフロー**: 宣言されたコマンドメタデータの記録およびワークスペースのファイルハッシュと選択された環境変数値の比較による引き継ぎ支援 |
| `ros2-troubleshooting/scripts/check_qos_compat.py --topic /scan` | 発行者・購読者ペアのJazzy QoS互換性 |
| `ros2-troubleshooting/scripts/check_tf_tree.py --sensors laser_frame,imu_link` | TF接続性および実機比較用の取り付けRPY角度 |
| `ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data` | 静止水平状態での `--base base_link` 重力ベクトル |
| `ros2-troubleshooting/scripts/check_odom_direction.py --topic /odom` | 観測された移動前後の新規オドメトリ進行方向 |

**診断スクリプト終了コード: 0 合格, 1 失敗, 2 判定不能/無効な要求。**
**証拠検査（inspect）終了コード: 0 一致(Consistent), 1 変更あり(Changed), 2 不完全(Incomplete)。**
証拠ツールは、呼び出し側が宣言した結果とツールが観測したファイルハッシュを厳格に分離します。ユーザーコマンドの自動実行や再実行は行わず、鮮度の保証や中間変更の検出、ロボット全体の正常性を証明するものではありません。[docs/DESIGN.md](docs/DESIGN.md) を参照してください。

## 検証の限界

過去の Claude Code Opus 5.5 High の評価において、スキル適用群とベースライン群は同じ課題を完了しました。インターフェース移行比較実験（[RESULTS.md](evals/workflow_value/RESULTS.md)）の観測実行ではスキル適用群で所要時間の短縮が記録されましたが、小規模サンプルやキャッシュの影響により、**速度向上や信頼性の改善、コーディング能力の向上を因果的に実証したものではありません。**

実機ロボット、MCUファームウェア、完全なNav2/MoveIt環境は未検証です。

## コントリビューション & ライセンス

[CONTRIBUTING.md](CONTRIBUTING.md) · [evals/AUTHORING.md](evals/AUTHORING.md) · [Apache-2.0](LICENSE).
