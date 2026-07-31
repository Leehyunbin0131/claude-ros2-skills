import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.realpath(__file__))
    urdf_path = os.path.join(pkg_dir, "urdf", "test_robot.urdf")
    controllers_yaml = os.path.join(pkg_dir, "config", "controllers.yaml")

    with open(urdf_path, "r") as f:
        robot_description_content = f.read()

    robot_description = {"robot_description": robot_description_content}

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    controller_manager_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, controllers_yaml],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager-timeout", "30"],
        output="screen",
    )

    position_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["position_controller", "--controller-manager-timeout", "30"],
        output="screen",
    )

    return LaunchDescription(
        [
            robot_state_publisher_node,
            controller_manager_node,
            joint_state_broadcaster_spawner,
            position_controller_spawner,
        ]
    )
