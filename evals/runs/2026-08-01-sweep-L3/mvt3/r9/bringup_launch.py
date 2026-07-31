#!/usr/bin/env python3
"""Launch description for the simple_arm MoveIt 2 setup.

Starts robot_state_publisher (TF), a fake joint_states publisher
(so MoveIt always has a complete current robot state), and move_group
configured with the 'arm' planning group over the OMPL pipeline.
No trajectory execution / controllers are configured since this setup
is only used for motion planning (plan_only requests).
"""
import sys
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

PKG_DIR = Path(__file__).resolve().parent


def load_file(path: Path) -> str:
    with open(path, "r") as f:
        return f.read()


def load_yaml(path: Path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def generate_launch_description():
    robot_description = {"robot_description": load_file(PKG_DIR / "arm.urdf")}
    robot_description_semantic = {
        "robot_description_semantic": load_file(PKG_DIR / "arm.srdf")
    }

    robot_description_kinematics = {
        "robot_description_kinematics": load_yaml(
            PKG_DIR / "config" / "kinematics.yaml"
        )
    }

    robot_description_planning = {
        "robot_description_planning": load_yaml(
            PKG_DIR / "config" / "joint_limits.yaml"
        )
    }

    ompl_yaml = load_yaml(PKG_DIR / "config" / "ompl_planning.yaml")
    # Pull in the stock planner type definitions (RRTConnect, etc.) that ship
    # with moveit_configs_utils, same as MoveItConfigsBuilder does by default.
    defaults_path = (
        Path(get_package_share_directory("moveit_configs_utils"))
        / "default_configs"
        / "ompl_defaults.yaml"
    )
    if "planner_configs" not in ompl_yaml:
        ompl_yaml.update(load_yaml(defaults_path))

    planning_pipelines = {
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": ompl_yaml,
    }

    move_group_configuration = {
        "publish_robot_description_semantic": True,
        # Planning-only setup: no controllers/trajectory execution configured.
        "allow_trajectory_execution": False,
        "capabilities": "",
        "disable_capabilities": "",
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
        "monitor_dynamics": False,
    }

    move_group_params = [
        robot_description,
        robot_description_semantic,
        robot_description_kinematics,
        robot_description_planning,
        planning_pipelines,
        move_group_configuration,
    ]

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=move_group_params,
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    fake_joint_states = ExecuteProcess(
        cmd=[sys.executable, str(PKG_DIR / "joint_state_publisher_node.py")],
        output="screen",
    )

    return LaunchDescription(
        [robot_state_publisher_node, fake_joint_states, move_group_node]
    )
