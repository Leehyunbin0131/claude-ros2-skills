#!/usr/bin/env python3
"""Optional local Codex discovery integration; no model calls or user configuration edits."""
import importlib.util
import json
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('installer', ROOT/'scripts/install.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


@unittest.skipUnless(shutil.which('codex'), 'requires the optional Codex CLI')
class CodexDiscovery(unittest.TestCase):
    def test_native_discovery_from_project_and_nested_directory(self):
        with tempfile.TemporaryDirectory(prefix='ros2 codex discovery ') as tmp:
            project = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(project)], check=True, timeout=10)
            nested = project/'src'/'robot'
            nested.mkdir(parents=True)
            subprocess.run([sys.executable, str(ROOT/'scripts/install.py'), '--agent', 'codex',
                            '--project', str(project)], check=True, capture_output=True, timeout=10)
            with tempfile.TemporaryFile(mode='w+') as errors:
                process = subprocess.Popen(['codex', 'app-server', '--stdio'], cwd=project,
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=errors, text=True, bufsize=1)
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)

                def send(message):
                    process.stdin.write(json.dumps(message)+'\n')
                    process.stdin.flush()

                def receive(request_id):
                    deadline = time.monotonic()+30
                    while time.monotonic() < deadline:
                        if not selector.select(max(0, deadline-time.monotonic())):
                            break
                        line = process.stdout.readline()
                        if not line:
                            break
                        response = json.loads(line)
                        if response.get('id') == request_id:
                            self.assertNotIn('error', response, response)
                            return response['result']
                    errors.seek(0)
                    self.fail('No Codex discovery response: '+errors.read()[-2000:])

                try:
                    send({'id': 1, 'method': 'initialize', 'params': {
                        'clientInfo': {'name': 'ros2-discovery-test', 'version': '0.1.2'}}})
                    receive(1)
                    send({'method': 'initialized'})
                    send({'id': 2, 'method': 'skills/list', 'params': {
                        'cwds': [str(project), str(nested)], 'forceReload': True}})
                    result = receive(2)
                    self.assertEqual(len(result['data']), 2)
                    for entry in result['data']:
                        skills = [skill for skill in entry['skills']
                                  if Path(skill['path']).is_relative_to(project)]
                        self.assertEqual({skill['name'] for skill in skills}, set(installer.SKILLS))
                        self.assertEqual(len(skills), 3)
                        for skill in skills:
                            self.assertTrue(skill['enabled'])
                            self.assertEqual(skill['scope'], 'repo')
                            self.assertEqual(Path(skill['path']),
                                             project/'.agents/skills'/skill['name']/'SKILL.md')
                        self.assertFalse([error for error in entry['errors']
                                          if Path(error['path']).is_relative_to(project)])
                finally:
                    selector.close()
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    process.stdin.close()
                    process.stdout.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
