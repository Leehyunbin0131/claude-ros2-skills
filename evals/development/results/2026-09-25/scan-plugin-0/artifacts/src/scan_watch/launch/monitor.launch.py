import math
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def build_parameters(params_file, limit):
    """Return the node parameter list: YAML first, explicit limit on top.

    An empty limit means "not supplied", so the YAML value stays in effect.
    """
    parameters = [params_file]
    limit = limit.strip()
    if limit:
        try:
            value = float(limit)
        except ValueError:
            raise ValueError(f"limit:={limit!r} is not a number") from None
        if math.isnan(value):
            raise ValueError('limit:=nan is not allowed')
        parameters.append({'limit': value})
    return parameters


def _launch_node(context):
    return [Node(
        package='scan_watch',
        executable='scan-watch',
        name='scan_watch',
        namespace=LaunchConfiguration('namespace'),
        output='screen',
        parameters=build_parameters(
            LaunchConfiguration('params_file').perform(context),
            LaunchConfiguration('limit').perform(context)),
    )]


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('scan_watch'), 'config', 'monitor.yaml')
    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace', default_value='',
            description='Namespace for the node and its scan/near_count topics'),
        DeclareLaunchArgument(
            'limit', default_value='',
            description='Override the limit [m]; empty uses params_file'),
        DeclareLaunchArgument(
            'params_file', default_value=default_params,
            description='Parameter YAML file (defaults to installed monitor.yaml)'),
        OpaqueFunction(function=_launch_node),
    ])
