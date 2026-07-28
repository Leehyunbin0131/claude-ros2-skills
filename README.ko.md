<div align="center">

<img src="assets/hero.png" alt="claude-ros2-skills — Claude Code skills for ROS 2 Jazzy" width="100%"/>

**Claude Code Skills for ROS 2 Jazzy Jalisco robotics development.**

AI 에이전트의 ROS 2 개발 방식을 혁신하는 스킬: 불명확한 파라미터를 사전에 파악하고, 설치된 패키지를 기준으로 설정을 검증하며, 실제 동작 증거를 통해 실행을 확인합니다.

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

[English](README.md) | **한국어** | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

<sub>🌐 이 문서는 기계 번역본입니다. 원문은 [English](README.md)입니다.</sub>

| 스킬 | 상시 로드 프로토콜 | 문서 링크 (CI 검증됨) | 로봇 실기 검증 |
| :---: | :---: | :---: | :---: |
| **11개** | **28줄** | **32개** | **4개 스크립트** |

</div>

---

## 목차

- [비용이 드는 실패들](#비용이-드는-실패들)
- [이 스킬들의 설계 원칙](#이-스킬들의-설계-원칙)
- [무엇이 다른가](#무엇이-다른가)
- [실측 평가](#실측-평가)
- [빠른 시작](#빠른-시작)
- [스킬 목록](#스킬-목록)
- [검증 스크립트](#검증-스크립트)
- [동작 방식](#동작-방식)
- [업데이트](#업데이트)
- [기여하기](#기여하기)
- [라이선스](#라이선스)

## 비용이 드는 실패들

AI가 생성한 ROS 2 코드에서 가장 비싼 비용을 치르게 하는 오류는 단순한 구문(syntax) 실수가 아닙니다. 오히려 겉보기에는 정상처럼 보이는 미묘한 문제입니다.

| 실패 유형 | 현상 | 에이전트가 이 문제에 직면하는 이유 |
| :--- | :--- | :--- |
| **소리 없는 실패** | `ros2 topic hz`에는 30 Hz로 출력되지만 콜백이 전혀 실행되지 않음 | 기본값인 RELIABLE 구독자가 BEST_EFFORT 발행자에 연결을 시도함. 코드는 정상적으로 컴파일되고 코드 리뷰도 통과하지만 DDS 미들웨어 수준에서 실패함. |
| **잘못된 기준 좌표** | `/cmd_vel`은 전진을 나타내고 `/odom`도 전진을 보고하지만, 실제 로봇은 **후진**함 | 고정 TF 프레임이 실제 물리적 장착 상태와 반대로 뒤집혀 있음. 하위 구성 요소가 *잘못된 트랜스폼을 사용하여* 계산을 정상 수행하므로 명시적인 오류가 발생하지 않음. |
| **구버전 API 사용** | 코드 리뷰는 통과하지만 런타임에 잘못된 메서드를 호출하여 실패함 | 에이전트가 Jazzy에서 이름이 변경되거나 제거된 Foxy 또는 Humble의 더 이상 사용되지 않는(deprecated) API 메서드를 사용함. |
| **잘못된 전제** | 한 문장으로 바로잡을 수 있었을 전제를 바탕으로 에이전트가 200줄의 코드를 작성함 | 코드 생성 전에 누락된 세부 정보를 검증하도록 에이전트에 요청하는 메커니즘이 없음. |

컴파일러, 린터, 로그 분석기 그 무엇도 이러한 숨겨진 문제를 감지하지 못합니다. 이러한 오류를 하나 해결할 때마다 출력 검토, 원인 진단, 수정 사항 설명, 코드 재생성이라는 추가 피드백 주기가 소모됩니다.

## 이 스킬들의 설계 원칙

이 리포지토리의 모든 스킬은 4가지 설계 원칙을 따릅니다.

**1. 불명확한 변수를 사전에 파악합니다.** 실제 하드웨어인지 시뮬레이션 환경인지, 기존 워크스페이스를 확장할지 새 워크스페이스를 생성할지, 어떤 노드가 이미 트랜스폼을 발행 중인지, 로봇의 정확한 형상이 어떠한지 등 주요 운용 세부 사항은 문서에 명시되어 있지 않은 경우가 많습니다. [`CLAUDE.md`](./CLAUDE.md)는 에이전트가 코드를 생성하기 전에 이러한 미지의 항목을 명확히 하도록 지시합니다. 도메인 특화 스킬은 타깃 파라미터를 관리합니다. 예를 들어 `ros2-dev`는 Nav2 파라미터를 설정하기 전에 로봇 footprint, 구동 키네마틱스(drive kinematics), 위치 추정 소스(localization source)를 요청합니다.

**2. 명확한 종료 조건이 있는 구조화된 루프를 실행합니다.** 모든 스킬은 *검증(verify) → 작성(write) → 증명(prove)* 주기를 따릅니다. 설치된 환경에서 시스템 기본값을 검사하고, 단계적 변경 사항을 적용하며, 실행을 확인합니다. 단순히 코드 파일을 생성하는 것이 아니라 빌드 성공, `ros2 topic echo`의 실시간 데이터 수집, 검증 스크립트 통과 등 관찰된 증거가 뒷받침될 때만 작업이 완료됩니다.

**3. 긴 설명보다 구조화된 실패 대응 표를 우선시합니다.** 증상 → 근본 원인 → 시정 조치를 매핑한 구조화된 표는 공식 문서에 부족한 명확하고 지속 가능한 지침을 제공하며, 버전에 관계없이 높은 신뢰성을 유지합니다.

> `[`는 GZ→ROS, `]`는 ROS→GZ · `16UC1`은 밀리미터, `32FC1`은 미터 · `joint_state_broadcaster`는 자동 스폰되지 않음 · `raytrace_max_range` ≤ `obstacle_max_range`이면 장애물이 삭제되지 않음 · rclc는 바운드되지 않은 메시지 필드를 자동 할당하지 않음

**4. 3계층 아키텍처로 컨텍스트 사용을 최적화합니다.** 각 스킬은 컨텍스트 효율성의 균형을 맞춥니다. 스킬 설명은 컨텍스트에 유지되고, 스킬 본문은 호출될 때 로드되며, `references/`의 심층 참조 파일은 필요한 경우에만 로드됩니다. 방대한 심볼 카탈로그와 세부 파라미터 튜닝 표는 `references/`에 위치하므로, 컨텍스트를 절약하고 특정 구성 요소(예: AMCL)를 디버깅할 때 불필요한 문서(예: 행동 트리 노드)가 로드되지 않도록 합니다.

## 무엇이 다른가

대부분의 로보틱스 스킬 팩은 정적 API 지식을 스킬 파일에 직접 내장합니다. 초기 사용은 쉬울지 몰라도, 기반 패키지가 업데이트되면 이 방식은 무너지며 소리 없이 실패하는 구버전 코드 조각(snippet)을 남기게 됩니다. 본 리포지토리는 동적 문서 기반 접근 방식을 취합니다.

| 기능 | 콘텐츠 중심의 스킬 팩 | **claude-ros2-skills** |
| :--- | :--- | :--- |
| 지식 저장 위치 | 스킬 파일 내에 내장 (**스킬당 400~1,800줄**) | 공식 문서와 연결 (**~60줄**의 스킬 본문); 세부 참조 문서는 **필요할 때만** 로드 |
| 상시 로드 컨텍스트 | 전체 `SKILL.md` 파일 | **28줄** 핵심 프로토콜 |
| Jazzy API 업데이트 대응 | 스니펫이 눈에 띄지 않게 오래됨; 지속적인 수동 테스트 업데이트 필요 | 구버전 스니펫 위험이 진입점 링크 및 심볼 이름 수준으로 최소화됨 — **32개 문서 링크**를 CI로 매주 검증 |
| 검증 방식 | 정적 코드 분석 또는 로그 확인 | **물리 및 런타임 검증**: IMU 중력 검사, 방향성 오도메트리 테스트, TF 프레임 정렬, DDS QoS 호환성 |
| 지원 범위 | 단일 배포판만 지원하면서 여러 ROS 배포판을 지원하다고 주장 | **ROS 2 Jazzy 전용**, 의도된 설계 — "Humble에서도 작동함"과 같은 어설픈 수식 없음 |

본 리포지토리는 하나의 결과에 최적화되어 있습니다. 바로 ROS 2 Jazzy에서 실행 시 실패하는 '그럴듯해 보이는 코드'가 생성될 위험을 최소화하는 것입니다.

## 실측 평가

**이곳에서 스킬이 검증된 것으로 인정받으려면 두 가지 질문에 답할 수 있어야 합니다.** 스킬이 자체 내용을 다루는 작업에서 에이전트가 생성하는 결과를 변화시키는가, 그리고 이 스킬 본문이 해당 변화를 만들어내는 *가장 작은* 본문인가? 정확함은 기본 조건(floor)일 뿐 기준(bar)이 아닙니다. 더 적은 토큰과 텍스트로도 동일한 결과를 얻을 수 있으며, 이를 테스트하기 전까지는 "에이전트가 스킬을 사용했다"는 절반의 답변에 불과합니다.

**아직 어떤 스킬도 검증을 완료하지 않았습니다.** 스킬별 상태는 [`evals/RESULTS.md`](./evals/RESULTS.md)에 정리되어 있으며, 각 스킬이 두 축을 모두 통과하면 실패한 스킬을 포함하여 결과가 그곳에 게시됩니다. 중간 측정 결과는 의도적으로 공개하지 않습니다. 이전 라운드에서 단일 실행의 결과로 그럴듯한 결론이 나왔으나 통제된 재실행에서 번복된 적이 있으며, 부분적인 결과는 오류를 바로잡기도 전에 빠르게 확산될 수 있기 때문입니다.

측정 항목, 채점 방식 및 재실행 방법: [`evals/README.md`](./evals/README.md). 지금까지 진행된 모든 실행의 트랜스크립트와 로그는 [`evals/runs/`](./evals/runs/) 아래에 커밋되어 있습니다.

## 빠른 시작

**옵션 A — 플러그인 마켓플레이스 (권장):**

```
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

언제든지 `/plugin marketplace update` 명령어로 설치된 플러그인을 업데이트할 수 있습니다.

**옵션 B — 수동 설치:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git

# 프로젝트 단위 설치 (현재 프로젝트에만 적용)
mkdir -p your-project/.claude/skills
cp -r claude-ros2-skills/skills/* your-project/.claude/skills/
cp claude-ros2-skills/CLAUDE.md your-project/

# 사용자 단위 설치 (모든 프로젝트에 적용)
mkdir -p ~/.claude/skills
cp -r claude-ros2-skills/skills/* ~/.claude/skills/
```

설치된 스킬을 적용하려면 Claude Code를 재시작(또는 새 세션 시작)하세요.

## 스킬 목록

| 스킬 | 경로 | 커버리지 |
| :--- | :--- | :--- |
| **ros2-core** | `skills/ros2-core/SKILL.md` | rclcpp, rclpy, TF2, EKF 오도메트리, QoS 프로필, 파라미터 |
| **ros2-package** | `skills/ros2-package/SKILL.md` | `ros2 pkg create`, CMakeLists/setup.py 연결, colcon 빌드 및 소스 적용, 커스텀 인터페이스 |
| **ros2-dev** | `skills/ros2-dev/SKILL.md` | Nav2 (AMCL, costmaps, MPPI/Smac), SLAM Toolbox, RTAB-Map, Isaac ROS |
| **gazebo-sim** | `skills/gazebo-sim/SKILL.md` | Gazebo Harmonic, ros_gz_bridge, ros_gz_sim, SDFormat 모델링 |
| **ros2-control** | `skills/ros2-control/SKILL.md` | ros2_control 하드웨어 추상화, controller manager, URDF 태그 |
| **ros2-moveit** | `skills/ros2-moveit/SKILL.md` | MoveIt 2, MoveGroup C++/Python API, IK 솔버, OMPL, MoveIt Servo |
| **ros2-perception** | `skills/ros2-perception/SKILL.md` | image_transport, cv_bridge, vision_msgs, depth_image_proc, PCL |
| **ros2-testing** | `skills/ros2-testing/SKILL.md` | launch_testing, gtest/pytest, rosbag2 C++/Python API, ros2trace |
| **ros2-microros** | `skills/ros2-microros/SKILL.md` | micro-ROS Agent, rclc 클라이언트 API, 커스텀 트랜스포트, 정적 메모리 |
| **ros2-troubleshooting** | `skills/ros2-troubleshooting/SKILL.md` | REP 103/105 기준 좌표 TF 트리, LiDAR/IMU 정렬, 물리 검증 |

## 검증 스크립트

이 검증 스크립트들은 `ros2-troubleshooting` 스킬(`skills/ros2-troubleshooting/scripts/`)에 번들로 포함되어 있으며 모든 설치에 함께 제공됩니다. 물리 하드웨어 검사를 실행 가능한 성공/실패 검증 단계로 변환합니다(ROS 2 환경 소싱 필요; 반환 코드: 0 = PASS, 1 = FAIL, 2 = NO DATA):

| 스크립트 | 검증 내용 |
| :--- | :--- |
| `check_imu_gravity.py` | 정지 상태의 로봇이 **+Z** 축을 따라 ~+9.81 m/s²의 중력을 측정하는지 검증합니다(REP 103). 뒤집히거나 잘못 정렬된 IMU 장착을 감지합니다. |
| `check_odom_direction.py` | 로봇을 앞으로 밀었을 때 헤딩(heading) 방향을 따라 양(+)의 오도메트리 변위가 발생하는지 검증합니다. 모터 방향 반전, 인코더 극성 문제 또는 뒤집힌 TF 설정을 감지합니다. |
| `check_tf_tree.py` | `map→odom→base_link`가 올바르게 확인(resolve)되는지 검증합니다. 각 센서의 장착 오프셋을 RPY 도(degree) 단위로 표시하고 잠재적인 180° 방향 오류를 강조합니다. |
| `check_qos_compat.py` | DDS 규칙을 사용하여 토픽의 모든 발행자/구독자 쌍 간의 QoS 호환성을 검증합니다. 소리 없는 실패(BEST_EFFORT 발행자와 RELIABLE 구독자의 조합, 또는 내구성, 마감일, 생동성 불일치 등)를 방지합니다. |

핵심 결정 로직은 ROS와 독립적으로 단위 테스트되며(`python3 skills/ros2-troubleshooting/scripts/test_checks.py`), 푸시할 때마다 지속적 통합(CI)을 통해 실행됩니다.

## 동작 방식

```mermaid
flowchart LR
    A["사용자의 요청"] --> B["CLAUDE.md<br/>프로토콜 + 게이트,<br/>API 세부정보 없음"]
    B --> C["skills/&lt;name&gt;/SKILL.md<br/>게이트, 루프,<br/>실패 대응 표"]
    C --> D["/opt/ros/jazzy/<br/>또는 공식 Jazzy 문서"]
    C -.필요한 경우만.-> R["references/<br/>심볼 카탈로그,<br/>튜닝 표"]
    D --> E["코드 작성 후 실행 결과 증명"]
    R --> E
```

`CLAUDE.md`에는 구체적인 API 세부 정보가 포함되어 있지 않습니다. 대신 운용 프로토콜을 수립하고 코드를 작성하기 전에 불명확한 질문에 답하도록 요구합니다. 각 `SKILL.md` 파일은 불명확한 변수 식별, 검증-작성-증명 루프 실행, 실패 대응 표 참조 등 도메인 특화 결정을 관리합니다. 세부 참조 자료는 `references/` 디렉토리에 별도로 저장됩니다. 자세한 내용은 [`CLAUDE.md`](./CLAUDE.md)를 참조하세요.

## 업데이트

```bash
cd claude-ros2-skills
git pull
cp -r skills/* ~/.claude/skills/   # 또는 프로젝트의 .claude/skills/
```

## 기여하기

요약: 스킬 파일은 결정 로직(검증 게이트, 루프 단계, 실패 대응 표)에 집중해야 하며, 세부 문서는 `references/`에 유지되어야 합니다. 모든 API 심볼은 공식 Jazzy 문서 또는 `/opt/ros/jazzy/` 설치 환경을 기준으로 검증되어야 합니다. 검증 스크립트는 ROS 의존성 없이 단위 테스트가 가능한 순수 로직을 유지해야 합니다. 전체 가이드라인, 스킬 및 스크립트 체크리스트, 이슈 템플릿은 [`CONTRIBUTING.md`](./CONTRIBUTING.md)를 참조하세요.

## 라이선스

Apache-2.0 — [LICENSE](./LICENSE)를 참조하세요.
