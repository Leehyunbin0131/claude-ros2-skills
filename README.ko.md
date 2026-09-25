<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy를 위한 Claude Code 스킬" width="100%"/>

**코드 작성에서 실행 검증까지 이어지는 ROS 2 개발 스킬.**

[English](README.md) | **한국어** | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

</div>

**Ubuntu 24.04 / ROS 2 Jazzy**용 Claude Code 스킬 3개를 제공합니다.
패키지를 개발하고, 테스트와 설치된 결과물을 확인하며, 실행 중 발생하는 문제를 진단합니다.
목표는 그럴듯하지만 실행해 보지 않은 코드를 수정하느라 드는 시간을 줄이는 것입니다.
프로젝트의 기존 구조와 ROS 공식 문서를 존중하면서 필요한 작업 흐름과 검사 도구를 제공합니다.

## 빠른 시작

설치 방법은 하나만 선택하세요.

**플러그인 — Claude Code 세션에서 실행:**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

새 세션을 시작하면 `SessionStart` 훅이 [검증 지침](CLAUDE.md)을 전달합니다.
플러그인 루트의 `CLAUDE.md`는 그 자체로 자동 로드되지 않습니다.
기본 사용자 범위 설치는 모든 프로젝트에 적용됩니다. ROS 작업 공간에만 적용하려면 프로젝트 설치를 사용하세요.

**수동 — 이미 존재하는 프로젝트에 설치:**

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

Claude는 설명을 보고 필요한 스킬을 선택합니다. 명시적으로 사용하려면 요청에 이름을 넣으세요.

- “ros2-development를 사용해서 기존 Jazzy 패키지에 서비스를 추가해줘. 소비 패키지도 빌드하고 관련 테스트와 설치된 노드 실행을 확인해줘.”
- “ros2-troubleshooting을 사용해줘. `/scan`은 발행되는데 내 노드의 콜백이 실행되지 않아. 호환되지 않는 엔드포인트를 찾고 수정 결과도 확인해줘.”
- “수평으로 놓인 로봇에서 IMU를 뒤집어 장착했어. 선언된 TF를 적용해서 정상 장착과 실제 오류를 구분해줘.”

알고 있다면 실물/시뮬레이션 여부와 작업 공간을 함께 알려주세요.
로봇의 실제 치수나 기존 토픽·TF 발행자가 불명확하면 에이전트가 이를 확인해야 합니다.

## 검사 도구

스크립트는 각 스킬에 포함됩니다. Claude Code에서는 현재 폴더가 아닌
`${CLAUDE_SKILL_DIR}/scripts/`를 기준으로 찾아 `python3`로 실행합니다.
`ros2 run`으로 실행하는 ROS 패키지가 아닙니다.

| 스크립트 | 확인하는 증거 |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py <results> --packages <name>` | 새 colcon 결과에서 실행·통과한 테스트 확인. 기능 변경은 `--require-test PACKAGE::test_name`으로 필요한 테스트를 지정. 스타일 검사만으로 기능 검증을 대신하지 않음 |
| `check_qos_compat.py --topic /scan` | 발견된 발행자·구독자 조합의 실제 Jazzy QoS 호환성 |
| `check_tf_tree.py --sensors laser_frame,imu_link` | TF 연결과 실물에 대조할 장착 각도. 특이한 각도 표시는 참고 사항 |
| `check_imu_gravity.py --topic /imu/data` | 정지·수평 상태에서 가속도를 `--base base_link`로 변환한 뒤 중력 확인. TF가 없으면 판정 불가, 중력만으로 yaw 확인 불가 |
| `check_odom_direction.py --topic /odom` | 외부에서 확인한 이동 전후의 새로운 오도메트리. 방향 검사이며 거리 보정 검사는 아님 |

아래 4개 스크립트는 `ros2-troubleshooting/scripts/`에 있습니다.
**종료 코드: 0 통과, 1 실패, 2 판정 불가 또는 잘못된 요청.**
데이터 누락·NaN·사용 불가 IMU 필드·불명확한 QoS·실행한 테스트 없음·불충분한 이동을 성공으로 처리하지 않습니다.
런타임 검사는 Jazzy 환경을 먼저 불러와야 합니다. 이동 명령을 발행하지 않으며,
오도메트리 검사는 스크립트 외부에서 수행한 이동을 관찰합니다.
통과는 해당 속성을 확인했다는 뜻이지 로봇 전체가 올바르다는 뜻은 아닙니다.

## 개발 흐름

프로토콜로 로컬 API와 전제를 확인하고, `ros2-development`로 패키지 의존성과 테스트를 검증합니다.
실행 중 문제가 있으면 `ros2-troubleshooting`으로 관측하고, 수정 후 같은 검사를 다시 실행합니다.
Nav2·MoveIt·ros2_control을 포함한 개발에서도 이 흐름을 활용하되, 프로젝트에 맞는 실행 증거를 선택합니다.

새 개발 스킬이 다루는 구체적인 문제는 **실행한 테스트가 0개인데 명령이 성공하는 경우**입니다.
실제 임시 패키지 검증에서 기본 `colcon` 명령은 0으로 종료했지만 새 검사는 2로 종료해 완료 증거가 없음을 표시했습니다.
스킬 개수를 늘리기 위해 과거의 방대한 도메인 문서를 그대로 복원하지는 않습니다.

## 검증 범위와 한계

CI는 설치·업데이트 시 파일 보존, Python·셸 코드, 판정 로직, 실제 임시 Python/CMake 패키지의
빌드·테스트, 합성 데이터 기반 Jazzy 통신·TF, 평가 도구를 검사합니다.
실제 Claude Code 플러그인 세션에서도 프로토콜 전달을 확인했습니다.
명령은 [기여 안내](CONTRIBUTING.md)에 있습니다.

이는 도구 동작과 로딩 검증이며 **에이전트 개발 능력이 얼마나 향상되는지 측정한 결과는 아닙니다.**
새 개발 지침은 아직 모델 대조 실험을 하지 않았습니다.
실물 로봇·MCU·보정 작업은 별도 검증이 필요하며, 이번 변경에서 Nav2·MoveIt·Gazebo 전체 개발을 다시 시험하지 않았습니다.

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
