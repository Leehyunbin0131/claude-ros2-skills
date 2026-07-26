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
        if include_only:
            conds += [f"only:{cid}" for cid in self.claim_ids]
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


PROBES: list[Probe] = [P_SCAN, P_TF, P_PARAMS, P_EXECUTOR, P_ROS1, P_DOMAIN, P_ODOM]
