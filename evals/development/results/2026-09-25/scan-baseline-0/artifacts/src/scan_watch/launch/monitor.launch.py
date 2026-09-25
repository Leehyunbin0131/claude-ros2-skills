import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _parse_limit(text):
    try:
        return float(text)
    except ValueError:
        raise RuntimeError(f"limit:= must be a number, got '{text}'") from None


def _launch_setup(context):
    params = [os.path.join(get_package_share_directory('scan_watch'), 'config', 'monitor.yaml')]
    limit = LaunchConfiguration('limit').perform(context).strip()
    # Only override the YAML value when limit:= was explicitly supplied.
    if limit:
        params.append({'limit': _parse_limit(limit)})
    return [Node(
        package='scan_watch',
        executable='scan-watch',
        name='scan_watch',
        namespace=LaunchConfiguration('namespace'),
        parameters=params,
        output='screen',
    )]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='',
                              description='Namespace for the node and its topics'),
        DeclareLaunchArgument('limit', default_value='',
                              description='Override for the limit in config/monitor.yaml'),
        OpaqueFunction(function=_launch_setup),
    ])
