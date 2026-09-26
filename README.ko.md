<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy를 위한 Claude Code·Codex 스킬" width="100%"/>

**코드 작성에서 실행 검증까지 이어지는 ROS 2 개발 스킬.**

[English](README.md) | **한국어** | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

</div>

**Ubuntu 24.04 / ROS 2 Jazzy**용 Claude Code·Codex 스킬 3개를 제공합니다.
패키지를 개발하고, 테스트와 설치된 결과물을 확인하며, 실행 중 발생하는 문제를 진단합니다.
목표는 그럴듯하지만 실행해 보지 않은 코드를 수정하느라 드는 시간을 줄이는 것입니다.
프로젝트의 기존 구조와 ROS 공식 문서를 존중하면서 필요한 작업 흐름과 검사 도구를 제공합니다.

## 빠른 시작

사용할 도구를 선택하세요. Claude Code에서는 플러그인과 수동 설치 중 하나만 사용하세요.

**Codex — 이미 존재하는 프로젝트에 설치:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# 모든 프로젝트에 적용하려면 위 명령 대신 실행
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

[Codex 공식 스킬 경로](https://learn.chatgpt.com/docs/build-skills)인
`<프로젝트>/.agents/skills` 또는 `~/.agents/skills`에 설치합니다. 중복 표시를 피하려면
두 범위 중 하나만 선택하세요. 각 스킬에 공통 [검증 지침](CLAUDE.md)을 포함하므로
Codex가 스킬을 사용할 때 지침도 함께 읽습니다. Claude 훅이나 규칙 파일에 의존하지 않습니다.
기존 `AGENTS.md`, `CLAUDE.md`, Codex 설정과 다른 스킬은 보존하며, 로컬 수정이 있으면
업데이트를 중단합니다. 대상 작업 공간에서 새 Codex 세션을 시작하세요.
CLI·IDE에서는 `$ros2-development`, `$ros2-troubleshooting`으로 명시적으로 호출할 수 있고,
데스크톱에서는 스킬 선택기에서 같은 이름을 선택하면 됩니다.

실시간 ROS 검사는 대상 ROS 그래프에 접근할 수 있어야 합니다. 제한된 Codex 환경에서
ROS 로그 경로 쓰기가 거부되면 `ROS_LOG_DIR`를 작업 공간의 쓰기 가능한 폴더로 지정할 수 있습니다.
토픽은 보이지만 메시지가 오지 않는 경우 샌드박스·DDS 통신 제약도 확인해야 합니다.
프로젝트의 도메인과 탐색 범위를 유지하세요. `SUBNET`으로 확대하는 것을 일반적인 설치 해결책으로
사용하지 않습니다. 관측할 수 없으면 판정 불가로 보고해야 합니다. [실행 중 확인한 제한](evals/CODEX.md).

**플러그인 — Claude Code 세션에서 실행:**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

새 세션을 시작하면 `SessionStart` 훅이 [검증 지침](CLAUDE.md)을 전달합니다.
플러그인 루트의 `CLAUDE.md`는 그 자체로 자동 로드되지 않습니다.
기본 사용자 범위 설치는 모든 프로젝트에 적용됩니다. ROS 작업 공간에만 적용하려면 프로젝트 설치를 사용하세요.

**Claude Code 수동 — 이미 존재하는 프로젝트에 설치:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --project /path/to/your-workspace
# 모든 프로젝트에 적용하려면 위 명령 대신 실행
# python3 claude-ros2-skills/scripts/install.py --user
```

스킬 3개와 `.claude/rules/ros2-verification.md`가 설치됩니다.
기존 `CLAUDE.md`와 다른 스킬은 보존합니다. 사용자가 수정한 파일은 덮어쓰지 않으며,
예전에 설치한 폐기 스킬은 검토할 수 있도록 알려줍니다. 설치 후 Claude Code를 다시 시작하세요.
ROS, colcon, 로봇 드라이버는 설치하지 않으므로 작업 공간에 필요한 의존성은 별도로 준비해야 합니다.
이미 Jazzy가 설치된 Ubuntu에서는 검사 도구의 의존성을 다음과 같이 준비할 수 있습니다.

```bash
sudo apt install python3-colcon-common-extensions python3-pytest \
  ros-jazzy-tf2-ros ros-jazzy-sensor-msgs ros-jazzy-nav-msgs
source /opt/ros/jazzy/setup.bash
```

Ubuntu/Jazzy에서 제공하는 테스트 도구나 별도로 검증한 환경을 사용하세요.
검증 당시 Jazzy의 `launch_testing`은 pytest 9에서 시작 오류가 났으며,
ROS 환경을 포함한 검사는 Ubuntu의 pytest 7.4.4로 확인했습니다.
테스트 실행기 오류와 구현의 검증 실패를 구분해야 합니다.

## 스킬과 사용 예시

| 스킬 | 사용할 때 | 제공하는 도움 |
| :--- | :--- | :--- |
| [ros2-development](skills/ros2-development/SKILL.md) | 패키지·노드·인터페이스·launch·설정·테스트 개발 | 의존성을 고려한 빌드, 설치된 결과물 검증, 실제 실행된 테스트가 없는 상태 탐지 |
| [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md) | 토픽·콜백·TF·IMU·오도메트리의 실행 오류 | 실행 가능한 진단 4개와 좌표계·QoS·실물 보정 참고 자료 |
| [ros2-microros](skills/ros2-microros/SKILL.md) | MCU 통신·에이전트·rclc·메시지 메모리 작업 | 소스와 진단 지침. **MCU에서 검증하지 않음** |

두 도구 모두 설명을 보고 필요한 스킬을 선택할 수 있습니다. 명시적으로 사용하려면 요청에 이름을 넣으세요.

- “ros2-development를 사용해서 기존 Jazzy 패키지에 서비스를 추가해줘. 소비 패키지도 빌드하고 관련 테스트와 설치된 노드 실행을 확인해줘.”
- “ros2-troubleshooting을 사용해줘. `/scan`은 발행되는데 내 노드의 콜백이 실행되지 않아. 호환되지 않는 엔드포인트를 찾고 수정 결과도 확인해줘.”
- “수평으로 놓인 로봇에서 IMU를 뒤집어 장착했어. 선언된 TF를 적용해서 정상 장착과 실제 오류를 구분해줘.”

알고 있다면 실물/시뮬레이션 여부와 작업 공간을 함께 알려주세요.
로봇의 실제 치수나 기존 토픽·TF 발행자가 불명확하면 에이전트가 이를 확인해야 합니다.

## 검사 도구

스크립트는 각 스킬에 포함됩니다. 읽어 들인 `SKILL.md`가 있는 절대 경로를 기준으로
`scripts/`를 찾아 `python3`로 실행합니다. 예제의 `ROS2_SKILL_DIR`는 그 경로로 직접 설정하는
셸 변수이며, 도구가 자동 제공하는 변수가 아닙니다.
`ros2 run`으로 실행하는 ROS 패키지가 아닙니다.

| 스크립트 | 확인하는 증거 |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py <results> --packages <name>` | 새 colcon 결과에서 실행·통과한 테스트 확인. 기능 변경은 `--require-test PACKAGE::test_name`으로 필요한 테스트를 지정. 스타일 검사만으로 기능 검증을 대신하지 않음 |
| `check_qos_compat.py --topic /scan` | 발견된 발행자·구독자 조합의 실제 Jazzy QoS 호환성 |
| `check_tf_tree.py --sensors laser_frame,imu_link` | TF 연결과 실물에 대조할 장착 각도. 특이한 각도 표시는 참고 사항 |
| `check_imu_gravity.py --topic /imu/data` | 선언된 TF 또는 `--assume-aligned`를 적용하여 수평 기준 프레임의 +Z 중력 가속도 측정치 확인. 최소 2개 샘플 필요, 샘플 간 RMS 편차 >1.5 m/s²(`--max-variation`으로 조정 가능) 또는 TF 누락 시 판정 불가. 어느 방식이든 물리적 정지 상태 자체는 입증하지 못하며 중력만으로 yaw 확인 불가 |
| `check_odom_direction.py --topic /odom` | 외부에서 확인한 이동 전후의 새로운 오도메트리. 방향 검사이며 거리 보정 검사는 아님 |

아래 4개 스크립트는 `ros2-troubleshooting/scripts/`에 있습니다.
**종료 코드: 0 통과, 1 실패, 2 판정 불가 또는 잘못된 요청.**
데이터 누락·NaN·사용 불가 IMU 필드·불충분한 샘플(2개 미만)·과도한 샘플 편차·불명확한 QoS·실행한 테스트 없음·불충분한 이동을 성공으로 처리하지 않습니다.
런타임 검사는 Jazzy 환경을 먼저 불러와야 합니다. 이동 명령을 발행하지 않으며,
오도메트리 검사는 스크립트 외부에서 수행한 이동을 관찰합니다.
검사 결과는 관측한 속성에 관한 근거만 제공합니다. IMU 통과(PASS)는 선언된 TF 또는 명시적인 축 정렬 가정을 거쳐 수평 기준 프레임에서 측정된 +Z 중력 방향을 확인할 뿐이며, 물리적 정지 상태나 로봇 전체의 정상 상태를 입증하지는 못합니다.

## 개발 흐름

프로토콜로 로컬 API와 전제를 확인하고, `ros2-development`로 패키지 의존성과 테스트를 검증합니다.
실행 중 문제가 있으면 `ros2-troubleshooting`으로 관측하고, 수정 후 같은 검사를 다시 실행합니다.
Nav2·MoveIt·ros2_control을 포함한 개발에서도 이 흐름을 활용하되, 프로젝트에 맞는 실행 증거를 선택합니다.

새 개발 스킬이 다루는 구체적인 문제는 **실행한 테스트가 0개인데 명령이 성공하는 경우**입니다.
실제 임시 패키지 검증에서 기본 `colcon` 명령은 0으로 종료했지만 새 검사는 2로 종료해 완료 증거가 없음을 표시했습니다.
스킬 개수를 늘리기 위해 과거의 방대한 도메인 문서를 그대로 복원하지는 않습니다.

## 검증 범위와 한계

Codex 지원 검증은 [별도 보고서](evals/CODEX.md)에 기록합니다. 오프라인 설치·탐색 및 모델명이 기록되지 않은
2건의 프로젝트 설치 워크플로를 다루며, 기존 Claude 실행 결과는 Codex 성능의 증거가 아닙니다.
Codex에서는 스킬을 활성화할 때 공통 지침이 적용됩니다.

CI는 설치·업데이트 시 파일 보존, Python·셸 코드, 판정 로직, 실제 Python/CMake 및 ament 테스트,
합성 Jazzy 통신·TF, 독립적인 평가 판정기의 정상·오류 사례를 검사합니다.
명령은 [기여 안내](CONTRIBUTING.md)에 있습니다.

실제 Claude Code **Opus 5.5 High**로 센서 패키지 개발, 휠 속도 기능 테스트 수정,
IMU/TF 진단을 플러그인·수동 설치 방식에서 각각 완료했습니다.
두 설치 방식의 로딩 검사에서는 지침 전달과 제공 스크립트 실행도 확인했습니다.
스킬 없는 기본 실행도 세 과제를 모두 통과했습니다. **방식·과제마다 한 번의 관측이며,
성능 향상이나 같은 신뢰성을 입증한 결과가 아닙니다.**
종료 지침을 보강한 뒤의 런타임 재검증을 포함한 모든 시도와 한계는
[배포 검증 기록](evals/development/RESULTS.md)에 공개합니다.

후속 [인터페이스 변경 비교 실험](evals/workflow_value/RESULTS.md)은 동결된 0.1.2 스냅샷을 대상으로 Opus 5.5 High를
사용해 Python·C++ 소비자가 있는 세 변형을 스킬 유무에 따라 비교했습니다. 여섯 결과물 모두 독립적인
빌드·실행·회귀 검증을 통과했습니다. 검증 보고의 정확성, 해석이 갈리는 프로젝트 규칙,
프로세스 종료 문제는 별도로 기록했습니다. 해당 실험에서 스킬 팩 세션은 출력 토큰 수와 API 비용 추정치가
더 높았으며, 관측된 경과 시간 단축은 실행 순서, 프롬프트 캐시, 백그라운드 프로브 대기 시간의 혼재로 인한 것입니다.
토큰 수, 총 비용, 속도 측면의 입증된 이점은 없으며 이를 주장하지 않습니다. 이번 유지보수 패치는 대규모 스킬 개편이
아닌 선별적인 IMU 수정입니다.

유지보수는 지원 범위 내의 구체적인 결함, 필수 테스트 회귀, 확인된 실행 환경 호환성 변화,
명시적인 사용자 범위 확장이 있을 때만 재개하며, 업스트림 모델 업데이트만으로는 불충분합니다.

실물 로봇·MCU·물리 보정과 Nav2·MoveIt·Gazebo 전체 애플리케이션은 검증하지 않았습니다.
작은 인터페이스 사례로 일반적인 overlay 복구, 구형·신형 DDS 타입 간 통신, 외부 C++ 라이브러리 사용,
`--packages-up-to` 지침의 효과까지 입증한 것은 아닙니다.

## 평가 기록

[CAPABILITIES.md](evals/CAPABILITIES.md)는 과거 수치와 저장된 판정의 차이를 공개합니다.
일부는 원본이나 재채점 자료가 없어 재현할 수 없습니다. 이를 현재 성능으로 홍보하거나
모든 도메인 지식이 불필요하다는 근거로 사용하지 않습니다.
새 스킬은 실제 개발 문제를 해결해야 하며, 모델 성능 향상을 주장하려면 동일 조건의 대조 실험이 필요합니다.
[작성 기준](evals/AUTHORING.md)과 [평가 방법](evals/LADDER.md)을 참고하세요.

## 업데이트

플러그인 설치는 다음 명령을 사용합니다.

```bash
claude plugin update claude-ros2-skills@claude-ros2-skills
```

수동 설치는 저장소를 갱신한 뒤 같은 설치 명령을 다시 실행합니다.
로컬 수정이 있으면 덮어쓰지 않고 중단하므로 먼저 충돌을 검토하세요. 이후 새 세션을 시작하세요.

## 기여 및 라이선스

[CONTRIBUTING.md](CONTRIBUTING.md) · [Apache-2.0](LICENSE).
정확성 수정, 실용적인 개발 흐름, 재현 가능한 실패 사례를 환영합니다.
