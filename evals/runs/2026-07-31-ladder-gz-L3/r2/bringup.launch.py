import os

from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node

THIS_DIR = os.path.dirname(os.path.realpath(__file__))


def generate_launch_description():
    urdf_path = os.path.join(THIS_DIR, 'robot.urdf')
    world_path = os.path.join(THIS_DIR, 'world.sdf')

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    # Start Gazebo (server only, unpaused) with our world.
    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', '-v', '2', world_path],
        output='screen',
    )

    # Publishes /robot_description (and /tf) from the URDF, using sim time.
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
    )

    # Bridges Gazebo's /clock and /imu topics into ROS 2.
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

    # Spawns the robot (read from /robot_description) into the running world.
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-world', 'default',
            '-topic', 'robot_description',
            '-name', 'my_robot',
            '-z', '0.5',
        ],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        gz_sim,
        robot_state_publisher,
        bridge,
        # Give Gazebo a few seconds to come up before asking it to spawn.
        TimerAction(period=5.0, actions=[spawn]),
    ])
