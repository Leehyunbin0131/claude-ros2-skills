#!/usr/bin/env python3
"""Workflow cells: existing instruction masks plus a private /tmp.

Preserves OAuth; never copies credentials. This is not a security sandbox.
The only allowed sibling payload is the declared external pack directory.
"""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evals/harness'))
import isolation

INNER = r'''
set -euo pipefail
masks=$1 scratch=$2 work=$3 uid=$4 gid=$5 runtime=$6 mode=$7 sentinel=$8
shift 8
mkdir -p "$scratch/empty" "$scratch/runtime"
# Keep a mount reference to the runtime before hiding the host /tmp.
mount --bind "$runtime" "$scratch/runtime"
mount -o remount,bind,ro "$scratch/runtime"
n=0
while IFS=' ' read -r kind path; do
  [ -n "$kind" ] || continue
  n=$((n+1))
  if [ "$kind" = d ]; then mkdir "$scratch/empty/$n"; else touch "$scratch/empty/$n"; fi
  mount --bind "$scratch/empty/$n" "$path"
done <<< "$masks"
mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs /tmp
mkdir -p "$runtime"
mount --bind "$scratch/runtime" "$runtime"
mount -o remount,bind,ro "$runtime"
cd "$work"
# The nested user namespace cannot unmount parent-namespace masks.
exec unshare --map-user="$uid" --map-group="$gid" -- bash -c '
set -euo pipefail
masks=$1 uid=$2 mode=$3 sentinel=$4 runtime=$5
shift 5
[ "$(id -u)" = "$uid" ]
[ ! -e "$sentinel" ]
while IFS=" " read -r kind path; do
  [ -n "$kind" ] || continue
  if [ "$kind" = d ]; then
    [ -z "$(ls -A "$path")" ]
    if umount "$path" 2>/dev/null || umount -l "$path" 2>/dev/null; then exit 4; fi
  else
    [ ! -s "$path" ]
  fi
done <<< "$masks"
if umount /tmp 2>/dev/null || umount -l /tmp 2>/dev/null; then exit 4; fi
if touch "$runtime/.workflow-write-probe" 2>/dev/null; then exit 4; fi
if [ "$mode" = check ]; then echo "isolation ok: masked paths, private /tmp, read-only runtime, original UID"; exit 0; fi
exec "$@" </dev/null
' _ "$masks" "$uid" "$mode" "$sentinel" "$runtime" "$@"
'''


def mask_plan(workspace, pack, extras):
    home = str(Path.home())
    masks = isolation.plan(repo=str(ROOT), workdir=str(workspace),
        cfg=os.environ.get('CLAUDE_CONFIG_DIR') or str(Path.home()/'.claude'),
        home=home, extra=':'.join(str(p) for p in extras),
        managed=os.environ.get('EVAL_MANAGED_POLICY_DIR', '/etc/claude-code'))
    # The payload is outside the source workspace, but is the one intentional
    # treatment. Keep only its own discovered masks out of the generic plan.
    masks = [(kind, path) for kind, path in masks
             if not Path(path).is_relative_to(pack)
             and not Path(path).is_relative_to('/tmp')]
    for _, path in masks:
        if pack.is_relative_to(path):
            raise ValueError(f'mask would hide the declared payload: {path}')
    return masks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--pack', type=Path, required=True)
    ap.add_argument('--runtime', type=Path, required=True)
    ap.add_argument('--mask', type=Path, action='append', default=[])
    ap.add_argument('command', nargs=argparse.REMAINDER)
    args = ap.parse_args()
    ws, pack, runtime = (p.resolve() for p in (args.workspace, args.pack, args.runtime))
    if not all(p.is_dir() for p in (ws, pack, runtime)):
        ap.error('workspace, pack, runtime must exist')
    if ws.is_relative_to('/tmp') or pack.is_relative_to('/tmp'):
        ap.error('workspace and payload must be outside the private /tmp')
    if runtime.parent != Path('/tmp'):
        ap.error('this runner expects the declared runtime directly under /tmp')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not args.check and not command:
        ap.error('a command is required')
    masks = mask_plan(ws, pack, [p.resolve() for p in args.mask])
    mask_text = '\n'.join(f'{kind} {path}' for kind, path in masks)
    if any('\n' in path for _, path in masks):
        ap.error('newline in a mask path')
    with tempfile.TemporaryDirectory(prefix='workflow-mount-', dir='/var/tmp') as scratch, \
         tempfile.NamedTemporaryFile(prefix='workflow-host-sentinel-', dir='/tmp') as sentinel:
        return subprocess.run(['unshare', '--map-root-user', '--mount', '--',
            'bash', '-c', INNER, '_', mask_text, scratch, str(ws), str(os.getuid()),
            str(os.getgid()), str(runtime), 'check' if args.check else 'run',
            sentinel.name, *command]).returncode


if __name__ == '__main__':
    raise SystemExit(main())
