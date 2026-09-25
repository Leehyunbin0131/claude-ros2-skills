#!/usr/bin/env python3
"""Oracle validation for the workflow usefulness study. Makes no model calls.

Pure checks always run. The real colcon/ROS positive and negative controls run
only with WV_ORACLE_CONTROLS=1 in a shell with /opt/ros/jazzy available; they
rebuild each control from a clean copy and take a while for all seeds.
WV_SEEDS=0,1,2 selects variants; WV_ROS_DOMAIN_ID sets the grader domain;
WV_CONTROLS=a,b limits controls. With WV_CONTROL_OUTPUT=/new/root each control
keeps its workspace, grader evidence and verdict.json under
root/seed<N>/<control>/; existing control directories are never overwritten.
"""
from pathlib import Path
import ast
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixture  # noqa: E402
import grade  # noqa: E402

SEEDS = [int(x) for x in os.environ.get('WV_SEEDS', '0,1,2').split(',') if x.strip()]
ROS = os.environ.get('WV_ORACLE_CONTROLS') == '1' and grade.JAZZY.is_file()
OUTPUT_ROOT = os.environ.get('WV_CONTROL_OUTPUT')


class Fixture(unittest.TestCase):
    def test_specs_are_distinct_and_documented(self):
        names = set()
        for seed in fixture.SEEDS:
            s = fixture.spec(seed)
            names.add((s['interface_package'], s['py_topic'], s['cpp_topic']))
            self.assertNotEqual(s['old_field'], s['new_field'])
            self.assertEqual(len(s['runtime_valid']), 3)
        self.assertEqual(len(names), len(fixture.SEEDS))

    def test_prompt_is_neutral_and_names_both_consumers(self):
        for seed in fixture.SEEDS:
            s, text = fixture.spec(seed), fixture.prompt(seed).lower()
            for word in ('skill', 'claude', 'codex', 'plugin', 'evaluat', 'benchmark', 'grader'):
                self.assertNotIn(word, text)
            self.assertIn(s['py_package'], text)
            self.assertIn(s['cpp_package'], text)

    def test_create_and_controls_write_parseable_sources(self):
        for seed in fixture.SEEDS:
            for control in fixture.CONTROLS:
                with self.subTest(seed=seed, control=control), tempfile.TemporaryDirectory() as d:
                    fixture.create(d, seed)
                    fixture.apply_control(d, seed, control)
                    for path in Path(d).rglob('*.py'):
                        ast.parse(path.read_text(), str(path))
                    s = fixture.spec(seed)
                    found = grade.cpp_definitions((Path(d) / s['cpp_helper']).read_text())
                    self.assertEqual(len(found), 0 if control == 'header_inline_helper' else 1)

    def test_create_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'keep').write_text('x')
            with self.assertRaises(FileExistsError):
                fixture.create(d, 0)


class Instrumentation(unittest.TestCase):
    SOURCE = '''#include "x/conversion.hpp"
// normalize(ignored comment) {
namespace x
{
static double helper(double v) { return v; }
const char * text = "normalize( in a string ) {";
double normalize(const range_interfaces::msg::RangeReading & reading) noexcept
{
  if (reading.valid) { return helper(reading.distance_m); }
  return 0.0;
}
double use(const range_interfaces::msg::RangeReading & r) { return normalize(r); }
}  // namespace x
'''

    def test_locator_ignores_comments_strings_calls_and_declarations(self):
        found = grade.cpp_definitions(self.SOURCE)
        self.assertEqual(len(found), 1)
        self.assertIn('RangeReading', found[0]['params'])
        declaration = 'double normalize(const range_interfaces::msg::RangeReading & msg);\n'
        self.assertEqual(grade.cpp_definitions(declaration), [])

    def test_qualified_definition_is_found(self):
        text = ('double x::normalize(const range_interfaces::msg::RangeReading & m)\n'
                '{\n  return m.distance_m;\n}\n')
        self.assertEqual(len(grade.cpp_definitions(text)), 1)

    def test_cpp_instrumentation_replaces_only_the_helper(self):
        s = fixture.spec(0)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'conversion.cpp'
            path.write_text(self.SOURCE)
            grade.instrument_cpp(path, s)
            text = path.read_text()
            self.assertEqual(len(grade.cpp_definitions(text)), 1)
            self.assertIn('WV_NORMALIZE_MODE', text)
            self.assertIn('static double helper', text)
            self.assertIn('return normalize(r);', text)
            self.assertIn('& wv_msg) noexcept', text)
            self.assertNotIn('return helper(reading.distance_m)', text)

    def test_missing_helper_definition_is_an_instrumentation_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'conversion.cpp'
            path.write_text('#include "x/conversion.hpp"\n')
            with self.assertRaises(LookupError):
                grade.instrument_cpp(path, fixture.spec(0))

    def test_python_instrumentation_overrides_module_function(self):
        s = fixture.spec(0)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'conversion.py'
            path.write_text('def helper():\n    return 1\n\n\ndef normalize(msg):\n    return 0\n')
            grade.instrument_python(path, s)
            namespace = {}
            exec(compile(path.read_text(), str(path), 'exec'), namespace)

            class Msg:
                distance_m, valid = 2.5, True
            os.environ['WV_NORMALIZE_MODE'] = 'old_scale'
            try:
                self.assertAlmostEqual(namespace['normalize'](Msg()), 0.025)
            finally:
                del os.environ['WV_NORMALIZE_MODE']
            self.assertEqual(namespace['normalize'](Msg()), 2.5)
            self.assertEqual(namespace['helper'](), 1)


class Evidence(unittest.TestCase):
    def xml(self, directory, name, body, suite='pytest'):
        path = Path(directory) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<testsuites><testsuite name="{suite}">{body}</testsuite></testsuites>')

    def test_only_assertions_count_as_assertion_failures(self):
        with tempfile.TemporaryDirectory() as d:
            ws, results = Path(d) / 'ws', Path(d) / 'results'
            self.xml(results / 'pkg', 'pytest.xml',
                     '<testcase classname="t" name="plain"><failure message="assert 1 == 2">'
                     'E       assert 1 == 2</failure></testcase>'
                     '<testcase classname="t" name="raised"><failure message="KeyError: 2.5">'
                     'E       KeyError: 2.5</failure></testcase>'
                     '<testcase classname="t" name="setup"><error message="x"/></testcase>'
                     '<testcase classname="t" name="ok"/>'
                     '<testcase classname="t" name="skip"><skipped/></testcase>')
            self.xml(ws / 'build/pkg/test_results/pkg', 'test_x.gtest.xml',
                     '<testcase classname="C" name="expect"><failure message="x.cpp:3&#10;'
                     'Expected equality"/></testcase>'
                     '<testcase classname="C" name="thrown"><failure message="C++ exception '
                     'with description &quot;x&quot; thrown in the test body."/></testcase>',
                     suite='C')
            self.xml(ws / 'build/pkg/test_results/pkg', 'test_y.xunit.xml',
                     '<testcase classname="pkg" name="test_y.missing_result">'
                     '<failure message="crash"/></testcase>', suite='test_y')
            cases = grade.collect(ws, results, 'pkg')
            self.assertEqual(cases, {'t.plain': 'assertion', 't.raised': 'failure', 't.setup': 'error',
                                     't.ok': 'passed', 't.skip': 'skipped', 'C.expect': 'assertion',
                                     'C.thrown': 'failure', 'pkg.test_y.missing_result': 'error'})

    def test_project_copy_keeps_root_sources_and_drops_generated_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            source, dest = Path(d) / 'ws', Path(d) / 'copy'
            for relative in ('src/p/x.py', 'tools/helper.py', 'pytest.ini', 'build/p/junk',
                             'install/setup.bash', 'log/latest', '.git/HEAD', '.colcon/x',
                             'src/p/__pycache__/x.pyc', 'src/p/build/keep.txt'):
                (source / relative).parent.mkdir(parents=True, exist_ok=True)
                (source / relative).write_text('x')
            grade.copy_project(source, dest)
            kept = sorted(str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file())
            self.assertEqual(kept, ['pytest.ini', 'src/p/build/keep.txt', 'src/p/x.py',
                                    'tools/helper.py'])

    def test_rule_observations_are_flags_not_verdicts(self):
        for control, flags in (('reference', []), ('starter', ['interface CHANGELOG.rst unchanged'])):
            with self.subTest(control=control), tempfile.TemporaryDirectory() as d:
                fixture.create(d, 0)
                fixture.apply_control(d, 0, control)
                result = grade.rule_observations(Path(d), fixture.spec(0))
                self.assertEqual(result['automated_flags'], flags, result)
                self.assertNotIn('violations', result)

    def test_output_inside_workspace_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                grade.grade(d, Path(d) / 'grade', 0)


# control: (mutation stage, gradable, checks that must be False, checks that must be True)
ALL = ('clean_build', 'interface', 'tests', 'runtime_python', 'runtime_cpp', 'regression_tests')
IMPLEMENTED = ('clean_build', 'interface', 'tests', 'runtime_python', 'runtime_cpp')
EXPECTED = {
    'reference': (True, True, (), ALL),
    'starter': (False, True, ('interface',), ('clean_build', 'tests')),
    'interface_only': (False, True, ('clean_build',), ()),
    'missed_python': (False, True, ('tests', 'runtime_python'),
                      ('clean_build', 'interface', 'runtime_cpp')),
    'missed_cpp': (False, True, ('clean_build',), ()),
    'cpp_node_bypass': (False, True, ('runtime_cpp',),
                        ('clean_build', 'interface', 'tests', 'runtime_python')),
    'valid_only_tests': (True, True, ('regression_tests',), IMPLEMENTED),
    'invalid_only_tests': (True, True, ('regression_tests',), IMPLEMENTED),
    'vacuous_tests': (True, True, ('regression_tests',), IMPLEMENTED),
    'exception_tests': (True, True, ('regression_tests',), IMPLEMENTED),
    'crash_tests': (True, True, ('regression_tests',), IMPLEMENTED),
    # Public ABI intact; only the grader's instrumentation boundary moved.
    'header_inline_helper': (True, False, (), IMPLEMENTED),
}
SURVIVORS = {'valid_only_tests': {'ignore_valid'}, 'invalid_only_tests': {'old_scale'},
             'vacuous_tests': set(grade.MUTANTS), 'exception_tests': set(grade.MUTANTS),
             'crash_tests': set(grade.MUTANTS)}
SELECTED = [c for c in os.environ.get('WV_CONTROLS', ','.join(EXPECTED)).split(',') if c]


def control_dir(seed, control):
    if OUTPUT_ROOT:
        path = Path(OUTPUT_ROOT) / f'seed{seed}' / control
        path.mkdir(parents=True, exist_ok=False)
        return path, None
    holder = tempfile.TemporaryDirectory(prefix=f'wv-control-{seed}-{control}-')
    return Path(holder.name), holder


@unittest.skipUnless(ROS, 'set WV_ORACLE_CONTROLS=1 with ROS 2 Jazzy for real controls')
class Controls(unittest.TestCase):
    def check(self, seed, control):
        mutation, gradable, false, true = EXPECTED[control]
        root, holder = control_dir(seed, control)
        try:
            workspace = root / 'workspace'
            fixture.create(workspace, seed)
            fixture.apply_control(workspace, seed, control)
            verdict = grade.grade(workspace, root / 'grade', seed, mutation=mutation)
            (root / 'verdict.json').write_text(json.dumps(verdict, indent=2) + '\n')
            summary = {k: verdict.get(k) for k in ('accepted', 'gradable', 'needs_review',
                                                   'checks', 'reasons')}
            self.assertEqual(verdict['gradable'], gradable, summary)
            self.assertEqual(verdict['accepted'], control == 'reference', summary)
            for key in false:
                self.assertIs(verdict['checks'][key], False, (key, summary))
            for key in true:
                self.assertIs(verdict['checks'][key], True, (key, summary))
            if control == 'reference':
                self.assertFalse(verdict['needs_review'], summary)
                self.assertEqual(verdict['rules']['automated_flags'], [], verdict['rules'])
            if control == 'header_inline_helper':
                self.assertTrue(verdict['needs_review'], summary)
            if control in SURVIVORS:
                s = fixture.spec(seed)
                for package in (s['py_package'], s['cpp_package']):
                    killed = verdict['dimensions']['regression_tests']['packages'][package][
                        'killed_by_assertion']
                    survivors = {m for m, ids in killed.items() if not ids}
                    self.assertEqual(survivors, SURVIVORS[control], (package, killed))
        finally:
            if holder is not None:
                holder.cleanup()

    def test_controls(self):
        for seed in SEEDS:
            for control in SELECTED:
                with self.subTest(seed=seed, control=control):
                    self.check(seed, control)


if __name__ == '__main__':
    unittest.main(verbosity=2)
