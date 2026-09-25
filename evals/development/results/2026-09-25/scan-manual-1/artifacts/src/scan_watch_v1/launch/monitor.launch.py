import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _launch_node(context):
    params = [LaunchConfiguration('params_file').perform(context)]
    limit = LaunchConfiguration('limit').perform(context).strip()
    # Only an explicitly supplied limit overrides the YAML value.
    if limit:
        try:
            params.append({'limit': float(limit)})
        except ValueError:
            raise ValueError(f"limit:='{limit}' is not a number")
    return [Node(
        package='scan_watch_v1',
        executable='scan-watch',
        name='scan_watch_v1',
        namespace=LaunchConfiguration('namespace'),
        parameters=params,
        output='screen',
    )]


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('scan_watch_v1'), 'config', 'monitor.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='',
                              description='Namespace for the node and its scan/near_count topics'),
        DeclareLaunchArgument('params_file', default_value=default_params,
                              description='Parameter YAML file'),
        DeclareLaunchArgument('limit', default_value='',
                              description='Override the YAML limit [m]; empty keeps the YAML value'),
        OpaqueFunction(function=_launch_node),
    ])
