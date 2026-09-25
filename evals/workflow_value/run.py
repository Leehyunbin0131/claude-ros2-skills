#!/usr/bin/env python3
"""One fresh, frozen, real Opus workflow cell. Private output; never overwrite.

Run with Jazzy sourced and the declared /tmp runtime's bin first on PATH.
`freeze PATH` records source hashes without making a model call.
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'evals/harness'))
import procscope

MODEL = 'claude-opus-5-5'
EFFORT = 'low'
SKILLS = {'ros2-development', 'ros2-troubleshooting', 'ros2-microros'}
ORDER = [('baseline', 0), ('pack', 0), ('pack', 1), ('baseline', 1), ('baseline', 2), ('pack', 2)]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and
            '__pycache__' not in p.parts and p.suffix != '.pyc'}


def freeze_state():
    paths = [ROOT/'CLAUDE.md', ROOT/'LICENSE', ROOT/'scripts/install.py', HERE/'PROTOCOL.md',
             *HERE.glob('*.py'), ROOT/'evals/harness/isolation.py', ROOT/'evals/harness/procscope.py']
    for name in ('skills', 'hooks', '.claude-plugin'):
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths)) if '__pycache__' not in p.parts and p.suffix != '.pyc'}


def pair_matches(current, previous):
    fields = ('seed', 'model', 'effort', 'input_sha256', 'prompt_sha256',
              'freeze_sha256', 'cli_version', 'versions', 'settings')
    return (current['cell'] % 2 == 0 and previous.get('cell') == current['cell']-1 and
            previous.get('condition') != current['condition'] and
            all(current.get(k) is not None and current.get(k) == previous.get(k) for k in fields))


def stop(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=3)


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


def execute(command, cwd, env, log, timeout=300):
    with log.open('w') as output:
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=output,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return 124
        finally:
            stop(proc)


def read_events(path):
    rows = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except ValueError:
            pass
    return rows


def action_records(rows):
    """Paired tools only. Never exports model thinking blocks."""
    results = {}
    for row in rows:
        if row.get('type') != 'user':
            continue
        content = row.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get('type') == 'tool_result':
                result = block.get('content', '')
                if isinstance(result, list):
                    result = '\n'.join(x.get('text', '') for x in result if isinstance(x, dict))
                results[block.get('tool_use_id')] = {'output': result, 'is_error': block.get('is_error', False)}
    actions = []
    for row in rows:
        if row.get('type') != 'assistant':
            continue
        for block in row.get('message', {}).get('content', []):
            if block.get('type') == 'tool_use':
                actions.append({'index': len(actions)+1, 'tool': block.get('name'),
                    'input': block.get('input', {}), **results.get(block.get('id'), {'output': None})})
    return actions


def summarize(rows, condition, pack, payload, wall, rc):
    init = next((r for r in rows if r.get('type') == 'system' and r.get('subtype') == 'init'), {})
    final = next((r for r in reversed(rows) if r.get('type') == 'result'), {})
    names = {str(n).rsplit(':', 1)[-1] for n in init.get('skills', []) if 'ros2-' in str(n)}
    inventory = names == (SKILLS if condition == 'pack' else set())
    inventory &= all(p.get('path') == 'builtin' or (condition == 'pack' and
        p.get('name') == 'claude-ros2-skills' and Path(p.get('path', '')).resolve() == pack)
        for p in init.get('plugins', []))
    hook = condition == 'baseline' or any(r.get('type') == 'system' and
        r.get('subtype') == 'hook_response' and r.get('hook_event') == 'SessionStart' and
        r.get('exit_code') == 0 and r.get('stdout', '').strip() == (ROOT/'CLAUDE.md').read_text().strip()
        for r in rows)
    return {'model': init.get('model'), 'effort': EFFORT, 'skills': init.get('skills'),
        'plugins': init.get('plugins'), 'tools': init.get('tools'), 'inventory_correct': inventory,
        'protocol_transport_verified': hook, 'pack_unchanged': hashes(pack) == payload,
        'is_error': final.get('is_error', True), 'result': final.get('result'),
        'usage': final.get('usage'), 'model_usage': final.get('modelUsage'),
        'num_turns': final.get('num_turns'), 'duration_ms': final.get('duration_ms'),
        'cost_usd_estimate': final.get('total_cost_usd'), 'wall_seconds': wall,
        'returncode': rc, 'timed_out': rc == 124}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cell', type=int, choices=range(1, 7))
    ap.add_argument('cell_root', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--freeze', type=Path, required=True)
    ap.add_argument('--pair-manifest', type=Path,
                    help='required for cells 2, 4, 6: first cell of the pair manifest.json')
    ap.add_argument('--runtime', type=Path, default=Path('/tmp/ros2-skill-validation-venv'))
    ap.add_argument('--mask', action='append', type=Path, default=[])
    args = ap.parse_args()
    if args.cell % 2 == 0 and args.pair_manifest is None:
        ap.error('even cells require --pair-manifest before a model call')
    if json.loads(args.freeze.read_text()) != freeze_state():
        ap.error('frozen source differs; no model call permitted')
    if os.environ.get('ROS_DISTRO') != 'jazzy':
        ap.error('source the Jazzy underlay first')
    if procscope.foreign_ros():
        ap.error('foreign ROS process conflicts with this evaluation')
    for name in ('ROS_DISCOVERY_SERVER', 'FASTDDS_DEFAULT_PROFILES_FILE',
                 'FASTRTPS_DEFAULT_PROFILES_FILE', 'CYCLONEDDS_URI'):
        if os.environ.get(name):
            ap.error(f'unset {name} for the local fixture')
    lock = open(Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))/f'claude-ros2-eval-{os.getuid()}.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        ap.error('another evaluation owns the per-user lock')
    cell, out, runtime = args.cell_root.resolve(), args.output.resolve(), args.runtime.resolve()
    if cell.exists() or out.exists():
        ap.error('new cell and output paths required; attempts are immutable')
    if cell.is_relative_to(out.parent) or cell.parent in (Path.home(), Path('/'), Path('/tmp')):
        ap.error('dedicated cell parent and separate output parent required')
    condition, seed = ORDER[args.cell-1]
    out.mkdir(parents=True, mode=0o700)
    ws, pack = cell/'workspace', cell/'pack'
    from fixture import create
    create(ws, seed=seed)
    pack.mkdir()
    if condition == 'pack':
        for name in ('skills', 'hooks', '.claude-plugin'):
            shutil.copytree(ROOT/name, pack/name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ('CLAUDE.md', 'LICENSE'):
            shutil.copy2(ROOT/name, pack/name)
    payload = hashes(pack)
    tag = procscope.new_tag()
    env = dict(os.environ, EVAL_RUN_TAG=tag, ROS_DOMAIN_ID=str(221+seed),
        ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST', ROS_STATIC_PEERS='',
        CLAUDE_CODE_EFFORT_LEVEL=EFFORT, COLCON_HOME=str(ws/'.colcon'),
        COLCON_DEFAULTS_FILE=str(ws/'colcon-defaults.yaml'), TMPDIR='/tmp')
    (ws/'colcon-defaults.yaml').write_text('{}\n')
    (ws/'.gitignore').write_text('build/\ninstall/\nlog/\n.colcon/\n__pycache__/\n*.pyc\n*.egg-info/\n')
    inputs = hashes(ws)
    for command in (['git', 'init', '-q'], ['git', 'add', '.'],
                    ['git', '-c', 'user.name=Workflow Fixture', '-c', 'user.email=fixture@example.invalid',
                     'commit', '-qm', 'Existing telemetry workspace']):
        subprocess.run(command, cwd=ws, check=True, capture_output=True)
    fixture_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ws, text=True).strip()
    masks = [out.parent, ROOT.parent/'coordination', *args.mask]
    masks += [p for p in cell.parent.iterdir() if p != cell]
    for path in (Path.home()/'.codex', Path.home()/'.claude/projects',
                 Path.home()/'.claude/plans', Path.home()/'.claude/history.jsonl'):
        if path.exists():
            masks.append(path)
    iso = [sys.executable, str(HERE/'isolate.py'), '--workspace', str(ws),
           '--pack', str(pack), '--runtime', str(runtime)]
    for path in masks:
        iso += ['--mask', str(path.resolve())]
    settings = {'autoMemoryEnabled': False, 'syncClaudeAiSkills': False,
                'syncClaudeAiPlugins': False, 'ultracode': False}
    prompt = (ws/'TASK.txt').read_text()
    toolset = 'Read,Glob,Grep,Bash,Write,Edit,Skill,WebFetch'
    cli = ['claude', '-p', prompt, '--model', MODEL, '--effort', EFFORT,
        '--output-format', 'stream-json', '--verbose', '--include-hook-events',
        '--no-session-persistence', '--setting-sources', 'project,local',
        '--settings', json.dumps(settings), '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
        '--permission-mode', 'dontAsk', '--tools', toolset, '--allowedTools', toolset]
    if condition == 'pack':
        cli += ['--plugin-dir', str(pack)]
    meta = {'cell': args.cell, 'condition': condition, 'seed': seed, 'model': MODEL, 'effort': EFFORT,
        'workspace': str(ws), 'payload_sha256': payload, 'input_sha256': inputs,
        'fixture_commit': fixture_commit,
        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'freeze_sha256': hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'cli_version': subprocess.check_output(['claude', '--version'], text=True).strip(),
        'versions': {n: importlib.metadata.version(n) for n in ('pytest', 'setuptools', 'colcon-core', 'rclpy')},
        'settings': settings, 'timeout_seconds': 1800, 'tag': tag, 'domain': env['ROS_DOMAIN_ID']}
    write_json(out/'manifest.json', meta)
    try:
        if args.cell % 2 == 0:
            matched = pair_matches(meta, json.loads(args.pair_manifest.read_text()))
            write_json(out/'pair-identity.json', {'matched': matched,
                'paired_manifest': str(args.pair_manifest.resolve())})
            if not matched:
                raise RuntimeError('paired task/project/settings differ; no model call made')
        if execute(iso+['--check'], ws, env, out/'isolation.log', 90):
            raise RuntimeError('isolation preflight failed; no model call made')
        if execute(['colcon', 'build', '--base-paths', 'src', '--parallel-workers', '2'],
                   ws, env, out/'prebuild.log', 300):
            raise RuntimeError('initial fixture did not build; no model call made')
        # Each tool shell inherits the existing overlay as a normal developer
        # terminal would. Evaluation and grader code stay masked from the model.
        launch = iso+['--', 'bash', '--noprofile', '--norc', '-c',
            'source /opt/ros/jazzy/setup.bash; source "$1/install/setup.bash"; shift; exec "$@"',
            '_', str(ws), *cli]
        started = time.time()
        meta['model_started_at'] = started
        write_json(out/'manifest.json', meta)
        with (out/'private-session.jsonl').open('w') as stdout, (out/'stderr.log').open('w') as stderr:
            proc = subprocess.Popen(launch, cwd=ws, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                rc = proc.wait(timeout=1800)
            except subprocess.TimeoutExpired:
                rc = 124
            finally:
                stop(proc)
        wall = time.time()-started
        leftovers = cleanup(tag)
        rows = read_events(out/'private-session.jsonl')
        summary = summarize(rows, condition, pack, payload, wall, rc)
        summary['leftover_owned_pids'] = leftovers
        write_json(out/'session-summary.json', summary)
        write_json(out/'actions.json', action_records(rows))
        (out/'final.txt').write_text(summary['result'] or '')
        # Include new tests and retain the original comparison even if the
        # model made a local commit. Intent-to-add changes only this cell index.
        subprocess.run(['git', 'add', '-A', '-N', '--', '.'], cwd=ws, check=True, capture_output=True)
        (out/'source.diff').write_text(subprocess.check_output(['git', 'diff', fixture_commit], cwd=ws, text=True))
        (out/'git-status.txt').write_text(subprocess.check_output(['git', 'status', '--short'], cwd=ws, text=True))
        from grade import copy_project
        copy_project(ws, out/'submitted-project')
        valid = (summary['inventory_correct'] and summary['protocol_transport_verified'] and
                 summary['pack_unchanged'] and summary['model'] == MODEL and not leftovers and
                 not (summary['is_error'] and rc != 124))
        write_json(out/'delivery.json', {'valid_before_action_audit': valid, 'timed_out': rc == 124})
        # Separate grader processes cannot see an inherited candidate overlay.
        grade_env = dict(env, EVAL_RUN_TAG=procscope.new_tag())
        try:
            grade_rc = execute([sys.executable, str(HERE/'grade.py'), str(ws), str(out/'grade'),
                               '--seed', str(seed), '--domain', str(225+seed)], ws, grade_env, out/'grade.log', 900)
            write_json(out/'grading-status.json', {'returncode': grade_rc,
                'verdict_present': (out/'grade/verdict.json').is_file()})
        finally:
            cleanup(grade_env['EVAL_RUN_TAG'])
        return 0 if valid and grade_rc == 0 and rc == 0 else 1
    finally:
        meta['leftover_owned_pids'] = cleanup(tag)
        meta['ended_at'] = time.time()
        write_json(out/'manifest.json', meta)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'freeze':
        target = Path(sys.argv[2])
        if target.exists():
            raise SystemExit('freeze destination already exists')
        write_json(target, freeze_state())
    else:
        raise SystemExit(main())
