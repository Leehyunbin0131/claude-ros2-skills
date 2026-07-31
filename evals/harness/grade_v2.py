#!/usr/bin/env python3
"""Grade a v2 task cell from its stream-json transcript.

Nothing here is graded by reading. Every rule is mechanical and anchored per
TASKS.md: a real outcome, a fact in the install, or an ordered fact about the
transcript. Rules that need a live system are marked and skipped (returning
None = ungradable, never False) when that system is not up.

Usage:
    python3 grade_v2.py <task-id> <result.jsonl>       # -> JSON on stdout
    python3 grade_v2.py --selftest                     # exercise every rule

Ungradable vs failed is the distinction this project has had to relearn most
often: a cell that never produced an answer is not a wrong answer, and scoring
it False deflates whichever baseline it lands in.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

JAZZY = Path("/opt/ros/jazzy")


# --------------------------------------------------------------------------
# transcript reduction
# --------------------------------------------------------------------------
class Cell:
    """A cell's transcript, flattened into what the graders need.

    `events` preserves order, which is the whole basis of the T3 rules: the
    question is not *whether* the agent asked but whether it asked *before* it
    wrote a config.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.events: list[tuple[str, str]] = []   # (kind, payload)
        self.tools: list[tuple[str, dict]] = []   # (name, input)
        self.tool_ids: list[str] = []             # parallel to self.tools
        # tool_use_id -> (result text, is_error). T5 needs this: whether the
        # *first* colcon build succeeded is only visible in the result, and a
        # broken package builds clean, so the build log is the only witness.
        self.results: dict[str, tuple[str, bool]] = {}
        self.assistant_text: list[str] = []
        self.final = ""
        self._load()

    def _load(self) -> None:
        # Committed transcripts are gzipped. Reading them as text silently
        # yields nothing, which once made a whole round report "0 cells graded"
        # and an isolation check report "no leaks" -- a false all-clear is worse
        # than an error, so handle both forms here rather than at call sites.
        if self.path.suffix == ".gz":
            import gzip
            raw = gzip.open(self.path, "rt", errors="ignore").read()
        else:
            raw = self.path.read_text(errors="ignore")
        for line in raw.splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") == "assistant":
                for b in d.get("message", {}).get("content", []):
                    if b.get("type") == "tool_use":
                        self.tools.append((b.get("name", ""), b.get("input", {}) or {}))
                        self.tool_ids.append(b.get("id", ""))
                        self.events.append(("tool", b.get("name", "")))
                    elif b.get("type") == "text":
                        self.assistant_text.append(b.get("text", ""))
                        self.events.append(("text", b.get("text", "")))
            elif d.get("type") == "user":
                content = d.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            body = b.get("content", "")
                            if isinstance(body, list):
                                body = "\n".join(
                                    str(x.get("text", "")) for x in body
                                    if isinstance(x, dict))
                            self.results[b.get("tool_use_id", "")] = (
                                str(body), bool(b.get("is_error")))
            elif d.get("type") == "result":
                self.final = d.get("result", "") or ""

    # -- helpers -----------------------------------------------------------
    @property
    def answer(self) -> str:
        return self.final or "\n".join(self.assistant_text)

    # Strings that mean the harness failed, not that the model answered. A
    # round was scored 10/10 on a negative check because every cell returned
    # "Not logged in - Please run /login" and the check only asked whether a
    # wrong parameter appeared in it. An error message is not an answer.
    HARNESS_FAILURE = re.compile(
        r"(not logged in|please run /login|invalid api key|authentication"
        r"|rate limit|no stdin data received|usage limit|credit balance)", re.I)

    def gradable(self) -> bool:
        """False when the cell produced no answer, or produced a harness error."""
        a = self.answer.strip()
        if not a:
            return False
        # A genuine answer can be long and mention rate limits in passing; a
        # harness failure is short and is nothing but the error.
        return not (len(a) < 400 and self.HARNESS_FAILURE.search(a))

    def tool_names(self) -> set[str]:
        return {n for n, _ in self.tools}

    def tool_blob(self, *names: str) -> str:
        want = set(names)
        return "\n".join(
            json.dumps(i) for n, i in self.tools if not want or n in want
        )

    def first_index(self, pred) -> int | None:
        for i, ev in enumerate(self.events):
            if pred(ev):
                return i
        return None

    def files_written(self, suffix: str = "") -> list[str]:
        out = []
        for n, i in self.tools:
            if n in ("Write", "Edit", "NotebookEdit"):
                p = str(i.get("file_path", ""))
                if p.endswith(suffix):
                    out.append(p)
        return out


# --------------------------------------------------------------------------
# install-anchored facts, read once
# --------------------------------------------------------------------------
_PLUGINS: set[str] | None = None


def registered_plugins() -> set[str]:
    """Every class pluginlib registers in this install."""
    global _PLUGINS
    if _PLUGINS is None:
        names: set[str] = set()
        for f in glob.glob(str(JAZZY / "share/**/*.xml"), recursive=True):
            try:
                txt = Path(f).read_text(errors="ignore")
            except OSError:
                continue
            if "library path" not in txt and "<class" not in txt:
                continue
            names |= set(re.findall(r'type="([A-Za-z_0-9]+::[A-Za-z_0-9]+)"', txt))
        _PLUGINS = names
    return _PLUGINS


def live_topic_type(topic: str) -> str | None:
    """Ask the running system, not a document. None when nothing is up."""
    try:
        r = subprocess.run(
            ["bash", "-lc",
             f"source /opt/ros/jazzy/setup.bash 2>/dev/null; "
             f"timeout 8 ros2 topic info {topic}"],
            capture_output=True, text=True, timeout=25)
    except Exception:
        return None
    m = re.search(r"Type:\s*(\S+)", r.stdout or "")
    return m.group(1) if m else None


# --------------------------------------------------------------------------
# shared rule helpers
# --------------------------------------------------------------------------
NEGATION = re.compile(
    r"(no longer|not exist|nonexistent|non-existent|removed|replaced|does not|"
    r"doesn't|don't|do not|deprecat|older|earlier|humble|iron|pre-jazzy|"
    r"instead of|invent|there is no)", re.I)


def prescribes(text: str, token: str) -> bool:
    """True when `token` is recommended rather than warned about.

    The distinction matters: an answer that names a removed parameter in order
    to tell the reader it does not exist is correct, and a check that greps for
    the bare string scores it wrong. That bug has been shipped here twice.
    """
    hits = list(re.finditer(re.escape(token), text))
    if not hits:
        return False
    for m in hits:
        window = text[max(0, m.start() - 180):m.end() + 80]
        if not NEGATION.search(window):
            return True
    return False


REPO_PATH = str(Path(__file__).resolve().parents[2])


def leaked(c: Cell) -> list[str]:
    """Tool inputs that reached this repository.

    A cell that read evals/DESIGN.md or a scenario source has seen the answer
    key. Round 2 had one such cell; isolate_cell.sh closes the hole, and this
    stays as the check that it is actually closed. A round with any leak is
    reported with the count, never silently averaged in.
    """
    hits = []
    for name, inp in c.tools:
        blob = json.dumps(inp)
        if REPO_PATH in blob:
            hits.append(f"{name}: {blob[:120]}")
    return hits


def searched_or_read_install(c: Cell) -> bool:
    if c.tool_names() & {"WebSearch", "WebFetch"}:
        return True
    blob = c.tool_blob("Read", "Grep", "Glob", "Bash")
    return "/opt/ros/jazzy" in blob


# --------------------------------------------------------------------------
# T1 — version-specific breakage
# --------------------------------------------------------------------------
def t1(c: Cell, live: bool = False) -> dict:
    if not c.gradable():
        return {k: None for k in
                ("t1_correct_type", "t1_no_invented_param",
                 "t1_searched_or_read", "t1_command_runs")}
    a = c.answer
    g = {
        "t1_correct_type": bool(re.search(r"TwistStamped", a)),
        "t1_no_invented_param": not prescribes(a, "use_stamped_vel"),
        "t1_searched_or_read": searched_or_read_install(c),
        "t1_command_runs": None,
    }
    if live:
        # Real outcome: does the type the agent told the user to publish match
        # what the running controller actually subscribes to?
        want = live_topic_type("/diff_drive_controller/cmd_vel")
        if want:
            short = want.rsplit("/", 1)[-1]
            cmds = c.tool_blob("Bash") + "\n" + a
            pub = re.findall(r"ros2 topic pub[^\n`]*", cmds)
            g["t1_command_runs"] = any(short in p for p in pub) if pub else False
    return g


# --------------------------------------------------------------------------
# T2 — content that exists nowhere else
# --------------------------------------------------------------------------
SCRIPT = "check_imu_gravity.py"


def t2(c: Cell) -> dict:
    if not c.gradable():
        return {k: None for k in
                ("t2_ran_script", "t2_exit_code_read",
                 "t2_no_ros2_run", "t2_evidence_not_guess")}
    bash = c.tool_blob("Bash")
    a = c.answer
    ran = bool(re.search(rf"python3?\s+\S*{re.escape(SCRIPT)}", bash))
    return {
        "t2_ran_script": ran,
        # Reporting a verdict only counts if the script was actually run.
        "t2_exit_code_read": (bool(re.search(r"\b(PASS|FAIL|NO DATA|no data)\b", a))
                              if ran else False),
        # Ungradable when the scripts were never mentioned: an answer that
        # never reaches for them cannot pass a "did not misuse them" rule.
        "t2_no_ros2_run": (None if SCRIPT not in (bash + a)
                           else not re.search(rf"ros2 run \S+ \S*{re.escape(SCRIPT)}", bash + a)),
        "t2_evidence_not_guess": bool(re.search(r"9\.8|\b[0-9]+\.[0-9]+\s*m/s", a))
                                 and bool(re.search(r"\b[xyz]\b", a, re.I)),
    }


# --------------------------------------------------------------------------
# T3 — known but not done
# --------------------------------------------------------------------------
CONFIG_SUFFIXES = (".yaml", ".yml")


def t3(c: Cell) -> dict:
    if not c.gradable():
        return {k: None for k in
                ("t3_asked_before_writing", "t3_asked_footprint",
                 "t3_asked_drive_type", "t3_read_shipped_defaults",
                 "t3_plugins_real")}

    def is_config_write(ev):
        kind, payload = ev
        return kind == "tool" and payload in ("Write", "Edit")

    # index of the first config write, matched back to its file path
    write_i = None
    seen = 0
    for i, (kind, payload) in enumerate(c.events):
        if kind == "tool" and payload in ("Write", "Edit"):
            paths = [p for n, inp in c.tools if n in ("Write", "Edit")
                     for p in [str(inp.get("file_path", ""))]]
            if seen < len(paths) and paths[seen].endswith(CONFIG_SUFFIXES):
                write_i = i
                break
            seen += 1

    ask_i = c.first_index(lambda ev: ev[0] == "text" and "?" in ev[1])
    all_text = "\n".join(c.assistant_text) + "\n" + c.answer

    blob = c.tool_blob("Read", "Grep", "Bash", "Glob")
    read_i = c.first_index(
        lambda ev: ev[0] == "tool" and ev[1] in ("Read", "Grep", "Bash", "Glob"))

    written = "\n".join(
        str(i.get("content", "")) for n, i in c.tools
        if n in ("Write", "Edit") and str(i.get("file_path", "")).endswith(CONFIG_SUFFIXES))
    strings = set(re.findall(r'["\']?([a-z_0-9]+::[A-Za-z_0-9]+)["\']?', written))

    return {
        # asked first, or never wrote a config at all
        "t3_asked_before_writing": (write_i is None
                                    or (ask_i is not None and ask_i < write_i)),
        "t3_asked_footprint": bool(re.search(
            r"footprint|inscribed radius|robot_radius|robot radius", all_text, re.I)),
        "t3_asked_drive_type": bool(re.search(
            r"differential|ackermann|omni|holonomic|drive type", all_text, re.I)),
        "t3_read_shipped_defaults": ("nav2_params.yaml" in blob
                                     and (write_i is None or (read_i is not None and read_i < write_i))),
        "t3_plugins_real": (None if not strings
                            else strings <= registered_plugins()),
    }


# --------------------------------------------------------------------------
# T4 — null control
# --------------------------------------------------------------------------
def t4(c: Cell, workdir: str | None = None) -> dict:
    # Unlike the other tasks, T4's deliverable is a file, not prose. A cell that
    # wrote a node and said nothing is gradable; only a cell that produced
    # neither is not.
    src = "\n".join(
        str(i.get("content", "")) for n, i in c.tools
        if n in ("Write", "Edit") and str(i.get("file_path", "")).endswith(".py"))
    if not src and workdir:
        for p in Path(workdir).glob("*.py"):
            src += p.read_text(errors="ignore")
    if not src:
        return {"t4_node_runs": None, "t4_guards_range": None}
    return {
        # Real outcome is run by the scenario script, which writes a sentinel;
        # here we only report whether the emitted code is runnable Python that
        # subscribes to LaserScan. Execution is graded by the caller.
        "t4_node_runs": bool(re.search(r"LaserScan", src))
                        and bool(re.search(r"create_subscription", src)),
        "t4_guards_range": bool(re.search(r"isfinite|isinf|isnan|math\.inf", src))
                           or bool(re.search(r"range_min", src) and re.search(r"range_max", src)),
    }


def _external_checks(c: Cell, check, keys: list[str], found_key: str,
                     first_build_key: str) -> dict:
    """Shared shape for ladder rungs: real outcomes from a JSON verdict file,
    plus one transcript fact about the first `colcon build`."""
    out: dict[str, bool | None] = {k: None for k in keys}
    out[first_build_key] = None
    if not c.gradable():
        return out

    if check:
        p = Path(check)
        if p.exists():
            try:
                d = json.loads(p.read_text())
            except json.JSONDecodeError:
                d = {}
            found = d.get(found_key)
            for k in keys:
                out[k] = bool(d.get(k)) if found else False

    for i, (n, inp) in enumerate(c.tools):
        if n != "Bash" or "colcon build" not in str(inp.get("command", "")):
            continue
        body, is_err = c.results.get(c.tool_ids[i] if i < len(c.tool_ids) else "",
                                     ("", False))
        if not body:
            break
        if re.search(r"moved to the background|did not complete within", body):
            break
        out[first_build_key] = not is_err and not re.search(
            r"Failed\s+<<<|packages? failed|aborted", body)
        break
    return out


# --------------------------------------------------------------------------
# T5 — ros2-package: does the wiring prose earn its place?
# --------------------------------------------------------------------------
def t5(c: Cell, check: str | Path | None = None) -> dict:
    """Every check but one is a real outcome produced by `t5_check.sh`.

    Grading cannot be done from the transcript here. All three packaging
    defects this task is about -- no `setup.cfg`, launch/config missing from
    `data_files`, interfaces in an `ament_python` package -- **exit colcon with
    code 0**. The failure only appears when you try to use the package. See the
    discrimination table in `t5_check.sh`.
    """
    # `t5_first_build_clean` is separated from the rest because final success is
    # reachable by iterating until the error stops, which is what a build loop
    # is for; getting the wiring right first time is the different thing.
    # No workspace at all counts as a real failure, not as missing data.
    return _external_checks(
        c, check,
        ["t5_builds", "t5_interface_resolves", "t5_run_works",
         "t5_launch_resolves", "t5_params_installed"],
        "t5_workspace_found", "t5_first_build_clean")


# --------------------------------------------------------------------------
# T6 — ros2-package ladder rung L2 (evals/LADDER.md)
# --------------------------------------------------------------------------
def t6(c: Cell, check: str | Path | None = None) -> dict:
    """L2 adds a C++ executable, a `.srv` used from both languages, and a
    launch file that includes another package's launch file.

    As at L1, every defect this rung can catch **builds clean**: verified
    2026-07-30 against two broken reference workspaces, both `colcon build`
    rc=0. The two failures leave different signatures, which is what makes the
    diagnosis mechanical rather than a story:

        cpp_run_works FAIL                  -> wrong install destination
        cpp_run_works pass, composed FAIL   -> launch/ never installed
    """
    return _external_checks(
        c, check,
        ["t6_builds", "t6_srv_resolves", "t6_cpp_run_works", "t6_py_run_works",
         "t6_composed_launch", "t6_service_available"],
        "t6_workspace_found", "t6_first_build_clean")


# --------------------------------------------------------------------------
# T7 — ros2-package ladder rung L3 (evals/LADDER.md)
# --------------------------------------------------------------------------
def t7(c: Cell, check: str | Path | None = None) -> dict:
    """L3 adds a cross-package message field, a composable node loaded into an
    rclcpp_components container, and a test `colcon test` has to actually run.

    `t7_tests_ran` is deliberately separate from `t7_tests_pass`: **`colcon
    test` exits 0 when there are no tests.** Verified 2026-07-30 -- the
    `no_tests` reference workspace reports rc=0 with `tests_total=0`. "The tests
    pass" is not a claim until something has been shown to run.

    Signatures, for the mechanical diagnosis rule 6 requires:

        component_registered FAIL          -> never registered
        registered pass, loads FAIL        -> library not installed/loadable
        tests_ran FAIL                     -> colcon test ran nothing, rc=0
    """
    return _external_checks(
        c, check,
        ["t7_builds", "t7_msg_dep_resolves", "t7_component_registered",
         "t7_component_loads", "t7_tests_ran", "t7_tests_pass"],
        "t7_workspace_found", "t7_first_build_clean")


# --------------------------------------------------------------------------
# G1 — gazebo-sim ladder rung L1 (evals/LADDER.md)
# --------------------------------------------------------------------------
def g1(c: Cell, check: str | Path | None = None) -> dict:
    """A world that loads, advertises odometry, and drives when commanded.

    All four checks have a demonstrated failing case, which is the standard this
    project holds graders to:

        g1_sdf_valid      -- a mismatched </inertia> gives XML_ERROR_MISMATCHED_ELEMENT
        g1_sim_runs       -- ogre2 headless on this machine segfaults the process
        g1_topics_present -- a world with no DiffDrive plugin never advertises /odom
        g1_robot_moves    -- DiffDrive naming joints no <joint> declares: loads,
                             publishes odometry, moves 0 cm

    There is no `first build` analogue here, so the transcript key is unused and
    always None.
    """
    return _external_checks(
        c, check,
        ["g1_sdf_valid", "g1_sim_runs", "g1_topics_present", "g1_robot_moves"],
        "g1_world_found", "g1_unused_transcript_key")


# --------------------------------------------------------------------------
# G2 — gazebo-sim ladder rung L2 (evals/LADDER.md)
# --------------------------------------------------------------------------
def g2(c: Cell, check: str | Path | None = None) -> dict:
    """The cell's own bringup.sh is executed and the result read from ROS.

    Each check has an isolated failing case, verified 2026-07-30 against four
    reference workspaces:

        no gz-sim-sensors-system -> g2_scan_in_ros FAIL, clock and motion fine
                                    (/scan advertises in Gazebo and never
                                     publishes -- the silent one)
        '[' on /cmd_vel          -> g2_ros_cmd_moves FAIL, scan and clock fine
        /clock not bridged       -> g2_clock_in_ros FAIL, scan and motion fine

    `g2_scan_360` moves with `g2_scan_in_ros` in those variants; a 180-sample
    lidar would separate them but was not run, so it is validated by
    construction rather than by a reference variant.
    """
    return _external_checks(
        c, check,
        ["g2_scan_in_ros", "g2_scan_360", "g2_clock_in_ros", "g2_ros_cmd_moves"],
        "g2_bringup_found", "g2_unused_transcript_key")


# --------------------------------------------------------------------------
# G3 — gazebo-sim ladder rung L3 (evals/LADDER.md)
# --------------------------------------------------------------------------
def g3(c: Cell, check: str | Path | None = None) -> dict:
    """URDF spawned with ros_gz_sim, an IMU, frame naming, and sim time.

    Verified 2026-07-30 against four reference workspaces:

        no gz-sim-imu-system -> g3_imu_in_ros FAIL, spawn and clock fine
        no <gz_frame_id>     -> g3_frame_id_is_link FAIL, and the frame comes
                                back as `imubot/base_link/imu_sensor`, which is
                                SKILL.md's <model>/<link>/<sensor> claim
                                confirmed literally
        /clock not bridged   -> g3_sim_time FAIL, everything else fine

    **`g3_spawned` was REMOVED after the round, and that needs justifying,**
    because dropping a failing check after seeing it fail is the manufacturing
    pattern in reverse.

    It never met the standard the other three met. Before the round it was
    recorded as "validated by construction" -- no reference variant ever made it
    fail. Three definitions were tried and each encoded something the frozen
    prompt does not require:

        >= 2 models          -- assumes a ground plane. 5/10 cells built a world
                                without one; the prompt never asked for it.
        URDF robot name in   -- assumes the Gazebo model name equals the URDF
        the model list          robot name. `ros_gz_sim create -name` sets it.
        `gz model --list`    -- queries world "default" unless told otherwise;
                                cells naming their world anything else came back
                                empty.

    It is also redundant: an IMU publishing from a robot is proof that robot is
    in the world, so every "not spawned" cell contradicted itself by passing
    `g3_imu_in_ros`. Keeping a check whose failures are provably false would be
    worse than removing it -- but this is the weakest link in the round's rigor
    and is recorded as such rather than smoothed over.
    """
    return _external_checks(
        c, check,
        ["g3_imu_in_ros", "g3_frame_id_is_link", "g3_sim_time"],
        "g3_bringup_found", "g3_unused_transcript_key")


# --------------------------------------------------------------------------
# TR1 — ros2-troubleshooting executor ladder, rung L1 (evals/LADDER.md)
# --------------------------------------------------------------------------
def tr1(c: Cell, check: str | Path | None = None) -> dict:
    """Graded by running the cell's node.py against a live slow service.

    Validated 2026-07-31 against three references, and validating them
    corrected SKILL.md §3C in passing:

        call_async + done callback        -> 5 results, rc 0, 7 s. passes.
        spin_until_future_complete(node,  -> SILENT HANG, rc 124 at 45 s, no
        fut) with no executor arg while      output whatsoever. This is the
        on a MultiThreadedExecutor           real hang, and §3C does not
                                             describe it.
        nested spin inside a callback     -> NOT a hang. rclpy raises
        while rclpy.spin runs                RuntimeError("Executor is already
                                             spinning") in ~1 s. Loud and
                                             immediate -- the opposite of what
                                             §3C says happens.

    The two failures fail through different checks, which is what makes rule 6's
    mechanical diagnosis possible here.
    """
    return _external_checks(
        c, check,
        ["tr1_logs_5", "tr1_no_hang", "tr1_exits_clean"],
        "tr1_node_found", "tr1_unused_transcript_key")


# --------------------------------------------------------------------------
# TR2 — ros2-troubleshooting executor ladder, rung L2 (evals/LADDER.md)
# --------------------------------------------------------------------------
def tr2(c: Cell, check: str | Path | None = None) -> dict:
    """The service call moves into a subscription callback, and the node has to
    hold its own 10 Hz heartbeat while calls are in flight.

    Validated 2026-07-31 against three references. Every check has a failing
    case, and `tr2_heartbeat_steady` has one that ISOLATES it -- the standard
    `g3_spawned` failed to meet:

        reentrant everywhere      -> all pass. 59 beats, max gap 0.31 s, rc 0.
        rclpy's default group     -> all FAIL. Full deadlock, not partial
        everywhere                   starvation: the response needs the same
                                     group the blocked callback holds, so the
                                     future never completes. rc 124.
        reentrant CLIENT only,    -> logs_5, no_hang and exits_clean all PASS;
        timer+sub left in the        only heartbeat_steady fails. Max gap
        default group                **1.06 s** where 10 Hz means 0.1 s.

    Measured as max gap, not average rate: an executor that stalls one second
    per call still averages respectably, and the average is what hides it.
    """
    return _external_checks(
        c, check,
        ["tr2_logs_5", "tr2_no_hang", "tr2_exits_clean", "tr2_heartbeat_steady"],
        "tr2_node_found", "tr2_unused_transcript_key")


# --------------------------------------------------------------------------
# TR3 — ros2-troubleshooting executor ladder, rung L3 (evals/LADDER.md)
# --------------------------------------------------------------------------
def tr3(c: Cell, check: str | Path | None = None) -> dict:
    """Five service calls issued concurrently from one callback, batch under 3 s.

    Wall time is the check that matters, and it is the one a merely-working node
    cannot satisfy. Validated 2026-07-31 against two references, the second of
    which ISOLATES it:

        all five call_async before   -> batch 2.015 s. all four checks pass.
        awaiting any, Reentrant on
        a MultiThreadedExecutor
        issue-and-await one at a     -> five correct results, exit 0, TOTAL
        time                            printed -- and 5.029 s. Only
                                        tr3_batch_under_3s fails.

    The scenario server runs 4 threads, so a perfectly concurrent batch lands at
    ~2 s rather than ~1 s -- inside the 3 s the frozen prompt allows, without
    requiring unbounded server parallelism from the cell.
    """
    return _external_checks(
        c, check,
        ["tr3_logs_5", "tr3_exits_clean", "tr3_total_line", "tr3_batch_under_3s"],
        "tr3_node_found", "tr3_unused_transcript_key")


TASKS = {"t1": t1, "t2": t2, "t3": t3, "t4": t4, "t5": t5, "t6": t6, "t7": t7,
         "g1": g1, "g2": g2, "g3": g3, "tr1": tr1, "tr2": tr2, "tr3": tr3}


# --------------------------------------------------------------------------
def selftest() -> int:
    """Exercise every rule against hand-written transcripts.

    A grader that has only ever seen good answers is not validated -- each rule
    is checked in both directions.
    """
    def mk(events):
        lines = []
        for kind, payload in events:
            if kind == "text":
                lines.append(json.dumps({"type": "assistant", "message": {
                    "content": [{"type": "text", "text": payload}]}}))
            else:
                name, inp = payload
                lines.append(json.dumps({"type": "assistant", "message": {
                    "content": [{"type": "tool_use", "name": name, "input": inp}]}}))
        import tempfile
        fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        fh.write("\n".join(lines))
        fh.close()
        return Cell(fh.name)

    fails = []

    def expect(label, got, want):
        if got != want:
            fails.append(f"{label}: got {got}, expected {want}")

    # T1
    good = mk([("tool", ("WebSearch", {"query": "diff_drive_controller jazzy"})),
               ("text", "It subscribes with TwistStamped only; there is no use_stamped_vel parameter in Jazzy.")])
    bad = mk([("text", "Set use_stamped_vel: false in your controller YAML.")])
    expect("t1 good/type", t1(good)["t1_correct_type"], True)
    expect("t1 good/param", t1(good)["t1_no_invented_param"], True)
    expect("t1 good/searched", t1(good)["t1_searched_or_read"], True)
    expect("t1 bad/param", t1(bad)["t1_no_invented_param"], False)
    expect("t1 bad/searched", t1(bad)["t1_searched_or_read"], False)
    expect("t1 empty", t1(mk([]))["t1_correct_type"], None)

    # T2
    ran = mk([("tool", ("Bash", {"command": "python3 .claude/skills/ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data"})),
              ("text", "[FAIL] mean accel = (+9.81, -0.01, 0.00) m/s^2 — gravity is on X, not Z.")])
    invented = mk([("tool", ("Bash", {"command": "ros2 run ros2_troubleshooting_helpers check_imu_gravity.py"})),
                   ("text", "It reports FAIL.")])
    silent = mk([("text", "Your IMU is probably mounted wrong; check the datasheet.")])
    expect("t2 ran", t2(ran)["t2_ran_script"], True)
    expect("t2 verdict", t2(ran)["t2_exit_code_read"], True)
    expect("t2 evidence", t2(ran)["t2_evidence_not_guess"], True)
    expect("t2 misuse", t2(invented)["t2_no_ros2_run"], False)
    expect("t2 silent/ran", t2(silent)["t2_ran_script"], False)
    expect("t2 silent/ungradable", t2(silent)["t2_no_ros2_run"], None)

    # T3
    asked = mk([("text", "Before I write anything: what is the robot's footprint, and is it differential or ackermann?"),
                ("tool", ("Read", {"file_path": "/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml"})),
                ("tool", ("Write", {"file_path": "/tmp/nav2_params.yaml",
                                    "content": 'plugin: "nav2_mppi_controller::MPPIController"'}))])
    wrote = mk([("tool", ("Write", {"file_path": "/tmp/nav2_params.yaml",
                                    "content": 'plugin: "mppi_controller::MPPIController"'})),
                ("text", "Done. Anything else?")])
    expect("t3 asked/order", t3(asked)["t3_asked_before_writing"], True)
    expect("t3 asked/footprint", t3(asked)["t3_asked_footprint"], True)
    expect("t3 asked/drive", t3(asked)["t3_asked_drive_type"], True)
    expect("t3 asked/defaults", t3(asked)["t3_read_shipped_defaults"], True)
    expect("t3 asked/plugins", t3(asked)["t3_plugins_real"], True)
    expect("t3 wrote/order", t3(wrote)["t3_asked_before_writing"], False)
    expect("t3 wrote/plugins", t3(wrote)["t3_plugins_real"], False)

    # T4
    ok = mk([("tool", ("Write", {"file_path": "/tmp/n.py",
                                 "content": "from sensor_msgs.msg import LaserScan\n"
                                            "self.create_subscription(LaserScan, '/scan', cb, 10)\n"
                                            "if math.isfinite(r):\n"}))])
    naive = mk([("tool", ("Write", {"file_path": "/tmp/n.py",
                                    "content": "from sensor_msgs.msg import LaserScan\n"
                                               "self.create_subscription(LaserScan, '/scan', cb, 10)\n"
                                               "m = min(msg.ranges)\n"}))])
    expect("t4 ok/runs", t4(ok)["t4_node_runs"], True)
    expect("t4 ok/guard", t4(ok)["t4_guards_range"], True)
    expect("t4 naive/guard", t4(naive)["t4_guards_range"], False)

    # T5 -- needs tool_use ids and tool_results, which mk() does not emit.
    import tempfile

    def mk_build(cmd_results):
        """Transcript of Bash calls paired with their results."""
        lines = []
        for k, (cmd, body, is_err) in enumerate(cmd_results):
            tid = f"toolu_{k}"
            lines.append(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": tid, "name": "Bash",
                 "input": {"command": cmd}}]}}))
            lines.append(json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": tid,
                 "content": body, "is_error": is_err}]}}))
        lines.append(json.dumps({"type": "result",
                                 "result": "Workspace built. " + "x" * 500}))
        fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        fh.write("\n".join(lines))
        fh.close()
        return Cell(fh.name)

    def chk(d):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(d, fh)
        fh.close()
        return fh.name

    all_ok = chk({"t5_workspace_found": True, "t5_builds": True,
                  "t5_interface_resolves": True, "t5_run_works": True,
                  "t5_launch_resolves": True, "t5_params_installed": True})
    # The real no_datafiles variant, measured 2026-07-30: builds clean, the
    # launch file and params never reach share/.
    no_df = chk({"t5_workspace_found": True, "t5_builds": True,
                 "t5_interface_resolves": True, "t5_run_works": True,
                 "t5_launch_resolves": False, "t5_params_installed": False})

    clean = mk_build([("colcon build", "Summary: 2 packages finished", False)])
    retried = mk_build([
        ("colcon build", "Failed   <<< battery_monitor_msgs\n1 package failed", False),
        ("colcon build", "Summary: 2 packages finished", False)])
    backgrounded = mk_build([
        ("colcon build", "Command did not complete within its 120s timeout and "
                         "was moved to the background (ID: abc)", False)])

    expect("t5 ok/run", t5(clean, all_ok)["t5_run_works"], True)
    expect("t5 ok/first-build", t5(clean, all_ok)["t5_first_build_clean"], True)
    expect("t5 nodf/launch", t5(clean, no_df)["t5_launch_resolves"], False)
    expect("t5 nodf/params", t5(clean, no_df)["t5_params_installed"], False)
    expect("t5 nodf/builds", t5(clean, no_df)["t5_builds"], True)
    expect("t5 retried/first-build", t5(retried, all_ok)["t5_first_build_clean"], False)
    expect("t5 retried/final", t5(retried, all_ok)["t5_run_works"], True)
    expect("t5 backgrounded/first-build",
           t5(backgrounded, all_ok)["t5_first_build_clean"], None)
    expect("t5 no-check/run", t5(clean, None)["t5_run_works"], None)
    expect("t5 no-workspace/run",
           t5(clean, chk({"t5_workspace_found": False}))["t5_run_works"], False)

    if fails:
        print("SELFTEST FAILED")
        for f in fails:
            print("  -", f)
        return 1
    print(f"selftest passed — {len(registered_plugins())} plugins indexed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("task", nargs="?", choices=sorted(TASKS))
    ap.add_argument("transcript", nargs="?")
    ap.add_argument("--live", action="store_true",
                    help="enable graders that query a running system")
    ap.add_argument("--workdir", help="cell working directory, for files on disk")
    ap.add_argument("--check", help="t5/t6/t7: the JSON verdict written by t5_check.sh "
                                    "at cell time (defaults to the sibling "
                                    "<stem>_check.json)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not (a.task and a.transcript):
        ap.error("task and transcript are required unless --selftest")

    cell = Cell(a.transcript)
    fn = TASKS[a.task]
    if a.task == "t1":
        grade = fn(cell, live=a.live)
    elif a.task == "t4":
        grade = fn(cell, workdir=a.workdir)
    elif a.task in ("t5", "t6", "t7", "g1", "g2", "g3", "tr1", "tr2", "tr3"):
        chk = a.check
        if not chk:
            p = Path(a.transcript)
            chk = p.parent / (p.name.split("_result.jsonl")[0] + "_check.json")
        grade = fn(cell, check=chk)
    else:
        grade = fn(cell)
    print(json.dumps({"transcript": a.transcript, "task": a.task,
                      "tools": sorted(cell.tool_names()),
                      "leaked": leaked(cell), "grade": grade}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
