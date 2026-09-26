# 動作の証拠を伴う ROS 2 開発

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

Ubuntu 24.04 / ROS 2 Jazzy 向けの Claude Code と Codex スキルを3つ提供します。パッケージ開発、テストとインストール成果物の確認、実行時の障害診断を支援し、既存プロジェクトの規約を尊重します。

## インストール

### Codex へのインストール

リポジトリを clone してから以下を実行します。プロジェクトでは `.agents/skills`、`--project` の代わりに `--user` を使うと `~/.agents/skills` に配置します。共通の検証手順は各スキルに含まれ、スキル使用時に読み込まれます。既存の `AGENTS.md`、`CLAUDE.md` と設定を保持します。作業フォルダーで新しいセッションを開始してください。CLI/IDE では `$ros2-development` で明示的に呼び出せます。[Codex 検証記録](evals/CODEX.md)。以下のプラグインと既定の手動コマンドは Claude Code 用です。

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

### Claude Code

インストール方法は1つ選んでください。Claude Code セッションでプラグインを追加します：

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

既存プロジェクトへの手動インストール：

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --project /path/to/your-workspace
# --user: alternative to --project
```

新しいセッションで反映されます。プラグインは SessionStart フックでプロトコルを読み込み、ユーザー範囲では全プロジェクトに適用されます。手動インストールは既存の CLAUDE.md と他のスキルを保持し、.claude/rules/ros2-verification.md にプロトコルを配置します。ローカル変更は上書きしません。ROS、colcon、ドライバーは別途必要です。

## スキル

- [ros2-development](skills/ros2-development/SKILL.md): パッケージ、ノード、インターフェース、launch/config、テストの開発。各パッケージでテストが実際に実行されたか確認します。
- [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md): QoS、TF、IMU、オドメトリ方向の4つの実行可能な診断と、座標系・校正の参考資料。
- [ros2-microros](skills/ros2-microros/SKILL.md): MCU、エージェント、rclc、メモリのガイダンス。MCUでの動作は未検証です。

依頼にスキル名を明示できます。例：「ros2-development を使ってこの Jazzy パッケージを変更し、依存関係をビルドして、インストール済みノードと実行されたテストを確認してください。」

## 検証と限界

終了コードは0が合格、1が失敗、2が判定不能または無効な要求です。欠落データ、NaN、不明なQoS、欠落TF、2件未満のサンプル、過大なサンプル変動（>1.5 m/s²、--max-variationで調整可）、テスト未実行を成功と扱いません。PASSは宣言されたTFまたは明示的な軸整列の仮定（--assume-aligned）後に水平基準フレームで測定された+Z重力のみを評価し、いずれも物理的静止を証明するものではなく、重力ではyawを検証できません。オドメトリは方向のみで距離校正は対象外です。実行時診断は移動指令を送信しません。

CIはインストール保護、判定ロジック、実際の一時Python/CMakeパッケージのビルドとテスト、合成Jazzy通信・TF、評価ツールを確認します。Opus 5.5 High による3課題はプラグイン・手動インストールの両方で完了しました。ベースラインも全課題を完了しており、方式・課題ごとに1回の観測です。[検証記録](evals/development/RESULTS.md)を参照してください。ツールの動作検証はエージェント能力の向上を証明しません。実機とMCUは別途検証が必要です。

後続の[インターフェース移行比較](evals/workflow_value/RESULTS.md)では、Opus 5.5 High で Python/C++ 消費側を含む3変種を検証しました。スキル有無の6成果物すべてが独立検証を通過しました。報告の正確性、規則の曖昧さ、残存プロセスは別に記録しています。信頼性向上や因果的な高速化は実証されず、スキルは 0.1.2 のままです。

過去の成績には欠落記録や再現できない再採点があります。現在の性能として宣伝しません。 [CAPABILITIES.md](evals/CAPABILITIES.md).

## 更新

手動インストールはリポジトリを更新して同じインストーラーを再実行します。プラグインには以下を使い、その後新しいセッションを開始します。

```bash
claude plugin update claude-ros2-skills@claude-ros2-skills
```

[詳細な開発手順と検証範囲 (English)](README.md) · [貢献ガイド](CONTRIBUTING.md) · [Apache-2.0](LICENSE).
