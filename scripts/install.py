#!/usr/bin/env python3
"""Install/update the skills and protocol without replacing CLAUDE.md.

python3 scripts/install.py --project /path/to/robot-workspace
python3 scripts/install.py --user

Only files recorded by this installer are replaced on update. Local edits and
pre-existing files cause a refusal before any installed content is changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'claude-ros2-skills-install.json'
SKILLS = ('ros2-development', 'ros2-troubleshooting', 'ros2-microros')
RETIRED = ('ros2-core', 'ros2-dev', 'ros2-control', 'ros2-moveit',
           'ros2-perception', 'ros2-testing', 'ros2-package', 'gazebo-sim')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payload():
    files = {'rules/ros2-verification.md': (ROOT / 'CLAUDE.md').read_bytes()}
    for name in SKILLS:
        for source in (ROOT / 'skills' / name).rglob('*'):
            if source.is_file() and '__pycache__' not in source.parts and source.suffix != '.pyc':
                files[source.relative_to(ROOT).as_posix()] = source.read_bytes()
    return files


def checked_path(target, relative):
    path = Path(relative)
    allowed = path == Path('rules/ros2-verification.md') or any(
        path.is_relative_to(Path('skills') / skill) for skill in SKILLS)
    if path.is_absolute() or '..' in path.parts or not allowed:
        raise ValueError(f'invalid managed path: {relative}')
    destination = target / path
    for part in (destination, *destination.parents):
        if part.is_symlink():
            raise ValueError(f'refusing symlink destination: {part}')
        if part == target:
            break
    return destination


def install(target):
    if target.is_symlink():
        raise ValueError(f'refusing symlink destination: {target}')
    target = target.resolve()
    legacy = [target/'skills'/name for name in RETIRED if (target/'skills'/name).exists()]
    if legacy:
        print('Retired skill directories remain active; inspect/back up these old copies.')
        print('Nothing is deleted automatically. To remove them after inspection:')
        print(shlex.join(['rm', '-r', '--', *map(str, legacy)]))
    manifest = target / MANIFEST
    if manifest.is_symlink():
        raise ValueError(f'refusing symlink manifest: {manifest}')
    previous = json.loads(manifest.read_text()) if manifest.exists() else {}
    if not isinstance(previous, dict) or any(not isinstance(v, str) for v in previous.values()):
        raise ValueError('invalid installation manifest')
    files = payload()
    for skill in SKILLS:
        directory = target/'skills'/skill
        if directory.exists() and not any(name.startswith(f'skills/{skill}/') for name in previous):
            raise ValueError(f'preserving pre-existing skill directory: {directory}; move it aside first')
    for relative in sorted(set(previous) | set(files)):
        path = checked_path(target, relative)
        if path.exists():
            if not path.is_file() or relative not in previous or digest(path.read_bytes()) != previous[relative]:
                raise ValueError(f'preserving existing or locally edited file: {path}; '
                                 'move it aside before installing')
        elif relative in previous:
            raise ValueError(f'managed file was removed locally: {path}; '
                             'restore it before updating')
    # Stage complete files before replacing managed targets. Keep originals for
    # rollback if any filesystem operation fails during this update.
    target.mkdir(parents=True, exist_ok=True)
    originals = {name: (target/name).read_bytes() for name in previous}
    original_manifest = manifest.read_bytes() if manifest.exists() else None
    with tempfile.TemporaryDirectory(prefix='.ros2-install-', dir=target) as staging:
        stage = Path(staging)
        for relative, data in files.items():
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        new_manifest = stage / MANIFEST
        new_manifest.write_text(json.dumps({name: digest(data) for name, data in sorted(files.items())}, indent=2)+'\n')
        changed = []
        try:
            for relative in files:
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                (stage/relative).replace(destination)
                changed.append(relative)
            for relative in previous.keys() - files.keys():
                (target/relative).unlink()
                changed.append(relative)
            new_manifest.replace(manifest)
        except OSError:
            for relative in reversed(changed):
                path = target / relative
                if relative in originals:
                    path.write_bytes(originals[relative])
                else:
                    path.unlink(missing_ok=True)
            if original_manifest is not None:
                manifest.write_bytes(original_manifest)
            else:
                manifest.unlink(missing_ok=True)
            raise
    print(f'Installed {len(SKILLS)} skills and rules/ros2-verification.md in {target}')
    print('Existing CLAUDE.md and unrelated skills were preserved. Start a new Claude Code session.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', type=Path, help='existing project directory')
    group.add_argument('--user', action='store_true', help='install for every project of this user')
    args = parser.parse_args()
    if args.project is not None and not args.project.is_dir():
        parser.error('--project must name an existing directory')
    target = (args.project if args.project is not None else Path.home()) / '.claude'
    try:
        install(target)
    except (OSError, ValueError) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
