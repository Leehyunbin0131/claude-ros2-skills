import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch_ros.actions import Node


def monitor_parameters(params_file, limit):
    """Parameters for the node: the YAML file, then an explicit limit if one was given."""
    parameters = [params_file]
    if limit.strip():
        try:
            parameters.append({'limit': float(limit)})
        except ValueError:
            raise RuntimeError(f"limit:='{limit}' is not a number") from None
    return parameters


def launch_setup(context):
    config = context.launch_configurations
    # Resolved at launch time so that edits to the installed YAML take effect.
    params_file = os.path.join(
        get_package_share_directory('scan_watch_v3'), 'config', 'monitor.yaml')
    return [Node(
        package='scan_watch_v3',
        executable='scan-watch',
        name='scan_watch_v3',
        namespace=config['namespace'],
        parameters=monitor_parameters(params_file, config['limit']),
        output='screen',
    )]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace', default_value='',
            description='Namespace for the node and its scan / near_count topics'),
        DeclareLaunchArgument(
            'limit', default_value='',
            description='Override the limit [m]; empty uses config/monitor.yaml'),
        OpaqueFunction(function=launch_setup),
    ])
