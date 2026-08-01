import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')

    # Core nodes that make up the navigation stack. The local costmap lives
    # inside controller_server; everything else here just needs to reach the
    # ACTIVE lifecycle state alongside it.
    lifecycle_nodes = [
        'controller_server',
        'smoother_server',
        'planner_server',
        'behavior_server',
        'bt_navigator',
        'waypoint_follower',
        'velocity_smoother',
    ]

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(os.path.dirname(__file__), 'nav2_params.yaml'),
        description='Full path to the Nav2 parameters file to use for all launched nodes',
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true',
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically bring the Nav2 stack up to the active state',
    )

    def nav2_node(package, executable, name, remappings=None):
        return Node(
            package=package,
            executable=executable,
            name=name,
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            remappings=remappings or [],
        )

    # nav2 publishes the local costmap on two topics: 'costmap' (a
    # nav_msgs/OccupancyGrid whose values are compressed into 0-100 and can
    # never exceed 100) and 'costmap_raw' (a nav2_msgs/Costmap carrying the
    # true 0-255 cost values, e.g. LETHAL_OBSTACLE=254). We swap them so the
    # well-known 'local_costmap/costmap' name carries the raw cost data.
    controller_server_remappings = [
        ('/local_costmap/costmap', '/local_costmap/costmap_occupancy_grid'),
        ('/local_costmap/costmap_raw', '/local_costmap/costmap'),
    ]

    return LaunchDescription([
        declare_params_file_cmd,
        declare_use_sim_time_cmd,
        declare_autostart_cmd,
        nav2_node(
            'nav2_controller', 'controller_server', 'controller_server',
            remappings=controller_server_remappings,
        ),
        nav2_node('nav2_smoother', 'smoother_server', 'smoother_server'),
        nav2_node('nav2_planner', 'planner_server', 'planner_server'),
        nav2_node('nav2_behaviors', 'behavior_server', 'behavior_server'),
        nav2_node('nav2_bt_navigator', 'bt_navigator', 'bt_navigator'),
        nav2_node('nav2_waypoint_follower', 'waypoint_follower', 'waypoint_follower'),
        nav2_node('nav2_velocity_smoother', 'velocity_smoother', 'velocity_smoother'),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[{
                'autostart': autostart,
                'node_names': lifecycle_nodes,
                'use_sim_time': use_sim_time,
            }],
        ),
    ])
