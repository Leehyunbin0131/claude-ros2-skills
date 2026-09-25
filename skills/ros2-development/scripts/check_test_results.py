#!/usr/bin/env python3
"""Check that each named package has executed, passing colcon test results.

Read-only. Use a fresh --test-result-base when running colcon test; this script
cannot infer whether arbitrary existing files came from the latest source.
Exit 0 PASS, 1 FAIL, 2 INCONCLUSIVE (including empty/all-skipped reports).
"""
import argparse
from pathlib import Path
import os
import re
import subprocess
import sys

SUMMARY = re.compile(r'^Summary: (\d+) tests?, (\d+) errors?, '
                     r'(\d+) failures?, (\d+) skipped\s*$', re.MULTILINE)


def verdict(returncode, stdout, stderr=''):
    if returncode not in (0, 1) or stderr.strip():
        return 2, 'test-result command did not complete cleanly; inspect its diagnostics'
    matches = SUMMARY.findall(stdout)
    if len(matches) != 1:
        return 2, 'no unambiguous colcon test summary'
    tests, errors, failures, skipped = map(int, matches[0])
    if errors or failures:
        return 1, f'{errors} errors, {failures} failures'
    if returncode:
        return 2, 'command failed without a test failure summary'
    if tests < skipped:
        return 2, 'invalid test counts'
    if tests - skipped == 0:
        return 2, f'no executed tests ({tests} total, {skipped} skipped)'
    return 0, f'{tests - skipped} executed tests passed ({skipped} skipped)'


def check(base, packages, *, run=subprocess.run):
    codes = []
    for package in packages:
        directory = base / package
        if not directory.is_dir():
            print(f'INCONCLUSIVE {package}: no results directory: {directory}')
            codes.append(2)
            continue
        try:
            result = run(['colcon', 'test-result', '--test-result-base', str(directory),
                          '--all', '--verbose'], capture_output=True, text=True,
                         timeout=30, env={**os.environ, 'LC_ALL': 'C', 'LANG': 'C'})
            code, detail = verdict(result.returncode, result.stdout, result.stderr)
            if code:
                print(result.stdout.rstrip())
                if result.stderr:
                    print(result.stderr.rstrip(), file=sys.stderr)
        except (OSError, subprocess.TimeoutExpired) as error:
            code, detail = 2, str(error)
        print(f'{("PASS", "FAIL", "INCONCLUSIVE")[code]} {package}: {detail}')
        codes.append(code)
    print(f'Results: {base}')
    return 1 if 1 in codes else 2 if 2 in codes else 0


def package_name(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', value):
        raise argparse.ArgumentTypeError('expected a package name, not a path')
    return value


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('result_base', type=Path, help='fresh colcon --test-result-base directory')
    ap.add_argument('--packages', nargs='+', required=True, type=package_name)
    args = ap.parse_args()
    if not args.result_base.is_dir():
        ap.error('result_base must be an existing directory')
    try:
        return check(args.result_base.resolve(), list(dict.fromkeys(args.packages)))
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
