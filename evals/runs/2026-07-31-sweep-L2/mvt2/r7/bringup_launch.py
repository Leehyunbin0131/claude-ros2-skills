"""Launch description that brings up ros2_control + move_group for the simple 3-joint arm.

Self-contained: reads URDF/SRDF/yaml files directly from this directory, so it
does not need to be installed as an ament package.
"""
import os
import yaml

from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

HERE = os.path.dirname(os.path.abspath(__file__))


def load_file(path):
    with open(path, "r") as f:
        return f.read()


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def generate_launch_description():
    urdf_content = load_file(os.path.join(HERE, "urdf", "arm.urdf"))
    srdf_content = load_file(os.path.join(HERE, "srdf", "arm.srdf"))

    robot_description = {
        "robot_description": ParameterValue(urdf_content, value_type=str)
    }
    robot_description_semantic = {
        "robot_description_semantic": ParameterValue(srdf_content, value_type=str)
    }

    kinematics_yaml = load_yaml(os.path.join(HERE, "config", "kinematics.yaml"))
    robot_description_kinematics = {"robot_description_kinematics": kinematics_yaml}

    joint_limits_yaml = load_yaml(os.path.join(HERE, "config", "joint_limits.yaml"))
    robot_description_planning = {"robot_description_planning": joint_limits_yaml}

    ompl_yaml = load_yaml(os.path.join(HERE, "config", "ompl_planning.yaml"))
    planning_pipelines_config = {
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": ompl_yaml,
    }

    moveit_controllers_yaml = load_yaml(
        os.path.join(HERE, "config", "moveit_controllers.yaml")
    )
    trajectory_execution = {
        "moveit_manage_controllers": True,
        "trajectory_execution": {
            "allowed_execution_duration_scaling": 1.2,
            "allowed_goal_duration_margin": 0.5,
            "allowed_start_tolerance": 0.01,
        },
    }
    trajectory_execution.update(moveit_controllers_yaml)

    planning_scene_monitor_parameters = {
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
    }

    ros2_controllers_path = os.path.join(HERE, "config", "ros2_controllers.yaml")

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="screen",
        parameters=[robot_description, ros2_controllers_path],
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager-timeout",
            "60",
        ],
        output="screen",
    )

    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "arm_controller",
            "--controller-manager-timeout",
            "60",
        ],
        output="screen",
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
            planning_pipelines_config,
            trajectory_execution,
            planning_scene_monitor_parameters,
            {"use_sim_time": False},
        ],
    )

    return LaunchDescription(
        [
            robot_state_publisher_node,
            ros2_control_node,
            joint_state_broadcaster_spawner,
            arm_controller_spawner,
            move_group_node,
        ]
    )
