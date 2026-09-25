#!/usr/bin/env python3
"""Interface-migration workspace for the workflow usefulness study.

``create`` writes source and project documents only; it never builds. The
caller prepares the old install/overlay. ``apply_control`` turns a created
workspace into a reference solution or a declared negative control, so the
independent grader can be validated before any model call.
"""
from pathlib import Path
import argparse
import json
import re
import textwrap

SEEDS = {
    0: dict(stem='range', msg='RangeReading', old_field='distance_cm', new_field='distance_m',
            factor=100, old_unit='centimetres', new_unit='metres', quantity='distance',
            input_topic='/sensor/range', py_topic='/monitor/py_range_m',
            cpp_topic='/monitor/cpp_range_m', sample=250.0,
            runtime_valid=(0.5, 2.25, 7.0), runtime_invalid=3.0),
    1: dict(stem='thermal', msg='ThermalReading', old_field='temperature_millic',
            new_field='temperature_c', factor=1000, old_unit='milli-degrees Celsius',
            new_unit='degrees Celsius', quantity='temperature',
            input_topic='/sensor/thermal', py_topic='/monitor/py_temperature_c',
            cpp_topic='/monitor/cpp_temperature_c', sample=21500.0,
            runtime_valid=(-12.5, 21.0, 36.625), runtime_invalid=40.0),
    2: dict(stem='power', msg='PowerReading', old_field='power_mw', new_field='power_w',
            factor=1000, old_unit='milliwatts', new_unit='watts', quantity='power',
            input_topic='/sensor/power', py_topic='/monitor/py_power_w',
            cpp_topic='/monitor/cpp_power_w', sample=12500.0,
            runtime_valid=(1.5, 42.0, 250.25), runtime_invalid=8.0),
}

CONTROLS = ('reference', 'starter', 'interface_only', 'missed_python', 'missed_cpp',
            'cpp_node_bypass', 'valid_only_tests', 'invalid_only_tests', 'vacuous_tests',
            'exception_tests', 'crash_tests', 'header_inline_helper')


def snake(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def spec(seed=0):
    """Names, topics and values for one variant. JSON-serialisable."""
    if seed not in SEEDS:
        raise ValueError(f'seed must be one of {sorted(SEEDS)}')
    s = dict(SEEDS[seed])
    stem = s['stem']
    s.update(seed=seed, interface_package=f'{stem}_interfaces',
             py_package=f'{stem}_py_monitor', cpp_package=f'{stem}_cpp_monitor',
             executable='monitor', msg_header=snake(s['msg']) + '.hpp',
             runtime_valid=list(s['runtime_valid']))
    s['msg_type'] = f"{s['interface_package']}/msg/{s['msg']}"
    s['py_helper'] = f"src/{s['py_package']}/{s['py_package']}/conversion.py"
    s['cpp_header'] = f"src/{s['cpp_package']}/include/{s['cpp_package']}/conversion.hpp"
    s['cpp_helper'] = f"src/{s['cpp_package']}/src/conversion.cpp"
    s['changelog'] = f"src/{s['interface_package']}/CHANGELOG.rst"
    return s


def prompt(seed=0):
    s = spec(seed)
    return (
        f"In this ROS 2 Jazzy workspace, change `{s['msg_type']}` so the sensor reports "
        f"`{s['new_field']}` ({s['quantity']} in {s['new_unit']}, float64) instead of "
        f"`{s['old_field']}`, and add `bool valid`. Update both consumers, "
        f"`{s['py_package']}` (Python) and `{s['cpp_package']}` (C++): their `normalize` "
        f"helpers and `monitor` nodes should output the {s['quantity']} in {s['new_unit']} "
        f"when `valid` is true and NaN when it is false. My normal terminal already has "
        f"/opt/ros/jazzy and this workspace's install/setup.bash sourced, and install/ "
        f"contains a build of the current sources. Follow the project's README and "
        f"CONTRIBUTING. Tell me what you changed and how you verified it.")


def _files(seed):
    s = spec(seed)
    i, py, cpp = s['interface_package'], s['py_package'], s['cpp_package']
    msg, old, factor = s['msg'], s['old_field'], s['factor']
    guard = f"{cpp.upper()}__CONVERSION_HPP_"
    files = {}
    files['README.md'] = f"""\
        # {s['stem'].capitalize()} monitor workspace

        ROS 2 Jazzy workspace. All packages are under `src/`.

        | Package | Build type | Purpose |
        | :--- | :--- | :--- |
        | `{i}` | ament_cmake (rosidl) | `{msg}` message |
        | `{py}` | ament_python | `ros2 run {py} monitor` subscribes to `{s['input_topic']}` and publishes `std_msgs/msg/Float64` on `{s['py_topic']}` |
        | `{cpp}` | ament_cmake | `ros2 run {cpp} monitor` subscribes to `{s['input_topic']}` and publishes `std_msgs/msg/Float64` on `{s['cpp_topic']}` |

        Both nodes publish the {s['quantity']} computed by their package's public
        conversion helper. Downstream tools call these helpers directly:

        - Python: `{py}.conversion.normalize(msg) -> float`, defined in
          `{s['py_helper']}`.
        - C++: `double {cpp}::normalize(const {i}::msg::{msg} & msg)`, declared in
          `{s['cpp_header']}` and defined in `{s['cpp_helper']}`.
        """
    files['CONTRIBUTING.md'] = f"""\
        # Contributing

        - CI builds and tests every package from a clean checkout on Ubuntu 24.04 with
          only `/opt/ros/jazzy` sourced:

              colcon build
              colcon test --return-code-on-test-failure --python-testing pytest

          A change is ready when that passes from a clean checkout.
        - Each behaviour change needs regression tests in every affected package. For
          conversion changes, cover both a valid and an invalid reading.
        - Edit sources only. Do not hand-edit generated files or anything under
          `build/`, `install/` or `log/`.
        - Keep the public conversion helpers, executables and topic names described
          in `README.md`.
        - Interface changes need an entry at the top of `{s['changelog']}`.
        - Package versions are bumped at release time; do not change them in a
          feature change.
        """
    files['TASK.txt'] = prompt(seed) + '\n'
    # Interface package.
    files[f'src/{i}/package.xml'] = f"""\
        <?xml version="1.0"?>
        <package format="3">
          <name>{i}</name>
          <version>0.3.1</version>
          <description>{msg} message for the monitor packages.</description>
          <maintainer email="robot-team@example.com">Robot Team</maintainer>
          <license>Apache-2.0</license>
          <buildtool_depend>ament_cmake</buildtool_depend>
          <buildtool_depend>rosidl_default_generators</buildtool_depend>
          <exec_depend>rosidl_default_runtime</exec_depend>
          <member_of_group>rosidl_interface_packages</member_of_group>
          <export>
            <build_type>ament_cmake</build_type>
          </export>
        </package>
        """
    files[f'src/{i}/CMakeLists.txt'] = f"""\
        cmake_minimum_required(VERSION 3.8)
        project({i})

        find_package(ament_cmake REQUIRED)
        find_package(rosidl_default_generators REQUIRED)

        rosidl_generate_interfaces(${{PROJECT_NAME}}
          "msg/{msg}.msg"
        )

        ament_export_dependencies(rosidl_default_runtime)
        ament_package()
        """
    files[f'src/{i}/msg/{msg}.msg'] = f"""\
        # {s['quantity'].capitalize()} reported by the sensor, in {s['old_unit']}.
        float64 {old}
        """
    title = f'Changelog for package {i}'
    files[s['changelog']] = f"""\
        {'^' * len(title)}
        {title}
        {'^' * len(title)}

        0.3.1 (2026-08-14)
        ------------------
        * Document the {msg} units.

        0.3.0 (2026-06-02)
        ------------------
        * Add {msg}.
        """
    # Python consumer.
    files[f'src/{py}/package.xml'] = f"""\
        <?xml version="1.0"?>
        <package format="3">
          <name>{py}</name>
          <version>0.3.1</version>
          <description>Python {s['quantity']} monitor.</description>
          <maintainer email="robot-team@example.com">Robot Team</maintainer>
          <license>Apache-2.0</license>
          <exec_depend>rclpy</exec_depend>
          <exec_depend>std_msgs</exec_depend>
          <exec_depend>{i}</exec_depend>
          <test_depend>python3-pytest</test_depend>
          <export>
            <build_type>ament_python</build_type>
          </export>
        </package>
        """
    files[f'src/{py}/resource/{py}'] = ''
    files[f'src/{py}/setup.cfg'] = f"""\
        [develop]
        script_dir=$base/lib/{py}
        [install]
        install_scripts=$base/lib/{py}
        """
    files[f'src/{py}/setup.py'] = f"""\
        from setuptools import setup

        package_name = '{py}'

        setup(
            name=package_name,
            version='0.3.1',
            packages=[package_name],
            data_files=[
                ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                ('share/' + package_name, ['package.xml']),
            ],
            install_requires=['setuptools'],
            zip_safe=True,
            maintainer='Robot Team',
            maintainer_email='robot-team@example.com',
            description='Python {s['quantity']} monitor.',
            license='Apache-2.0',
            tests_require=['pytest'],
            entry_points={{
                'console_scripts': [
                    'monitor = {py}.node:main',
                ],
            }},
        )
        """
    files[f'src/{py}/{py}/__init__.py'] = ''
    files[s['py_helper']] = f'''\
        """Public conversion helper shared by the node and downstream tools."""

        SCALE = {float(factor)}


        def normalize(msg):
            """Return the {s['quantity']} in {s['new_unit']}."""
            return msg.{old} / SCALE
        '''
    files[f'src/{py}/{py}/node.py'] = f'''\
        """Publish the normalized {s['quantity']} for every reading."""
        import rclpy
        from rclpy.executors import ExternalShutdownException
        from rclpy.node import Node
        from std_msgs.msg import Float64

        from {i}.msg import {msg}

        from .conversion import normalize


        class Monitor(Node):

            def __init__(self):
                super().__init__('{py}')
                self._publisher = self.create_publisher(Float64, '{s['py_topic'].lstrip('/')}', 10)
                self._subscription = self.create_subscription(
                    {msg}, '{s['input_topic'].lstrip('/')}', self._on_reading, 10)

            def _on_reading(self, msg):
                self._publisher.publish(Float64(data=float(normalize(msg))))


        def main(args=None):
            rclpy.init(args=args)
            node = Monitor()
            try:
                rclpy.spin(node)
            except (KeyboardInterrupt, ExternalShutdownException):
                pass
            finally:
                node.destroy_node()
                rclpy.try_shutdown()
        '''
    files[f'src/{py}/test/test_conversion.py'] = f'''\
        from {i}.msg import {msg}

        from {py}.conversion import normalize


        def test_converts_{snake(s['old_unit'].split()[0].replace('-', '_'))}():
            msg = {msg}()
            msg.{old} = {s['sample']}
            assert normalize(msg) == {s['sample'] / factor}
        '''
    # C++ consumer.
    files[f'src/{cpp}/package.xml'] = f"""\
        <?xml version="1.0"?>
        <package format="3">
          <name>{cpp}</name>
          <version>0.3.1</version>
          <description>C++ {s['quantity']} monitor.</description>
          <maintainer email="robot-team@example.com">Robot Team</maintainer>
          <license>Apache-2.0</license>
          <buildtool_depend>ament_cmake</buildtool_depend>
          <depend>rclcpp</depend>
          <depend>std_msgs</depend>
          <depend>{i}</depend>
          <test_depend>ament_cmake_gtest</test_depend>
          <export>
            <build_type>ament_cmake</build_type>
          </export>
        </package>
        """
    files[f'src/{cpp}/CMakeLists.txt'] = f"""\
        cmake_minimum_required(VERSION 3.8)
        project({cpp})

        if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
          add_compile_options(-Wall -Wextra -Wpedantic)
        endif()

        find_package(ament_cmake REQUIRED)
        find_package(rclcpp REQUIRED)
        find_package(std_msgs REQUIRED)
        find_package({i} REQUIRED)

        add_library(${{PROJECT_NAME}}_conversion src/conversion.cpp)
        target_include_directories(${{PROJECT_NAME}}_conversion PUBLIC
          $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/include>
          $<INSTALL_INTERFACE:include/${{PROJECT_NAME}}>)
        ament_target_dependencies(${{PROJECT_NAME}}_conversion {i})

        add_executable(monitor src/monitor_node.cpp)
        target_link_libraries(monitor ${{PROJECT_NAME}}_conversion)
        ament_target_dependencies(monitor rclcpp std_msgs {i})

        install(TARGETS monitor DESTINATION lib/${{PROJECT_NAME}})
        install(DIRECTORY include/ DESTINATION include/${{PROJECT_NAME}})

        if(BUILD_TESTING)
          find_package(ament_cmake_gtest REQUIRED)
          ament_add_gtest(test_conversion test/test_conversion.cpp)
          target_link_libraries(test_conversion ${{PROJECT_NAME}}_conversion)
          ament_target_dependencies(test_conversion {i})
        endif()

        ament_package()
        """
    files[s['cpp_header']] = f"""\
        #ifndef {guard}
        #define {guard}

        #include "{i}/msg/{s['msg_header']}"

        namespace {cpp}
        {{

        /// Public conversion helper: the {s['quantity']} in {s['new_unit']}.
        double normalize(const {i}::msg::{msg} & msg);

        }}  // namespace {cpp}

        #endif  // {guard}
        """
    files[s['cpp_helper']] = f"""\
        #include "{cpp}/conversion.hpp"

        namespace {cpp}
        {{

        double normalize(const {i}::msg::{msg} & msg)
        {{
          return msg.{old} / {float(factor)};
        }}

        }}  // namespace {cpp}
        """
    files[f'src/{cpp}/src/monitor_node.cpp'] = f"""\
        #include <memory>

        #include "rclcpp/rclcpp.hpp"
        #include "std_msgs/msg/float64.hpp"
        #include "{cpp}/conversion.hpp"

        class Monitor : public rclcpp::Node
        {{
        public:
          Monitor()
          : Node("{cpp}")
          {{
            publisher_ = create_publisher<std_msgs::msg::Float64>("{s['cpp_topic'].lstrip('/')}", 10);
            subscription_ = create_subscription<{i}::msg::{msg}>(
              "{s['input_topic'].lstrip('/')}", 10,
              [this](const {i}::msg::{msg} & msg) {{
                std_msgs::msg::Float64 out;
                out.data = {cpp}::normalize(msg);
                publisher_->publish(out);
              }});
          }}

        private:
          rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
          rclcpp::Subscription<{i}::msg::{msg}>::SharedPtr subscription_;
        }};

        int main(int argc, char ** argv)
        {{
          rclcpp::init(argc, argv);
          rclcpp::spin(std::make_shared<Monitor>());
          rclcpp::shutdown();
          return 0;
        }}
        """
    files[f'src/{cpp}/test/test_conversion.cpp'] = f"""\
        #include <gtest/gtest.h>

        #include "{cpp}/conversion.hpp"

        TEST(Conversion, Converts{s['quantity'].capitalize()})
        {{
          {i}::msg::{msg} msg;
          msg.{old} = {s['sample']};
          EXPECT_DOUBLE_EQ({cpp}::normalize(msg), {s['sample'] / factor});
        }}
        """
    return {path: textwrap.dedent(text) for path, text in files.items()}


def original_files(seed=0):
    """Relative path -> text of the untouched workspace (grader baseline)."""
    return _files(seed)


def create(workspace, seed=0):
    """Write a fresh, unbuilt workspace. The destination must be new or empty."""
    workspace = Path(workspace)
    if workspace.exists() and any(workspace.iterdir()):
        raise FileExistsError(f'{workspace} must be new or empty')
    for relative, text in _files(seed).items():
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return spec(seed)


def _write(workspace, relative, text):
    path = Path(workspace) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))


def _python_tests(s, kind):
    i, py, msg, new = s['interface_package'], s['py_package'], s['msg'], s['new_field']
    head = f'''\
        import math

        from {i}.msg import {msg}

        from {py}.conversion import normalize


        def _reading(value, valid):
            msg = {msg}()
            msg.{new} = value
            msg.valid = valid
            return msg
        '''
    valid = '''

        def test_valid_reading_passes_through():
            assert normalize(_reading(2.5, True)) == 2.5
        '''
    invalid = '''

        def test_invalid_reading_is_nan():
            assert math.isnan(normalize(_reading(2.5, False)))
        '''
    vacuous = '''

        def test_returns_float():
            assert isinstance(normalize(_reading(2.5, True)), float)
            assert isinstance(normalize(_reading(2.5, False)), float)
        '''
    # Negative controls: these detect a faulty helper only by raising an
    # exception or killing the runner, never by a failed assertion.
    exception = '''

        def test_valid_reading_passes_through():
            assert {2.5: True}[normalize(_reading(2.5, True))]


        def test_invalid_reading_is_nan():
            value = normalize(_reading(2.5, False))
            assert value != value or {}[value]
        '''
    crash = '''

        def test_valid_reading_passes_through():
            if normalize(_reading(2.5, True)) != 2.5:
                import os
                os._exit(3)


        def test_invalid_reading_is_nan():
            value = normalize(_reading(2.5, False))
            if value == value:
                import os
                os._exit(3)
        '''
    body = {'both': valid + invalid, 'valid': valid, 'invalid': invalid, 'vacuous': vacuous,
            'exception': exception, 'crash': crash}[kind]
    return head + body


def _cpp_tests(s, kind):
    i, cpp, msg, new = s['interface_package'], s['cpp_package'], s['msg'], s['new_field']
    head = f"""\
        #include <gtest/gtest.h>

        #include <cmath>

        #include "{cpp}/conversion.hpp"

        namespace
        {{
        {i}::msg::{msg} reading(double value, bool valid)
        {{
          {i}::msg::{msg} msg;
          msg.{new} = value;
          msg.valid = valid;
          return msg;
        }}
        }}  // namespace
        """
    valid = f"""
        TEST(Conversion, ValidReadingPassesThrough)
        {{
          EXPECT_DOUBLE_EQ({cpp}::normalize(reading(2.5, true)), 2.5);
        }}
        """
    invalid = f"""
        TEST(Conversion, InvalidReadingIsNaN)
        {{
          EXPECT_TRUE(std::isnan({cpp}::normalize(reading(2.5, false))));
        }}
        """
    vacuous = f"""
        TEST(Conversion, ReturnsADouble)
        {{
          const double valid = {cpp}::normalize(reading(2.5, true));
          const double invalid = {cpp}::normalize(reading(2.5, false));
          EXPECT_EQ(sizeof(valid), sizeof(invalid));
        }}
        """
    exception = f"""
        TEST(Conversion, ValidReadingPassesThrough)
        {{
          if ({cpp}::normalize(reading(2.5, true)) != 2.5) {{
            throw std::runtime_error("unexpected value");
          }}
        }}

        TEST(Conversion, InvalidReadingIsNaN)
        {{
          if (!std::isnan({cpp}::normalize(reading(2.5, false)))) {{
            throw std::runtime_error("expected NaN");
          }}
        }}
        """
    crash = f"""
        TEST(Conversion, ValidReadingPassesThrough)
        {{
          if ({cpp}::normalize(reading(2.5, true)) != 2.5) {{
            std::abort();
          }}
        }}

        TEST(Conversion, InvalidReadingIsNaN)
        {{
          if (!std::isnan({cpp}::normalize(reading(2.5, false)))) {{
            std::abort();
          }}
        }}
        """
    body = {'both': valid + invalid, 'valid': valid, 'invalid': invalid, 'vacuous': vacuous,
            'exception': exception, 'crash': crash}[kind]
    if kind in ('exception', 'crash'):
        head = head.replace('#include <cmath>', '#include <cmath>\n        #include <cstdlib>\n'
                            '        #include <stdexcept>')
    return head + body


def _migrate_interface(workspace, s):
    i, msg = s['interface_package'], s['msg']
    _write(workspace, f'src/{i}/msg/{msg}.msg', f"""\
        # {s['quantity'].capitalize()} reported by the sensor, in {s['new_unit']}.
        float64 {s['new_field']}
        # False when the sensor could not produce a reading.
        bool valid
        """)
    path = Path(workspace) / s['changelog']
    lines = path.read_text().splitlines(keepends=True)
    entry = (f"Forthcoming\n-----------\n* Replace ``{s['old_field']}`` with ``{s['new_field']}`` "
             f"({s['new_unit']}) and add ``valid``.\n\n")
    path.write_text(''.join(lines[:4]) + entry + ''.join(lines[4:]))


def _migrate_python(workspace, s, tests):
    _write(workspace, s['py_helper'], f'''\
        """Public conversion helper shared by the node and downstream tools."""
        import math


        def normalize(msg):
            """Return the {s['quantity']} in {s['new_unit']}, or NaN for an invalid reading."""
            return float(msg.{s['new_field']}) if msg.valid else math.nan
        ''')
    _write(workspace, f"src/{s['py_package']}/test/test_conversion.py", _python_tests(s, tests))


def _migrate_cpp(workspace, s, tests, bypass=False, inline=False):
    i, cpp, msg = s['interface_package'], s['cpp_package'], s['msg']
    _write(workspace, s['cpp_helper'], f"""\
        #include "{cpp}/conversion.hpp"

        #include <limits>

        namespace {cpp}
        {{

        double normalize(const {i}::msg::{msg} & msg)
        {{
          return msg.valid ? msg.{s['new_field']} : std::numeric_limits<double>::quiet_NaN();
        }}

        }}  // namespace {cpp}
        """)
    _write(workspace, f'src/{cpp}/test/test_conversion.cpp', _cpp_tests(s, tests))
    if inline:
        # A legitimate refactor outside the grader's documented instrumentation
        # boundary: public ABI unchanged, definition moved into the header.
        guard = f"{cpp.upper()}__CONVERSION_HPP_"
        _write(workspace, s['cpp_header'], f"""\
            #ifndef {guard}
            #define {guard}

            #include <limits>

            #include "{i}/msg/{s['msg_header']}"

            namespace {cpp}
            {{

            inline double normalize(const {i}::msg::{msg} & msg)
            {{
              return msg.valid ? msg.{s['new_field']} : std::numeric_limits<double>::quiet_NaN();
            }}

            }}  // namespace {cpp}

            #endif  // {guard}
            """)
        _write(workspace, s['cpp_helper'], f'#include "{cpp}/conversion.hpp"\n')
    if bypass:
        node = Path(workspace) / f'src/{cpp}/src/monitor_node.cpp'
        node.write_text(node.read_text().replace(f'{cpp}::normalize(msg)',
                                                 f"msg.{s['new_field']}"))


def apply_control(workspace, seed, variant):
    """Rewrite a freshly created workspace into a declared oracle control."""
    if variant not in CONTROLS:
        raise ValueError(f'unknown control {variant!r}; expected one of {CONTROLS}')
    s = spec(seed)
    if variant == 'starter':
        return
    _migrate_interface(workspace, s)
    if variant == 'interface_only':
        return
    tests = {'valid_only_tests': 'valid', 'invalid_only_tests': 'invalid',
             'vacuous_tests': 'vacuous', 'exception_tests': 'exception',
             'crash_tests': 'crash'}.get(variant, 'both')
    if variant != 'missed_python':
        _migrate_python(workspace, s, tests)
    if variant != 'missed_cpp':
        _migrate_cpp(workspace, s, tests, bypass=variant == 'cpp_node_bypass',
                     inline=variant == 'header_inline_helper')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('--seed', type=int, default=0, choices=sorted(SEEDS))
    parser.add_argument('--control', choices=CONTROLS,
                        help='oracle-control only: rewrite into this reference/negative variant')
    args = parser.parse_args()
    result = create(args.workspace, args.seed)
    if args.control:
        apply_control(args.workspace, args.seed, args.control)
    print(json.dumps({'workspace': str(args.workspace), 'control': args.control, **result}, indent=2))


if __name__ == '__main__':
    main()
