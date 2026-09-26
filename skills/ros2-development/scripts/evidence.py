#!/usr/bin/env python3
"""Record selected inputs around a caller-run check; inspect without executing it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from datetime import datetime, timezone

VERSION = 1
MAX_BYTES = 16 * 1024 * 1024
ENV_KEYS = (
    'ROS_VERSION', 'ROS_DISTRO', 'ROS_DOMAIN_ID', 'RMW_IMPLEMENTATION',
    'ROS_LOCALHOST_ONLY', 'ROS_AUTOMATIC_DISCOVERY_RANGE', 'ROS_STATIC_PEERS',
    'AMENT_PREFIX_PATH', 'CMAKE_PREFIX_PATH', 'COLCON_PREFIX_PATH', 'PYTHONPATH',
    'CYCLONEDDS_URI', 'FASTRTPS_DEFAULT_PROFILES_FILE', 'FASTDDS_DEFAULT_PROFILES_FILE',
)
ENV_SEMANTICS = ('Values describe only the inherited environment of the evidence process at each snapshot. '
                 'Null means the key was unset there; it does not show whether the caller command '
                 'ran inside or outside ROS, or sourced another setup file.')
LIMITS = [
    'Consistency covers only the listed paths and parent-shell environment values.',
    'Command, outcome and log provenance are caller-declared, not independently verified.',
    'No command is executed or replayed. Exit 0 concerns the record, not test or robot success.',
    'Intermediate changes reverted between snapshots are not detected.',
    'File scans are sequential, not atomic filesystem snapshots; keep watched inputs idle while recording.',
    'Unwatched dependencies, underlay contents, runtime graph, hardware and process cleanup are unobserved.',
    'The .git and __pycache__ directories and .pyc files are excluded.',
    ENV_SEMANTICS,
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def read_bounded(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'expected a regular, non-symlink file: {path}')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f'file exceeds {MAX_BYTES} bytes: {path}')
    return data


def relative_path(value):
    path = Path(value)
    if not isinstance(value, str) or not value or path.is_absolute() or '..' in path.parts:
        raise ValueError(f'expected a workspace-relative path: {value}')
    return path.as_posix()


def snapshot(workspace, watch, allow_missing=False):
    files = {}

    def visit(path):
        relative = path.relative_to(workspace).as_posix()
        info = path.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if path.is_symlink():
            target = path.resolve(strict=True)
            if not target.is_relative_to(workspace) or not target.is_file():
                raise ValueError(f'only symlinks to files inside the workspace are supported: {path}')
            files[relative] = {'kind': 'symlink', 'target': os.readlink(path),
                               'sha256': hash_file(target), 'mode': stat.S_IMODE(target.stat().st_mode)}
        elif stat.S_ISREG(info.st_mode):
            files[relative] = {'kind': 'file', 'sha256': hash_file(path), 'mode': mode}
        elif stat.S_ISDIR(info.st_mode):
            files[relative] = {'kind': 'directory', 'mode': mode}
            for child in sorted(path.iterdir()):
                if child.name not in ('.git', '__pycache__') and child.suffix != '.pyc':
                    visit(child)
        else:
            raise ValueError(f'unsupported input type: {path}')

    for name in watch:
        path = workspace / name
        # Reject a symlink directory in an ancestor as well as at the root.
        for parent in path.parents:
            if parent == workspace:
                break
            if parent.is_symlink():
                raise ValueError(f'symlink directory is not supported: {parent}')
        if not path.exists() and not path.is_symlink():
            if allow_missing:
                continue
            raise ValueError(f'watched input is missing: {path}')
        visit(path)
    return {'files': files, 'environment': {key: os.environ.get(key) for key in ENV_KEYS}}


def hash_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.evidence-', delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def save(directory, record):
    data = (json.dumps(record, indent=2, sort_keys=True) + '\n').encode()
    if len(data) > MAX_BYTES:
        raise ValueError('manifest exceeds size limit; choose a smaller watch scope')
    atomic_write(directory / 'manifest.json', data)


def load(directory):
    record = json.loads(read_bounded(directory / 'manifest.json'))
    if not isinstance(record, dict) or type(record.get('record_version')) is not int or record['record_version'] != VERSION:
        raise ValueError('unsupported or missing record_version')
    if type(record.get('complete')) is not bool:
        raise ValueError('missing completion state')
    for key in ('workspace', 'scope', 'command_declared', 'started_at'):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f'invalid {key}')
    if not Path(record['workspace']).is_absolute():
        raise ValueError('workspace must be absolute')
    watch = record.get('watch')
    if not isinstance(watch, list) or not watch or any(not isinstance(p, str) or relative_path(p) != p for p in watch):
        raise ValueError('invalid watch paths')
    validate_snapshot(record.get('before'), watch)
    if record['complete']:
        if not isinstance(record.get('finished_at'), str) or not record['finished_at']:
            raise ValueError('missing finish timestamp')
        validate_snapshot(record.get('after'), watch)
        result = record.get('result_declared')
        if not isinstance(result, dict) or result.get('outcome') not in ('exited', 'timeout', 'unavailable'):
            raise ValueError('invalid declared outcome')
        code = result.get('exit_code')
        if result['outcome'] == 'exited':
            if type(code) is not int or not 0 <= code <= 255:
                raise ValueError('invalid declared exit code')
        elif code is not None:
            raise ValueError('unexpected declared exit code')
        log_source = result.get('log_source')
        if (not isinstance(log_source, str) and not (log_source is None and result['outcome'] != 'exited')) or not valid_hash(record.get('log_sha256')):
            raise ValueError('invalid declared log')
    return record


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_snapshot(value, watch):
    if not isinstance(value, dict) or not isinstance(value.get('files'), dict):
        raise ValueError('invalid file snapshot')
    env = value.get('environment')
    if not isinstance(env, dict) or set(env) != set(ENV_KEYS) or any(v is not None and not isinstance(v, str) for v in env.values()):
        raise ValueError('invalid environment snapshot')
    for name, entry in value['files'].items():
        relative_path(name)
        if not any(Path(name).is_relative_to(Path(root)) for root in watch):
            raise ValueError('file outside declared watch scope')
        if not isinstance(entry, dict) or entry.get('kind') not in ('file', 'directory', 'symlink'):
            raise ValueError('invalid file metadata')
        if type(entry.get('mode')) is not int or not 0 <= entry['mode'] <= 0o7777:
            raise ValueError('invalid file mode')
        if entry['kind'] != 'directory' and not valid_hash(entry.get('sha256')):
            raise ValueError('invalid input hash')
        if entry['kind'] == 'symlink' and not isinstance(entry.get('target'), str):
            raise ValueError('invalid symlink target')


def differences(old, new, phase):
    changes = []
    for section in ('files', 'environment'):
        for key in sorted(old[section].keys() | new[section].keys()):
            if old[section].get(key) != new[section].get(key):
                changes.append(f'{phase}:{section}:{key}')
    return changes


def report(record, status, changes=(), reasons=()):
    declared = {'command': record.get('command_declared'), **record.get('result_declared', {}),
                'scope': record.get('scope')}
    # Declared outcome precedes consistency so a failing command cannot hide behind exit 0.
    print(json.dumps({'declared': declared, 'record_status': status,
                      'observed': {'watch': record.get('watch', []),
                                   'changes': list(changes), 'reasons': list(reasons),
                                   'environment_provenance': {
                                       'source': 'inherited environment of the evidence process',
                                       'null_meaning': ENV_SEMANTICS,
                                       'command_environment_verified': False,
                                       'keys_present_at_begin': [k for k, v in record.get('before', {}).get('environment', {}).items() if v is not None]}},
                      'limits': LIMITS}, indent=2))
    return {'open': 0, 'consistent': 0, 'changed': 1, 'incomplete': 2}[status]


def inspect(directory, workspace=None):
    record = load(directory)
    if not record['complete']:
        return report(record, 'incomplete', reasons=['record has not been finished'])
    log = read_bounded(directory / 'command.log')
    if digest(log) != record['log_sha256']:
        return report(record, 'incomplete', reasons=['stored log hash differs'])
    root = (workspace or Path(record['workspace'])).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('workspace must be a directory')
    current = snapshot(root, record['watch'], allow_missing=True)
    changes = differences(record['before'], record['after'], 'between-snapshots')
    changes += differences(record['after'], current, 'since-finish')
    if record['result_declared']['outcome'] != 'exited':
        return report(record, 'incomplete', changes, ['caller did not declare a completed command'])
    return report(record, 'changed' if changes else 'consistent', changes)


def begin(args):
    workspace = args.workspace.resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError('workspace must be a directory')
    watch = sorted(set(relative_path(p) for p in (args.watch or ['src'])))
    output = args.output.resolve()
    if args.output.is_symlink() or output.exists():
        raise ValueError('output must be a new directory')
    if any(output.is_relative_to(workspace / p) for p in watch):
        raise ValueError('output must be outside watched inputs')
    before = snapshot(workspace, watch)
    if not args.scope.strip() or not args.command.strip():
        raise ValueError('scope and command must be nonempty')
    record = {'record_version': VERSION, 'complete': False, 'workspace': str(workspace),
              'scope': args.scope, 'watch': watch, 'command_declared': args.command,
              'started_at': now(), 'before': before, 'environment_semantics': ENV_SEMANTICS}
    output.mkdir(parents=True, exist_ok=False)
    # Exclude record folders from package discovery when kept inside a workspace.
    (output / 'COLCON_IGNORE').touch()
    save(output, record)
    return report(record, 'open')


def finish(args):
    directory = args.directory.resolve(strict=True)
    record = load(directory)
    if record['complete']:
        raise ValueError('record already finished; begin a new record')
    if args.exit_code is not None and not 0 <= args.exit_code <= 255:
        raise ValueError('exit code must be in 0..255')
    if args.log is None and args.outcome is None:
        raise ValueError('--log is required for a declared exited command')
    log = read_bounded(args.log) if args.log is not None else b''
    after = snapshot(Path(record['workspace']), record['watch'], allow_missing=True)
    atomic_write(directory / 'command.log', log)
    record.update(complete=True, after=after, finished_at=now(), log_sha256=digest(log),
                  result_declared={'outcome': args.outcome or 'exited',
                                   'exit_code': args.exit_code,
                                   'log_source': str(args.log.resolve()) if args.log is not None else None})
    save(directory, record)
    return inspect(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    start = sub.add_parser('begin', help='snapshot selected inputs before a caller-run check')
    start.add_argument('--workspace', required=True, type=Path)
    start.add_argument('--output', required=True, type=Path)
    start.add_argument('--scope', required=True)
    start.add_argument('--command', required=True, help='display text only; never executed')
    start.add_argument('--watch', action='append', help='workspace-relative path; default: src; repeated options replace default')
    end = sub.add_parser('finish', help='attach caller-declared outcome, log and second snapshot')
    end.add_argument('directory', type=Path)
    outcome = end.add_mutually_exclusive_group(required=True)
    outcome.add_argument('--exit-code', type=int)
    outcome.add_argument('--outcome', choices=('timeout', 'unavailable'))
    end.add_argument('--log', type=Path, help='required with --exit-code; optional for timeout/unavailable')
    check = sub.add_parser('inspect', help='compare a record with current selected inputs; no commands run')
    check.add_argument('directory', type=Path)
    check.add_argument('--workspace', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == 'begin':
            return begin(args)
        if args.action == 'finish':
            return finish(args)
        return inspect(args.directory, args.workspace)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        return report({}, 'incomplete', reasons=[str(error)])


if __name__ == '__main__':
    sys.exit(main())
