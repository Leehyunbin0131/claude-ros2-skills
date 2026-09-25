#!/usr/bin/env python3
"""Run one declared release-acceptance session. Makes a real Claude Code call.

Requires a sourced Jazzy environment, working Claude subscription, and colcon.
Never overwrites a cell. All model/fixture processes use separate ownership tags.
Raw private session logs may include model reasoning; do not publish them.
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

from fixtures import create, case_spec
from grade import command, stop

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT/'evals/harness'
sys.path.insert(0, str(HARNESS))
import procscope

SKILL_NAMES = {'ros2-development', 'ros2-troubleshooting', 'ros2-microros'}
SCRIPT_NAME = re.compile(r'check_(test_results|qos_compat|tf_tree|imu_gravity|odom_direction)\.py')


def freeze_state():
    paths = [ROOT/'CLAUDE.md', ROOT/'LICENSE', ROOT/'scripts/install.py',
             ROOT/'evals/development/PROTOCOL.md',
             *(ROOT/'evals/development').glob('*.py'),
             *(HARNESS/name for name in ('isolate_cell.sh', 'isolation.py', 'procscope.py'))]
    for directory in ('skills', 'hooks', '.claude-plugin'):
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths)) if '__pycache__' not in p.parts and p.suffix != '.pyc'}


def reference_masks(workspace, roots=None):
    """Hide known fixture/control copies as well as repository copies.

    This bounded scan complements, not replaces, explicit masks for private
    material. It is not a general filesystem security boundary.
    """
    found = []
    package_names = {case_spec(seed)[key] for seed in range(10)
                     for key in ('scan_package', 'tests_package')}
    for base in roots or (Path('/tmp'), Path.home()):
        for directory, children, _ in os.walk(base):
            path = Path(directory)
            if path == workspace or path.is_relative_to(workspace):
                children[:] = []
                continue
            if not workspace.is_relative_to(path) and (path.name in package_names or
                    path.name.startswith(('ros2-acceptance-', 'ros2-oracle-'))):
                found.append(path)
                children[:] = []
                continue
            if len(path.relative_to(base).parts) >= 6:
                children[:] = []
            else:
                children[:] = [name for name in children if name not in
                    ('.git', '.cache', 'node_modules', '__pycache__', '.codex', '.claude')
                    and not (path/name).is_symlink()]
    return found


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file() and
            '__pycache__' not in p.parts and p.suffix != '.pyc'}


def export_plugin(destination):
    destination.mkdir()
    for name in ('skills', 'hooks', '.claude-plugin'):
        shutil.copytree(ROOT/name, destination/name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('CLAUDE.md', 'LICENSE'):
        shutil.copy2(ROOT/name, destination/name)
    return hashes(destination)


def cleanup(tag):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        pids = procscope.select(tag, [])
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        if not pids:
            return []
        time.sleep(.5)
    return procscope.select(tag, [])


def events(path):
    result = []
    for line in path.read_text().splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                result.append(value)
        except ValueError:
            continue
    return result


def summarize(rows):
    init = next((r for r in rows if r.get('type') == 'system' and r.get('subtype') == 'init'), {})
    final = next((r for r in reversed(rows) if r.get('type') == 'result'), {})
    routing = []
    results = {}
    for row in rows:
        if row.get('type') == 'user':
            for block in row.get('message', {}).get('content', []):
                if block.get('type') == 'tool_result':
                    content = block.get('content', '')
                    if isinstance(content, list):
                        content = '\n'.join(item.get('text', '') for item in content if isinstance(item, dict))
                    results[block.get('tool_use_id')] = str(content)
    for row in rows:
        if row.get('type') != 'assistant':
            continue
        for block in row.get('message', {}).get('content', []):
            if block.get('type') != 'tool_use':
                continue
            payload = block.get('input', {})
            if block.get('name') == 'Skill' or SCRIPT_NAME.search(str(payload)) or (
                    'ros2-' in str(payload) and 'SKILL.md' in str(payload)):
                routing.append({'tool': block.get('name'), 'input': payload,
                                'result_excerpt': results.get(block.get('id'), '')[:6000]})
    return {'model': init.get('model'), 'skills': init.get('skills'), 'plugins': init.get('plugins'),
            'tools': init.get('tools'), 'routing': routing,
            'is_error': final.get('is_error', True), 'result': final.get('result'),
            'usage': final.get('usage'), 'num_turns': final.get('num_turns'),
            'duration_ms': final.get('duration_ms'), 'cost_usd': final.get('total_cost_usd')}


def delivery(rows, summary, condition, workspace):
    names = {str(name).rsplit(':', 1)[-1] for name in (summary.get('skills') or []) if 'ros2-' in str(name)}
    inventory = names == (set() if condition == 'baseline' else SKILL_NAMES)
    plugins = summary.get('plugins') or []
    inventory &= all(p.get('path') == 'builtin' or
        (condition == 'plugin' and p.get('name') == 'claude-ros2-skills' and
         Path(p.get('path', '')).resolve() == (workspace/'.acceptance-plugin').resolve()) for p in plugins)
    protocol = ROOT.joinpath('CLAUDE.md').read_text()
    if condition == 'plugin':
        protocol_present = any(row.get('type') == 'system' and row.get('subtype') == 'hook_response'
            and row.get('hook_event') == 'SessionStart' and row.get('exit_code') == 0 and
            row.get('stdout', '').strip() == protocol.strip() for row in rows)
    elif condition == 'manual':
        rule = workspace/'.claude/rules/ros2-verification.md'
        protocol_present = rule.is_file() and rule.read_text() == protocol
    else:
        protocol_present = True
    script_executed = any(item['tool'] == 'Bash' and 'check_test_results.py' in str(item['input'])
        and 'INCONCLUSIVE drive_math' in item['result_excerpt'] and 'Results:' in item['result_excerpt']
        and 'No such file' not in item['result_excerpt'] for item in summary['routing'])
    return {'inventory_correct': inventory, 'protocol_transport_verified': protocol_present,
            'smoke_script_executed': script_executed}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('task', choices=('scan', 'tests', 'imu', 'smoke'))
    ap.add_argument('condition', choices=('baseline', 'plugin', 'manual'))
    ap.add_argument('workspace', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--timeout', type=int, default=1800)
    ap.add_argument('--freeze', type=Path, help='required content-hash manifest for acceptance cells')
    ap.add_argument('--mask', action='append', default=[], type=Path)
    args = ap.parse_args()
    if args.task != 'smoke' and args.freeze is None:
        ap.error('acceptance requires --freeze; write it with run_acceptance.py freeze PATH')
    if args.freeze is not None:
        try:
            unchanged = json.loads(args.freeze.read_text()) == freeze_state()
        except (OSError, ValueError) as error:
            ap.error(f'cannot read freeze manifest: {error}')
        if not unchanged:
            ap.error('frozen source changed; refusing a model call')
    case_spec(args.seed)
    if os.environ.get('ROS_DISTRO') != 'jazzy':
        ap.error('source /opt/ros/jazzy/setup.bash first')
    for name in ('claude', 'colcon'):
        if not shutil.which(name):
            ap.error(f'{name} is required')
    for variable in ('ROS_DISCOVERY_SERVER', 'FASTDDS_DEFAULT_PROFILES_FILE',
                     'FASTRTPS_DEFAULT_PROFILES_FILE', 'CYCLONEDDS_URI'):
        if os.environ.get(variable):
            ap.error(f'unset {variable} for the isolated local fixture')
    if procscope.foreign_ros():
        ap.error('a foreign ROS process is running; stop the fixture conflict before evaluating')
    args.output = args.output.resolve()
    args.workspace = args.workspace.resolve()
    if args.workspace.parent in (Path('/tmp'), Path.home(), Path('/')):
        ap.error('use a dedicated workspace parent, separate from the output parent')
    if args.workspace.is_relative_to(args.output.parent):
        ap.error('output parent would hide workspace; use separate roots')
    lock = open(Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))/f'claude-ros2-eval-{os.getuid()}.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        ap.error('another evaluation holds the per-user lock; cells run sequentially')
    if args.output.exists() or args.workspace.exists():
        ap.error('workspace and output must be new paths; prior cells are immutable')
    args.output.mkdir(parents=True)
    os.chmod(args.output, 0o700)
    if args.task == 'smoke':
        args.workspace.mkdir(parents=True)
        report = args.workspace/'fresh-results/drive_math/pytest.xml'
        report.parent.mkdir(parents=True)
        report.write_text('<testsuite tests="2" errors="0" failures="0" skipped="1"><testcase classname="test_style" name="test_lint"/><testcase classname="test_math" name="test_ratio"><skipped/></testcase></testsuite>')
        prompt = ('This existing ROS 2 Jazzy simulation workspace contains fresh colcon reports in '
                  'fresh-results for package drive_math. The pure calculation test test_ratio '
                  'should cover the changed behavior. Check whether that test actually executed; '
                  'do not treat passing style checks as evidence for it. There is no robot or '
                  'running ROS graph, and no source change is needed. Save evidence.json with '
                  'an executed boolean and the command/observation supporting it.')
        (args.workspace/'TASK.txt').write_text(prompt)
    else:
        create(args.workspace, args.task, seed=args.seed)
        prompt = (args.workspace/'TASK.txt').read_text()
    if args.condition == 'plugin':
        payload = export_plugin(args.workspace/'.acceptance-plugin')
    elif args.condition == 'manual':
        install = subprocess.run([sys.executable, str(ROOT/'scripts/install.py'), '--project', str(args.workspace)],
                                 capture_output=True, text=True)
        (args.output/'install.log').write_text(install.stdout+install.stderr)
        if install.returncode:
            raise RuntimeError('manual installer failed')
        payload = hashes(args.workspace/'.claude')
    else:
        payload = {}
    (args.workspace/'colcon-defaults.yaml').write_text('{}\n')
    model_tag, scene_tag = procscope.new_tag(), procscope.new_tag()
    env = dict(os.environ, EVAL_RUN_TAG=model_tag, ROS_DOMAIN_ID=str(211+args.seed),
               ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST', ROS_STATIC_PEERS='',
               CLAUDE_CODE_EFFORT_LEVEL='high', COLCON_HOME=str(args.workspace/'.colcon'),
               COLCON_DEFAULTS_FILE=str(args.workspace/'colcon-defaults.yaml'))
    masks = [args.output, *args.mask]
    masks.append(args.output.parent)
    coordination = ROOT.parent/'coordination'
    if coordination.exists():
        masks.append(coordination)
    masks.extend(path for path in args.workspace.parent.iterdir() if path != args.workspace)
    masks.extend(reference_masks(args.workspace))
    for path in (Path.home()/'.codex', Path.home()/'.claude/projects',
                 Path.home()/'.claude/plans', Path.home()/'.claude/history.jsonl'):
        if path.exists():
            masks.append(path)
    env['EVAL_MASK_PATHS'] = ':'.join(str(p.resolve()) for p in masks)
    settings = {'autoMemoryEnabled': False, 'syncClaudeAiSkills': False,
                'syncClaudeAiPlugins': False, 'ultracode': False}
    tools = 'Read,Glob,Grep,Bash,Write,Edit,Skill,WebFetch'
    cli = ['claude', '-p', prompt, '--model', 'claude-opus-5-5', '--effort', 'high',
           '--output-format', 'stream-json', '--verbose', '--include-hook-events',
           '--no-session-persistence', '--setting-sources', 'project,local',
           '--settings', json.dumps(settings), '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
           '--permission-mode', 'dontAsk', '--tools', tools, '--allowedTools', tools]
    if args.condition == 'plugin':
        cli += ['--plugin-dir', str(args.workspace/'.acceptance-plugin')]
    meta = {'task': args.task, 'condition': args.condition, 'seed': args.seed,
            'model': 'claude-opus-5-5', 'effort': 'high', 'settings': settings,
            'payload_sha256': payload, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
            'fixture_sha256': hashes(ROOT/'evals/development'),
            'cli_version': subprocess.check_output(['claude', '--version'], text=True).strip(),
            'versions': {name: importlib.metadata.version(name) for name in
                         ('pytest', 'setuptools', 'colcon-core', 'rclpy')},
            'domain': env['ROS_DOMAIN_ID'], 'tags': [model_tag, scene_tag],
            'workspace': str(args.workspace), 'started_at': time.time(), 'timeout': args.timeout}
    meta['source_head'] = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    meta['freeze_sha256'] = hashlib.sha256(args.freeze.read_bytes()).hexdigest() if args.freeze else None
    (args.output/'manifest.json').write_text(json.dumps(meta, indent=2))
    scenario = None
    scene_log = None
    try:
        # Prove the mount masks before spending a model call.
        check = subprocess.run(['bash', str(HARNESS/'isolate_cell.sh'), '--check', str(args.workspace)],
                               env=env, capture_output=True, text=True, timeout=60)
        (args.output/'isolation.log').write_text(check.stdout+check.stderr)
        if check.returncode:
            raise RuntimeError('isolation preflight failed')
        if args.task == 'imu':
            scene_env = dict(env, EVAL_RUN_TAG=scene_tag)
            state = args.output/'scene.json'
            scene_log = (args.output/'scene.log').open('w')
            scenario = subprocess.Popen([sys.executable, str(ROOT/'evals/development/imu_scene.py'),
                'serve', '--state', str(state), '--seed', str(args.seed)], env=scene_env,
                stdout=scene_log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic()+12
            while not state.is_file() and scenario.poll() is None and time.monotonic() < deadline:
                time.sleep(.1)
            if not state.is_file():
                raise RuntimeError('IMU fixture did not become ready')
            ready = subprocess.run([sys.executable, str(ROOT/'evals/development/imu_scene.py'),
                'observe', '--seed', str(args.seed)], env=scene_env, capture_output=True, text=True, timeout=15)
            (args.output/'readiness.json').write_text(ready.stdout)
            if ready.returncode or [v['status'] for v in json.loads(ready.stdout).values()] != list(case_spec(args.seed)['imu_roles']):
                raise RuntimeError('IMU observation preflight failed')
        with (args.output/'private-session.jsonl').open('w') as out, (args.output/'stderr.log').open('w') as err:
            proc = subprocess.Popen(['bash', str(HARNESS/'isolate_cell.sh'), str(args.workspace), *cli],
                env=env, stdout=out, stderr=err, start_new_session=True)
            try:
                model_rc = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                model_rc = 124
            finally:
                stop(proc)
                cleanup(model_tag)
        rows = events(args.output/'private-session.jsonl')
        summary = summarize(rows)
        summary.update({'returncode': model_rc, 'wall_seconds': time.time()-meta['started_at']})
        timed_out = model_rc == 124
        summary['timed_out'] = timed_out
        payload_root = args.workspace/('.acceptance-plugin' if args.condition == 'plugin' else '.claude')
        current_payload = hashes(payload_root) if args.condition != 'baseline' else {}
        summary['pack_unchanged'] = all(current_payload.get(name) == digest for name, digest in payload.items())
        summary['extra_config_files'] = sorted(current_payload.keys()-payload.keys())
        summary['delivery'] = delivery(rows, summary, args.condition, args.workspace)
        (args.output/'session-summary.json').write_text(json.dumps(summary, indent=2))
        if (model_rc or summary['is_error']) and not timed_out:
            (args.output/'verdict.json').write_text(json.dumps({'accepted': False, 'gradable': False,
                'reason': 'model session did not complete', 'returncode': model_rc}, indent=2))
            return 2
        if not timed_out and not (summary['delivery']['inventory_correct'] and summary['delivery']['protocol_transport_verified']):
            (args.output/'verdict.json').write_text(json.dumps({'accepted': False, 'gradable': False,
                'reason': 'delivery or inventory check failed', 'delivery': summary['delivery']}, indent=2))
            return 2
        if not summary['pack_unchanged']:
            (args.output/'verdict.json').write_text(json.dumps({'accepted': False, 'gradable': True,
                'reason': 'model changed the supplied pack'}, indent=2))
            return 1
        if args.task == 'imu':
            if scenario.poll() is not None:
                raise RuntimeError('fixture process stopped during model session')
            grade_cmd = [sys.executable, str(ROOT/'evals/development/imu_scene.py'), 'grade',
                         '--workspace', str(args.workspace), '--state', str(state), '--pid', str(scenario.pid),
                         '--seed', str(args.seed)]
            graded = subprocess.run(grade_cmd, env=scene_env, capture_output=True, text=True, timeout=20)
            (args.output/'grade.log').write_text(graded.stderr)
            if graded.returncode not in (0, 1):
                raise RuntimeError('IMU grader did not complete')
            verdict = json.loads(graded.stdout)
            verdict.update({'timed_out': timed_out, 'accepted': verdict['accepted'] and not timed_out})
            (args.output/'verdict.json').write_text(json.dumps(verdict, indent=2))
            return 1 if timed_out else graded.returncode
        if args.task == 'smoke':
            try:
                evidence = json.loads((args.workspace/'evidence.json').read_text())
            except (OSError, ValueError):
                evidence = {}
            result = {'accepted': evidence.get('executed') is False and
                      summary['delivery']['smoke_script_executed'] and not timed_out,
                      'answer': evidence, 'delivery': summary['delivery'], 'timed_out': timed_out}
            (args.output/'verdict.json').write_text(json.dumps(result, indent=2))
            return 0 if result['accepted'] else 1
        grade_env = dict(env, EVAL_RUN_TAG=procscope.new_tag())
        try:
            graded = subprocess.run([sys.executable, str(ROOT/'evals/development/grade.py'), args.task,
                str(args.workspace), str(args.output/'grade'), '--seed', str(args.seed)], env=grade_env,
                capture_output=True, text=True, timeout=300)
            (args.output/'grade.log').write_text(graded.stdout+graded.stderr)
            if not (args.output/'grade/verdict.json').is_file():
                raise RuntimeError('package grader did not produce evidence')
            verdict = json.loads((args.output/'grade/verdict.json').read_text())
            verdict.update({'timed_out': timed_out, 'accepted': verdict['accepted'] and not timed_out})
            (args.output/'verdict.json').write_text(json.dumps(verdict, indent=2))
            return 1 if timed_out else graded.returncode
        finally:
            cleanup(grade_env['EVAL_RUN_TAG'])
    finally:
        cleanup(model_tag)
        if scenario is not None:
            stop(scenario)
        cleanup(scene_tag)
        if scene_log:
            scene_log.close()
        meta['ended_at'] = time.time()
        (args.output/'manifest.json').write_text(json.dumps(meta, indent=2))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'freeze':
        Path(sys.argv[2]).write_text(json.dumps(freeze_state(), indent=2, sort_keys=True)+'\n')
    else:
        raise SystemExit(main())
