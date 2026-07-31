import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    urdf_file = os.path.join(pkg_dir, "robot.urdf")
    controllers_file = os.path.join(pkg_dir, "controllers.yaml")

    with open(urdf_file, "r") as f:
        robot_description_content = f.read()

    robot_description = {"robot_description": robot_description_content}

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, controllers_file],
        output="screen",
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    position_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["position_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    return LaunchDescription([
        control_node,
        robot_state_publisher_node,
        joint_state_broadcaster_spawner,
        position_controller_spawner,
    ])
