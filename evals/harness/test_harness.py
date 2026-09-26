#!/usr/bin/env python3
"""Regression tests for the eval harness itself. No model calls, no ROS.

    python3 evals/harness/test_harness.py

Each test pins one defect that shipped in 39fed2a: the grader's CLI ignoring
checker verdicts, cut-off and error transcripts graded as answers, an absent
install fact graded False, discarded cells pooled into a round, a control gate
reporting a pass it never ran, host-wide `pkill`, a cell running as root of its
namespace and able to unmount its own isolation. Where git history is
available, the "before" half runs the 39fed2a file and shows the defect; CI
checkouts without history skip only that half.

Processes spawned here are `sleep`s renamed with `exec -a`; every one is killed
by PID in tearDown. Nothing outside the test's own processes is signalled.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
REPO = HARNESS.parents[1]
BASE = "39fed2a"
sys.path.insert(0, str(HARNESS))

import analyze_v2  # noqa: E402
import grade_v2  # noqa: E402
import isolation  # noqa: E402
import procscope  # noqa: E402
import scenario_ready  # noqa: E402

# sha256 of every `PROMPT='...'` line of run_ab.sh at 39fed2a (34 lines).
# LADDER.md rule 1: a frozen prompt never changes, not even for a typo.
FROZEN_PROMPTS_SHA256 = "e16101d17e01b4051c07feff6564b04c134be01ffd62a1e59065706fb88e28e9"


def have_base() -> bool:
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{BASE}^{{commit}}"],
                          capture_output=True).returncode == 0


def old_file(rel: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(subprocess.run(["git", "-C", str(REPO), "show", f"{BASE}:{rel}"],
                                    capture_output=True, check=True).stdout)
    return dest


def userns_ok() -> bool:
    r = subprocess.run(["unshare", "--map-root-user", "--mount", "--", "true"],
                       capture_output=True)
    return r.returncode == 0


def transcript(path: Path, *, text="A real answer. " + "x" * 450, result=True,
               is_error=False, subtype="success", init: dict | None = None) -> Path:
    lines = []
    lines.append(json.dumps(init if init is not None else
                            {"type": "system", "subtype": "init",
                             "model": "claude-test", "skills": [], "plugins": []}))
    lines.append(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": text}]}}))
    if result:
        lines.append(json.dumps({"type": "result", "subtype": subtype,
                                 "is_error": is_error, "result": text}))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def empty_keys(task: str) -> list[str]:
    """The check keys a sidecar task reports, read off the grader itself."""
    with tempfile.TemporaryDirectory() as d:
        t = transcript(Path(d) / f"{task}-baseline_result.jsonl")
        return list(grade_v2.grade_cell(task, t, check=Path(d) / "absent.json"))


def all_pass_verdict(task: str) -> dict:
    d = {k: True for k in empty_keys(task)}
    for found in ("workspace", "bringup", "node", "world", "params"):
        d[f"{task}_{found}_found"] = True
    return d


# ---------------------------------------------------------------------------
class GraderDispatch(unittest.TestCase):
    def test_cli_reads_every_sidecar_task(self):
        """39fed2a: `grade_v2.py ctl1 <t>` returned null for every sweep task."""
        self.assertEqual(grade_v2.SIDECAR_TASKS,
                         frozenset(grade_v2.TASKS) - {"t1", "t2", "t3", "t4"})
        with tempfile.TemporaryDirectory() as d:
            for task in sorted(grade_v2.SIDECAR_TASKS):
                t = transcript(Path(d) / task / f"{task}-baseline_result.jsonl")
                (t.parent / f"{task}-baseline_check.json").write_text(
                    json.dumps(all_pass_verdict(task)))
                out = subprocess.run([sys.executable, str(HARNESS / "grade_v2.py"),
                                      task, str(t)], capture_output=True, text=True)
                self.assertEqual(out.returncode, 0, out.stderr)
                grade = json.loads(out.stdout)["grade"]
                self.assertTrue(grade, task)
                # t5-t7 also carry one transcript fact (first colcon build);
                # this transcript ran no build, so that one is ungradable.
                verdict = {k: v for k, v in grade.items()
                           if not k.endswith("_first_build_clean")}
                self.assertTrue(all(v is True for v in verdict.values()), (task, grade))

    def test_committed_cell_grades_from_its_verdict(self):
        t = REPO / "evals/runs/2026-07-31-sweep-L1/ctl1/r1/ctl1-baseline_result.jsonl"
        grade = grade_v2.grade_cell("ctl1", t)
        self.assertEqual(grade, {"ctl1_cm_running": True, "ctl1_jsb_active": True,
                                 "ctl1_joint_states": True})

    @unittest.skipUnless(have_base(), f"{BASE} not in this checkout's history")
    def test_before_cli_returned_null(self):
        with tempfile.TemporaryDirectory() as d:
            old = old_file("evals/harness/grade_v2.py", Path(d) / "grade_v2.py")
            t = REPO / "evals/runs/2026-07-31-sweep-L1/ctl1/r1/ctl1-baseline_result.jsonl"
            out = subprocess.run([sys.executable, str(old), "ctl1", str(t)],
                                 capture_output=True, text=True, check=True)
            grade = json.loads(out.stdout)["grade"]
            self.assertTrue(all(v is None for v in grade.values()), grade)

    def test_no_pseudo_checks(self):
        for task in sorted(grade_v2.SIDECAR_TASKS):
            for k in empty_keys(task):
                self.assertNotIn("unused", k, task)


class Gradability(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _cell(self, **kw):
        return grade_v2.Cell(transcript(self.d / "t1-baseline_result.jsonl", **kw))

    def test_ungradable_forms(self):
        self.assertTrue(self._cell().gradable())
        self.assertFalse(self._cell(result=False).gradable(), "cut off: no result event")
        self.assertFalse(self._cell(is_error=True).gradable(), "CLI-reported error")
        self.assertFalse(self._cell(subtype="error_max_turns").gradable())
        self.assertFalse(self._cell(text="Not logged in · Please run /login").gradable())
        self.assertFalse(self._cell(text="You've hit your session limit · resets 7am").gradable())
        self.assertFalse(self._cell(text="").gradable())

    def test_error_cell_is_not_failed_by_its_verdict(self):
        t = transcript(self.d / "ctl1-baseline_result.jsonl", is_error=True)
        (self.d / "ctl1-baseline_check.json").write_text(json.dumps(
            {"ctl1_bringup_found": True, "ctl1_cm_running": False}))
        self.assertTrue(all(v is None for v in grade_v2.grade_cell("ctl1", t).values()))

    def test_broken_verdict_file_is_ungradable_not_failed(self):
        t = transcript(self.d / "ctl1-baseline_result.jsonl")
        chk = self.d / "ctl1-baseline_check.json"
        for body in ("{truncated", json.dumps({"ctl1_cm_running": True}), "[]"):
            chk.write_text(body)
            self.assertTrue(all(v is None for v in grade_v2.grade_cell("ctl1", t).values()),
                            body)
        chk.write_text(json.dumps({"ctl1_bringup_found": False}))
        self.assertTrue(all(v is False for v in grade_v2.grade_cell("ctl1", t).values()),
                        "no workspace at all is a real failure")

    def test_pack_components_seen_in_init(self):
        init = {"type": "system", "subtype": "init", "model": "m",
                "skills": ["debug", "ros2-troubleshooting"],
                "plugins": [{"name": "claude-ros2-skills", "path": "/x"}]}
        c = self._cell(init=init)
        self.assertEqual(sorted(c.pack_components_loaded()),
                         ["claude-ros2-skills", "ros2-troubleshooting"])
        self.assertEqual(self._cell().pack_components_loaded(), [])

    def test_partial_and_invalid_verdicts_never_invent_evidence(self):
        t = transcript(self.d / "ctl1-baseline_result.jsonl")
        chk = self.d / "ctl1-baseline_check.json"
        chk.write_text(json.dumps({"ctl1_bringup_found": True,
                                   "ctl1_cm_running": True,
                                   "ctl1_jsb_active": "false"}))
        self.assertEqual(grade_v2.grade_cell("ctl1", t),
                         {"ctl1_cm_running": True, "ctl1_jsb_active": None,
                          "ctl1_joint_states": None})
        chk.write_text(json.dumps({"ctl1_bringup_found": "false"}))
        self.assertTrue(all(v is None for v in grade_v2.grade_cell("ctl1", t).values()))

    def test_non_object_json_lines_do_not_crash(self):
        p = transcript(self.d / "t1-baseline_result.jsonl")
        p.write_text('null\n[]\n42\n' + p.read_text())
        self.assertTrue(grade_v2.Cell(p).gradable())


class InstallFacts(unittest.TestCase):
    def test_selftest_is_hermetic(self):
        """39fed2a: selftest FAILED on any host without Nav2 installed."""
        out = subprocess.run([sys.executable, str(HARNESS / "grade_v2.py"), "--selftest"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_absent_nav2_is_ungradable(self):
        with tempfile.TemporaryDirectory() as d:
            real = grade_v2.JAZZY, grade_v2._PLUGINS
            try:
                grade_v2.JAZZY, grade_v2._PLUGINS = Path(d), None
                t = self._t3_cell(d, "nav2_mppi_controller::MPPIController")
                self.assertIsNone(grade_v2.t3(t)["t3_plugins_real"])
            finally:
                grade_v2.JAZZY, grade_v2._PLUGINS = real

    @staticmethod
    def _t3_cell(d, plugin):
        p = Path(d) / "t3-baseline_result.jsonl"
        lines = [json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Write",
             "input": {"file_path": "/w/nav2_params.yaml",
                       "content": f'plugin: "{plugin}"'}}]}}),
                 json.dumps({"type": "result", "subtype": "success", "is_error": False,
                             "result": "Wrote it. " + "x" * 450})]
        p.write_text("\n".join(lines))
        return grade_v2.Cell(p)


# ---------------------------------------------------------------------------
def run_analyze(root: Path, *args) -> str:
    out = subprocess.run([sys.executable, str(HARNESS / "analyze_v2.py"), str(root), *args],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


class Analysis(unittest.TestCase):
    def test_synthetic_round(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "round"
            verdict = json.dumps(all_pass_verdict("ctl1"))

            def cell(rel, **kw):
                t = transcript(root / rel, **kw)
                (t.parent / t.name.replace("_result.jsonl", "_check.json")).write_text(verdict)

            cell("ctl1/r1/ctl1-baseline_result.jsonl")
            cell("ctl1-DISCARDED-mid-round-edit/r1/ctl1-baseline_result.jsonl")
            cell("ctl1-SUPERSEDED-grader-race/r1/ctl1-baseline_result.jsonl")
            cell("ctl1/r2/ctl1-baseline_result.jsonl", result=False)
            cell("ctl1/r3/ctl1-baseline_result.jsonl",
                 init={"type": "system", "subtype": "init", "model": "m",
                       "skills": ["ros2-troubleshooting"], "plugins": []})
            out = run_analyze(root)
            self.assertIn("| `ctl1` | ctl1_cm_running | 1/1 |", out)
            self.assertIn("`ctl1-DISCARDED-mid-round-edit` — 1 transcript(s)", out)
            self.assertIn("`ctl1-SUPERSEDED-grader-race` — 1 transcript(s)", out)
            self.assertIn("`ctl1/r2/ctl1-baseline_result.jsonl`", out)   # ungradable
            self.assertIn("CONTAMINATED", out)
            self.assertIn("`ctl1/r3/ctl1-baseline_result.jsonl` — ros2-troubleshooting", out)
            self.assertIn("NOT EVALUATED", out)
            self.assertNotIn("the other tasks can be read", out)
            self.assertNotIn("unused_transcript_key", out)
            self.assertNotIn("TASKS.md before the round", out)
            audit = run_analyze(root, "--include-superseded")
            self.assertIn("| `ctl1` | ctl1_cm_running | 3/3 |", audit)

    def test_t4_cells_do_not_share_files(self):
        """Two conditions in one out-dir used to overwrite each other's node.py,
        and t4 then graded whichever survived."""
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "t4-skills_result.jsonl"
            (Path(d) / "t4-skills_files").mkdir()
            self.assertEqual(analyze_v2.cell_workdir(f, "t4-skills"),
                             str(Path(d) / "t4-skills_files"))
            self.assertEqual(analyze_v2.cell_workdir(f, "t4-baseline"), d)

    def test_committed_rounds_reproduce_committed_verdicts(self):
        """The numbers evals/CAPABILITIES.md's reconciliation table quotes."""
        want = {
            "2026-07-31-sweep-L1": ["| `mvt1` | mvt1_move_group_up | 10/10 |",
                                    "| `per1` | per1_frames | 9/10 |",
                                    "40 cells read; 0 ungradable"],
            "2026-07-31-sweep-L2": ["| `ctl2` | ctl2_command_lands | 6/8 |",
                                    "| `tst2` | tst2_launch_testing | 9/10 |",
                                    "| `per2` | per2_detection_correct | 8/10 |",
                                    "| `mvt2` | mvt2_move_group_up | 7/10 |",
                                    "40 cells read; 2 ungradable"],
            "2026-08-01-sweep-L3": ["| `tst3` | tst3_bag_written | 3/10 |",
                                    "| `per3` | per3_clouds | 7/10 |",
                                    "| `ctl3` | ctl3_custom_plugin | 10/10 |"],
            "2026-08-01-sweep-coredev": ["| `dev1` | dev1_servers_load | 0/10 |",
                                         "| `dev2` | dev2_servers_up | 9/9 |",
                                         "| `dev3` | dev3_obstacle_marked | 10/10 |"],
        }
        for rnd, lines in want.items():
            out = run_analyze(REPO / "evals/runs" / rnd)
            for line in lines:
                self.assertIn(line, out, rnd)
            self.assertIn("Models (from each transcript's init event): `claude-sonnet-5`", out)
            self.assertNotIn("CONTAMINATED", out, rnd)

    @unittest.skipUnless(have_base(), f"{BASE} not in this checkout's history")
    def test_before_pooled_discarded_and_passed_absent_gate(self):
        with tempfile.TemporaryDirectory() as d:
            old_file("evals/harness/grade_v2.py", Path(d) / "grade_v2.py")
            old = old_file("evals/harness/analyze_v2.py", Path(d) / "analyze_v2.py")
            out = subprocess.run([sys.executable, str(old),
                                  str(REPO / "evals/runs/2026-07-31-sweep-L1")],
                                 capture_output=True, text=True, check=True).stdout
            self.assertIn("| `mvt1` | mvt1_move_group_up | 12/12 |", out)
            self.assertIn("the other tasks can be read", out)

    def test_thresholds_unchanged(self):
        self.assertEqual(analyze_v2.ALPHA, 0.05)
        src = (HARNESS / "analyze_v2.py").read_text()
        self.assertIn('abs(r["delta"]) >= 0.25', src)


# ---------------------------------------------------------------------------
class Procs(unittest.TestCase):
    """procscope: only this run's processes, whatever they are named."""

    def setUp(self):
        self.tag = procscope.new_tag()
        self.spawned: list[subprocess.Popen] = []

    def tearDown(self):
        for p in self.spawned:
            if p.poll() is None:
                p.kill()
            p.wait()

    def spawn(self, argv0: str, tagged: bool, *, extra_env=None, prefix=()):
        env = {k: v for k, v in os.environ.items() if k != procscope.TAG_VAR}
        if tagged:
            env[procscope.TAG_VAR] = self.tag
        env.update(extra_env or {})
        p = subprocess.Popen([*prefix, "bash", "-c", f'exec -a "{argv0}" sleep 300'],
                             env=env, start_new_session=True)
        self.spawned.append(p)
        return p

    def wait_argv0(self, p, argv0, timeout=5.0):
        end = time.time() + timeout
        while time.time() < end:
            if argv0 in procscope.cmdline(p.pid):
                return
            time.sleep(0.02)
        self.fail(f"{argv0} never started")

    def kill(self, *patterns, env_tag=True, any_tag=False):
        env = {k: v for k, v in os.environ.items() if k != procscope.TAG_VAR}
        if env_tag:
            env[procscope.TAG_VAR] = self.tag
        args = [sys.executable, str(HARNESS / "procscope.py"), "kill"]
        if any_tag:
            args.append("--any-tag")
        return subprocess.run(args + list(patterns), env=env, capture_output=True, text=True)

    @staticmethod
    def dead(p, timeout=5.0):
        try:
            p.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False

    def test_same_name_untagged_process_survives(self):
        ours = self.spawn("robot_state_publisher", True)
        theirs = self.spawn("robot_state_publisher", False)
        other = self.spawn("unrelated_node", True)
        for p, a in ((ours, "robot_state_publisher"), (theirs, "robot_state_publisher"),
                     (other, "unrelated_node")):
            self.wait_argv0(p, a)
        # What the old checkers ran matched both: pgrep is read-only proof.
        hits = subprocess.run(["pgrep", "-f", "robot_state_publisher"],
                              capture_output=True, text=True).stdout.split()
        self.assertIn(str(theirs.pid), hits, "the old `pkill -9 -f` selector reached it")
        self.kill("robot_state_publisher")
        self.assertTrue(self.dead(ours))
        self.assertIsNone(theirs.poll(), "an untagged process was killed")
        self.assertIsNone(other.poll(), "a non-matching process was killed")
        self.kill()  # no pattern: everything of this run
        self.assertTrue(self.dead(other))
        self.assertIsNone(theirs.poll())

    def test_refuses_without_tag(self):
        theirs = self.spawn("robot_state_publisher", False)
        self.wait_argv0(theirs, "robot_state_publisher")
        r = self.kill("robot_state_publisher", env_tag=False)
        self.assertEqual(r.returncode, 2)
        self.assertIsNone(theirs.poll())

    @unittest.skipUnless(userns_ok(), "unprivileged user namespaces unavailable")
    def test_reaches_into_the_cell_namespace(self):
        ours = self.spawn("move_group", True,
                          prefix=("unshare", "--map-root-user", "--mount", "--"))
        self.wait_argv0(ours, "move_group")
        self.kill("move_group")
        self.assertTrue(self.dead(ours))

    def test_callers_ancestors_are_spared(self):
        env = {k: v for k, v in os.environ.items() if k != procscope.TAG_VAR}
        env[procscope.TAG_VAR] = self.tag
        # The parent's own argv0 matches the pattern; it must survive and report.
        p = subprocess.run(
            ["bash", "-c", f'exec -a spawner_parent bash -c \'"{sys.executable}" '
                           f'"{HARNESS}/procscope.py" kill spawner_parent; echo alive\''],
            env=env, capture_output=True, text=True, timeout=30)
        self.assertIn("alive", p.stdout)

    def test_adopt_domain_reads_only_our_process(self):
        """An unscoped `pgrep -f ros2_control_node | head -1` picks the oldest
        match on the host -- here, somebody else's controller on domain 7."""
        theirs = self.spawn("ros2_control_node", False, extra_env={"ROS_DOMAIN_ID": "7"})
        self.wait_argv0(theirs, "ros2_control_node")
        ours = self.spawn("ros2_control_node", True, extra_env={"ROS_DOMAIN_ID": "42"})
        self.wait_argv0(ours, "ros2_control_node")
        env = {k: v for k, v in os.environ.items() if k != procscope.TAG_VAR}
        env[procscope.TAG_VAR] = self.tag
        env["ROS_DOMAIN_ID"] = "55"
        out = subprocess.run(
            ["bash", "-c", f'source "{HARNESS}/procscope.sh"; '
                           f'adopt_domain_from ros2_control_node; echo "$ROS_DOMAIN_ID"'],
            env=env, capture_output=True, text=True, timeout=30).stdout.split()
        self.assertEqual(out[-1], "42")

    def test_foreign_ros_detection(self):
        name = "/opt/ros/jazzy/lib/robot_state_publisher/robot_state_publisher --ros-args"
        theirs = self.spawn(name, False)
        ours = self.spawn(name, True)
        self.wait_argv0(theirs, "--ros-args")
        self.wait_argv0(ours, "--ros-args")
        pids = {pid for pid, _ in procscope.foreign_ros()}
        self.assertIn(theirs.pid, pids)
        self.assertNotIn(ours.pid, pids)

    def test_discovery_defaults_cannot_inherit_subnet_or_static_peers(self):
        env = dict(os.environ, ROS_AUTOMATIC_DISCOVERY_RANGE="SUBNET",
                   ROS_STATIC_PEERS="192.0.2.1", EVAL_RUN_TAG=self.tag)
        for name in ("ROS_DISCOVERY_SERVER", "FASTDDS_DEFAULT_PROFILES_FILE",
                     "FASTRTPS_DEFAULT_PROFILES_FILE", "CYCLONEDDS_URI"):
            env.pop(name, None)
        script = (f'source "{HARNESS}/procscope.sh"; '
                  'echo "$ROS_AUTOMATIC_DISCOVERY_RANGE/${ROS_STATIC_PEERS-unset}"')
        out = subprocess.run(["bash", "-c", script], env=env, text=True, capture_output=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "LOCALHOST/unset")
        env["ROS_DISCOVERY_SERVER"] = "192.0.2.1:11811"
        out = subprocess.run(["bash", "-c", script], env=env, text=True, capture_output=True)
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("LOCALHOST", out.stdout)


class ScenarioReadiness(unittest.TestCase):
    def test_inactive_controller_does_not_satisfy_prompt(self):
        self.assertFalse(scenario_ready.controller_active(
            "diff_drive_controller diff_drive_controller/DiffDriveController inactive"))
        self.assertFalse(scenario_ready.controller_active(
            "other diff_drive_controller/DiffDriveController active"))
        self.assertTrue(scenario_ready.controller_active(
            "diff_drive_controller diff_drive_controller/DiffDriveController \x1b[92mactive\x1b[0m"))

    def test_readiness_retries_then_stops_at_total_deadline(self):
        now = [0.0]
        calls = []
        def sleep(seconds):
            now[0] += seconds
        def absent(command, **kwargs):
            calls.append(command)
            now[0] += kwargs['timeout']
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])
        ready, detail = scenario_ready.wait_until_ready(
            't2', 8, probe=absent, clock=lambda: now[0], sleep=sleep)
        self.assertFalse(ready)
        self.assertIn('/imu/data', detail)
        self.assertEqual(now[0], 8)
        self.assertEqual(len(calls), 2)

    def test_all_promised_resources_are_required(self):
        seen = []
        def probe(command, **kwargs):
            seen.append(command)
            return subprocess.CompletedProcess(command, 0, 'message', '')
        self.assertTrue(scenario_ready.wait_until_ready('per2', probe=probe)[0])
        self.assertEqual([c[3] for c in seen], ['/camera/image_raw', '/camera/camera_info'])
        seen.clear()
        self.assertTrue(scenario_ready.wait_until_ready('t2', probe=probe)[0])
        self.assertEqual(len(seen), 2)
        self.assertIn('imu_link', seen[1])

    def test_failed_readiness_prevents_model_call(self):
        # Exercise the real start_scenario function with a configuration-only
        # task and a failing readiness command. No ROS package or model needed.
        src = (HARNESS / 'run_ab.sh').read_text()
        function = src[src.index('start_scenario() {'):src.index('\nstop_scenario() {')]
        # Sourcing ROS is irrelevant for t3 and unavailable in the pure CI job.
        function = function.replace('source /opt/ros/jazzy/setup.bash', ':')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'scenario_ready.py').write_text('raise SystemExit(2)\n')
            script = ('set -euo pipefail\nTASK=t3\n'
                      f'HARNESS="{root}"\nSCEN_LOG="{root}/scenario.log"\n'
                      'ROS_DOMAIN_ID=90\n' + function +
                      '\nstart_scenario\necho MODEL_STARTED\n')
            result = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn('MODEL_STARTED', result.stdout)
            self.assertIn('no model call made', result.stderr)


class Scripts(unittest.TestCase):
    SH = sorted(HARNESS.glob("*.sh"))

    @staticmethod
    def code(path: Path) -> str:
        return "\n".join(l for l in path.read_text().splitlines()
                         if not l.lstrip().startswith("#"))

    def test_syntax(self):
        for f in self.SH:
            r = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")

    def test_no_host_wide_process_selection(self):
        for f in self.SH:
            c = self.code(f)
            self.assertNotRegex(c, r"\bpkill\b", f.name)
            self.assertNotRegex(c, r'pgrep -f "\$1"', f.name)
            self.assertNotRegex(c, r"pgrep -fc", f.name)
            if f.name != "procscope.sh":  # the one, scoped, definition
                self.assertNotIn("adopt_domain_from() {", c, f.name)

    def test_every_checker_scopes_before_it_kills(self):
        for f in sorted(HARNESS.glob("*_check.sh")):
            c = self.code(f)
            if "source /opt/ros/jazzy/setup.bash" not in c:
                continue
            src = c.find('/procscope.sh"')
            self.assertGreater(src, 0, f.name)
            for use in ("kill_all\n", "kill_sims\n", "kill_owned", "adopt_domain_from "):
                i = c.find(use, src - 1 if use == "kill_owned" else 0)
                if use in ("kill_all\n", "kill_sims\n", "adopt_domain_from ") and i >= 0:
                    self.assertGreater(i, src, f"{f.name}: {use.strip()} before procscope.sh")

    def test_frozen_prompts_unchanged(self):
        lines = [l for l in (HARNESS / "run_ab.sh").read_text().splitlines()
                 if "PROMPT='" in l]
        self.assertEqual(len(lines), 34)
        self.assertEqual(hashlib.sha256("\n".join(lines).encode()).hexdigest(),
                         FROZEN_PROMPTS_SHA256)

    def test_run_ab_uses_isolation_flags(self):
        c = self.code(HARNESS / "run_ab.sh")
        for flag in ("--setting-sources project,local", "--strict-mcp-config",
                     'isolate_cell.sh" "$dir"'):
            self.assertIn(flag, c)
        self.assertNotIn('MODEL="${MODEL:-haiku}"', c)

    @unittest.skipUnless(have_base(), f"{BASE} not in this checkout's history")
    def test_historical_runs_untouched(self):
        r = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", BASE, "--",
                            "evals/runs"], capture_output=True)
        self.assertEqual(r.returncode, 0, "evals/runs/ changed")


class Preflight(unittest.TestCase):
    def run_ab(self, env_extra: dict) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items()
               if k not in ("MODEL", procscope.TAG_VAR)}
        env.update(env_extra)
        return subprocess.run(["bash", str(HARNESS / "run_ab.sh"), "--preflight", "ctl1"],
                              env=env, capture_output=True, text=True, timeout=120)

    def test_model_must_be_named(self):
        r = self.run_ab({})
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("MODEL is not set", r.stderr)

    def test_leftover_eval_process_blocks(self):
        env = {k: v for k, v in os.environ.items() if k != procscope.TAG_VAR}
        env[procscope.TAG_VAR] = procscope.new_tag()
        p = subprocess.Popen(["bash", "-c", "exec -a leftover_node sleep 300"], env=env,
                             start_new_session=True)
        try:
            end = time.time() + 5
            while "leftover_node" not in procscope.cmdline(p.pid) and time.time() < end:
                time.sleep(0.02)
            r = self.run_ab({"MODEL": "sonnet"})
            self.assertEqual(r.returncode, 3)
            self.assertIn("earlier eval run are still alive", r.stderr)
            self.assertIn(str(p.pid), r.stderr)
            self.assertIsNone(p.poll(), "preflight must report, never kill")
        finally:
            p.kill()
            p.wait()


# ---------------------------------------------------------------------------
@unittest.skipUnless(shutil.which("unshare") and userns_ok(),
                     "unprivileged user namespaces unavailable")
class Isolation(unittest.TestCase):
    """A fake repository, a fake HOME and a fake /tmp, so nothing real is read."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="iso-test-"))
        r = self.root
        self.repo = r / "repo"
        (self.repo / "evals/harness").mkdir(parents=True)
        for f in ("isolate_cell.sh", "isolation.py"):
            shutil.copy(HARNESS / f, self.repo / "evals/harness" / f)
        (self.repo / "SECRET").write_text("eval design")
        self.home = r / "home"
        (self.home / ".claude/skills/mine").mkdir(parents=True)
        (self.home / ".claude/skills/mine/SKILL.md").write_text("user skill")
        (self.home / ".claude/CLAUDE.md").write_text("user instructions")
        (self.home / ".claude/.credentials.json").write_text("{}")
        (self.home / "clone/evals/harness").mkdir(parents=True)
        (self.home / "clone/evals/harness/isolate_cell.sh").write_text("")
        (self.home / "clone/SECRET").write_text("second clone")
        self.tmp = r / "tmp"
        (self.tmp / "eval-x-skills-abcd").mkdir(parents=True)
        (self.tmp / "eval-x-skills-abcd/CLAUDE.md").write_text(isolation.MARKER + "\n")
        self.extra = r / "coordination"
        self.extra.mkdir()
        (self.extra / "transcript.jsonl").write_text("quotes the repo")
        (r / "parent").mkdir()
        (r / "parent/CLAUDE.md").write_text("ancestor instructions")
        self.work = r / "parent/work"
        self.work.mkdir()
        self.managed = r / "managed-empty"
        self.managed.mkdir()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def env(self, **kw):
        e = dict(os.environ)
        for k in ("EVAL_MASK_PATHS", "CLAUDE_CONFIG_DIR", "EVAL_ALLOW_MANAGED_POLICY"):
            e.pop(k, None)
        e.update(HOME=str(self.home), EVAL_SCAN_TMP=str(self.tmp),
                 EVAL_MASK_PATHS=str(self.extra),
                 EVAL_MANAGED_POLICY_DIR=str(self.managed))
        e.update(kw)
        return e

    PROBE = ('echo "uid=$(id -u)"; '
             'for f in "$R/SECRET" "$H/clone/SECRET" "$H/.claude/CLAUDE.md" '
             '"$H/.claude/skills/mine/SKILL.md" "$T/eval-x-skills-abcd/CLAUDE.md" '
             '"$X/transcript.jsonl" "$P/CLAUDE.md"; do '
             '  if [ -s "$f" ]; then echo "VISIBLE $f"; fi; done; '
             '[ -s "$H/.claude/.credentials.json" ] || [ -f "$H/.claude/.credentials.json" ] '
             '  && echo "credentials visible"; '
             'if umount "$R" 2>/dev/null; then echo UNMOUNTED; fi; '
             '[ -s "$R/SECRET" ] && echo "VISIBLE-AFTER-UMOUNT"; true')

    def run_iso(self, script: Path, env=None):
        e = env or self.env()
        e.update(R=str(self.repo), H=str(self.home), T=str(self.tmp), X=str(self.extra),
                 P=str(self.root / "parent"))
        return subprocess.run(["bash", str(script), str(self.work), "bash", "-c", self.PROBE],
                              env=e, capture_output=True, text=True, timeout=60)

    def test_everything_hidden_and_agent_is_not_root(self):
        r = self.run_iso(self.repo / "evals/harness/isolate_cell.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"uid={os.getuid()}", r.stdout)
        self.assertNotIn("VISIBLE", r.stdout)
        self.assertNotIn("UNMOUNTED", r.stdout)
        self.assertIn("credentials visible", r.stdout)

    def test_check_mode(self):
        r = subprocess.run(["bash", str(self.repo / "evals/harness/isolate_cell.sh"),
                            "--check", str(self.work)], env=self.env(),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"agent uid {os.getuid()}", r.stdout)

    @unittest.skipUnless(have_base(), f"{BASE} not in this checkout's history")
    def test_before_agent_was_root_and_could_unmount(self):
        old = old_file("evals/harness/isolate_cell.sh",
                       self.root / "oldrepo/evals/harness/isolate_cell.sh")
        (self.root / "oldrepo/SECRET").write_text("eval design")
        e = self.env()
        e["R"], e["H"] = str(self.root / "oldrepo"), str(self.home)
        r = subprocess.run(["bash", str(old), str(self.work), "bash", "-c",
                            'echo "uid=$(id -u)"; umount "$R" && cat "$R/SECRET"; '
                            'cat "$H/.claude/CLAUDE.md"'],
                           env=e, capture_output=True, text=True, timeout=60)
        self.assertIn("uid=0", r.stdout)
        self.assertIn("eval design", r.stdout, "the mask could be removed from inside")
        self.assertIn("user instructions", r.stdout, "host instructions were visible")

    def refuse(self, code, **kw):
        r = subprocess.run(["bash", str(self.repo / "evals/harness/isolate_cell.sh"),
                            str(self.work), "true"], env=self.env(**kw),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, code, r.stderr)
        self.assertIn("REFUSING", r.stderr)

    def test_refusals(self):
        (self.managed / "CLAUDE.md").write_text("org policy")
        self.refuse(5)
        (self.managed / "CLAUDE.md").unlink()
        self.refuse(2, EVAL_MASK_PATHS=str(self.root / "no-such-dir"))
        self.refuse(6, EVAL_MASK_PATHS=str(self.home))            # would hide credentials
        self.refuse(6, EVAL_MASK_PATHS=str(self.root / "parent"))  # would hide the workdir

    def test_no_unshare_refuses(self):
        bindir = self.root / "bin"
        bindir.mkdir()
        for tool in ("bash", "python3", "mktemp", "dirname", "rm", "rmdir", "mkdir", "sed"):
            src = shutil.which(tool)
            if src:
                os.symlink(src, bindir / tool)
        r = subprocess.run([str(bindir / "bash"), str(self.repo / "evals/harness/isolate_cell.sh"),
                            str(self.work), "true"], env=self.env(PATH=str(bindir)),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 3, r.stderr)


class Plan(unittest.TestCase):
    def test_shipped_protocol_heading_matches_copy_and_leak_markers(self):
        heading = (REPO / "CLAUDE.md").read_text().splitlines()[0]
        self.assertEqual(heading, f"# {isolation.MARKER}")
        self.assertIn(isolation.MARKER, grade_v2.CONTENT_MARKERS)

    def test_nested_masks_collapse_and_workdir_content_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "home/.claude/plugins/cache/x/evals/harness").mkdir(parents=True)
            (d / "home/.claude/plugins/cache/x/evals/harness/isolate_cell.sh").write_text("")
            (d / "work/.claude/skills/ros2-troubleshooting").mkdir(parents=True)
            (d / "work/.claude/skills/ros2-troubleshooting/SKILL.md").write_text("x")
            (d / "work/CLAUDE.md").write_text(isolation.MARKER)
            (d / "repo").mkdir()
            (d / "managed").mkdir()
            masks = isolation.plan(repo=str(d / "repo"), workdir=str(d / "work"),
                                   cfg=str(d / "home/.claude"), home=str(d / "home"),
                                   tmp=str(d / "no-tmp"), managed=str(d / "managed"))
            paths = [p for _, p in masks]
            self.assertIn(os.path.realpath(d / "home/.claude/plugins"), paths)
            self.assertFalse(any("plugins/cache" in p for p in paths), paths)
            self.assertFalse(any(p.startswith(os.path.realpath(d / "work")) for p in paths),
                             "the cell's own treatment files must stay")


if __name__ == "__main__":
    unittest.main(verbosity=2)
