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

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

# --- extraction helpers ------------------------------------------------------

FENCE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", re.S)

# Tools are off in this harness by design (see README: measuring unaided prior
# knowledge, not tool use), but sonnet reaches for one more readily than haiku
# did and, finding none, sometimes stops after the attempt instead of
# answering. The stub text varies by tool/rendering ("**Tool: bash**",
# "**tool_call**: Bash", raw `{"command": ...}` JSON, `<tool_call name=...>`),
# but is always short. Found 2026-07-28 re-checking ros2-core on sonnet: every
# `param_callback`/`param_declare` failure in a confirmation run was one of
# these, not a real miss -- and worse, a few had accidentally been scored a
# *pass* because the tool-call payload happened to mention the target function
# name while trying to look it up, never having written it.
_TOOL_STUB_RE = re.compile(
    # Loose on purpose: "Tool" followed by a colon within a short window,
    # case-sensitive so lowercase "the tool: X" in ordinary prose is never
    # swept up. Went through three narrower drafts before this one --
    # "**Tool:", "**tool_call**:", an icon glyph in front of the word, and
    # "Tool Call:" (a space instead of an underscore) were each a distinct
    # miss found on 2026-07-28, and each scored a hard False rather than
    # ungradable before being caught. Anchoring to
    # "right after **" or to an exact separator character kept losing to the
    # next rendering; matching the word and the colon loosely does not.
    r"\bTool\b.{0,20}:"
    r"|<\s*tool_call\b"
    r"|^\s*tool_use\s*$"
    r"|\bINPUT:\s*[`{]"
    r"|^\s*\*{0,2}\s*\{\s*\"(?:command|description)\"\s*:"
    r"|\*\[Tool\s+execution\s+failed\]\*"
    r"|\[Errno\s+2\]\s+No\s+such\s+file\s+or\s+directory:\s*'[a-zA-Z_]+'"
    # Function-call-shaped tool invocation rendering, e.g.
    # `Search(pattern: "ros2-*", path: "...")` -- found 2026-07-28, where
    # "let me check for a relevant skill... Search(...)" scored a hard False
    # on real content questions instead of ungradable.
    r"|\b[A-Z][A-Za-z]*\([a-z_]+\s*:\s*[\"']",
    re.M,
)


def _is_tool_stub(answer: str | None) -> bool:
    """True when the answer is a stub tool-call attempt with nothing real
    after it. Length-gated (real answers to these probes run well over 700
    chars; every stub sampled was under 400) so a long answer that merely
    mentions a tool in passing while still delivering real content is never
    swept up.
    """
    if not answer or len(answer) >= 700:
        return False
    return bool(_TOOL_STUB_RE.search(answer))


def code(answer: str, lang_hint: str = "python") -> str | None:
    """Concatenated fenced code, or None when the answer contains none.

    Falls back to the whole answer only when it looks like bare code, so a prose
    reply that merely mentions `range_min` is never graded as if it wrote it.
    """
    if _is_tool_stub(answer):
        return None
    blocks = FENCE.findall(answer or "")
    if blocks:
        return "\n".join(blocks)
    if answer and re.search(r"^\s*(import rclpy|#include|def main\()", answer, re.M):
        return answer
    return None


def prose(answer: str) -> str | None:
    if _is_tool_stub(answer):
        return None
    return answer if (answer or "").strip() else None


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text) for p in patterns)


# --- real-build grading -------------------------------------------------------
# Regex checks are a proxy: "did the text contain the right pattern." For
# ros2-package the actual ground truth is "does the package build and does
# `ros2 run` find the executable" -- and colcon/ros2 are installed right here,
# so nothing forces settling for the proxy. Kept to one hybrid probe (below)
# rather than every probe, because a build+run cycle costs seconds, not
# milliseconds, and doesn't need repeating per claim to make its point.

FILE_BLOCK = re.compile(r"FILE:\s*(\S+)\s*\n```[a-zA-Z0-9_+-]*\n(.*?)```", re.S)


def _extract_files(answer: str) -> dict[str, str] | None:
    if not answer:
        return None
    matches = FILE_BLOCK.findall(answer)
    if not matches:
        return None
    return {path.strip().lstrip("/"): content for path, content in matches}


@lru_cache(maxsize=256)
def _build_and_check(answer: str, pkg_name: str, node_name: str) -> tuple[bool | None, bool | None]:
    """Write the answer's files into a fresh workspace, colcon build, and check
    the entry point is discoverable afterward.

    Returns (builds_clean, executable_discoverable); either is None when there
    was nothing to grade (no FILE: blocks) or the question doesn't apply
    (executable_discoverable is None when the build itself already failed).
    `ros2 pkg executables` reflects the *installed* location, not just whether
    setup.py declared an entry point, so a package missing `setup.cfg`
    (script_dir/install_scripts) builds clean but comes back with the
    executable un-discoverable — verified by hand against this exact pipeline
    before wiring it in.
    """
    files = _extract_files(answer)
    if not files:
        return None, None
    tmp = tempfile.mkdtemp(prefix="ros2pkg_probe_")
    try:
        ws = os.path.join(tmp, "ws")
        pkg_root = os.path.join(ws, "src", pkg_name)
        for rel_path, content in files.items():
            full = os.path.join(pkg_root, rel_path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(content)
        try:
            build = subprocess.run(
                ["bash", "-c",
                 f"source /opt/ros/jazzy/setup.bash && cd {ws!r} && "
                 f"colcon build --packages-select {pkg_name} --symlink-install"],
                capture_output=True, text=True, timeout=90,
            )
        except subprocess.TimeoutExpired:
            return False, None
        if build.returncode != 0:
            return False, None
        try:
            exe = subprocess.run(
                ["bash", "-c",
                 f"source /opt/ros/jazzy/setup.bash && source {os.path.join(ws, 'install', 'setup.bash')!r} && "
                 f"ros2 pkg executables {pkg_name}"],
                capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            return True, False
        return True, node_name in exe.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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

# Re-read against claims.jsonl 2026-07-28: the confirmation commit that cut
# ros2-core to 45 lines (d647ed8) renumbered sections 2, 4 and 5, and these
# constants were never updated to match. Every ablate:<id> condition on the
# nine affected ids either hit the wrong line or (for :04/:05/:07/:08, which
# no longer exist) crashed KeyError -- caught only now, on the first full
# re-sweep since that cut, because the original confirmation run was
# naked-vs-full only and never re-exercised per-claim ablation. The ROS1-idiom
# rule and both Parameters symptom rows were among the five lines that cut;
# their constants now point at no claim (claims=[] below) rather than at
# whatever line inherited their old number.
# Re-read again 2026-07-28 after the sonnet re-check cut two more claims: the
# TF-catch rule (old 5strict:01) and the TF-Extrapolation symptom row (old
# 4symptom:03) both hit naked=full=ablate=1.00 -- sonnet needs no prompting for
# either, joint-tested for the rule (see git history) before cutting. The TF2
# symbols bullet (2symbols:01) individually read the same way but was kept: it
# bundles the (now-redundant) exception-symbol list with an untested REP105
# frame-convention pointer to ros2-troubleshooting in one claim atom, and nothing
# has measured that pointer's half on its own. Splitting the bullet so each half
# can be judged on its own evidence is future work, not done here.
C_QOS_RULE = "ros2-core:5strict-coding-rules:01"
C_QOS_ROW = "ros2-core:4symptom-root-cause-action:01"
C_QOS_SYM = "ros2-core:2symbols-to-verify-there-never-write-the:02"
C_BOUNDS_RULE = "ros2-core:5strict-coding-rules:02"
C_BOUNDS_ROW = "ros2-core:4symptom-root-cause-action:04"
C_SHUTDOWN_RULE = "ros2-core:5strict-coding-rules:03"
C_SHUTDOWN_ROW = "ros2-core:4symptom-root-cause-action:05"
C_TF_RULE = None  # rule was cut
C_TF_SYM = "ros2-core:2symbols-to-verify-there-never-write-the:01"
C_TF_ROW = None  # symptom row was cut
C_ROS1_RULE = None  # rule was cut; no-ros1 check now owns no claim
C_PARAM_YAML_ROW = None  # symptom row was cut
C_PARAM_CB_ROW = None  # symptom row was cut
C_PARAM_SYM = None  # symbols bullet was cut
C_EXEC_ROW = "ros2-core:4symptom-root-cause-action:03"
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
        "ros2-core:2symbols-to-verify-there-never-write-the:03",
        "ros2-core:3local-system-inspection-interfaces-grou:01",
        "ros2-core:3local-system-inspection-interfaces-grou:02",
        "ros2-core:3local-system-inspection-interfaces-grou:03",
        C_TF_SYM,
        C_EXEC_ROW, C_DOMAIN_ROW,
        # C_TF_RULE / C_TF_ROW / C_ROS1_RULE / C_PARAM_YAML_ROW / C_PARAM_CB_ROW
        # / C_PARAM_SYM are not
        # listed: those four claims were cut from the shipped body, so there is
        # nothing left at those old ids to ablate for the interference sweep.
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
        "tf_exception": Check(_tf_exception, [C_TF_SYM],
                              "lookup guarded against TF exceptions — C_TF_RULE used to co-own "
                              "this with C_TF_SYM (joint-tested 2026-07-28: naked=full=drop-both="
                              "1.00, p=1.000); the rule was cut, C_TF_SYM is the one claim left"),
        "tf_latest_time": Check(_tf_latest_time, [],
                                "asks for the latest transform instead of a now() timestamp — its "
                                "own symptom row was cut (naked=full=ablate=1.00, no redundancy "
                                "partner); ground-truth guard, not an ablation instrument"),
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
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"add_on_set_parameters_callback")


def _param_declare(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
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
        "yaml_node_key": Check(_yaml_node_key, [],
                               "YAML top-level key matches the node name or uses /** — its own "
                               "symptom row was cut in the original ros2-core confirmation run"),
        "param_callback": Check(_param_callback, [],
                                "a set-parameters callback actually applies the new value — its "
                                "own symptom row was cut in the original ros2-core confirmation run"),
        "param_declare": Check(_param_declare, [],
                               "parameter is declared — control check, near-universal prior; its "
                               "own symbols bullet was cut in the original ros2-core confirmation run"),
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
        "no_ros1": Check(_no_ros1, [],
                         "no ROS 1 idioms — the rule that used to state this was already cut "
                         "in the original ros2-core confirmation run; kept as a ground-truth "
                         "guard, not an ablation instrument"),
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


# --- ros2-testing suite -------------------------------------------------------
# Third skill; also the first suite that turns on the "addition" and "position"
# cases (`only:<id>` = does this one claim alone suffice; `reorder:4,1,2,3` =
# does moving the symptom table ahead of the doc pointers change anything)
# alongside the usual single/joint deletion. Repeats kept at the statistical
# floor (n=4 — the smallest sample where a clean 0/n vs n/n can still reach
# p<0.05) since the case count per claim roughly triples; anything that looks
# ambiguous gets a targeted top-up rather than a blanket re-run, same as the
# false negatives caught in ros2-core.

# Re-read against claims.jsonl 2026-07-28, twice. First pass: the 78->76 cut
# removed the launch_testing-hang and CI rows at old :03/:04 and renumbered the
# QoS and use_sim_time rows down from :05/:06, so C_T_SYM03/04 had been silently
# pointing at the wrong claim's text (wrong content, not a crash, so nothing
# caught it) and C_T_SYM05/06 at ids that no longer existed.
#
# Second pass, same day: `variant:compressed` was adopted (76 -> 42 lines) after
# tying `full` on all 13 checks at n=8. That rewrite merged two redundancy
# groups the sweep had flagged, which collapsed four claims into two and
# renumbered the symptom table again:
#   * the colcon code block, its prose, and symptom rows :01 (test count) and
#     :02 (--verbose) all became one sentence -> C_T_RUN1. RUN2/SYM01/SYM02 gone.
#   * the launch_testing code block and the ReadyToTest prose became one
#     sentence -> C_T_LAUNCH. READY gone.
#   * the QoS and use_sim_time rows are the only symptom rows left, so they
#     renumbered from :03/:04 to :01/:02 -- which is why SYM05/SYM06 (their
#     stable names here) now hold the *low* numbers. Do not "tidy" that up.
C_T_NAV1 = "ros2-testing:1documentation-entry-points:01"
C_T_NAV2 = "ros2-testing:1documentation-entry-points:02"
C_T_NAV3 = "ros2-testing:1documentation-entry-points:03"
C_T_RUN1 = "ros2-testing:2running-tests:01"  # merged colcon sentence
C_T_RUN2 = None  # merged into C_T_RUN1 by variant:compressed
C_T_WRITER = "ros2-testing:a-programmatic-rosbag2-writer-c:01"
C_T_LAUNCH = "ros2-testing:b-integration-testing-launch-testing-pyt:01"  # merged
C_T_READY = None  # merged into C_T_LAUNCH by variant:compressed
C_T_SYM01 = None  # test-count row folded into C_T_RUN1
C_T_SYM02 = None  # --verbose row folded into C_T_RUN1
C_T_SYM03 = None  # launch_testing-hang row was cut
C_T_SYM04 = None  # CI row was cut
C_T_SYM05 = "ros2-testing:4symptom-root-cause-action:01"  # QoS row, renumbered twice
C_T_SYM06 = "ros2-testing:4symptom-root-cause-action:02"  # sim_time row, renumbered twice

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
        "names_verbose": Check(_t_verbose_flag, [C_T_RUN1],
                               "names --verbose to see per-case detail"),
        "checks_test_count": Check(_t_checks_test_count, [C_T_RUN1],
                                   "checks the test count against what's expected, not just the exit code"),
        "names_test_result": Check(_t_names_test_result, [C_T_RUN1],
                                   "names colcon test-result as the place the real detail lives"),
    },
    note="Was a declared four-claim redundancy group (2running-tests x2 plus "
         "symptom rows 01/02) all pushing the same 'don't trust the summary' "
         "behaviour. The joint ablation came back Δ=0 on all three checks, and "
         "variant:compressed then merged the four into one sentence with no "
         "loss, so there is a single claim here now and nothing left to join.",
    extra_claims=[C_T_NAV1, C_T_NAV2, C_T_NAV3],
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
        "ready_to_test": Check(_t_ready_to_test, [C_T_LAUNCH],
                               "marks the launch/test boundary with ReadyToTest()"),
        "post_shutdown": Check(_t_post_shutdown, [C_T_LAUNCH],
                               "uses a @post_shutdown_test() class for exit checks"),
        "exit_code_check": Check(_t_exit_code_check, [C_T_LAUNCH],
                                 "asserts exit codes via launch_testing.asserts"),
    },
    note="The code block and the ReadyToTest() explanation were a declared "
         "redundancy pair, same shape as ros2-core's shutdown pair; the joint "
         "ablation showed no effect and variant:compressed replaced both with "
         "one sentence, tying 8/8 on all three checks. Worth recording that the "
         "prose version produced *better* code than the block it replaced -- "
         "answers added @pytest.mark.launch_test, assertWaitForStartup, and the "
         "add_launch_test() CMake call, all verified present in the Jazzy "
         "install, none of which the original example showed. "
         "(The old interference claim here, C_T_SYM03, was the launch_testing-hang "
         "symptom row; it was cut, so there is nothing left at that id to ablate.)",
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
        "hang_cause": Check(_t_hang_cause, [], "names ReadyToTest() as the missing boundary — its "
                            "own symptom row was cut; ground-truth guard, not an ablation instrument"),
        "ci_cause": Check(_t_ci_cause, [], "names wall-clock/workspace state as the cause — its "
                          "own symptom row was cut; ground-truth guard, not an ablation instrument"),
        "qos_test_cause": Check(_t_qos_test_cause, [C_T_SYM05], "names a QoS mismatch"),
        "simtime_cause": Check(_t_simtime_cause, [C_T_SYM06], "names use_sim_time/--clock alignment"),
    },
    note="One prompt, four independent scenarios — covers the four symptom rows "
         "that aren't part of another probe's joint group.",
    probe_only=True,
    extra_conditions=[REORDER_SYMPTOMS_FIRST],
)


# --- ros2-package suite -------------------------------------------------------
# Fourth skill. Two things distinguish it from the first three: the highest
# duplication density found so far (the symptom table largely restates the
# code-block sections), and a ground truth stronger than any regex -- does the
# package actually build and does `ros2 run` find the executable, both
# available right here via colcon. Hybrid grading per the user's direction:
# regex for the per-claim ablation probes (cheap, consistent with prior
# suites), one dedicated real-build probe for ground truth (below), kept out
# of the ablation sweep entirely so its cost doesn't multiply by claim count.

# Claim ids below match the shipped body, which an earlier haiku-graded pass had
# already reduced: 15 claims cut (naked at ceiling, nothing else depended on
# them alone), 2 added (package.xml export tag, setup.cfg script_dir), and the
# two full reference code blocks (ament-cmake:01, ament-python:01) plus the
# 4custom-interfaces CMake/XML blocks kept regardless of per-clause ceiling
# effects, on structural-completeness grounds rather than statistical ones.
# Those runs were deleted with the rest of the haiku-era record; the skill is
# back to IN PROGRESS pending a sonnet sweep, and these ids will need
# re-validating against claims.jsonl before it runs -- ids shift whenever a
# section's numbering closes a gap, exactly like ablate() does to a reduced
# body.
#
# The symptom row (old 6symptom:02, ModuleNotFoundError) and the "one concern
# per package" rule (old 7strict-rules:01) were briefly restored after three
# confirmation runs (confirm/confirm2/confirm3) reported them as regressions.
# Those reports were themselves the artifact: the ad hoc analysis script used
# for those runs keyed its per-check tallies on (probe, check) instead of
# (probe, condition, check), so naked-condition failures bled into the full
# tallies. Recomputed with the same 3-key scheme analyze.py uses, there were
# no significant regressions. Both lines are cut again here; C_PKG_SYM_IFACE
# and C_PKG_RULE_ONE_CONCERN no longer have a claim id to point to.
# Re-mapped 2026-07-28 after variant:compressed shipped (115 -> 69 lines). The
# rewrite dropped four whole claims and merged the wiring section, so every
# section number below the doc pointers shifted. Constant NAMES are stable and
# deliberately no longer track the digits in their ids -- C_PKG_CMAKE_WIRING is
# now :01 of section 2, not "ament-cmake:01". That mismatch looks like a bug and
# is not; do not "fix" it by renaming to match.
#
# What went, and why (n=4 sweep + targeted top-ups, sonnet):
#   scaffolding block, the ament_cmake code block, the ament_python data_files/
#   entry_points block, the colcon build/source block and the launch-install
#   symptom row all measured naked = full = ablate = 1.00. The two code blocks
#   became two prose sentences; the compressed body then tied `full` on all 27
#   checks at n=8, including the real-build ground-truth probe.
# What stayed: the setup.cfg block and all four interface claims came back
#   UNDERPOWERED with large positive deltas, which is not a cut.
C_PKG_INTRO = "ros2-package:ros-2-package-creation-build-wiring-ubun:01"
C_PKG_NAV1 = "ros2-package:1documentation-entry-points:01"
C_PKG_NAV2 = "ros2-package:1documentation-entry-points:02"
C_PKG_NAV3 = "ros2-package:1documentation-entry-points:03"
C_PKG_CREATE_CMD = None  # scaffolding block cut (naked 4/4 = full 4/4)
C_PKG_CMAKE_WIRING = "ros2-package:2the-wiring-that-makes-a-node-runnable:01"
C_PKG_PYSETUP = None  # data_files/entry_points block cut, folded into the below
C_PKG_EXPORT_TAG = "ros2-package:2the-wiring-that-makes-a-node-runnable:02"
C_PKG_SETUP_CFG = "ros2-package:2the-wiring-that-makes-a-node-runnable:03"
C_PKG_IFACE_LOC = "ros2-package:3custom-interfaces-msg-srv:01"
C_PKG_IFACE_CMAKE = "ros2-package:3custom-interfaces-msg-srv:02"
C_PKG_IFACE_XML = "ros2-package:3custom-interfaces-msg-srv:03"
C_PKG_IFACE_VERIFY = "ros2-package:3custom-interfaces-msg-srv:04"
C_PKG_BUILD_CMD = None  # colcon build/source block cut (naked 4/4 = full 4/4)
C_PKG_SYM_LAUNCH = None  # launch-install symptom row cut (naked 4/4 = full 4/4)
C_PKG_RULE_RESOURCE = "ros2-package:4strict-rules:01"


def _pkg_create_cmd(answer: str) -> bool | None:
    text = code(answer) or prose(answer)
    if text is None:
        return None
    return _has(text, r"ros2 pkg create") and _has(text, r"--build-type\s+ament_python") \
        and _has(text, r"--node-name")


def _pkg_resource_dir(answer: str) -> bool | None:
    text = code(answer) or prose(answer)
    if text is None:
        return None
    return _has(text, r"resource/", r"resource_index")


P_PKG_CREATE = Probe(
    id="pkg-create",
    suite="package",
    skill="ros2-package",
    prompt=(
        "What's the exact command to create a new ROS 2 Jazzy ament_python "
        "package called `my_package` with a starter node `my_node`? Also tell "
        "me exactly which files and directories that command creates."
    ),
    checks={
        "create_cmd": Check(_pkg_create_cmd, [C_PKG_CREATE_CMD],
                            "the real ros2 pkg create invocation, ament_python + node name"),
        "resource_dir": Check(_pkg_resource_dir, [],
                              "names the resource/ ament-index registration file — "
                              "kept for the confirmation run; its own claims (2scaffolding:02/03) "
                              "were cut, naked already at ceiling"),
    },
    note="Carries the doc-pointer and intro-sentence claims as extras so the "
         "interference/only: sweep touches them too.",
    extra_claims=[C_PKG_NAV1, C_PKG_NAV2, C_PKG_NAV3, C_PKG_INTRO],
    probe_only=True,
)


def _pkg_install_targets_lib(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return bool(re.search(r"install\(\s*TARGETS.*?DESTINATION\s+lib/\$\{PROJECT_NAME\}", src, re.S))


def _pkg_target_deps(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ament_target_dependencies", r"target_link_libraries")


def _pkg_install_launch_dir(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return bool(re.search(r"install\(\s*DIRECTORY.*?launch.*?DESTINATION\s+share", src, re.S))


def _pkg_ament_package_call(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"ament_package\(\)")


P_PKG_CMAKE = Probe(
    id="pkg-cmake-wiring",
    suite="package",
    skill="ros2-package",
    prompt=(
        "Write the CMakeLists.txt wiring (find_package, add_executable, "
        "install, ament_package) for a ROS 2 Jazzy ament_cmake package "
        "`my_package` with one C++ node `my_node.cpp` that depends on "
        "`rclcpp`, plus a `launch/` directory that should get installed too."
    ),
    checks={
        "install_targets_lib": Check(_pkg_install_targets_lib, [C_PKG_CMAKE_WIRING],
                                     "install(TARGETS ...) lands at lib/${PROJECT_NAME}, not somewhere else"),
        "target_deps": Check(_pkg_target_deps, [C_PKG_CMAKE_WIRING],
                             "links the dependency so headers resolve"),
        "install_launch_dir": Check(_pkg_install_launch_dir, [C_PKG_CMAKE_WIRING],
                                    "launch/ is explicitly installed, not assumed automatic"),
        "ament_package_call": Check(_pkg_ament_package_call, [C_PKG_CMAKE_WIRING],
                                    "ament_package() present"),
    },
    note="Kept as a whole reference block despite every clause individually "
         "measuring naked=ceiling — see NOTES.md's structural-completeness "
         "discussion. The paired explanatory sentence (old ament-cmake:02) was "
         "cut; this is the sole surviving claim for the block.",
    probe_only=True,
)


def _pkg_console_scripts_entry(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"console_scripts") and \
        bool(re.search(r"my_node\s*=\s*my_package\.my_node:main", src))


def _pkg_resource_index(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"resource_index/packages")


def _pkg_export_build_type(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return bool(re.search(r"<export>\s*<build_type>\s*ament_python\s*</build_type>\s*</export>", src, re.S))


def _pkg_setup_cfg_script_dir(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"script_dir\s*=") and _has(src, r"install_scripts\s*=")


P_PKG_PYENTRY = Probe(
    id="pkg-py-entry",
    suite="package",
    skill="ros2-package",
    prompt=(
        "Write the setup.py `entry_points` and `data_files` sections, the "
        "full `package.xml`, and `setup.cfg`, for a ROS 2 Jazzy ament_python "
        "package `my_package` with node `my_node` (function `main` in "
        "`my_package/my_node.py`), so `ros2 run my_package my_node` finds it "
        "and `colcon build` configures it correctly."
    ),
    checks={
        "console_scripts_entry": Check(_pkg_console_scripts_entry, [C_PKG_PYSETUP],
                                       "a real console_scripts entry point line"),
        "resource_index": Check(_pkg_resource_index, [C_PKG_PYSETUP],
                                "registers the package in the ament index"),
        "setup_cfg_script_dir": Check(_pkg_setup_cfg_script_dir, [C_PKG_SETUP_CFG],
                                      "setup.cfg routes the console_scripts install to lib/<pkg>/"),
        "export_build_type": Check(_pkg_export_build_type, [C_PKG_EXPORT_TAG],
                                   "package.xml declares <export><build_type>ament_python</build_type></export>"),
    },
    note="This check's naked baseline (~0.94) is inflated by this probe's own "
         "prompt explicitly naming 'the full package.xml' — a leading tell "
         "the pkg-build-ground-truth probe's prompt doesn't have. Trust that "
         "probe's naked baseline over this one for export_build_type's verdict; "
         "see NOTES.md.",
    probe_only=True,
)


def _pkg_separate_cmake_pkg(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"ament_cmake", r"separate", r"new package", r"dedicated")


def _pkg_rosidl_generate(answer: str) -> bool | None:
    text = code(answer) or prose(answer)
    if text is None:
        return None
    return _has(text, r"rosidl_generate_interfaces")


def _pkg_iface_xml_tags(answer: str) -> bool | None:
    text = code(answer) or prose(answer)
    if text is None:
        return None
    return _has(text, r"rosidl_default_generators") and _has(text, r"rosidl_default_runtime") \
        and _has(text, r"member_of_group")


def _pkg_iface_verify_cmd(answer: str) -> bool | None:
    text = code(answer) or prose(answer)
    if text is None:
        return None
    return _has(text, r"ros2 interface show")


P_PKG_INTERFACES = Probe(
    id="pkg-interfaces",
    suite="package",
    skill="ros2-package",
    prompt=(
        "I need a custom message `Num.msg` with one `int64 num` field, used by "
        "a package that's currently `ament_python` called `my_package`. Walk "
        "me through exactly how to set this up — package structure, "
        "CMakeLists.txt/package.xml content, and how to verify it worked."
    ),
    checks={
        "separate_cmake_pkg": Check(_pkg_separate_cmake_pkg, [C_PKG_IFACE_LOC],
                                    "interfaces move to a dedicated ament_cmake package"),
        "rosidl_generate": Check(_pkg_rosidl_generate, [C_PKG_IFACE_CMAKE],
                                 "rosidl_generate_interfaces call present"),
        "iface_xml_tags": Check(_pkg_iface_xml_tags, [C_PKG_IFACE_XML],
                                "all three package.xml interface tags present"),
        "verify_cmd": Check(_pkg_iface_verify_cmd, [C_PKG_IFACE_VERIFY],
                            "names ros2 interface show to confirm generation ran"),
    },
    probe_only=True,
)


def _pkg_no_exe_cmake_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"install\(TARGETS", r"lib/\$\{?PROJECT_NAME\}?", r"DESTINATION")


def _pkg_no_exe_python_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"console_scripts", r"entry_points", r"setup\.py")


def _pkg_colcon_no_see_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"src/", r"package\.xml", r"workspace")


def _pkg_list_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"source", r"overlay", r"sourced")


P_PKG_DIAG_BUILD = Probe(
    id="pkg-diagnose-build",
    suite="package",
    skill="ros2-package",
    prompt=(
        "For each of these ROS 2 Jazzy package problems, give the root cause "
        "and the fix in one line each:\n"
        "1. Package builds successfully but `ros2 run my_pkg my_node` says no "
        "executable found (`ament_cmake` package).\n"
        "2. Same symptom, but the package is `ament_python`.\n"
        "3. `colcon build` doesn't seem to see my package at all.\n"
        "4. Package builds, but `ros2 pkg list` doesn't show it and imports fail."
    ),
    checks={
        "no_exe_cmake_cause": Check(_pkg_no_exe_cmake_cause, [],
                                    "names the install(TARGETS) destination — its own claim "
                                    "(old 6symptom:01) was cut, naked was already 1.00"),
        "no_exe_python_cause": Check(_pkg_no_exe_python_cause, [],
                                     "names the missing console_scripts entry — its own claim "
                                     "(old 6symptom:02) was cut, naked was already 1.00"),
        "colcon_no_see_cause": Check(_pkg_colcon_no_see_cause, [],
                                     "names workspace location / package.xml — its own claim "
                                     "(old 6symptom:05) was cut, naked was already 1.00"),
        "pkg_list_cause": Check(_pkg_list_cause, [C_PKG_BUILD_CMD], "names sourcing the overlay"),
    },
    note="Kept as a whole-probe confirmation check even though three of its "
         "four claims were cut — all four had naked=1.00 in the ablation run, "
         "so this probe's job now is to prove the reduced body didn't regress, "
         "not to ablate anything further.",
    probe_only=True,
)


def _pkg_launch_install_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"install\(DIRECTORY", r"data_files", r"not installed")


def _pkg_symlink_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"--symlink-install", r"rebuild")


def _pkg_iface_location_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"ament_python", r"ament_cmake", r"member_of_group")


def _pkg_link_deps_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"ament_target_dependencies", r"target_link_libraries", r"not linked")


def _pkg_headers_export_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"install\(DIRECTORY\s+include", r"export", r"include/")


P_PKG_DIAG_IFACE = Probe(
    id="pkg-diagnose-launch-iface",
    suite="package",
    skill="ros2-package",
    prompt=(
        "For each of these ROS 2 Jazzy package problems, give the root cause "
        "and the fix in one line each:\n"
        "1. `ros2 launch` reports the launch file doesn't exist, though it's "
        "in the source tree.\n"
        "2. Edited a Python node, ran it again, behavior is unchanged.\n"
        "3. Custom message import fails at runtime with ModuleNotFoundError / "
        "no type support.\n"
        "4. C++ link fails: undefined reference to an rclcpp symbol.\n"
        "5. A dependent package can't find your package's headers."
    ),
    checks={
        "launch_install_cause": Check(_pkg_launch_install_cause, [C_PKG_SYM_LAUNCH, C_PKG_CMAKE_WIRING],
                                      "names launch/ never installed — the one symptom row kept, "
                                      "plus the CMakeLists block that shows the same install() call"),
        "symlink_cause": Check(_pkg_symlink_cause, [C_PKG_BUILD_CMD],
                              "names --symlink-install / rebuild — its own claim (old 6symptom:04) "
                              "and the explanatory sentence (old 5build:02) were both cut"),
        "iface_location_cause": Check(_pkg_iface_location_cause,
                                      [C_PKG_IFACE_LOC],
                                      "names wrong package type or missing member_of_group — "
                                      "the symptom row and 'one concern per package' rule were cut; "
                                      "a prior confirmation run's regression report for this check "
                                      "(p=0.022) turned out to be an analysis-script artifact "
                                      "(condition-blind tallying), not a real regression — "
                                      "recomputed with (probe, condition, check) keys, no "
                                      "significant regression"),
        "link_deps_cause": Check(_pkg_link_deps_cause, [C_PKG_CMAKE_WIRING],
                                 "names the missing link/dependency call — its own claim "
                                 "(old 6symptom:08) was cut, naked was already 1.00"),
        "headers_export_cause": Check(_pkg_headers_export_cause, [],
                                      "names include/ install + export — its own claim "
                                      "(old 6symptom:09) was cut, naked was already 1.00"),
    },
    extra_claims=[C_PKG_RULE_RESOURCE],
    probe_only=True,
)


def _pkg_flags_missing_dep(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"not (okay|ok|safe)", r"declare", r"missing", r"add.*depend")


def _pkg_clean_machine_risk(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"clean machine", r"fresh", r"break", r"another machine", r"CI")


P_PKG_DEP_DECLARE = Probe(
    id="pkg-dep-declare",
    suite="package",
    skill="ros2-package",
    prompt=(
        "My node includes `#include <tf2_ros/transform_listener.h>` and links "
        "fine locally because a sibling package in my workspace happens to "
        "pull in `tf2_ros` already. My `package.xml` only lists `rclcpp` as a "
        "dependency. Is this OK to ship as-is? What should I check or fix?"
    ),
    checks={
        "flags_missing_dep": Check(_pkg_flags_missing_dep, [],
                                   "says this is not safe and tf2_ros must be declared — its own "
                                   "claim (old 7strict-rules:01) was cut, naked was already 1.00"),
        "clean_machine_risk": Check(_pkg_clean_machine_risk, [],
                                    "names the failure mode: works here, breaks elsewhere — same cut claim"),
    },
    note="Every claim this probe tested was cut (naked=1.00 on both checks in "
         "the ablation run). Kept in the confirmation sweep only to prove the "
         "reduced body didn't regress on a behaviour nothing in it states "
         "anymore.",
    probe_only=True,
)


def _pkg_builds_clean(answer: str) -> bool | None:
    b, _ = _build_and_check(answer, "hello_pkg", "hello_node")
    return b


def _pkg_exe_discoverable(answer: str) -> bool | None:
    b, d = _build_and_check(answer, "hello_pkg", "hello_node")
    if not b:
        return None if b is None else False
    return d


P_PKG_BUILD_HYBRID = Probe(
    id="pkg-build-ground-truth",
    suite="package",
    skill="ros2-package",
    prompt=(
        "Write a complete, minimal ROS 2 Jazzy ament_python package called "
        "`hello_pkg` with one node `hello_node` that just prints \"hello\" "
        "once and exits. I need every file required to build and run it — "
        "package.xml, setup.py, setup.cfg if needed, and the node script.\n\n"
        "Format your answer as a series of files: before each file's code "
        "block, put a line in exactly this form (nothing else on that line):\n"
        "FILE: <path relative to the package root, e.g. package.xml or "
        "hello_pkg/hello_node.py>\n\n"
        "Then the file's content in a fenced code block. No other commentary."
    ),
    checks={
        "builds_clean": Check(_pkg_builds_clean, [], "colcon build --packages-select hello_pkg succeeds"),
        "exe_discoverable": Check(_pkg_exe_discoverable, [],
                                  "ros2 pkg executables hello_pkg lists hello_node after install"),
    },
    note="Ground truth, not an ablation instrument: real colcon build + "
         "`ros2 pkg executables` against a fresh workspace per cell. Checks "
         "own no claims (claim_ids is empty), so conditions() is just the 4 "
         "baselines — run naked vs full only, never per-claim ablated, to "
         "keep the cost of a real build off the per-claim sweep entirely.",
)


# --- ros2-perception suite ---------------------------------------------------
# Claim ids re-read from claims.jsonl. Perception is the first suite where the
# cheap ground truth is a *compiler* rather than a build system: every C++
# snippet the model writes can be syntax-checked against the installed Jazzy
# headers in ~2-3s, with no workspace to create. That matters here more than in
# ros2-package, because the domain's headline trap is a header rename that regex
# grading would happily score either way -- Jazzy ships
# `cv_bridge/cv_bridge.hpp` and deleted the pre-Jazzy `cv_bridge/cv_bridge.h`,
# while `pcl_conversions/pcl_conversions.h` is still `.h`. Verified by hand
# before wiring in: the skill's own snippet compiles, the same snippet with the
# legacy `.h` spelling fails with "No such file or directory".

C_PERC_NAV_URL = "ros2-perception:1documentation-entry-points:01"
C_PERC_NAV_PKGS = "ros2-perception:1documentation-entry-points:02"
C_PERC_NAV_VERIFY = "ros2-perception:1documentation-entry-points:03"
# Post-cut ids. Only the pcl_ros code block was removed after the n=8 sweep
# (see ../runs/2026-07-28-perception); `a-`/`b-` disappeared from the cv_bridge
# heading slug once it stopped being one of a lettered pair. The
# `pointcloud_to_laserscan` row was cut alongside it and then restored: the
# confirmation run measured the reduced body at 5/8 on that check against 8/8
# both with the row and with no body at all, the same "a thinned table misleads
# where an empty one does not" interaction that made the CPU row a KEEP at
# p=0.007. Not significant on its own (p=0.20 at the n=8 cap), so the row is
# kept precautionarily rather than cut on an unresolved reading.
# Re-mapped 2026-07-28 after variant:compressed shipped (43 -> 38 lines). Five of
# the seven symptom rows were cut, so the two survivors renumbered: the QoS row
# keeps :01, and the K-vs-P row moved from :06 down to :02. C_PERC_SYM_KP is the
# stable NAME for that row and no longer matches the digits in its id; that is
# deliberate, not a bug to tidy up.
#
# Cut (all naked = full = ablate = 1.00 on sonnet, n=4, and the naked answers
# were read whole first -- they get 16UC1-is-millimetres / 32FC1-is-metres and
# passthrough right unaided, not just past the regex): the encoding-exception,
# depth-units, depth-registration, pointcloud_to_laserscan height-band and
# compressed-transport rows.
# Kept: the QoS row (UNDERPOWERED on one of its four checks) and the K-vs-P row,
# which is the strongest KEEP measured anywhere in this project -- ablate 0.00
# against naked 0.90, q=0.000. Removing it does not return the model to its
# unaided answer, it actively misleads: ablated answers blame box-coordinate
# scaling instead of the camera matrix. Verified against the installed
# sensor_msgs/msg/CameraInfo, whose own comments say K is for raw images and P
# for rectified ones.
C_PERC_CVBRIDGE = "ros2-perception:cv-bridge-opencv-conversion-c:01"
C_PERC_SYM_QOS = "ros2-perception:3symptom-root-cause-action:01"
C_PERC_SYM_ENC = None  # encoding-exception row cut
C_PERC_SYM_DEPTH = None  # depth-units row cut
C_PERC_SYM_REG = None  # depth-registration row cut
C_PERC_SYM_P2L = None  # pointcloud_to_laserscan height-band row cut
C_PERC_SYM_KP = "ros2-perception:3symptom-root-cause-action:02"  # renumbered from :06
C_PERC_SYM_CPU = None  # compressed-transport row cut

PERC_REORDER = "reorder:3,1,2"


@lru_cache(maxsize=1)
def _cpp_include_flags() -> list[str]:
    """Every per-package include dir under the Jazzy prefix, plus OpenCV/PCL/Eigen.

    ROS 2 installs headers one directory per package, so a single -I at the
    prefix root is not enough -- `rclcpp.hpp` transitively includes
    `rcl_interfaces/srv/...` which lives in its own tree.
    """
    flags = []
    base = "/opt/ros/jazzy/include"
    if os.path.isdir(base):
        flags += [f"-I{os.path.join(base, d)}" for d in sorted(os.listdir(base))
                  if os.path.isdir(os.path.join(base, d))]
        flags.append(f"-I{base}")
    for extra in ("/usr/include/opencv4", "/usr/include/eigen3"):
        if os.path.isdir(extra):
            flags.append(f"-I{extra}")
    import glob as _glob
    for pcl in sorted(_glob.glob("/usr/include/pcl-*")):
        flags.append(f"-I{pcl}")
    return flags


@lru_cache(maxsize=256)
def _compiles_cpp(answer: str) -> bool | None:
    """True if the answer's C++ passes `g++ -fsyntax-only` against the install.

    Syntax-only rather than a full link: the question is whether the headers,
    namespaces and call signatures the model wrote actually exist in Jazzy, and
    that is exactly what the front end resolves. None when the answer has no
    C++ to compile -- never graded as a failure.
    """
    src = code(answer)
    if src is None or "#include" not in src:
        return None
    tmp = tempfile.mkdtemp(prefix="ros2perc_probe_")
    try:
        path = os.path.join(tmp, "probe.cpp")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
            # A bare callback body is a legal translation unit on its own; no
            # main() is appended, so nothing is invented on the model's behalf.
        try:
            res = subprocess.run(
                ["g++", "-fsyntax-only", "-std=c++17", *_cpp_include_flags(), path],
                capture_output=True, text=True, timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        return res.returncode == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _perc_cv_compiles(answer: str) -> bool | None:
    return _compiles_cpp(answer)


def _perc_cvbridge_hpp(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return bool(re.search(r"cv_bridge/cv_bridge\.hpp", src))


def _perc_tocvcopy(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"toCvCopy", r"toCvShare")


P_PERC_CVBRIDGE = Probe(
    id="perc-cv-bridge-cpp",
    suite="perception",
    skill="ros2-perception",
    prompt=(
        "Write the C++ body of a ROS 2 Jazzy image callback: take an incoming "
        "`sensor_msgs::msg::Image::ConstSharedPtr`, convert it to an OpenCV "
        "BGR8 `cv::Mat`, draw a filled circle on it, and convert it back to a "
        "`sensor_msgs::msg::Image` ready to publish.\n\n"
        "Give me the complete set of #include lines and the function, in one "
        "fenced C++ code block. No CMakeLists, no commentary."
    ),
    checks={
        "compiles": Check(_perc_cv_compiles, [C_PERC_CVBRIDGE],
                          "g++ -fsyntax-only against the installed Jazzy headers — "
                          "the pre-Jazzy cv_bridge/cv_bridge.h spelling fails here"),
        "cvbridge_hpp": Check(_perc_cvbridge_hpp, [C_PERC_CVBRIDGE],
                              "includes cv_bridge/cv_bridge.hpp, the Jazzy spelling"),
        "tocvcopy": Check(_perc_tocvcopy, [C_PERC_CVBRIDGE],
                          "uses toCvCopy/toCvShare rather than hand-rolling the buffer"),
    },
    probe_only=True,
    extra_conditions=[PERC_REORDER],
)


def _perc_pcl_compiles(answer: str) -> bool | None:
    return _compiles_cpp(answer)


def _perc_pcl_conversions_h(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return bool(re.search(r"pcl_conversions/pcl_conversions\.h\b", src))


def _perc_rosmsg_roundtrip(answer: str) -> bool | None:
    src = code(answer)
    if src is None:
        return None
    return _has(src, r"fromROSMsg") and _has(src, r"toROSMsg")


P_PERC_PCL = Probe(
    id="perc-pcl-cpp",
    suite="perception",
    skill="ros2-perception",
    prompt=(
        "Write the C++ body of a ROS 2 Jazzy callback that takes an incoming "
        "`sensor_msgs::msg::PointCloud2::SharedPtr`, downsamples it with a PCL "
        "voxel grid filter at 5 cm leaf size, and converts the result back to a "
        "`sensor_msgs::msg::PointCloud2`.\n\n"
        "Give me the complete set of #include lines and the function, in one "
        "fenced C++ code block. No CMakeLists, no commentary."
    ),
    checks={
        "compiles": Check(_perc_pcl_compiles, [],
                          "g++ -fsyntax-only against installed pcl_conversions/PCL headers"),
        "pcl_conversions_h": Check(_perc_pcl_conversions_h, [],
                                   "includes pcl_conversions/pcl_conversions.h — still .h in "
                                   "Jazzy, the opposite of cv_bridge's .hpp"),
        "rosmsg_roundtrip": Check(_perc_rosmsg_roundtrip, [],
                                  "uses pcl::fromROSMsg and pcl::toROSMsg for both directions"),
    },
    note="Was an ablation instrument for the pcl_ros code block; that block was "
         "cut after measuring 8/8 naked, 8/8 ablated and 8/8 full on a real "
         "compiler. The probe is kept with no claims so the confirmation run "
         "still answers the question the cut turns on — does the model keep "
         "emitting PCL that compiles now that the body no longer shows it — "
         "which a regression here, and only here, would refute.",
)


def _perc_qos_mismatch_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"[Bb]est.?[Ee]ffort") and _has(text, r"[Rr]eliab")


def _perc_sensor_data_qos_cpp(answer: str) -> bool | None:
    src = code(answer) or prose(answer)
    if src is None:
        return None
    return _has(src, r"SensorDataQoS", r"rmw_qos_profile_sensor_data",
                r"BestEffort\(\)", r"best_effort\(\)")


def _perc_no_python_qos_in_cpp(answer: str) -> bool | None:
    """The cross-language trap the skill calls out by name.

    `rclcpp.qos.qos_profile_sensor_data` is Python syntax against the C++
    library and exists nowhere; a C++ answer containing it is wrong regardless
    of how the rest reads.
    """
    src = code(answer)
    if src is None:
        return None
    return not _has(src, r"rclcpp\.qos", r"qos_profile_sensor_data")


def _perc_qos_verify_cmd(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"ros2 topic info[^\n]*(-v|--verbose)", text))


P_PERC_QOS = Probe(
    id="perc-qos-silent",
    suite="perception",
    skill="ros2-perception",
    prompt=(
        "My ROS 2 Jazzy C++ node subscribes to `/camera/image_raw` from a "
        "RealSense driver. `ros2 topic hz /camera/image_raw` reports a steady "
        "30 Hz, `ros2 topic list` shows the topic, but my subscription callback "
        "never fires once. Nothing in the logs looks like an error.\n\n"
        "What is going on, how do I confirm it, and what is the C++ fix?"
    ),
    checks={
        "qos_mismatch_cause": Check(_perc_qos_mismatch_cause, [C_PERC_SYM_QOS],
                                    "names the BestEffort publisher / Reliable subscriber mismatch"),
        "sensor_data_qos": Check(_perc_sensor_data_qos_cpp, [C_PERC_SYM_QOS],
                                 "gives a sensor-data / best-effort QoS as the fix"),
        "no_python_qos_in_cpp": Check(_perc_no_python_qos_in_cpp, [C_PERC_SYM_QOS],
                                      "does not write the Python spelling (rclcpp.qos / "
                                      "qos_profile_sensor_data) into C++ — the exact "
                                      "cross-language error the claim calls out"),
        "verify_cmd": Check(_perc_qos_verify_cmd, [C_PERC_SYM_QOS],
                            "names ros2 topic info -v to confirm the offered QoS"),
    },
    probe_only=True,
)


def _perc_encoding_check(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"encoding") and _has(text, r"16UC1", r"32FC1", r"passthrough")


def _perc_depth_units(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    mm = _has(text, r"millimet", r"\bmm\b")
    scale = _has(text, r"1000")
    return mm and scale


def _perc_no_bgr8_for_depth(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"passthrough", r"msg->encoding", r"msg\.encoding",
                r"don'?t assume", r"never assume", r"not.*bgr8")


P_PERC_DEPTH = Probe(
    id="perc-depth-encoding",
    suite="perception",
    skill="ros2-perception",
    prompt=(
        "I'm subscribing to a depth image topic in ROS 2 Jazzy and running it "
        "through cv_bridge. Two things go wrong depending on the camera: "
        "sometimes cv_bridge raises an exception about the encoding, and "
        "sometimes it converts fine but every distance I read out is about a "
        "thousand times too large.\n\n"
        "Explain both and tell me exactly what to check and do."
    ),
    checks={
        "encoding_check": Check(_perc_encoding_check, [C_PERC_SYM_ENC],
                                "says to check the actual encoding, naming 16UC1/32FC1 or passthrough"),
        "depth_units": Check(_perc_depth_units, [C_PERC_SYM_DEPTH],
                             "names millimetres and the /1000 conversion to metres"),
        "no_bgr8_for_depth": Check(_perc_no_bgr8_for_depth, [C_PERC_SYM_ENC],
                                   "says to read msg->encoding / use passthrough rather than "
                                   "assuming a colour encoding"),
    },
    # Both rows were about "the encoding is not what you assumed" and were a
    # declared joint group; the joint ablation came back clean at naked=1.00, so
    # both were cut (delete, not merge -- the model supplies this unaided). No
    # group left to declare.
    probe_only=True,
)


def _perc_registration_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"regist", r"depth_registered", r"optical frame")


def _perc_height_band_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"min_height", r"max_height") or (
        _has(text, r"height") and _has(text, r"target_frame"))


def _perc_k_vs_p_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"\brectif", r"\bP\b.*projection", r"projection matrix") and \
        _has(text, r"\bK\b", r"camera matrix", r"intrinsic")


def _perc_compressed_transport_cause(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return _has(text, r"image_transport", r"compressed", r"throttl", r"downscal", r"downsampl")


P_PERC_DIAGNOSE = Probe(
    id="perc-diagnose",
    suite="perception",
    skill="ros2-perception",
    prompt=(
        "For each of these ROS 2 Jazzy perception problems, give the root cause "
        "and the fix in one line each:\n"
        "1. The point cloud from my RGB-D camera doesn't line up with the RGB "
        "image when I overlay them.\n"
        "2. `pointcloud_to_laserscan` runs without errors but every scan it "
        "publishes is empty.\n"
        "3. My detector's bounding boxes are drawn at visibly wrong positions "
        "when I project them onto the image.\n"
        "4. CPU usage is pegged by a handful of image subscribers on the same "
        "network."
    ),
    checks={
        "registration_cause": Check(_perc_registration_cause, [C_PERC_SYM_REG],
                                    "names depth/colour registration or the optical frame"),
        "height_band_cause": Check(_perc_height_band_cause, [C_PERC_SYM_P2L],
                                   "names the min_height/max_height band or the target_frame TF"),
        "k_vs_p_cause": Check(_perc_k_vs_p_cause, [C_PERC_SYM_KP],
                              "names mixing rectified/raw images with the wrong K or P matrix"),
        "compressed_transport_cause": Check(_perc_compressed_transport_cause, [C_PERC_SYM_CPU],
                                            "names image_transport compressed, or throttling/downscaling"),
    },
    probe_only=True,
)


def _perc_docs_url(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"docs\.ros\.org/en/jazzy/p/", text))


def _perc_interface_show(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"ros2 interface show", text))


P_PERC_DOCS = Probe(
    id="perc-docs-lookup",
    suite="perception",
    skill="ros2-perception",
    prompt=(
        "I'm working with `depth_image_proc` on ROS 2 Jazzy and I don't know "
        "its API. Where exactly do I read its documentation, and how do I "
        "confirm the exact field names of the `sensor_msgs/msg/Image` messages "
        "it consumes on this machine rather than trusting my memory?"
    ),
    checks={
        "docs_url": Check(_perc_docs_url, [C_PERC_NAV_URL],
                          "gives the docs.ros.org/en/jazzy/p/<package>/ pattern"),
        "interface_show": Check(_perc_interface_show, [C_PERC_NAV_VERIFY],
                                "names ros2 interface show against the local install"),
    },
    extra_claims=[C_PERC_NAV_PKGS],
    probe_only=True,
)


# --- ros2-troubleshooting suite ---------------------------------------------
#
# Biggest skill in the repo: 119 lines, 50 claims. Probe design started from a
# measurement rather than from the file, because the file's generic content was
# expected to be at ceiling and turned out to be: asked naked, sonnet diagnoses
# the silent-QoS case correctly and unprompted, works the inverted-drive bug
# layer by layer, and gives the ROS_DOMAIN_ID range as 0-232 *with* the 0-101
# ephemeral-port caveat and the 7400 + 250*id port arithmetic behind it -- a
# superset of what this skill says. Writing probes around REP 103 axes, executor
# deadlocks or domain IDs would have measured nothing.
#
# What the model cannot know is the part of this skill that is local to this
# repository: four scripts that ship next to the SKILL.md, how they are invoked,
# and one behaviour of check_tf_tree.py that is deliberately counter-intuitive.
# Those are the probes below. This follows the project's own finding that what
# survives ablation is what the model cannot supply -- project-local facts and
# pointers -- not correct general knowledge.

C_TS_SCRIPTS_PATH = "ros2-troubleshooting:1a-runnable-ground-truth-checks:01"
C_TS_PYTHON3_RULE = "ros2-troubleshooting:1a-runnable-ground-truth-checks:02"
C_TS_EXAMPLE_CMD = "ros2-troubleshooting:1a-runnable-ground-truth-checks:03"
C_TS_RUN_FIRST = "ros2-troubleshooting:1a-runnable-ground-truth-checks:04"
C_TS_IMU_SCRIPT = "ros2-troubleshooting:1a-runnable-ground-truth-checks:05"
C_TS_ODOM_SCRIPT = "ros2-troubleshooting:1a-runnable-ground-truth-checks:06"
C_TS_TF_SCRIPT = "ros2-troubleshooting:1a-runnable-ground-truth-checks:07"
C_TS_QOS_SCRIPT = "ros2-troubleshooting:1a-runnable-ground-truth-checks:08"


def _ts_names_a_script(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"check_(imu_gravity|odom_direction|tf_tree|qos_compat)\.py", text))


def _ts_invokes_with_python3(answer: str) -> bool | None:
    """The scripts are plain files, not a ROS 2 package. `python3 <path>` is
    correct; `ros2 run <anything> check_*.py` is the documented failure mode."""
    text = prose(answer)
    if text is None:
        return None
    if not re.search(r"check_\w+\.py", text):
        return False
    return bool(re.search(r"python3\s+\S*check_\w+\.py", text))


def _ts_no_ros2_run_for_script(answer: str) -> bool | None:
    """Negative form: true when the answer does NOT invent a ROS 2 package to
    `ros2 run` the script from. Ungradable unless a script was actually named --
    otherwise an answer that never mentions the scripts at all passes trivially,
    which is the empty-check failure mode this project has already been bitten
    by once."""
    text = prose(answer)
    if text is None:
        return None
    if not re.search(r"check_\w+\.py", text):
        return None
    return not re.search(r"ros2\s+run\s+\S+\s+check_\w+\.py", text)


def _ts_qos_script_named(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"check_qos_compat\.py", text))


def _ts_imu_script_named(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"check_imu_gravity\.py", text))


def _ts_odom_script_named(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"check_odom_direction\.py", text))


def _ts_tf_script_named(answer: str) -> bool | None:
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(r"check_tf_tree\.py", text))


def _ts_advisory_not_a_verdict(answer: str) -> bool | None:
    """check_tf_tree.py prints VERIFY PHYSICALLY for any ~180 deg roll/yaw even
    when the mounting is intentional. Reporting it to the user as 'your TF is
    wrong' is the failure this claim exists to prevent."""
    text = prose(answer)
    if text is None:
        return None
    return bool(re.search(
        r"(always|even when|even if|regardless|intentional|by design|not a verdict"
        r"|prompt to (compare|check)|advisory)", text, re.I))


P_TS_SILENT_TOPIC = Probe(
    id="ts-silent-topic",
    suite="troubleshooting",
    skill="ros2-troubleshooting",
    prompt=(
        "ROS 2 Jazzy. `ros2 topic hz /scan` reports a steady 10 Hz, but my "
        "subscriber node never gets a single callback. I do not want a theory "
        "-- I want to turn this into a definite pass/fail answer. What exact "
        "command do I run to settle it?"
    ),
    checks={
        "names_a_script": Check(_ts_names_a_script, [C_TS_QOS_SCRIPT],
                                "names one of the shipped check_*.py scripts"),
        "qos_script": Check(_ts_qos_script_named, [C_TS_QOS_SCRIPT],
                            "names check_qos_compat.py specifically"),
        "python3_invocation": Check(_ts_invokes_with_python3,
                                    [C_TS_PYTHON3_RULE, C_TS_EXAMPLE_CMD],
                                    "invokes it as python3 <path>, not via ros2 run"),
        "no_ros2_run": Check(_ts_no_ros2_run_for_script, [C_TS_PYTHON3_RULE],
                             "does not invent a ros2 run package for the script"),
    },
    note="The silent-QoS diagnosis itself is at ceiling -- naked answers reach "
         "ros2 topic info -v unprompted. What is measurable is whether the "
         "agent reaches for the shipped script, which it cannot know exists, "
         "and whether it invokes it correctly. Prompts here deliberately do NOT "
         "say skills are installed: an earlier draft did, and it sent naked and "
         "protocol cells hunting for the skill with a tool this harness has "
         "turned off, stubbing 9 of 16 naked cells and leaving the baseline at "
         "n=1. A probe prompt must read like a user's question, not like a hint "
         "that context exists to be found.",
    extra_claims=[C_TS_SCRIPTS_PATH, C_TS_RUN_FIRST],
    joint=[[C_TS_PYTHON3_RULE, C_TS_EXAMPLE_CMD]],
    probe_only=True,
)


P_TS_IMU_MOUNT = Probe(
    id="ts-imu-mount",
    suite="troubleshooting",
    skill="ros2-troubleshooting",
    prompt=(
        "My robot's EKF odometry drifts and occasionally spins on the spot, "
        "but every topic looks healthy and nothing errors. I suspect the IMU "
        "mounting. I want evidence, not a hunch -- give me the exact command "
        "that turns that suspicion into a pass or fail."
    ),
    checks={
        "imu_script": Check(_ts_imu_script_named, [C_TS_IMU_SCRIPT],
                            "names check_imu_gravity.py"),
        "python3_invocation": Check(_ts_invokes_with_python3,
                                    [C_TS_PYTHON3_RULE, C_TS_EXAMPLE_CMD],
                                    "invokes it as python3 <path>"),
        "no_ros2_run": Check(_ts_no_ros2_run_for_script, [C_TS_PYTHON3_RULE],
                             "does not invent a ros2 run package for the script"),
    },
    extra_claims=[C_TS_SCRIPTS_PATH, C_TS_RUN_FIRST],
    probe_only=True,
)


P_TS_DRIVE_BACKWARD = Probe(
    id="ts-drive-backward",
    suite="troubleshooting",
    skill="ros2-troubleshooting",
    prompt=(
        "Differential drive robot, ROS 2 Jazzy. Publishing "
        "`cmd_vel.linear.x = 0.2` drives it backward. Nothing errors anywhere. "
        "Before I touch any code I want to establish, as a measured fact, "
        "whether odometry agrees with which way the robot physically moved. "
        "What exact command do I run?"
    ),
    checks={
        "odom_script": Check(_ts_odom_script_named, [C_TS_ODOM_SCRIPT],
                             "names check_odom_direction.py"),
        "names_a_script": Check(_ts_names_a_script, [C_TS_ODOM_SCRIPT],
                                "reaches for a shipped script at all"),
        "python3_invocation": Check(_ts_invokes_with_python3,
                                    [C_TS_PYTHON3_RULE, C_TS_EXAMPLE_CMD],
                                    "invokes it as python3 <path>"),
    },
    extra_claims=[C_TS_SCRIPTS_PATH, C_TS_RUN_FIRST],
    probe_only=True,
)


P_TS_TF_ADVISORY = Probe(
    id="ts-tf-advisory",
    suite="troubleshooting",
    skill="ros2-troubleshooting",
    prompt=(
        "I ran a TF tree check script on my robot and it printed a "
        "`VERIFY PHYSICALLY` advisory for my LiDAR's 180 degree roll. The "
        "LiDAR really is mounted upside-down and the URDF declares that "
        "correctly. Is my TF wrong? Explain what that output actually means "
        "and name the script that produces it."
    ),
    checks={
        "tf_script": Check(_ts_tf_script_named, [C_TS_TF_SCRIPT],
                           "names check_tf_tree.py"),
        "advisory_not_verdict": Check(_ts_advisory_not_a_verdict, [C_TS_TF_SCRIPT],
                                      "says the advisory always prints and is not a verdict"),
    },
    note="The one claim here that is neither general knowledge nor a filename: "
         "the advisory fires on any ~180 deg roll/yaw including a correct "
         "intentional mount, so reporting it as 'your TF is broken' is wrong. "
         "A model that has never read this skill cannot know the script's "
         "behaviour, only guess it.",
    extra_claims=[C_TS_SCRIPTS_PATH],
    probe_only=True,
)


PROBES: list[Probe] = [
    P_SCAN, P_TF, P_PARAMS, P_EXECUTOR, P_ROS1, P_DOMAIN, P_ODOM,
    P_T_COLCON, P_T_ROSBAG_WRITE, P_T_LAUNCH_TESTING, P_T_DIAGNOSE,
    P_PKG_CREATE, P_PKG_CMAKE, P_PKG_PYENTRY, P_PKG_INTERFACES,
    P_PKG_DIAG_BUILD, P_PKG_DIAG_IFACE, P_PKG_DEP_DECLARE, P_PKG_BUILD_HYBRID,
    P_PERC_CVBRIDGE, P_PERC_PCL, P_PERC_QOS, P_PERC_DEPTH,
    P_PERC_DIAGNOSE, P_PERC_DOCS,
    P_TS_SILENT_TOPIC, P_TS_IMU_MOUNT, P_TS_DRIVE_BACKWARD, P_TS_TF_ADVISORY,
]
