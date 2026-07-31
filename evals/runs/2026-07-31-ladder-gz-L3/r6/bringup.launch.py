import os

from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
WORLD_PATH = os.path.join(THIS_DIR, 'world.sdf')
URDF_PATH = os.path.join(THIS_DIR, 'robot.urdf')
WORLD_NAME = 'default'
ROBOT_NAME = 'my_robot'

with open(URDF_PATH, 'r') as f:
    robot_description = f.read()


def generate_launch_description():
    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', '-s', '-r', '-v', '3', WORLD_PATH],
        output='screen',
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
    )

    # Publishes /robot_description onto the topic (not just the parameter),
    # which is what `ros_gz_sim create -topic robot_description` consumes.
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-world', WORLD_NAME,
            '-topic', 'robot_description',
            '-name', ROBOT_NAME,
            '-z', '0.5',
        ],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
        ],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        gz_sim,
        robot_state_publisher,
        # Give gz sim a few seconds to come up before spawning/bridging.
        TimerAction(period=5.0, actions=[spawn_robot, bridge]),
    ])
