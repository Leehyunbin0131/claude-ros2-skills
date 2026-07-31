import os

import yaml
from launch import LaunchDescription
from launch_ros.actions import Node


def load_file(path):
    with open(path, "r") as f:
        return f.read()


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))

    urdf_path = os.path.join(pkg_dir, "arm.urdf")
    srdf_path = os.path.join(pkg_dir, "arm.srdf")

    robot_description = {"robot_description": load_file(urdf_path)}
    robot_description_semantic = {
        "robot_description_semantic": load_file(srdf_path)
    }
    robot_description_kinematics = {
        "robot_description_kinematics": load_yaml(
            os.path.join(pkg_dir, "kinematics.yaml")
        )
    }
    robot_description_planning = {
        "robot_description_planning": load_yaml(
            os.path.join(pkg_dir, "joint_limits.yaml")
        )
    }

    ompl_yaml = load_yaml(os.path.join(pkg_dir, "ompl_planning.yaml"))
    planning_pipeline_config = {
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": ompl_yaml,
    }

    trajectory_execution = {
        "moveit_manage_controllers": False,
        "allow_trajectory_execution": False,
    }

    planning_scene_monitor_parameters = {
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
        "publish_robot_description_semantic": True,
    }

    move_group_capabilities = {
        "capabilities": "",
        "disable_capabilities": "",
    }

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    joint_state_publisher_node = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        output="screen",
        arguments=[urdf_path],
        parameters=[{"rate": 20}],
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            planning_pipeline_config,
            trajectory_execution,
            planning_scene_monitor_parameters,
            move_group_capabilities,
            {"use_sim_time": False},
        ],
    )

    return LaunchDescription(
        [
            robot_state_publisher_node,
            joint_state_publisher_node,
            move_group_node,
        ]
    )
