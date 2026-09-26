#!/usr/bin/env python3
"""Offline install/update/transport regressions, confined to temporary folders."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT/'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ros2 install test ')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.target = self.project/'.claude'
        self.agent = 'claude'
        self.protocol_file = 'rules/ros2-verification.md'

    def install(self):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.target, self.agent)

    def test_repeat_install_preserves_instructions_and_unrelated_files(self):
        (self.project/'CLAUDE.md').write_text('My existing project instructions')
        (self.project/'AGENTS.md').write_text('My existing Codex instructions')
        unrelated = self.target/'skills/other/SKILL.md'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text('unrelated skill')
        self.install()
        self.install()
        self.assertEqual((self.project/'CLAUDE.md').read_text(), 'My existing project instructions')
        self.assertEqual((self.project/'AGENTS.md').read_text(), 'My existing Codex instructions')
        self.assertEqual(unrelated.read_text(), 'unrelated skill')
        self.assertIn((ROOT/'CLAUDE.md').read_bytes().rstrip(), (self.target/self.protocol_file).read_bytes())
        self.assertFalse(list(self.target.rglob('*.pyc')))
        for name in installer.SKILLS:
            self.assertTrue((self.target/'skills'/name/'SKILL.md').is_file())
        helper = self.target/'skills/ros2-troubleshooting/scripts/check_imu_gravity.py'
        result = subprocess.run(['python3', str(helper), '--help'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = self.target/'skills/ros2-development/scripts/evidence.py'
        result = subprocess.run(['python3', str(evidence), '--help'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        checker = self.target/'skills/ros2-development/scripts/check_test_results.py'
        result = subprocess.run(['python3', str(checker), '--help'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_update_replaces_only_managed_unchanged_files(self):
        self.install()
        payload = installer.payload(self.agent)
        payload[self.protocol_file] += b'\nfixture update\n'
        with patch.object(installer, 'payload', return_value=payload):
            self.install()
        self.assertEqual((self.target/self.protocol_file).read_bytes(), payload[self.protocol_file])

    def test_edit_conflict_does_not_partially_update(self):
        self.install()
        path = self.target/self.protocol_file
        path.write_text('my local change')
        before = (self.target/installer.MANIFEST).read_bytes()
        with self.assertRaisesRegex(ValueError, 'locally edited'):
            self.install()
        self.assertEqual(path.read_text(), 'my local change')
        self.assertEqual((self.target/installer.MANIFEST).read_bytes(), before)

    def test_existing_install_and_symlink_are_preserved(self):
        path = self.target/'skills/ros2-troubleshooting'
        path.mkdir(parents=True)
        (path/'custom').write_text('mine')
        with self.assertRaisesRegex(ValueError, 'pre-existing'):
            self.install()
        self.assertFalse((self.target/self.protocol_file).exists())
        self.assertEqual((path/'custom').read_text(), 'mine')

    def test_refuses_symlink_rule_destination(self):
        self.install()
        rule = self.target/self.protocol_file
        rule.unlink()
        outside = self.project/'original'
        outside.write_text('outside')
        rule.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.install()
        self.assertEqual(outside.read_text(), 'outside')

    def test_manifest_cannot_escape_destination(self):
        self.target.mkdir()
        (self.target/installer.MANIFEST).write_text(json.dumps({'../CLAUDE.md': 'bad'}))
        with self.assertRaisesRegex(ValueError, 'invalid managed path'):
            self.install()
        self.assertFalse((self.project/'CLAUDE.md').exists())

    def test_write_error_rolls_back_content(self):
        self.install()
        before = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
        payload = installer.payload(self.agent)
        payload[self.protocol_file] += b'changed'
        original_replace = Path.replace
        calls = 0
        def fail_second(path, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('fixture failure')
            return original_replace(path, destination)
        with patch.object(installer, 'payload', return_value=payload), patch.object(Path, 'replace', fail_second):
            with self.assertRaisesRegex(OSError, 'fixture failure'):
                self.install()
        after = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_retired_skills_are_reported_not_deleted(self):
        stale = self.target/'skills/ros2-moveit'
        stale.mkdir(parents=True)
        (stale/'SKILL.md').write_text('old')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            installer.install(self.target, self.agent)
        self.assertIn('ros2-moveit', output.getvalue())
        self.assertEqual((stale/'SKILL.md').read_text(), 'old')

    def test_plugin_hook_delivers_exact_protocol_from_path_with_spaces(self):
        root = self.project/'plugin with spaces'
        root.mkdir()
        (root/'CLAUDE.md').write_bytes((ROOT/'CLAUDE.md').read_bytes())
        config = json.loads((ROOT/'hooks/hooks.json').read_text())
        command = config['hooks']['SessionStart'][0]['hooks'][0]['command']
        result = subprocess.run(['bash', '-c', command], input='{}', text=True,
                                capture_output=True, timeout=5,
                                env={**os.environ, 'CLAUDE_PLUGIN_ROOT': str(root)}, cwd=self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, (ROOT/'CLAUDE.md').read_text())


class CodexInstallation(Installation):
    def setUp(self):
        super().setUp()
        self.target = self.project/'.agents'
        self.agent = 'codex'
        self.protocol_file = 'skills/ros2-development/SKILL.md'

    def test_each_skill_delivers_protocol_and_original_resources(self):
        self.install()
        protocol = (ROOT/'CLAUDE.md').read_bytes().rstrip()
        self.assertFalse((self.target/'rules').exists())
        self.assertFalse((self.project/'AGENTS.md').exists())
        self.assertFalse((self.project/'.claude').exists())
        for name in installer.SKILLS:
            source = ROOT/'skills'/name
            installed = self.target/'skills'/name
            original_header, _, original_body = (source/'SKILL.md').read_bytes().partition(b'\n---\n')
            header, _, body = (installed/'SKILL.md').read_bytes().partition(b'\n---\n')
            self.assertEqual(header, original_header)
            self.assertEqual(body, b'\n'+protocol+b'\n\n'+original_body.lstrip(b'\n'))
            for path in source.rglob('*'):
                if path.is_file() and path.name != 'SKILL.md' and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    self.assertEqual((installed/path.relative_to(source)).read_bytes(), path.read_bytes())

    def test_project_cli_can_coexist_with_default_claude_installation(self):
        for options in ([], ['--agent', 'codex']):
            result = subprocess.run([sys.executable, str(ROOT/'scripts/install.py'),
                                     '--project', str(self.project), *options],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project/'.claude/rules/ros2-verification.md').is_file())
        self.assertTrue((self.target/self.protocol_file).is_file())
        for host in ('.claude', '.agents'):
            self.assertEqual(len(list((self.project/host/'skills').glob('*/SKILL.md'))), 3)

    def test_user_install_uses_agents_under_home_and_preserves_global_instructions(self):
        codex = self.project/'.codex'
        codex.mkdir()
        instructions = codex/'AGENTS.md'
        instructions.write_text('Global user instructions')
        config = codex/'config.toml'
        config.write_text('model = "user-choice"\n')
        with patch.object(Path, 'home', return_value=self.project), \
             patch.object(sys, 'argv', ['install.py', '--agent', 'codex', '--user']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 0)
        self.assertTrue((self.target/self.protocol_file).is_file())
        self.assertEqual(instructions.read_text(), 'Global user instructions')
        self.assertEqual(config.read_text(), 'model = "user-choice"\n')

    def test_manifest_cannot_manage_claude_rules(self):
        self.target.mkdir()
        (self.target/installer.MANIFEST).write_text(json.dumps({'rules/ros2-verification.md': 'bad'}))
        with self.assertRaisesRegex(ValueError, 'invalid managed path'):
            self.install()
        self.assertFalse((self.target/'rules').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
