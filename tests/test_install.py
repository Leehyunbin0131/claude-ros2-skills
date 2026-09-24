#!/usr/bin/env python3
"""Offline install/update/transport regressions, confined to temporary folders."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
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

    def install(self):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.target)

    def test_repeat_install_preserves_instructions_and_unrelated_files(self):
        (self.project/'CLAUDE.md').write_text('My existing project instructions')
        unrelated = self.target/'skills/other/SKILL.md'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text('unrelated skill')
        self.install()
        self.install()
        self.assertEqual((self.project/'CLAUDE.md').read_text(), 'My existing project instructions')
        self.assertEqual(unrelated.read_text(), 'unrelated skill')
        self.assertEqual((self.target/'rules/ros2-verification.md').read_bytes(), (ROOT/'CLAUDE.md').read_bytes())
        self.assertFalse(list(self.target.rglob('*.pyc')))
        helper = self.target/'skills/ros2-troubleshooting/scripts/check_imu_gravity.py'
        result = subprocess.run(['python3', str(helper), '--help'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_update_replaces_only_managed_unchanged_files(self):
        self.install()
        payload = installer.payload()
        payload['rules/ros2-verification.md'] += b'\nfixture update\n'
        with patch.object(installer, 'payload', return_value=payload):
            self.install()
        self.assertEqual((self.target/'rules/ros2-verification.md').read_bytes(), payload['rules/ros2-verification.md'])

    def test_edit_conflict_does_not_partially_update(self):
        self.install()
        path = self.target/'rules/ros2-verification.md'
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
        self.assertFalse((self.target/'rules/ros2-verification.md').exists())
        self.assertEqual((path/'custom').read_text(), 'mine')

    def test_refuses_symlink_rule_destination(self):
        rule = self.target/'rules/ros2-verification.md'
        rule.parent.mkdir(parents=True)
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
        payload = installer.payload()
        payload['rules/ros2-verification.md'] += b'changed'
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
            installer.install(self.target)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
