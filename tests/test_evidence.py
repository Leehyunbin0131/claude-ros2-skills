#!/usr/bin/env python3
"""Contract tests for the optional ros2-development evidence CLI.

Written from the agreed interface specification before reviewing the
implementation, so that these cases can fail it.  Every case runs the CLI as a
subprocess and asserts only on its documented stdout JSON and exit status.  No
ROS, colcon, model, hardware or network access is involved.

Agreed interface (2026-09-26):

    begin  --workspace W --output DIR --scope TEXT --command TEXT
           [--watch PATH ...]      # omitted -> the default scope, not a subset
    finish DIR (--exit-code N | --outcome timeout|unavailable) --log FILE
    inspect DIR [--workspace W]    # default: the recorded workspace

    stdout: {"record_status": "open"|"consistent"|"changed"|"incomplete",
             "declared": {...},
             "observed": {"watch": [...], "changes": [...]},
             "limits": [...]}
    exit:   0 = open|consistent, 1 = changed, 2 = incomplete

Rules under test: a caller-declared outcome is recorded verbatim and is never
presented as a verified command result; a scope that cannot be snapshotted is
incomplete; an input that changed between begin and finish is changed and stays
changed; a change outside the declared watch scope is consistent but must be
stated as a limit; the tool never claims that a test passed.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'skills/ros2-development/scripts/evidence.py'

RECORD_VERSION = 1
CLI_TIMEOUT = 60
EXIT_STATUS = {'open': 0, 'consistent': 0, 'changed': 1, 'incomplete': 2}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_digest(path):
    """Content digest of every regular file under ``path``, for write detection."""
    path = Path(path)
    if not path.exists():
        return {}
    return {str(p.relative_to(path)): sha256_file(p)
            for p in sorted(path.rglob('*')) if p.is_file() and not p.is_symlink()}


@unittest.skipUnless(EVIDENCE.exists(),
                     'evidence.py is not implemented in this checkout yet')
class EvidenceCLIContract(unittest.TestCase):
    """Every assertion below is traceable to one line of the agreed spec."""

    FORBIDDEN_SUCCESS_CLAIMS = {'pass', 'passed', 'passing', 'verified', 'success'}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.ws = self.base/'ws'
        (self.ws/'src/pkg').mkdir(parents=True)
        (self.ws/'src/pkg/node.py').write_text('VALUE = 1\n')
        (self.ws/'src/pkg/config.yaml').write_text('rate: 10\n')
        self.out = self.base/'record-01'
        self.build_log = self.base/'build.log'
        self.build_log.write_text('--- colcon build ---\nfinished\n')

    # --- harness -----------------------------------------------------------

    def run_cli(self, *args, env=None, cwd=None):
        cmd = [sys.executable, str(EVIDENCE)] + [str(a) for a in args]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=CLI_TIMEOUT, env=env, cwd=cwd)
        payload = None
        if proc.stdout.strip():
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError:
                payload = None
        return proc, payload

    def cli(self, *args, expect=None, env=None, cwd=None):
        """Run one CLI call and enforce the documented envelope and exit map."""
        proc, payload = self.run_cli(*args, env=env, cwd=cwd)
        self.assertIsNotNone(
            payload, 'stdout is not JSON (rc=%s)\nstdout=%r\nstderr=%r'
            % (proc.returncode, proc.stdout[:600], proc.stderr[-600:]))
        for key in ('record_status', 'declared', 'observed', 'limits'):
            self.assertIn(key, payload, payload)
        status = payload['record_status']
        self.assertIn(status, EXIT_STATUS, payload)
        self.assertEqual(
            proc.returncode, EXIT_STATUS[status],
            'exit status must match record_status %r, got rc=%s: %r'
            % (status, proc.returncode, payload))
        self.assertIsInstance(payload['limits'], list)
        self.assertTrue(payload['limits'],
                        'limits must always state what was not observed: %r' % payload)
        self.assertTrue(all(isinstance(x, str) for x in payload['limits']),
                        payload['limits'])
        self.assertIsInstance(payload['observed'].get('watch'), list)
        self.assertIsInstance(payload['observed'].get('changes'), list)
        if expect is not None:
            self.assertEqual(status, expect, payload)
        return payload

    def begin(self, *, output=None, watch=(), workspace=None,
              scope='pkg build and test evidence',
              command='colcon build --packages-select pkg', env=None, expect='open'):
        args = ['begin', '--workspace', str(workspace or self.ws),
                '--output', str(output or self.out),
                '--scope', scope, '--command', command]
        for rel in watch:
            args += ['--watch', str(rel)]
        return self.cli(*args, expect=expect, env=env)

    def finish(self, *, record=None, exit_code=0, outcome=None, log=None,
               env=None, expect=None):
        args = ['finish', str(record or self.out)]
        if outcome is not None:
            args += ['--outcome', outcome]
        else:
            args += ['--exit-code', str(exit_code)]
        args += ['--log', str(log or self.build_log)]
        return self.cli(*args, expect=expect, env=env)

    def inspect(self, *, record=None, workspace=None, env=None, expect=None):
        args = ['inspect', str(record or self.out)]
        if workspace is not None:
            args += ['--workspace', str(workspace)]
        return self.cli(*args, expect=expect, env=env)

    def manifest(self, record=None):
        return json.loads((Path(record or self.out)/'manifest.json').read_text())

    def assert_changed_path_named(self, payload, fragment):
        self.assertIn(fragment, json.dumps(payload),
                      'the report must name what changed: %r' % payload)

    def assert_scope_matches(self, payload, fragment):
        watched = [str(w) for w in payload['observed']['watch']]
        self.assertTrue(any(fragment in w for w in watched), watched)

    def assert_scope_is_only(self, payload, fragment):
        watched = [str(w).rstrip('/') for w in payload['observed']['watch']]
        self.assertTrue(watched, watched)
        for w in watched:
            self.assertTrue(w == fragment or w.endswith('/' + fragment),
                            '%r is outside the declared scope %r' % (w, fragment))

    def assert_no_success_claim(self, node, path='$'):
        """The tool records a declared outcome; it never certifies success."""
        if isinstance(node, dict):
            for key, value in node.items():
                self.assert_no_success_claim(value, '%s.%s' % (path, key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                self.assert_no_success_claim(value, '%s[%d]' % (path, index))
        elif isinstance(node, str):
            self.assertNotIn(
                node.strip().lower(), self.FORBIDDEN_SUCCESS_CLAIMS,
                'record asserts a successful outcome at %s: %r' % (path, node))

    def make_record(self, **kwargs):
        self.begin(**kwargs)
        return self.finish()

    # --- recording envelope ------------------------------------------------

    def test_begin_reports_open_and_declares_only_the_command(self):
        payload = self.begin()
        self.assertEqual(payload['record_status'], 'open')
        self.assertEqual(payload['declared'].get('command'),
                         'colcon build --packages-select pkg')
        for undeclared in ('outcome', 'exit_code'):
            self.assertNotIn(undeclared, payload['declared'],
                             'begin has no result to declare yet')
        self.assertEqual(payload['observed']['changes'], [])
        self.assert_scope_matches(payload, 'src')

        manifest = self.manifest()
        self.assertEqual(manifest['record_version'], RECORD_VERSION)
        self.assertFalse(manifest['complete'])
        self.assertEqual(Path(manifest['workspace']).resolve(), self.ws.resolve())
        self.assertEqual(manifest['scope'], 'pkg build and test evidence')
        self.assertEqual(manifest['command_declared'],
                         'colcon build --packages-select pkg')
        self.assertIn('files', manifest['before'])
        self.assertIn('environment', manifest['before'])

    def test_finish_copies_the_log_and_closes_the_record(self):
        self.begin()
        payload = self.finish()
        self.assertEqual(payload['record_status'], 'consistent')
        self.assertEqual(payload['declared']['command'],
                         'colcon build --packages-select pkg')
        self.assertEqual(payload['declared']['outcome'], 'exited')
        self.assertEqual(payload['declared']['exit_code'], 0)
        self.assertEqual(payload['declared']['log_source'], str(self.build_log))

        copied = self.out/'command.log'
        self.assertTrue(copied.is_file(), 'the log must be copied into the record')
        self.assertEqual(copied.read_text(), self.build_log.read_text())
        manifest = self.manifest()
        self.assertTrue(manifest['complete'])
        self.assertEqual(manifest['log_sha256'], sha256_file(copied))
        self.assertEqual(manifest['result_declared']['outcome'], 'exited')
        self.assertEqual(manifest['result_declared']['exit_code'], 0)
        self.assertEqual(manifest['result_declared']['log_source'], str(self.build_log))

    def test_manifest_records_matching_before_and_after_structures(self):
        self.make_record()
        manifest = self.manifest()
        before, after = manifest['before'], manifest['after']
        self.assertEqual(set(before), set(after))
        self.assertEqual(set(before['files']), set(after['files']))
        self.assertIn('src/pkg/node.py', before['files'])
        self.assertIsInstance(before['environment'], dict)
        self.assertIsInstance(after['environment'], dict)

    def test_inspect_without_changes_is_consistent_and_writes_nothing(self):
        self.make_record()
        manifest_before = (self.out/'manifest.json').read_bytes()
        workspace_before = tree_digest(self.ws)
        payload = self.inspect()
        self.assertEqual(payload['record_status'], 'consistent')
        self.assertEqual(payload['observed']['changes'], [])
        self.assertEqual((self.out/'manifest.json').read_bytes(), manifest_before,
                         'inspect must not rewrite a completed record')
        self.assertEqual(tree_digest(self.ws), workspace_before,
                         'inspect must not write into the workspace')
        self.assert_no_success_claim(payload)

    # --- input change detection --------------------------------------------

    def test_modified_input_is_changed(self):
        self.make_record()
        (self.ws/'src/pkg/node.py').write_text('VALUE = 2\n')
        payload = self.inspect()
        self.assertEqual(payload['record_status'], 'changed')
        self.assert_changed_path_named(payload, 'src/pkg/node.py')

    def test_deleted_input_is_changed_not_incomplete(self):
        self.make_record()
        (self.ws/'src/pkg/config.yaml').unlink()
        payload = self.inspect()
        self.assertEqual(payload['record_status'], 'changed')
        self.assert_changed_path_named(payload, 'src/pkg/config.yaml')

    def test_added_input_inside_the_scope_is_changed(self):
        self.make_record()
        (self.ws/'src/pkg/extra.py').write_text('EXTRA = 1\n')
        payload = self.inspect()
        self.assertEqual(payload['record_status'], 'changed')
        self.assert_changed_path_named(payload, 'src/pkg/extra.py')

    def test_environment_change_is_changed(self):
        env_a = dict(os.environ, ROS_DOMAIN_ID='7')
        env_b = dict(os.environ, ROS_DOMAIN_ID='8')
        self.begin(env=env_a)
        self.assertEqual(self.finish(env=env_b)['record_status'], 'changed')

        self.out = self.base/'record-02'
        self.begin(env=env_a)
        self.finish(env=env_a)
        payload = self.inspect(env=env_b)
        self.assertEqual(payload['record_status'], 'changed')
        self.assertIn('ROS_DOMAIN_ID', json.dumps(payload))

    def test_unrelated_environment_variable_does_not_change_the_record(self):
        env_a = dict(os.environ, EVIDENCE_UNRELATED_VAR='first')
        env_b = dict(os.environ, EVIDENCE_UNRELATED_VAR='second')
        self.begin(env=env_a)
        self.assertEqual(self.finish(env=env_b)['record_status'], 'consistent')
        self.assertEqual(self.inspect(env=env_b)['record_status'], 'consistent')

    def test_change_between_begin_and_finish_is_changed_and_stays_changed(self):
        self.begin()
        (self.ws/'src/pkg/node.py').write_text('VALUE = 99\n')
        payload = self.finish()
        self.assertEqual(payload['record_status'], 'changed')
        manifest = self.manifest()
        self.assertNotEqual(manifest['before']['files']['src/pkg/node.py'],
                            manifest['after']['files']['src/pkg/node.py'],
                            'recorded metadata must be content-sensitive')
        (self.ws/'src/pkg/node.py').write_text('VALUE = 1\n')
        self.assertEqual(self.inspect()['record_status'], 'changed',
                         'a window change is not forgiven by later restoring it')

    def test_change_outside_the_scope_is_consistent_and_stated_as_a_limit(self):
        self.make_record()
        (self.ws/'notes.txt').write_text('outside the default scope\n')
        payload = self.inspect()
        self.assertEqual(payload['record_status'], 'consistent')
        self.assertTrue(payload['limits'], payload)
        self.assert_scope_matches(payload, 'src')
        self.assertIn('src', json.dumps(payload['observed']['watch']))

    def test_explicit_watch_replaces_the_default_scope(self):
        self.begin(watch=['src/pkg'])
        (self.ws/'src/other').mkdir(parents=True)
        (self.ws/'src/other/thing.py').write_text('X = 1\n')
        payload = self.finish()
        self.assertEqual(payload['record_status'], 'consistent',
                         'an explicit --watch is the whole scope, not a subset')
        self.assert_scope_is_only(payload, 'src/pkg')
        (self.ws/'src/pkg/node.py').write_text('VALUE = 3\n')
        self.assertEqual(self.inspect()['record_status'], 'changed')

    # --- snapshot exclusions -----------------------------------------------

    def test_pycache_pyc_and_dot_git_are_excluded(self):
        self.begin()
        (self.ws/'src/pkg/__pycache__').mkdir()
        (self.ws/'src/pkg/__pycache__/node.cpython-312.pyc').write_bytes(b'cache')
        (self.ws/'src/pkg/module.pyc').write_bytes(b'compiled')
        (self.ws/'.git').mkdir()
        (self.ws/'.git/HEAD').write_text('ref: refs/heads/main\n')
        payload = self.finish()
        self.assertEqual(payload['record_status'], 'consistent',
                         'ignored build artifacts must not read as input changes')
        (self.ws/'src/pkg/__pycache__/later.pyc').write_bytes(b'later')
        (self.ws/'.git/HEAD').write_text('ref: refs/heads/other\n')
        self.assertEqual(self.inspect()['record_status'], 'consistent')

    # --- links and unsupported file types ----------------------------------

    def test_symlink_to_a_file_inside_the_workspace_is_hashed_by_content(self):
        os.symlink('node.py', self.ws/'src/pkg/alias.py')
        self.make_record()
        self.assertEqual(self.inspect()['record_status'], 'consistent')
        (self.ws/'src/pkg/node.py').write_text('VALUE = 4\n')
        self.assertEqual(self.inspect()['record_status'], 'changed')

    def test_symlink_pointing_outside_the_workspace_is_incomplete(self):
        outside = self.base/'outside.txt'
        outside.write_text('outside\n')
        os.symlink(outside, self.ws/'src/pkg/outside.py')
        self.begin(expect='incomplete')

    def test_symlink_to_a_directory_is_incomplete(self):
        (self.ws/'src/pkg/real').mkdir()
        (self.ws/'src/pkg/real/inner.py').write_text('INNER = 1\n')
        os.symlink('real', self.ws/'src/pkg/dirlink')
        self.begin(expect='incomplete')

    def test_fifo_inside_the_scope_is_incomplete(self):
        os.mkfifo(self.ws/'src/pkg/pipe')
        self.begin(expect='incomplete')

    def test_missing_watch_path_is_incomplete(self):
        self.begin(watch=['src/does-not-exist'], expect='incomplete')

    # --- record integrity ---------------------------------------------------

    def test_truncated_manifest_is_incomplete(self):
        self.make_record()
        manifest = self.out/'manifest.json'
        manifest.write_text(manifest.read_text()[:len(manifest.read_text())//2])
        self.inspect(expect='incomplete')

    def test_future_record_version_is_incomplete(self):
        self.make_record()
        manifest_path = self.out/'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['record_version'] = RECORD_VERSION + 1
        manifest_path.write_text(json.dumps(manifest))
        self.inspect(expect='incomplete')

    def test_missing_log_is_incomplete(self):
        self.make_record()
        (self.out/'command.log').unlink()
        self.inspect(expect='incomplete')

    def test_modified_log_is_incomplete(self):
        self.make_record()
        with (self.out/'command.log').open('a') as handle:
            handle.write('appended after the record was closed\n')
        self.inspect(expect='incomplete')

    def test_finish_twice_is_refused(self):
        self.make_record()
        manifest_before = (self.out/'manifest.json').read_bytes()
        self.finish(expect='incomplete')
        self.assertEqual((self.out/'manifest.json').read_bytes(), manifest_before,
                         'a completed record is immutable')

    def test_begin_refuses_an_existing_output_directory(self):
        self.out.mkdir()
        self.begin(expect='incomplete')

    def test_begin_refuses_output_inside_the_watch_scope(self):
        self.begin(output=self.ws/'src/evidence-out', expect='incomplete')
        self.begin(output=self.ws/'src/pkg/evidence-out', watch=['src/pkg'],
                   expect='incomplete')

    def test_missing_record_directory_is_incomplete(self):
        self.finish(record=self.base/'no-such-record', expect='incomplete')
        self.inspect(record=self.base/'no-such-record', expect='incomplete')

    # --- workspace relocation and missing workspaces ------------------------

    def test_inspect_defaults_to_the_recorded_workspace(self):
        self.make_record()
        self.assertEqual(self.inspect()['record_status'], 'consistent')

    def test_inspect_accepts_a_relocated_workspace(self):
        self.make_record()
        moved = self.base/'ws-moved'
        shutil.copytree(self.ws, moved)
        self.assertEqual(self.inspect(workspace=moved)['record_status'],
                         'consistent')
        (moved/'src/pkg/node.py').write_text('VALUE = 5\n')
        self.assertEqual(self.inspect(workspace=moved)['record_status'], 'changed')

    def test_inspect_on_a_missing_workspace_is_incomplete(self):
        # Reading of "a scope with no files is incomplete": nothing can be
        # re-hashed, so the record cannot be reported as merely changed.
        self.make_record()
        shutil.rmtree(self.ws)
        self.inspect(expect='incomplete')

    # --- declared outcomes --------------------------------------------------

    def test_declared_timeout_is_incomplete(self):
        self.begin()
        payload = self.finish(outcome='timeout')
        self.assertEqual(payload['record_status'], 'incomplete')
        self.assertEqual(payload['declared']['outcome'], 'timeout')
        self.assertIsNone(payload['declared']['exit_code'])
        self.assertEqual(self.manifest()['result_declared']['outcome'], 'timeout')

    def test_declared_unavailable_is_incomplete(self):
        self.begin()
        payload = self.finish(outcome='unavailable')
        self.assertEqual(payload['record_status'], 'incomplete')
        self.assertEqual(payload['declared']['outcome'], 'unavailable')

    def test_finish_without_a_declared_outcome_is_incomplete(self):
        self.begin()
        proc, payload = self.run_cli('finish', str(self.out), '--log', str(self.build_log))
        self.assertEqual(proc.returncode, 2,
                         'a finish with no declared outcome must be incomplete')
        if payload is not None:
            self.assertEqual(payload['record_status'], 'incomplete')

    def test_invalid_arguments_never_report_changed(self):
        # Exit 1 has a specific meaning here, so argument errors must be 2.
        self.begin()
        for bad in (('--exit-code', 'not-a-number'), ('--outcome', 'maybe')):
            with self.subTest(bad=bad):
                proc, payload = self.run_cli(
                    'finish', str(self.out), *bad, '--log', str(self.build_log))
                self.assertNotEqual(proc.returncode, 1,
                                    'an argument error must never read as changed')
                self.assertEqual(proc.returncode, 2, proc.stderr[-400:])
                if payload is not None:
                    self.assertEqual(payload['record_status'], 'incomplete')
        # "--exit-code N | --outcome ..." is exclusive.  Accepting both silently
        # is a review question, but it must never read as a changed record.
        proc, _ = self.run_cli('finish', str(self.out), '--exit-code', '0',
                               '--outcome', 'timeout', '--log', str(self.build_log))
        self.assertNotEqual(proc.returncode, 1)

    def test_zero_test_success_never_becomes_a_pass_claim(self):
        log = self.base/'colcon-test-zero.log'
        run = subprocess.run(
            [sys.executable, '-c',
             "print('Summary: 0 tests, 0 errors, 0 failures')"],
            capture_output=True, text=True, timeout=CLI_TIMEOUT)
        log.write_text(run.stdout)
        self.begin()
        payload = self.finish(exit_code=run.returncode, log=log)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(payload['record_status'], 'consistent')
        self.assertEqual(payload['declared']['outcome'], 'exited')
        self.assertEqual(payload['declared']['exit_code'], 0)
        self.assert_no_success_claim(payload)
        self.assert_no_success_claim(self.manifest())

    # --- agreed follow-ups (F3 directory validation, F4 optional log for a
    # --- non-exited outcome, F7 inherited-environment provenance) ----------

    ENV_PROVENANCE_SOURCE = 'inherited environment of the evidence process'
    ROS_MARKERS = ('ROS_DISTRO', 'ROS_VERSION', 'ROS_DOMAIN_ID', 'RMW_IMPLEMENTATION',
                   'ROS_LOCALHOST_ONLY', 'ROS_AUTOMATIC_DISCOVERY_RANGE',
                   'ROS_STATIC_PEERS', 'AMENT_PREFIX_PATH')

    def plain_env(self, **overrides):
        """An environment with no ROS marker key present."""
        env = {key: value for key, value in os.environ.items()
               if key not in self.ROS_MARKERS}
        env.update(overrides)
        return env

    def assert_provenance(self, payload):
        provenance = payload['observed'].get('environment_provenance')
        self.assertIsInstance(provenance, dict, payload['observed'])
        self.assertEqual(provenance['source'], self.ENV_PROVENANCE_SOURCE)
        self.assertIsInstance(provenance['null_meaning'], str)
        self.assertTrue(provenance['null_meaning'].strip())
        self.assertIs(provenance['command_environment_verified'], False,
                      'the record can never attest to the command environment')
        present = provenance['keys_present_at_begin']
        self.assertIsInstance(present, list)
        self.assertTrue(all(isinstance(key, str) for key in present), present)
        return provenance

    def test_inspect_rejects_a_workspace_that_is_not_a_directory(self):
        self.make_record()
        self.inspect(workspace=self.build_log, expect='incomplete')
        self.inspect(workspace=self.ws/'src/pkg/node.py', expect='incomplete')

    def test_timeout_without_a_log_finalises_with_an_empty_log(self):
        for outcome in ('timeout', 'unavailable'):
            with self.subTest(outcome=outcome):
                self.out = self.base/('record-' + outcome)
                self.begin()
                payload = self.cli('finish', str(self.out), '--outcome', outcome,
                                   expect='incomplete')
                self.assertEqual(payload['declared']['outcome'], outcome)
                self.assertIsNone(payload['declared']['log_source'])
                self.assertIsNone(payload['declared']['exit_code'])

                manifest = self.manifest()
                self.assertIs(manifest['complete'], True,
                              'a declared non-exited outcome still closes the record')
                self.assertIsNone(manifest['result_declared']['log_source'])
                copied = self.out/'command.log'
                self.assertTrue(copied.is_file(), 'the record must carry a log file')
                self.assertEqual(copied.read_bytes(), b'')
                self.assertEqual(manifest['log_sha256'], sha256_file(copied))
                self.assert_no_success_claim(payload)
                self.inspect(expect='incomplete')

    def test_exited_command_without_a_log_is_incomplete_and_not_finalised(self):
        self.begin()
        proc, payload = self.run_cli('finish', str(self.out), '--exit-code', '0')
        self.assertNotEqual(proc.returncode, 1)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        if payload is not None:
            self.assertEqual(payload['record_status'], 'incomplete')
        self.assertIs(self.manifest()['complete'], False,
                      'an exited command without a log must not finalise the record')
        self.assertFalse((self.out/'command.log').exists())
        # The record is still open, so a correctly declared finish must succeed.
        self.finish(expect='consistent')

    def test_environment_provenance_never_verifies_the_command_environment(self):
        env = self.plain_env()
        begin = self.begin(env=env)
        provenance = self.assert_provenance(begin)
        for marker in self.ROS_MARKERS:
            self.assertNotIn(marker, provenance['keys_present_at_begin'],
                             'no ROS key was set when the record started')
        self.assert_provenance(self.finish(env=env))
        inspected = self.inspect(env=env)
        self.assert_provenance(inspected)
        self.assertEqual(inspected['observed']['environment_provenance']['keys_present_at_begin'],
                         provenance['keys_present_at_begin'])

        semantics = self.manifest().get('environment_semantics')
        self.assertIsInstance(semantics, str)
        self.assertTrue(semantics.strip())
        text = (provenance['null_meaning'] + ' ' + semantics).lower()
        self.assertIn('unset', text, 'null must be explained as unset at that snapshot')
        self.assertIn('command', text,
                      'the text must separate the snapshot shell from the caller command')

    def test_environment_provenance_lists_the_keys_present_at_begin(self):
        env = self.plain_env(ROS_DISTRO='jazzy', ROS_VERSION='2',
                             RMW_IMPLEMENTATION='rmw_fastrtps_cpp',
                             AMENT_PREFIX_PATH='/opt/ros/jazzy')
        provenance = self.assert_provenance(self.begin(env=env))
        for key in ('ROS_DISTRO', 'ROS_VERSION', 'RMW_IMPLEMENTATION', 'AMENT_PREFIX_PATH'):
            self.assertIn(key, provenance['keys_present_at_begin'])

        self.finish(env=env, expect='consistent')
        # The environment contract is unchanged: a different inspect shell still
        # differs, and the provenance keeps reporting what begin actually saw.
        handoff = self.inspect(env=self.plain_env(), expect='changed')
        handoff_provenance = self.assert_provenance(handoff)
        self.assertIn('ROS_DISTRO', handoff_provenance['keys_present_at_begin'])
        self.assertTrue(any('environment' in change for change in handoff['observed']['changes']),
                        handoff['observed']['changes'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
