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
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

SUMMARY = re.compile(r'^Summary: (\d+) tests?, (\d+) errors?, '
                     r'(\d+) failures?, (\d+) skipped\s*$', re.MULTILINE)


def test_cases(directory):
    """Resolve current CTest wrappers to their actual JUnit results.

    ament configures its JUnit paths at build time. They may be outside a fresh
    colcon test-result-base. A current, executed run_test.py wrapper rewrites its
    result; a notrun wrapper must never reuse that older file.
    """
    cases, wrappers, roots = {}, {}, {}
    missing = actual_failure = False

    def load(path):
        path = path.resolve()
        if path not in roots:
            roots[path] = ET.parse(path).getroot()
        return roots[path]

    for tag in directory.glob('**/Testing/TAG'):
        lines = tag.read_text().splitlines()
        if not lines or lines[0] in ('.', '..') or Path(lines[0]).name != lines[0]:
            raise ValueError(f'invalid CTest TAG: {tag}')
        root = load(tag.parent / lines[0] / 'Test.xml')
        for case in root.findall('Testing/Test'):
            identity = case.findtext('Name')
            if not identity:
                raise ValueError('CTest result has no test name')
            state = {'passed': 'passed', 'failed': 'failed', 'notrun': 'skipped'}.get(
                case.get('Status'), 'invalid')
            actual_failure |= state == 'failed'
            # Only the installed ament wrapper contract gives us a current
            # inner report. Never execute the recorded command.
            args = shlex.split(case.findtext('FullCommandLine') or '')
            inner = None
            for i, arg in enumerate(args[:-1]):
                if Path(arg).name == 'run_test.py' and 'ament_cmake_test' in Path(arg).parts:
                    inner = Path(args[i+1])
                    if not inner.is_absolute():
                        raise ValueError(f'ament result path is not absolute: {inner}')
                    break
            if inner is None or state == 'skipped':
                cases.setdefault(identity, []).append(state)
                continue
            if not inner.is_file():
                missing = True
                cases.setdefault(identity, []).append('missing result')
                continue
            wrappers.setdefault(inner.resolve(), []).append(identity)
            load(inner)

    for path in sorted(directory.rglob('*.xml')):
        # CTest TAG selected the current report above. Old CTest runs are not
        # evidence, even when the caller accidentally supplies a reused base.
        if path.name == 'Test.xml' and 'Testing' in path.parts:
            continue
        load(path)
    for path, root in roots.items():
        if root.tag not in ('testsuite', 'testsuites'):
            if path in wrappers:
                raise ValueError(f'ament wrapper did not produce JUnit: {path}')
            continue
        inner_states = []
        for case in root.iter('testcase'):
            name = case.get('name', '')
            identity = '.'.join(x for x in (case.get('classname', ''), name) if x)
            failed = case.find('failure') is not None or case.find('error') is not None
            # colcon's Python placeholder has no process-level verdict. Ament
            # wrapper failures are recorded by CTest, including crashes/hangs.
            synthetic = name == 'pytest.missing_result' and failed and path not in wrappers
            if synthetic:
                missing = True
                state = 'missing result'
            elif failed:
                actual_failure = True
                state = 'failed'
            elif case.find('skipped') is not None or case.get('status') == 'notrun':
                state = 'skipped'
            else:
                state = 'passed'
            inner_states.append(state)
            if identity:
                cases.setdefault(identity, []).append(state)
        for wrapper in wrappers.get(path, []):
            cases.setdefault(wrapper, []).extend(inner_states or ['missing result'])
            missing |= not inner_states
    return cases, missing, actual_failure


def required_verdict(cases, selector):
    """Match a full ID or dot-delimited suffix, optionally a parameter group."""
    def matches(identity):
        if '[' not in selector:
            identity = identity.split('[', 1)[0]
        return identity == selector or identity.endswith('.' + selector)
    states = [state for identity, values in cases.items() if matches(identity) for state in values]
    if 'failed' in states:
        return 1, f'required test {selector} failed'
    if 'passed' not in states:
        return 2, f'required test {selector} did not execute successfully'
    return 0, f'required test {selector} executed'


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


def check(base, packages, *, required=(), run=subprocess.run):
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
            cases, missing, actual_failure = test_cases(directory)
            if actual_failure:
                code, detail = 1, 'recorded test/process failure; missing ament results can mean crash, timeout or runner failure; inspect the test log'
            elif missing:
                code, detail = 2, 'test process produced no results (runner failure or crash); inspect the package test log'
            if code == 0 and cases and not any('passed' in states for states in cases.values()):
                code, detail = 2, 'no executed passing test cases; wrappers do not replace skipped inner tests'
            elif code == 0:
                detail = 'reports contain executed, passing test cases'
            for pkg, selector in required:
                if pkg != package:
                    continue
                required_code, required_detail = required_verdict(cases, selector)
                if code != 1 and required_code:
                    code, detail = required_code, required_detail
            if cases:
                print(f'Tests observed in {package}:')
                for identity, states in sorted(cases.items()):
                    print(f'  {package}::{identity}: {", ".join(states)}')
            elif required or code == 0:
                print(f'{package}: no individual JUnit/CTest test IDs available')
            if code:
                print(result.stdout.rstrip())
                if result.stderr:
                    print(result.stderr.rstrip(), file=sys.stderr)
        except (OSError, subprocess.TimeoutExpired, ET.ParseError, ValueError) as error:
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
    ap.add_argument('--require-test', action='append', default=[], metavar='PACKAGE::ID',
                    help='require an executed test ID or suffix; omit [parameters] to match the group')
    args = ap.parse_args()
    if not args.result_base.is_dir():
        ap.error('result_base must be an existing directory')
    required = []
    for value in args.require_test:
        package, separator, identity = value.partition('::')
        if not separator or not identity or package not in args.packages:
            ap.error('--require-test must be PACKAGE::ID with PACKAGE also in --packages')
        required.append((package, identity))
    try:
        return check(args.result_base.resolve(), list(dict.fromkeys(args.packages)), required=required)
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
