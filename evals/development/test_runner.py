#!/usr/bin/env python3
"""Verify isolation/delivery/freeze decisions without invoking a model."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

import run_acceptance as runner


class RunnerChecks(unittest.TestCase):
    def test_script_execution_pairs_tool_result_and_variable_path(self):
        rows = [{'type': 'system', 'subtype': 'init', 'skills': sorted(runner.SKILL_NAMES), 'plugins': []},
                {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Bash',
                 'id': 'call1', 'input': {'command': 'python3 ${CLAUDE_SKILL_DIR}/scripts/check_test_results.py fresh-results --packages drive_math'}}]}},
                {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'call1',
                 'content': 'INCONCLUSIVE drive_math: required test skipped\nResults: fresh-results'}]}},
                {'type': 'result', 'is_error': False, 'result': 'done'}]
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            rule = ws/'.claude/rules/ros2-verification.md'
            rule.parent.mkdir(parents=True)
            rule.write_text((runner.ROOT/'CLAUDE.md').read_text())
            evidence = runner.delivery(rows, runner.summarize(rows), 'manual', ws)
            self.assertTrue(all(evidence.values()), evidence)
            rows[2]['message']['content'][0]['content'] = 'python3: No such file'
            self.assertFalse(runner.delivery(rows, runner.summarize(rows), 'manual', ws)['smoke_script_executed'])

    def test_inventory_and_protocol_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            summary = {'skills': ['claude-ros2-skills:'+name for name in runner.SKILL_NAMES],
                       'plugins': [{'name': 'claude-ros2-skills', 'path': str(ws/'.acceptance-plugin')}], 'routing': []}
            hook = {'type': 'system', 'subtype': 'hook_response', 'hook_event': 'SessionStart',
                    'exit_code': 0, 'stdout': (runner.ROOT/'CLAUDE.md').read_text()}
            self.assertTrue(runner.delivery([hook], summary, 'plugin', ws)['protocol_transport_verified'])
            self.assertFalse(runner.delivery([], summary, 'plugin', ws)['protocol_transport_verified'])
            self.assertFalse(runner.delivery([hook], summary, 'baseline', ws)['inventory_correct'])
            summary['plugins'].append({'name': 'unrelated', 'path': '/unrelated'})
            self.assertFalse(runner.delivery([hook], summary, 'plugin', ws)['inventory_correct'])

    def test_reference_masks_leave_current_workspace_and_runtime_visible(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ws = root/'ros2-acceptance-workspaces/current'
            ws.mkdir(parents=True)
            reference = root/'ros2-acceptance-reference'
            reference.mkdir()
            runtime = root/'ros2-skill-validation-venv'
            runtime.mkdir()
            unknown = root/'other/src/drive_limits_v1'
            unknown.mkdir(parents=True)
            found = runner.reference_masks(ws, roots=[root])
            self.assertIn(reference, found)
            self.assertIn(unknown, found)
            self.assertNotIn(runtime, found)
            self.assertFalse(any(ws.is_relative_to(path) for path in found))

    def test_drift_aborts_before_dependencies_or_model_call(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            freeze = root/'freeze.json'
            freeze.write_text('{}')
            result = subprocess.run([sys.executable, str(Path(runner.__file__)), 'tests', 'baseline',
                str(root/'workspaces/cell'), str(root/'outputs/cell'), '--freeze', str(freeze)],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn('frozen source changed', result.stderr)
            self.assertFalse((root/'workspaces').exists())
            self.assertFalse((root/'outputs').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
