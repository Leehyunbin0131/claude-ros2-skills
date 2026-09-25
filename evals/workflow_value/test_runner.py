#!/usr/bin/env python3
"""Delivery evidence and real isolation regressions; no model calls."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

import run


class EvidenceTests(unittest.TestCase):
    def test_pair_gate_rejects_different_facts_or_settings(self):
        previous = dict(cell=1, condition='baseline', seed=0, model=run.MODEL, effort='high',
            input_sha256={'TASK.txt': 'a'}, prompt_sha256='a', freeze_sha256='b',
            cli_version='test', versions={'pytest': 'test'}, settings={'memory': False})
        current = dict(previous, cell=2, condition='pack')
        self.assertTrue(run.pair_matches(current, previous))
        for key, value in [('input_sha256', {'TASK.txt': 'different'}), ('seed', 1),
                           ('effort', 'low'), ('condition', 'baseline')]:
            with self.subTest(key=key):
                self.assertFalse(run.pair_matches(dict(current, **{key: value}), previous))

    def test_export_excludes_reasoning_and_pairs_outputs(self):
        rows = [{'type': 'assistant', 'message': {'content': [
            {'type': 'thinking', 'thinking': 'private deliberation'},
            {'type': 'tool_use', 'id': 'a', 'name': 'Bash', 'input': {'command': 'colcon build'}}]}},
            {'type': 'user', 'message': {'content': [
                {'type': 'tool_result', 'tool_use_id': 'a', 'content': 'build passed'}]}}]
        exported = run.action_records(rows)
        self.assertEqual(exported[0]['output'], 'build passed')
        self.assertNotIn('private deliberation', json.dumps(exported))

    def test_baseline_rejects_unexpected_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [{'type': 'system', 'subtype': 'init', 'model': run.MODEL,
                     'skills': ['ros2-development'], 'plugins': []}]
            summary = run.summarize(rows, 'baseline', Path(tmp), {}, 1, 0)
            self.assertFalse(summary['inventory_correct'])
            self.assertTrue(summary['is_error'])

    def test_pack_requires_real_hook_and_exact_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp)
            (pack/'data').write_text('original')
            payload = run.hashes(pack)
            rows = [{'type': 'system', 'subtype': 'init', 'model': run.MODEL,
                     'skills': list(run.SKILLS), 'plugins': [
                         {'name': 'claude-ros2-skills', 'path': str(pack)}]},
                    {'type': 'result', 'is_error': False, 'result': 'done'}]
            summary = run.summarize(rows, 'pack', pack, payload, 1, 0)
            self.assertTrue(summary['inventory_correct'])
            self.assertFalse(summary['protocol_transport_verified'])
            rows.append({'type': 'system', 'subtype': 'hook_response', 'hook_event': 'SessionStart',
                         'exit_code': 0, 'stdout': (run.ROOT/'CLAUDE.md').read_text()})
            (pack/'data').write_text('changed')
            summary = run.summarize(rows, 'pack', pack, payload, 1, 0)
            self.assertTrue(summary['protocol_transport_verified'])
            self.assertFalse(summary['pack_unchanged'])


@unittest.skipUnless(os.environ.get('WORKFLOW_ISOLATION_TEST') == '1',
                     'opt-in Linux user namespaces and local runtime required')
class IsolationTests(unittest.TestCase):
    def test_host_tmp_and_mask_hidden_payload_visible(self):
        runtime = Path('/tmp/ros2-skill-validation-venv')
        self.assertTrue(runtime.is_dir())
        with tempfile.TemporaryDirectory(dir='/var/tmp', prefix='workflow-test-') as tmp, \
             tempfile.NamedTemporaryFile(dir='/tmp', prefix='workflow-secret-') as host:
            root = Path(tmp)
            ws, pack, hidden = root/'workspace', root/'pack', root/'hidden'
            for p in (ws, pack, hidden):
                p.mkdir()
            (hidden/'answer').write_text('private fixture solution')
            (pack/'marker').write_text('declared treatment')
            program = ('from pathlib import Path; '
                f'assert not Path({host.name!r}).exists(); '
                f'assert list(Path({str(hidden)!r}).iterdir()) == []; '
                f'assert Path({str(pack/"marker")!r}).read_text() == "declared treatment"; '
                'Path("/tmp/only-in-cell").write_text("private"); print("probe passed")')
            proc = subprocess.run(['python3', str(run.HERE/'isolate.py'), '--workspace', str(ws),
                '--pack', str(pack), '--runtime', str(runtime), '--mask', str(hidden),
                '--', '/usr/bin/python3', '-c', program], capture_output=True, text=True, timeout=90)
            self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
            self.assertIn('probe passed', proc.stdout)
            self.assertFalse(Path('/tmp/only-in-cell').exists())
            self.assertEqual((hidden/'answer').read_text(), 'private fixture solution')


if __name__ == '__main__':
    unittest.main()
