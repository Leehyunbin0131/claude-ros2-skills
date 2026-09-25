import math
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _node(context):
    params_file = LaunchConfiguration('params_file').perform(context)
    parameters = [params_file]
    # An omitted or empty limit:= leaves the YAML value in effect.
    limit = LaunchConfiguration('limit').perform(context).strip()
    if limit:
        try:
            value = float(limit)
        except ValueError:
            value = math.nan
        if not math.isfinite(value):
            raise RuntimeError(f"limit:='{limit}' is not a finite number")
        parameters.append({'limit': value})
    return [Node(
        package='scan_watch_v2',
        executable='scan-watch',
        name='scan_watch_v2',
        namespace=LaunchConfiguration('namespace'),
        parameters=parameters,
        output='screen',
    )]


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('scan_watch_v2'), 'config', 'monitor.yaml')
    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace', default_value='',
            description='Namespace for the node and its relative scan/near_count topics'),
        DeclareLaunchArgument(
            'limit', default_value='',
            description='Override the limit [m] from params_file; empty keeps the YAML value'),
        DeclareLaunchArgument(
            'params_file', default_value=default_params,
            description='Parameter YAML for the node'),
        OpaqueFunction(function=_node),
    ])
