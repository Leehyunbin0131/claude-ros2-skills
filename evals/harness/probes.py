#!/usr/bin/env python3
"""Probes: one prompt, several mechanical checks, each tied to the claims it tests.

A probe is a task that gives the agent a genuine opportunity to apply a rule
**without naming the rule**. If the prompt says "remember to bounds-check", it
measures instruction-following, not whether the skill line was needed.

One prompt carries several checks on purpose. It makes each cell cheaper per
claim, and it turns every ablation into an interference test as well: removing
the bounds rule should not move the QoS check, and if it does, that is a real
finding about how skill bodies interact.

A check returns True (satisfied), False (not satisfied), or None (the answer
could not be graded — no code, refusal, truncation). None is never counted as a
failure; it is reported separately, because a grader that silently scores
unparseable output as "fail" invents effects.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

# --- extraction helpers ------------------------------------------------------

FENCE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", re.S)


def code(answer: str, lang_hint: str = "python") -> str | None:
    """Concatenated fenced code, or None when the answer contains none.

    Falls back to the whole answer only when it looks like bare code, so a prose
    reply that merely mentions `range_min` is never graded as if it wrote it.
    """
    blocks = FENCE.findall(answer or "")
    if blocks:
        return "\n".join(blocks)
    if answer and re.search(r"^\s*(import rclpy|#include|def main\()", answer, re.M):
        return answer
    return None


def prose(answer: str) -> str | None:
    return answer if (answer or "").strip() else None


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text) for p in patterns)


# --- check + probe types -----------------------------------------------------

@dataclass
class Check:
    """One graded property of an answer, and the claims that should produce it."""
    fn: Callable[[str], bool | None]
    claims: list[str]
    desc: str = ""


@dataclass
class Probe:
    id: str
    suite: str
    skill: str
    prompt: str
    checks: dict[str, Check]
    note: str = ""
    extra_claims: list[str] = field(default_factory=list)
    # Groups of claims that state the same behaviour in different places. Single
    # ablation cannot judge these: if each member suffices alone, removing any
    # one measures Δ=0 for all of them, and cutting the lot on that evidence
    # breaks the behaviour. Each group is ablated together as well as singly.
    joint: list[list[str]] = field(default_factory=list)
    # "Addition" and "position" cases beyond delete/joint-delete: test each claim
    # alone (no other content) and/or a whole-body reorder condition. Off by
    # default so existing suites are unaffected.
    probe_only: bool = False
    extra_conditions: list[str] = field(default_factory=list)

    @property
    def claim_ids(self) -> list[str]:
        seen: list[str] = []
        for c in self.checks.values():
            for cid in c.claims:
                if cid not in seen:
                    seen.append(cid)
        for cid in self.extra_claims:
            if cid not in seen:
                seen.append(cid)
        return seen

    def conditions(self, include_only: bool = False) -> list[str]:
        conds = ["naked", "protocol", "full", "shipped"]
        conds += [f"ablate:{cid}" for cid in self.claim_ids]
        conds += [f"ablate:{'+'.join(g)}" for g in self.joint]
        if include_only or self.probe_only:
            conds += [f"only:{cid}" for cid in self.claim_ids]
        conds += self.extra_conditions
        return conds

    def predicate(self, answer: str) -> dict[str, bool | None]:
        return {name: chk.fn(answer) for name, chk in self.checks.items()}


# --- ros2-core suite ---------------------------------------------------------
# Claim ids are the ones claims.py emits; they are asserted in tests so a skill
# edit that moves a line fails loudly instead of silently grading the wrong text.

C_QOS_RULE = "ros2-core:5strict-coding-rules:03"
C_QOS_ROW = "ros2-core:4symptom-root-cause-action:01"
C_QOS_SYM = "ros2-core:2symbols-to-verify-there-never-write-the:04"
C_BOUNDS_RULE = "ros2-core:5strict-coding-rules:04"
C_BOUNDS_ROW = "ros2-core:4symptom-root-cause-action:07"
C_SHUTDOWN_RULE = "ros2-core:5strict-coding-rules:05"
C_SHUTDOWN_ROW = "ros2-core:4symptom-root-cause-action:08"
C_TF_RULE = "ros2-core:5strict-coding-rules:02"
C_TF_SYM = "ros2-core:2symbols-to-verify-there-never-write-the:01"
C_TF_ROW = "ros2-core:4symptom-root-cause-action:05"
C_ROS1_RULE = "ros2-core:5strict-coding-rules:01"
C_PARAM_YAML_ROW = "ros2-core:4symptom-root-cause-action:03"
C_PARAM_CB_ROW = "ros2-core:4symptom-root-cause-action:04"
C_PARAM_SYM = "ros2-core:2symbols-to-verify-there-never-write-the:03"
C_EXEC_ROW = "ros2-core:4symptom-root-cause-action:06"
C_DOMAIN_ROW = "ros2-core:4symptom-root-cause-action:02"


def _scan_qos(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    if _has(src, r"qos_profile_sensor_data", r"SensorDataQoS"):
        return True
    # An explicit BEST_EFFORT profile is equally correct; require it to be wired
    # into the subscription rather than merely imported.
    if _has(src, r"ReliabilityPolicy\.BEST_EFFORT") and _has(src, r"QoSProfile"):
        return True
    return False


def _scan_bounds(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return bool(re.search(r"range_min", src) and re.search(r"range_max", src))


def _scan_nan(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"isfinite", r"isnan", r"math\.nan", r"np\.nan", r"!= *r\b.*r")


def _scan_shutdown(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ExternalShutdownException")


def _scan_shutdown_guard(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"rclpy\.ok\(\)", r"if +ok\(\)")


def _scan_timer(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"create_timer")


P_SCAN = Probe(
    id="scan-node",
    suite="core",
    skill="ros2-core",
    prompt=(
        "Write a ROS 2 Jazzy Python node that subscribes to `/scan` "
        "(`sensor_msgs/msg/LaserScan`) and logs the minimum range once per second. "
        "Give me the complete file, ready to run."
    ),
    checks={
        "sensor_qos": Check(_scan_qos, [C_QOS_RULE, C_QOS_ROW, C_QOS_SYM],
                            "subscription uses sensor-data QoS, not the depth-only default"),
        "bounds_filter": Check(_scan_bounds, [C_BOUNDS_RULE, C_BOUNDS_ROW],
                               "readings filtered against range_min/range_max"),
        "nan_handled": Check(_scan_nan, [C_BOUNDS_RULE, C_BOUNDS_ROW],
                             "non-finite readings excluded"),
        "clean_shutdown": Check(_scan_shutdown, [C_SHUTDOWN_RULE, C_SHUTDOWN_ROW],
                                "ExternalShutdownException caught"),
        "shutdown_guard": Check(_scan_shutdown_guard, [C_SHUTDOWN_RULE, C_SHUTDOWN_ROW],
                                "shutdown guarded by rclpy.ok()"),
        "independent_timer": Check(_scan_timer, [],
                                   "1 Hz logging on its own timer — control check, no claim owns it"),
    },
    note="The task the whole repo was built around; every prior run measured it at n=1.",
    # This probe carries the interference sweep: every claim in the body is
    # ablated against it, not only the seven its own checks depend on. Removing
    # the bounds rule should not move the QoS check — if it does, the body's
    # lines are interacting and "the effect of line X" is not well defined.
    extra_claims=[
        "ros2-core:1documentation-entry-points:01",
        "ros2-core:1documentation-entry-points:02",
        "ros2-core:1documentation-entry-points:03",
        "ros2-core:1documentation-entry-points:04",
        "ros2-core:1documentation-entry-points:05",
        "ros2-core:2symbols-to-verify-there-never-write-the:02",
        "ros2-core:2symbols-to-verify-there-never-write-the:05",
        "ros2-core:3local-system-inspection-interfaces-grou:01",
        "ros2-core:3local-system-inspection-interfaces-grou:02",
        "ros2-core:3local-system-inspection-interfaces-grou:03",
        C_TF_RULE, C_TF_SYM, C_TF_ROW, C_ROS1_RULE,
        C_PARAM_YAML_ROW, C_PARAM_CB_ROW, C_PARAM_SYM,
        C_EXEC_ROW, C_DOMAIN_ROW,
    ],
    # Three behaviours that `ros2-core` states in more than one place. The first
    # sweep measured every member of the bounds pair at Δ=0, which is the
    # signature of redundancy, not of uselessness — cutting both on that reading
    # would have removed the rule that took Task 1 from 0.020 m to 0.450 m.
    joint=[
        [C_QOS_RULE, C_QOS_ROW, C_QOS_SYM],
        [C_BOUNDS_RULE, C_BOUNDS_ROW],
        [C_SHUTDOWN_RULE, C_SHUTDOWN_ROW],
    ],
)


def _odom_msg(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"nav_msgs\.msg import Odometry", r"nav_msgs/msg/Odometry", r"\bOdometry\b")


def _imu_msg(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"sensor_msgs\.msg import Imu", r"sensor_msgs/msg/Imu", r"\bImu\b")


def _odom_qos(answer: str) -> bool | None:
    return _scan_qos(answer)


P_ODOM = Probe(
    id="odom-imu-yaw",
    suite="core",
    skill="ros2-core",
    prompt=(
        "Write a ROS 2 Jazzy Python node that subscribes to wheel odometry on `/odom` "
        "and to an IMU on `/imu/data`, and logs the yaw reported by each once per "
        "second so I can compare them. Complete file."
    ),
    checks={
        "odom_msg": Check(_odom_msg, ["ros2-core:2symbols-to-verify-there-never-write-the:02"],
                          "uses the real odometry message type"),
        "imu_msg": Check(_imu_msg, ["ros2-core:2symbols-to-verify-there-never-write-the:02"],
                         "uses the real IMU message type"),
        "sensor_qos": Check(_odom_qos, [C_QOS_RULE, C_QOS_ROW, C_QOS_SYM],
                            "sensor-data QoS on high-rate topics — the rule says odom/IMU too"),
    },
    note="Covers the one §2 bullet no other probe touches. Both message types are "
         "almost certainly known cold, which makes this a cut test for that bullet.",
)


def _tf_exception(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"TransformException", r"LookupException", r"ExtrapolationException",
                r"ConnectivityException", r"canTransform")


def _tf_latest_time(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    if not _has(src, r"lookup_transform"):
        return None
    window = re.search(r"lookup_transform\((?:[^()]|\([^()]*\))*\)", src, re.S)
    call = window.group(0) if window else src
    if _has(call, r"get_clock\(\)\.now\(\)"):
        return False
    return _has(call, r"Time\(\)", r"TimePointZero", r"rclpy\.time\.Time\(\)")


P_TF = Probe(
    id="tf-lookup",
    suite="core",
    skill="ros2-core",
    prompt=(
        "Write a ROS 2 Jazzy Python node that looks up the transform from `map` to "
        "`base_link` at 10 Hz and logs the translation. Give me the complete file, "
        "ready to run."
    ),
    checks={
        "tf_exception": Check(_tf_exception, [C_TF_RULE, C_TF_SYM],
                              "lookup guarded against TF exceptions"),
        "tf_latest_time": Check(_tf_latest_time, [C_TF_ROW],
                                "asks for the latest transform instead of a now() timestamp"),
    },
)


def _yaml_node_key(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    if not _has(src, r"ros__parameters"):
        return None
    return _has(src, r"^\s*(/\*\*|my_node|/my_node):", r"^\s*\S*my_node\S*:")


def _param_callback(answer: str) -> bool | None:
    text = answer or ""
    if not text.strip():
        return None
    return _has(text, r"add_on_set_parameters_callback")


def _param_declare(answer: str) -> bool | None:
    text = answer or ""
    if not text.strip():
        return None
    return _has(text, r"declare_parameter")


P_PARAMS = Probe(
    id="param-runtime",
    suite="core",
    skill="ros2-core",
    prompt=(
        "I have a ROS 2 Jazzy Python node called `my_node` in package `demo`. It has a "
        "`max_speed` setting. Give me the params YAML that sets it to 0.8, the launch "
        "command that loads it, and the node code — and it has to pick up the new value "
        "while running when I do `ros2 param set /my_node max_speed 0.4`."
    ),
    checks={
        "yaml_node_key": Check(_yaml_node_key, [C_PARAM_YAML_ROW],
                               "YAML top-level key matches the node name or uses /**"),
        "param_callback": Check(_param_callback, [C_PARAM_CB_ROW],
                                "a set-parameters callback actually applies the new value"),
        "param_declare": Check(_param_declare, [C_PARAM_SYM],
                               "parameter is declared — control check, near-universal prior"),
    },
)


def _executor_multithreaded(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"MultiThreadedExecutor")


def _executor_callback_group(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ReentrantCallbackGroup", r"MutuallyExclusiveCallbackGroup")


P_EXECUTOR = Probe(
    id="executor-starve",
    suite="core",
    skill="ros2-core",
    prompt=(
        "Write a ROS 2 Jazzy Python node with a 10 Hz timer that publishes a heartbeat, "
        "and that also calls a service `/slow_thing` (`std_srvs/srv/Trigger`) which takes "
        "about 2 seconds to answer. The heartbeat must keep going out at 10 Hz while a "
        "service call is in flight. Give me the complete file."
    ),
    checks={
        "multithreaded": Check(_executor_multithreaded, [C_EXEC_ROW],
                               "MultiThreadedExecutor rather than the default spin"),
        "callback_group": Check(_executor_callback_group, [C_EXEC_ROW],
                                "callbacks separated into callback groups"),
    },
)


def _no_ros1(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return not _has(src, r"\brospy\b", r"ros::init", r"\bcatkin\b", r"NodeHandle")


P_ROS1 = Probe(
    id="ros1-leak",
    suite="core",
    skill="ros2-core",
    prompt=(
        "Write the minimal ROS 2 Jazzy Python publisher that sends "
        "`std_msgs/msg/String` on `/chatter` at 1 Hz. Complete file."
    ),
    checks={
        "no_ros1": Check(_no_ros1, [C_ROS1_RULE],
                         "no ROS 1 idioms — expected to be satisfied without any skill"),
    },
    note="Deliberately a rule the model should already know. If naked passes at 5/5, the line is a cut candidate.",
)


def _domain_id(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"ROS_DOMAIN_ID")


def _rmw_impl(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"RMW_IMPLEMENTATION", r"rmw_fastrtps", r"rmw_cyclonedds")


def _multicast(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"multicast", r"firewall")


P_DOMAIN = Probe(
    id="cross-host-discovery",
    suite="core",
    skill="ros2-core",
    prompt=(
        "Two computers on the same LAN each run ROS 2 Jazzy nodes. On each machine "
        "`ros2 topic list` shows only that machine's own topics — they never see each "
        "other. What is wrong and how do I fix it?"
    ),
    checks={
        "domain_id": Check(_domain_id, [C_DOMAIN_ROW], "names ROS_DOMAIN_ID"),
        "rmw_impl": Check(_rmw_impl, [C_DOMAIN_ROW], "names the RMW implementation as a cause"),
        "multicast": Check(_multicast, [C_DOMAIN_ROW], "names multicast/firewall"),
    },
)


# --- ros2-security suite ------------------------------------------------------

C_SEC_ARCH = "ros2-security:1architecture:01"
C_SEC_NAV_CONCEPTS = "ros2-security:2documentation-entry-points:01"
C_SEC_NAV_TUTORIAL = "ros2-security:2documentation-entry-points:02"
C_SEC_NAV_VERIFY = "ros2-security:2documentation-entry-points:03"
C_SEC_CLI = "ros2-security:a-sros2-cli-commands:01"
C_SEC_POLICY = "ros2-security:b-high-level-access-control-policy-polic:01"


def _sec_create_keystore(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ros2 security create_keystore")


def _sec_create_enclave(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ros2 security create_enclave")


def _sec_enclave_flag(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"--enclave\b")


def _sec_env_enable(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ROS_SECURITY_ENABLE")


def _sec_env_strategy(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ROS_SECURITY_STRATEGY")


def _sec_env_keystore(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ROS_SECURITY_KEYSTORE")


P_SEC_KEYSTORE = Probe(
    id="sros2-keystore",
    suite="security",
    skill="ros2-security",
    prompt=(
        "I have a ROS 2 Jazzy node called `talker` (package `demo_nodes_cpp`) that I "
        "need to run inside enclave `/talker_listener/talker` with DDS security "
        "enabled. Give me every command and environment variable needed, from "
        "creating the keystore through launching the node with security turned on."
    ),
    checks={
        "create_keystore": Check(_sec_create_keystore, [C_SEC_CLI],
                                 "creates the root keystore via ros2 security create_keystore"),
        "create_enclave": Check(_sec_create_enclave, [C_SEC_CLI],
                                "creates the enclave via ros2 security create_enclave"),
        "enclave_flag": Check(_sec_enclave_flag, [C_SEC_CLI],
                              "launches the node with --enclave"),
        "env_enable": Check(_sec_env_enable, [C_SEC_CLI], "sets ROS_SECURITY_ENABLE"),
        "env_strategy": Check(_sec_env_strategy, [C_SEC_CLI], "sets ROS_SECURITY_STRATEGY"),
        "env_keystore": Check(_sec_env_keystore, [C_SEC_CLI], "sets ROS_SECURITY_KEYSTORE"),
    },
    note="Covers the whole CLI code block; carries the doc-pointer and architecture "
         "claims as extras so the interference sweep touches all 6 claims.",
    extra_claims=[C_SEC_NAV_CONCEPTS, C_SEC_NAV_TUTORIAL, C_SEC_NAV_VERIFY, C_SEC_ARCH],
)


def _sec_policy_root(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return bool(re.search(r"<policy\b", src)) and bool(re.search(r"version\s*=", src))


def _sec_policy_enclave_path(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"<enclave\s+path\s*=")


def _sec_policy_profile_node(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"<profile\s+node\s*=")


def _sec_policy_topics_allow(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r'publish\s*=\s*"ALLOW"', r"publish\s*=\s*'ALLOW'")


def _sec_policy_topic_name(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"<topic>\s*chatter\s*</topic>")


P_SEC_POLICY = Probe(
    id="sros2-access-policy",
    suite="security",
    skill="ros2-security",
    prompt=(
        "Write the SROS2 access-control policy XML that goes in the keystore's "
        "policies folder for enclave `/talker_listener/talker`. It should let the "
        "node `talker` in namespace `/` publish on topic `chatter`, and nothing else."
    ),
    checks={
        "policy_root": Check(_sec_policy_root, [C_SEC_POLICY], "root <policy version=...> element"),
        "enclave_path": Check(_sec_policy_enclave_path, [C_SEC_POLICY], "<enclave path=...> element"),
        "profile_node": Check(_sec_policy_profile_node, [C_SEC_POLICY], "<profile node=...> element"),
        "topics_allow": Check(_sec_policy_topics_allow, [C_SEC_POLICY], "publish=\"ALLOW\" attribute"),
        "topic_name": Check(_sec_policy_topic_name, [C_SEC_POLICY], "<topic>chatter</topic> element"),
    },
)


def _sec_arch_dds_security(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"DDS-Security", r"DDS Security")


def _sec_arch_pki(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"X\.509", r"\bPKI\b")


def _sec_arch_rmw_backend(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"Fast ?DDS", r"FastRTPS", r"Cyclone ?DDS")


P_SEC_ARCH = Probe(
    id="sros2-mechanism",
    suite="security",
    skill="ros2-security",
    prompt=(
        "In ROS 2 Jazzy, when SROS2 security is turned on, what actually "
        "authenticates nodes to each other and enforces the access-control rules "
        "under the hood — not the CLI commands, the underlying mechanism?"
    ),
    checks={
        "dds_security": Check(_sec_arch_dds_security, [C_SEC_ARCH], "names DDS-Security"),
        "pki": Check(_sec_arch_pki, [C_SEC_ARCH], "names X.509/PKI authentication"),
        "rmw_backend": Check(_sec_arch_rmw_backend, [C_SEC_ARCH], "names a DDS-Security-capable RMW"),
    },
    note="Deliberately a fact the model may already know cold — cut candidate if naked is high.",
)


# --- ros2-testing suite -------------------------------------------------------
# Third skill; also the first suite that turns on the "addition" and "position"
# cases (`only:<id>` = does this one claim alone suffice; `reorder:4,1,2,3` =
# does moving the symptom table ahead of the doc pointers change anything)
# alongside the usual single/joint deletion. Repeats kept at the statistical
# floor (n=4 — the smallest sample where a clean 0/n vs n/n can still reach
# p<0.05) since the case count per claim roughly triples; anything that looks
# ambiguous gets a targeted top-up rather than a blanket re-run, same as the
# false negatives caught in ros2-core and ros2-security.

C_T_NAV1 = "ros2-testing:1documentation-entry-points:01"
C_T_NAV2 = "ros2-testing:1documentation-entry-points:02"
C_T_NAV3 = "ros2-testing:1documentation-entry-points:03"
C_T_RUN1 = "ros2-testing:2running-tests:01"
C_T_RUN2 = "ros2-testing:2running-tests:02"
C_T_WRITER = "ros2-testing:a-programmatic-rosbag2-writer-c:01"
C_T_LAUNCH = "ros2-testing:b-integration-testing-launch-testing-pyt:01"
C_T_READY = "ros2-testing:b-integration-testing-launch-testing-pyt:02"
C_T_SYM01 = "ros2-testing:4symptom-root-cause-action:01"
C_T_SYM02 = "ros2-testing:4symptom-root-cause-action:02"
C_T_SYM03 = "ros2-testing:4symptom-root-cause-action:03"
C_T_SYM04 = "ros2-testing:4symptom-root-cause-action:04"
C_T_SYM05 = "ros2-testing:4symptom-root-cause-action:05"
C_T_SYM06 = "ros2-testing:4symptom-root-cause-action:06"

REORDER_SYMPTOMS_FIRST = "reorder:4,1,2,3"


def _t_verbose_flag(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"--verbose")


def _t_checks_test_count(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"expected", r"registered", r"test count")


def _t_names_test_result(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"colcon test-result")


P_T_COLCON = Probe(
    id="colcon-trust",
    suite="testing",
    skill="ros2-testing",
    prompt=(
        "I just ran `colcon test --packages-select my_package` and it printed "
        "`Summary: 3 tests, 0 errors, 0 failures, 0 skipped`. Before I trust that "
        "and move on, what exactly should I check to make sure this is telling "
        "the truth, and what commands do I run?"
    ),
    checks={
        "names_verbose": Check(_t_verbose_flag, [C_T_RUN1, C_T_SYM02],
                               "names --verbose to see per-case detail"),
        "checks_test_count": Check(_t_checks_test_count, [C_T_RUN2, C_T_SYM01],
                                   "checks the test count against what's expected, not just the exit code"),
        "names_test_result": Check(_t_names_test_result, [C_T_RUN1, C_T_SYM01],
                                   "names colcon test-result as the place the real detail lives"),
    },
    note="Three claims (2running-tests x2, symptom row 01) all push the same "
         "'don't trust the summary' behaviour, plus symptom row 02 pushes "
         "--verbose specifically. Declared as one joint group rather than found "
         "after the fact from single-ablation collisions.",
    extra_claims=[C_T_NAV1, C_T_NAV2, C_T_NAV3],
    joint=[[C_T_RUN1, C_T_RUN2, C_T_SYM01, C_T_SYM02]],
    probe_only=True,
    extra_conditions=[REORDER_SYMPTOMS_FIRST],
)


def _t_writer_header(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"rosbag2_cpp/writer\.hpp")


def _t_writer_create_topic(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"create_topic")


def _t_writer_write_call(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"\.write<", r"\.write\(")


P_T_ROSBAG_WRITE = Probe(
    id="rosbag2-write",
    suite="testing",
    skill="ros2-testing",
    prompt=(
        "Write a minimal C++ snippet that programmatically records a single "
        "`std_msgs/msg/String` message to a new rosbag2 bag called `my_bag` on "
        "topic `chatter`. Just the rosbag2-writing part, not a whole node."
    ),
    checks={
        "writer_header": Check(_t_writer_header, [C_T_WRITER], "includes rosbag2_cpp/writer.hpp"),
        "writer_create_topic": Check(_t_writer_create_topic, [C_T_WRITER], "registers the topic before writing"),
        "writer_write_call": Check(_t_writer_write_call, [C_T_WRITER], "calls Writer::write"),
    },
    probe_only=True,
    extra_conditions=[REORDER_SYMPTOMS_FIRST],
)


def _t_ready_to_test(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ReadyToTest\(\)")


def _t_post_shutdown(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"post_shutdown_test")


def _t_exit_code_check(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"assertExitCodes")


P_T_LAUNCH_TESTING = Probe(
    id="launch-testing-node",
    suite="testing",
    skill="ros2-testing",
    prompt=(
        "Write a `launch_testing` Python test that starts a `talker` node from "
        "`demo_nodes_cpp`, asserts it started successfully, and also checks the "
        "process exited cleanly after shutdown. Complete file."
    ),
    checks={
        "ready_to_test": Check(_t_ready_to_test, [C_T_LAUNCH, C_T_READY],
                               "marks the launch/test boundary with ReadyToTest()"),
        "post_shutdown": Check(_t_post_shutdown, [C_T_LAUNCH, C_T_READY],
                               "uses a @post_shutdown_test() class for exit checks"),
        "exit_code_check": Check(_t_exit_code_check, [C_T_LAUNCH],
                                 "asserts exit codes via launch_testing.asserts"),
    },
    note="The code block and the ReadyToTest() explanation are a second "
         "candidate redundancy pair, same shape as ros2-core's shutdown pair.",
    extra_claims=[C_T_SYM03],
    joint=[[C_T_LAUNCH, C_T_READY]],
    probe_only=True,
    extra_conditions=[REORDER_SYMPTOMS_FIRST],
)


def _t_hang_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"ReadyToTest")


def _t_ci_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"wall.?clock", r"sourced workspace", r"clean shell",
                r"wait.?for.?message", r"wait_for")


def _t_qos_test_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"\bQoS\b")


def _t_simtime_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"use_sim_time", r"--clock", r"/clock\b")


P_T_DIAGNOSE = Probe(
    id="testing-diagnose",
    suite="testing",
    skill="ros2-testing",
    prompt=(
        "For each of these ROS 2 Jazzy testing problems, give the root cause and "
        "the fix in one line each:\n"
        "1. A `launch_testing` test hangs forever and never finishes.\n"
        "2. `colcon test` passes locally but the same tests fail in CI.\n"
        "3. In an integration test, the node under test never receives the test "
        "fixture's published messages, even though the topic looks connected.\n"
        "4. Rosbag2 playback inside a test produces no callbacks even though the "
        "bag file has messages."
    ),
    checks={
        "hang_cause": Check(_t_hang_cause, [C_T_SYM03], "names ReadyToTest() as the missing boundary"),
        "ci_cause": Check(_t_ci_cause, [C_T_SYM04], "names wall-clock/workspace state as the cause"),
        "qos_test_cause": Check(_t_qos_test_cause, [C_T_SYM05], "names a QoS mismatch"),
        "simtime_cause": Check(_t_simtime_cause, [C_T_SYM06], "names use_sim_time/--clock alignment"),
    },
    note="One prompt, four independent scenarios — covers the four symptom rows "
         "that aren't part of another probe's joint group.",
    probe_only=True,
    extra_conditions=[REORDER_SYMPTOMS_FIRST],
)


PROBES: list[Probe] = [
    P_SCAN, P_TF, P_PARAMS, P_EXECUTOR, P_ROS1, P_DOMAIN, P_ODOM,
    P_SEC_KEYSTORE, P_SEC_POLICY, P_SEC_ARCH,
    P_T_COLCON, P_T_ROSBAG_WRITE, P_T_LAUNCH_TESTING, P_T_DIAGNOSE,
]
