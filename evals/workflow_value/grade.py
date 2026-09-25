#!/usr/bin/env python3
"""Independent grader for the interface-migration workflow study.

Never imports or runs the pack. Copies the submitted project (excluding VCS,
colcon build/install/log and caches) into a new directory, builds it in a
shell with only /opt/ros/jazzy sourced, and records per-dimension evidence:

1. clean_build - every package builds from the copied project.
2. interface - the installed message has the new float64 field and ``valid``,
   and no longer has the old field.
3. tests - the candidate's own test run completes, with at least one executed
   passing case and no failures or errors in each consumer.
4. runtime - both installed ``monitor`` executables publish the specified
   values for valid readings and NaN for an invalid one.
5. regression_tests - an instrumented copy replaces only the documented public
   ``normalize`` helpers. The candidate tests must pass the independent
   reference, and must record *assertion* failures for a helper that ignores
   ``valid`` and for one that applies the old scale to the new field. Build
   errors, import errors, other exceptions, crashes, timeouts and missing
   results never count as a rejected mutant.

Problems that exist only in the instrumented copy (helper not found where the
README documents it, instrumented build failure, reference run that does not
complete) make the verdict ungradable for analyst review instead of rejecting
the candidate. Rule observations are automated flags for the analyst, not a
violation count. Exit status: 0 accepted, 1 rejected, 2 ungradable.
"""
from pathlib import Path
import argparse
import ast
import difflib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fixture import original_files, spec  # noqa: E402

JAZZY = Path('/opt/ros/jazzy/setup.bash')
VENV_BIN = Path(os.environ.get('WV_VENV_BIN', '/tmp/ros2-skill-validation-venv/bin'))
MODES = ('reference', 'ignore_valid', 'old_scale')
MUTANTS = MODES[1:]
# Per-stage limits; every stage is also capped by the grade's total deadline.
# The runner allows the grader process 900 s, so the total stays below it.
STAGE_TIMEOUTS = {'build': 240, 'test': 150, 'probe': 120}
TOTAL_DEADLINE = 780
ROOT_EXCLUDES = {'.git', 'build', 'install', 'log', '.colcon'}
ANY_EXCLUDES = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.cache', '.git'}
SHELL = ('source /opt/ros/jazzy/setup.bash && '
         'if [ -n "${WV_OVERLAY:-}" ]; then source "$WV_OVERLAY"; fi && exec "$@"')


class Deadline:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def budget(self, stage):
        remaining = self.end - time.monotonic()
        if remaining <= 5:
            raise TimeoutError(f'grader total deadline exhausted before {stage}')
        return min(STAGE_TIMEOUTS[stage], remaining)


# --- bounded processes in a clean underlay-only environment -----------------

def clean_env(out, domain, tag, **extra):
    """Only the Jazzy underlay; private ROS/colcon state; the caller's ownership tag."""
    path = [str(VENV_BIN)] if (VENV_BIN / 'colcon').exists() else []
    defaults = out / 'colcon-defaults.yaml'
    if not defaults.exists():
        defaults.write_text('{}\n')
    env = {'HOME': os.environ.get('HOME', str(Path.home())),
           'PATH': ':'.join(path + ['/usr/local/bin', '/usr/bin', '/bin']),
           'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'EVAL_RUN_TAG': tag,
           'ROS_DOMAIN_ID': str(domain), 'ROS_AUTOMATIC_DISCOVERY_RANGE': 'LOCALHOST',
           'ROS_HOME': str(out / 'ros-home'), 'ROS_LOG_DIR': str(out / 'ros-log'),
           'COLCON_HOME': str(out / 'colcon-home'), 'COLCON_DEFAULTS_FILE': str(defaults),
           'PYTHONDONTWRITEBYTECODE': '1'}
    if os.environ.get('TMPDIR'):
        env['TMPDIR'] = os.environ['TMPDIR']
    env.update({k: str(v) for k, v in extra.items()})
    return env


def kill_group(pgid):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        time.sleep(1)


def run(args, cwd, log, env, timeout):
    """Run in its own session; return (returncode, or 124 on timeout, seconds)."""
    start = time.monotonic()
    with open(log, 'w') as handle:
        proc = subprocess.Popen(['bash', '--noprofile', '--norc', '-c', SHELL, '_', *map(str, args)],
                                cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            code = 124
        finally:
            kill_group(proc.pid)
            if proc.poll() is None:
                proc.wait(timeout=5)
    return code, round(time.monotonic() - start, 1)


def copy_project(source, dest):
    """Copy the submitted project, not only src/: root helpers/config count."""
    def ignore(directory, names):
        skip = {n for n in names if n in ANY_EXCLUDES or n.endswith('.pyc')}
        if Path(directory).resolve() == source.resolve():
            skip |= {n for n in names if n in ROOT_EXCLUDES}
        return skip
    shutil.copytree(source, dest, symlinks=False, ignore=ignore)


# --- test evidence -----------------------------------------------------------

def _pytest_assertion(failure):
    text = (failure.text or '')
    lines = [x.strip()[1:].strip() for x in text.splitlines() if x.strip().startswith('E ')]
    first = lines[0] if lines else (failure.get('message') or '').strip()
    return first.startswith(('assert', 'AssertionError', 'Failed:')) or \
        (not lines and 'AssertionError' in (failure.get('message') or ''))


def _gtest_assertion(failure):
    text = (failure.get('message') or '') + '\n' + (failure.text or '')
    return not re.search(r'C\+\+ exception|exception thrown|Unknown C\+\+', text)


def collect(ws, results, package):
    """testcase id -> state for one package, from this run's reports only.

    States: passed, skipped, assertion (a failed assertion), failure (any other
    failure, e.g. an exception or crash report) and error. Synthetic
    missing-result entries are errors, never assertions.
    """
    cases = {}
    seen = set()
    for base in (results / package, ws / 'build' / package / 'test_results'):
        if not base.is_dir():
            continue
        for path in sorted(base.rglob('*.xml')):
            if path.resolve() in seen or (path.name == 'Test.xml' and 'Testing' in path.parts):
                continue
            seen.add(path.resolve())
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                cases[f'unparseable:{path.name}'] = 'error'
                continue
            if root.tag not in ('testsuite', 'testsuites'):
                continue
            suites = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
            is_pytest = any(s.get('name') == 'pytest' for s in suites) or root.get('name') == 'pytest'
            is_gtest = path.name.endswith('.gtest.xml')
            for case in root.iter('testcase'):
                name = case.get('name', '')
                identity = '.'.join(x for x in (case.get('classname', ''), name) if x)
                failure = case.find('failure')
                if name.endswith('missing_result'):
                    state = 'error' if (failure is not None or case.find('error') is not None) \
                        else 'skipped'
                elif failure is not None:
                    judge = _pytest_assertion if is_pytest else _gtest_assertion if is_gtest else None
                    state = 'assertion' if judge and judge(failure) else 'failure'
                elif case.find('error') is not None:
                    state = 'error'
                elif case.find('skipped') is not None or case.get('status') == 'notrun':
                    state = 'skipped'
                else:
                    state = 'passed'
                cases[identity] = state
    return cases


def summarize(cases):
    counts = {k: sum(1 for v in cases.values() if v == k)
              for k in ('passed', 'assertion', 'failure', 'error', 'skipped')}
    return {**counts, 'cases': cases}


def run_tests(ws, out, env, label, consumers, timeout):
    for package in consumers:  # our copy only: never let an earlier report count
        shutil.rmtree(ws / 'build' / package / 'test_results', ignore_errors=True)
    results = out / f'results-{label}'
    code, seconds = run(['colcon', 'test', '--return-code-on-test-failure', '--python-testing',
                         'pytest', '--test-result-base', results], ws, out / f'test-{label}.log',
                        env, timeout)
    return code, seconds, {p: collect(ws, results, p) for p in consumers}


# --- instrumentation of the documented public helpers -------------------------

def mask_cpp(text):
    """Blank comments and string/char literals, preserving offsets."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        if text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
        elif text[i] in '"\'':
            quote, j = text[i], i + 1
            while j < n and text[j] != quote:
                j += 2 if text[j] == '\\' else 1
            j = min(j + 1, n)
        else:
            i += 1
            continue
        for k in range(i, j):
            if out[k] != '\n':
                out[k] = ' '
        i = j
    return ''.join(out)


def _match(masked, start, opening, closing):
    depth = 0
    for k in range(start, len(masked)):
        if masked[k] == opening:
            depth += 1
        elif masked[k] == closing:
            depth -= 1
            if depth == 0:
                return k
    return -1


def cpp_definitions(text):
    """Offsets of each out-of-class normalize definition.

    Returns dicts with ``paren``/``close`` (parameter list), ``brace``/``end``
    (body) and the masked ``params`` text.
    """
    masked = mask_cpp(text)
    found = []
    for m in re.finditer(r'\bnormalize\s*\(', masked):
        before = masked[:m.start()].rstrip()
        if before.endswith(('.', '->')):
            continue
        paren = m.end() - 1
        close = _match(masked, paren, '(', ')')
        if close < 0:
            continue
        k = close + 1
        while k < len(masked) and masked[k] not in '{;()=,':
            k += 1
        if k < len(masked) and masked[k] == '{':
            end = _match(masked, k, '{', '}')
            if end > 0:
                found.append({'paren': paren, 'close': close, 'brace': k, 'end': end,
                              'params': masked[paren:close + 1]})
    return found


def instrument_cpp(path, s):
    """Replace the helper's parameter name and body; keep its qualifiers."""
    text = path.read_text()
    found = cpp_definitions(text)
    if len(found) > 1:
        found = [d for d in found if s['msg'] in d['params']]
    if len(found) != 1:
        raise LookupError(f'expected one normalize definition in {path.name}, found {len(found)}')
    d = found[0]
    params = f"(const {s['interface_package']}::msg::{s['msg']} & wv_msg)"
    qualifiers = text[d['close'] + 1:d['brace']]
    body = f"""{{
  // workflow-value grader instrumentation, not candidate code
  const char * wv_env = std::getenv("WV_NORMALIZE_MODE");
  const std::string wv_mode = wv_env != nullptr ? wv_env : "reference";
  const double wv_value = static_cast<double>(wv_msg.{s['new_field']});
  if (wv_mode == "ignore_valid") {{
    return wv_value;
  }}
  if (!wv_msg.valid) {{
    return std::numeric_limits<double>::quiet_NaN();
  }}
  if (wv_mode == "old_scale") {{
    return wv_value / {float(s['factor'])};
  }}
  return wv_value;
}}"""
    header = '#include <cstdlib>\n#include <limits>\n#include <string>\n'
    path.write_text(header + text[:d['paren']] + params + qualifiers + body + text[d['end'] + 1:])


def instrument_python(path, s):
    if not path.is_file():
        raise LookupError(f'{path.name} not found at the documented helper path')
    path.write_text(path.read_text().rstrip('\n') + f'''


# --- workflow-value grader instrumentation, not candidate code ---
import math as _wv_math  # noqa: E402,I100
import os as _wv_os  # noqa: E402,I100


def normalize(msg):  # noqa: F811
    """Return the independent reference or a declared faulty conversion."""
    mode = _wv_os.environ.get('WV_NORMALIZE_MODE', 'reference')
    value = float(msg.{s['new_field']})
    if mode == 'ignore_valid':
        return value
    if not msg.valid:
        return _wv_math.nan
    if mode == 'old_scale':
        return value / {float(s['factor'])}
    return value
''')


def python_defines_normalize(path):
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return False
    return any(isinstance(n, ast.FunctionDef) and n.name == 'normalize' for n in tree.body)


def cpp_declares_normalize(path, s):
    try:
        masked = mask_cpp(path.read_text())
    except OSError:
        return False
    return re.search(r'\bnormalize\s*\([^)]*' + re.escape(s['msg']), masked) is not None


# --- dimensions -----------------------------------------------------------------

def mutation_dimension(ws, out, domain, tag, s, main_cases, deadline):
    """Returns (result, status); status in {'ok', 'ungradable'}."""
    consumers = (s['py_package'], s['cpp_package'])
    result = {'passed': False, 'packages': {}}
    try:
        instrument_python(ws / s['py_helper'], s)
        instrument_cpp(ws / s['cpp_helper'], s)
    except (OSError, LookupError) as error:
        result['instrumentation_error'] = str(error)
        return result, 'ungradable'
    code, seconds = run(['colcon', 'build'], ws, out / 'build-instrumented.log',
                        clean_env(out, domain, tag), deadline.budget('build'))
    result.update(build_returncode=code, build_seconds=seconds)
    if code:
        result['instrumentation_error'] = 'instrumented copy did not build'
        return result, 'ungradable'
    modes = {}
    for mode in MODES:
        tcode, tseconds, cases = run_tests(ws, out, clean_env(out, domain, tag, WV_NORMALIZE_MODE=mode),
                                           f'mode-{mode}', consumers, deadline.budget('test'))
        modes[mode] = {'returncode': tcode, 'seconds': tseconds, 'completed': tcode in (0, 1),
                       'cases': cases}
    result['modes'] = modes
    if not modes['reference']['completed']:
        # The candidate's own run completed; only the instrumented reference did not.
        result['instrumentation_error'] = 'instrumented reference test run did not complete'
        return result, 'ungradable'
    all_ok = True
    for package in consumers:
        per = {m: modes[m]['cases'][package] for m in MODES}
        bad = {m: {i for i, st in per[m].items() if st in ('assertion', 'failure', 'error')}
               for m in MODES}
        invariant = set.intersection(*bad.values())
        passed_before = {i for i, st in main_cases.get(package, {}).items() if st == 'passed'}
        regressions = sorted((passed_before & bad['reference']) - invariant)
        reference_passes = {i for i, st in per['reference'].items() if st == 'passed'}
        killed = {m: sorted(i for i, st in per[m].items()
                            if modes[m]['completed'] and st == 'assertion' and i in reference_passes)
                  for m in MUTANTS}
        non_assertion = {m: sorted(i for i, st in per[m].items()
                                   if st in ('failure', 'error') and i in reference_passes)
                         for m in MUTANTS}
        reference_ok = bool(reference_passes) and not regressions
        ok = reference_ok and all(killed.values())
        all_ok &= ok
        result['packages'][package] = {
            'reference_ok': reference_ok, 'reference_regressions': regressions,
            'instrumentation_invariant_failures': sorted(invariant),
            'killed_by_assertion': killed, 'non_assertion_failures': non_assertion,
            'passed': ok}
    result['incomplete_mutant_runs'] = [m for m in MUTANTS if not modes[m]['completed']]
    result['passed'] = all_ok
    return result, 'ok'


def rule_observations(root, s):
    """Automated flags for the analyst; not a final rule-violation count."""
    original = original_files(s['seed'])
    flags = []
    before = original[s['changelog']]
    try:
        after = (root / s['changelog']).read_text()
    except OSError:
        after = ''
        flags.append('interface CHANGELOG.rst missing')
    changelog_diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                  'original', 'submitted'))
    if after and after.strip() == before.strip():
        flags.append('interface CHANGELOG.rst unchanged')
    versions = {}
    pattern = re.compile(r'<version>\s*([^<]+?)\s*</version>')
    for package in (s['interface_package'], s['py_package'], s['cpp_package']):
        relative = f'src/{package}/package.xml'
        old = pattern.search(original[relative]).group(1)
        try:
            new = pattern.search((root / relative).read_text())
        except OSError:
            new = None
        versions[package] = {'original': old, 'submitted': new.group(1) if new else None}
        if not new or new.group(1) != old:
            flags.append(f'{package} version changed or missing')
    generated = []
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.stat().st_size < 1_000_000:
            try:
                if 'generated from rosidl_' in path.read_text(errors='ignore'):
                    generated.append(str(path.relative_to(root)))
            except OSError:
                continue
    if generated:
        flags.append('rosidl-generated files present in submitted sources')
    helpers = {'python_module_level_def': python_defines_normalize(root / s['py_helper']),
               'cpp_declaration_in_header': cpp_declares_normalize(root / s['cpp_header'], s),
               'cpp_definition_in_documented_file': len(cpp_definitions(
                   (root / s['cpp_helper']).read_text())) >= 1 if (root / s['cpp_helper']).is_file()
               else False}
    return {'automated_flags': flags, 'changelog_diff': changelog_diff, 'versions': versions,
            'helper_observations': helpers, 'generated_files_in_sources': generated,
            'note': 'Analyst decides rule compliance; flags only direct attention.'}


def grade(workspace, output, seed=0, *, domain=None, mutation=True, tag=None,
          total_seconds=TOTAL_DEADLINE):
    """Grade a submitted workspace; returns a JSON-serialisable verdict."""
    workspace, output = Path(workspace).resolve(), Path(output).resolve()
    if output.is_relative_to(workspace):
        raise ValueError('grader output must be outside the submitted workspace')
    output.mkdir(parents=True, exist_ok=False)
    s = spec(seed)
    domain = domain if domain is not None else int(os.environ.get('WV_ROS_DOMAIN_ID', 120 + seed))
    tag = tag or os.environ.get('EVAL_RUN_TAG') or f'wv-grade-{uuid.uuid4().hex}'
    deadline = Deadline(total_seconds)
    verdict = {'seed': seed, 'domain': domain, 'ownership_tag': tag, 'workspace': str(workspace),
               'accepted': False, 'gradable': True, 'needs_review': False, 'reasons': [],
               'dimensions': {}}
    dims = verdict['dimensions']
    started = time.monotonic()
    if not JAZZY.is_file() or not (shutil.which('colcon') or (VENV_BIN / 'colcon').exists()):
        verdict.update(gradable=False, reasons=['Jazzy underlay or colcon unavailable'])
        return verdict
    candidate, instrumented = output / 'candidate', output / 'instrumented'
    copy_project(workspace, candidate)
    shutil.copytree(candidate, instrumented)
    verdict['rules'] = rule_observations(candidate, s)
    consumers = (s['py_package'], s['cpp_package'])
    try:
        code, seconds = run(['colcon', 'build'], candidate, output / 'build.log',
                            clean_env(output, domain, tag), deadline.budget('build'))
        dims['clean_build'] = {'passed': code == 0, 'returncode': code, 'seconds': seconds}
        main_cases = {}
        if code == 0:
            tcode, tseconds, main_cases = run_tests(candidate, output, clean_env(output, domain, tag),
                                                    'candidate', consumers, deadline.budget('test'))
            packages = {p: summarize(main_cases[p]) for p in consumers}
            dims['tests'] = {
                'returncode': tcode, 'seconds': tseconds, 'packages': packages,
                'passed': tcode == 0 and all(v['passed'] >= 1 and not (v['assertion'] or v['failure']
                                                                     or v['error'])
                                             for v in packages.values())}
            runtime_dir = output / 'runtime'
            runtime_dir.mkdir()
            env = clean_env(output, domain, tag, WV_OVERLAY=candidate / 'install' / 'setup.bash')
            pcode, pseconds = run([sys.executable, HERE / 'runtime_probe.py', '--seed', seed,
                                   '--logdir', runtime_dir], candidate, runtime_dir / 'probe.log',
                                  env, deadline.budget('probe'))
            lines = [x for x in (runtime_dir / 'probe.log').read_text().splitlines()
                     if x.startswith('{')]
            try:
                probe = json.loads(lines[-1])
            except (IndexError, ValueError):
                probe = None
            if probe is None:
                dims['interface'] = {'passed': False, 'error': f'probe exit {pcode}; see runtime/probe.log'}
                dims['runtime'] = {'passed': {'py': False, 'cpp': False}, 'error': 'no probe report'}
                verdict['needs_review'] = True
            else:
                iface = probe['interface']
                iface['passed'] = bool(iface.get('importable') and iface.get('new_field') and
                                       iface.get('valid_field') and iface.get('old_field_absent'))
                dims['interface'] = iface
                dims['runtime'] = probe['runtime']
            dims['runtime'].update(probe_returncode=pcode, probe_seconds=pseconds)
            if 124 in (tcode, pcode):
                verdict['needs_review'] = True
                verdict['reasons'].append('a candidate test or runtime stage timed out')
        else:
            if code == 124:
                verdict['needs_review'] = True
            verdict['reasons'].append('clean build failed' if code != 124 else 'clean build timed out')

        if mutation and code == 0:
            mut, status = mutation_dimension(instrumented, output, domain, tag, s, main_cases, deadline)
            dims['regression_tests'] = mut
            if status == 'ungradable':
                verdict.update(gradable=False, needs_review=True)
                verdict['reasons'].append(f"instrumentation: {mut['instrumentation_error']}")
            elif mut.get('incomplete_mutant_runs'):
                verdict['needs_review'] = True
                verdict['reasons'].append('mutant test run did not complete; no kill counted from it')
            if any(p['instrumentation_invariant_failures'] for p in mut['packages'].values()):
                verdict['needs_review'] = True
        elif not mutation:
            dims['regression_tests'] = {'passed': None, 'skipped': 'mutation disabled for this control'}
    except TimeoutError as error:
        verdict.update(gradable=False, needs_review=True)
        verdict['reasons'].append(str(error))

    checks = {
        'clean_build': dims.get('clean_build', {}).get('passed', False),
        'interface': dims.get('interface', {}).get('passed', False),
        'tests': dims.get('tests', {}).get('passed', False),
        'runtime_python': dims.get('runtime', {}).get('passed', {}).get('py', False),
        'runtime_cpp': dims.get('runtime', {}).get('passed', {}).get('cpp', False),
        'regression_tests': dims.get('regression_tests', {}).get('passed', False),
    }
    verdict['checks'] = checks
    verdict['reasons'] += [f'{k} failed' for k, v in checks.items() if v is False]
    verdict['accepted'] = verdict['gradable'] and all(v is True for v in checks.values())
    verdict['seconds'] = round(time.monotonic() - started, 1)
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('output', type=Path, help='new directory for evidence and verdict.json')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--domain', type=int, help='ROS_DOMAIN_ID for grader processes')
    parser.add_argument('--no-mutation', action='store_true',
                        help='oracle controls only: skip the regression-test stage')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be a new path; earlier verdicts are never overwritten')
    verdict = grade(args.workspace, args.output, args.seed, domain=args.domain,
                    mutation=not args.no_mutation)
    (args.output / 'verdict.json').write_text(json.dumps(verdict, indent=2) + '\n')
    print(json.dumps({k: verdict[k] for k in ('accepted', 'gradable', 'needs_review', 'checks',
                                              'reasons')}, indent=2))
    return 0 if verdict['accepted'] else 2 if not verdict['gradable'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
