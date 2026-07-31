"""Launch robot_state_publisher, ros2_control_node, controller spawners, and move_group
for the 3-joint 'arm' MoveIt 2 setup defined in config/."""

from pathlib import Path

from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

THIS_DIR = Path(__file__).resolve().parent


def build_moveit_config():
    return (
        MoveItConfigsBuilder("arm", package_name="arm_moveit_config")
        .robot_description(file_path="config/arm.urdf")
        .robot_description_semantic(file_path="config/arm.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(default_planning_pipeline="ompl", pipelines=["ompl"])
        .planning_scene_monitor(
            publish_robot_description=False,
            publish_robot_description_semantic=True,
        )
        .to_moveit_configs()
    )


def generate_launch_description():
    moveit_config = build_moveit_config()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[moveit_config.robot_description],
    )

    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[str(THIS_DIR / "config" / "ros2_controllers.yaml")],
        remappings=[
            ("/controller_manager/robot_description", "/robot_description"),
        ],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        output="screen",
    )

    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_controller"],
        output="screen",
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "publish_robot_description_semantic": True,
                "allow_trajectory_execution": True,
                "publish_planning_scene": True,
                "publish_geometry_updates": True,
                "publish_state_updates": True,
                "publish_transforms_updates": True,
            },
        ],
    )

    return LaunchDescription(
        [
            robot_state_publisher,
            ros2_control_node,
            joint_state_broadcaster_spawner,
            arm_controller_spawner,
            move_group_node,
        ]
    )
