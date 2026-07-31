#!/usr/bin/env python3
"""Add a collision box to the MoveIt planning scene, verify it is there, plan a
joint-space motion for the 'arm' group, and report the result.

Requires `bash bringup.sh` to have already started move_group (see
launch/bringup_launch.py).
"""

import sys

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
    PlanningScene,
    PlanningSceneWorld,
    PlanningSceneComponents,
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose
from sensor_msgs.msg import JointState

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
BOX_ID = "box1"


def make_box_collision_object():
    box = CollisionObject()
    box.header.frame_id = "world"
    box.id = BOX_ID
    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [0.1, 0.1, 0.1]
    box.primitives = [primitive]
    pose = Pose()
    pose.position.x = 0.5
    pose.position.y = 0.0
    pose.position.z = 0.1
    pose.orientation.w = 1.0
    box.primitive_poses = [pose]
    box.operation = CollisionObject.ADD
    return box


def main():
    rclpy.init()
    node = Node("plan_py")

    # --- Add a box collision object to the planning scene ---
    apply_scene_client = node.create_client(
        ApplyPlanningScene, "/apply_planning_scene"
    )
    if not apply_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("apply_planning_scene service not available")
        rclpy.shutdown()
        sys.exit(1)

    scene = PlanningScene()
    scene.is_diff = True
    scene.world = PlanningSceneWorld(collision_objects=[make_box_collision_object()])

    apply_req = ApplyPlanningScene.Request()
    apply_req.scene = scene
    future = apply_scene_client.call_async(apply_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=30.0)
    apply_result = future.result()
    if apply_result is None or not apply_result.success:
        node.get_logger().error("Failed to apply planning scene diff")
        rclpy.shutdown()
        sys.exit(1)

    # --- Verify the scene contains the box ---
    get_scene_client = node.create_client(GetPlanningScene, "/get_planning_scene")
    if not get_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("get_planning_scene service not available")
        rclpy.shutdown()
        sys.exit(1)

    get_req = GetPlanningScene.Request()
    get_req.components.components = (
        PlanningSceneComponents.WORLD_OBJECT_NAMES
        | PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
    )
    future = get_scene_client.call_async(get_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=30.0)
    get_result = future.result()
    if get_result is None:
        node.get_logger().error("Failed to get planning scene")
        rclpy.shutdown()
        sys.exit(1)

    collision_objects = get_result.scene.world.collision_objects
    object_ids = [obj.id for obj in collision_objects]
    if BOX_ID not in object_ids:
        node.get_logger().error(
            f"Planning scene does not contain '{BOX_ID}', found: {object_ids}"
        )
        rclpy.shutdown()
        sys.exit(1)
    num_objects = len(collision_objects)

    # --- Request a joint-space motion plan for the 'arm' group ---
    action_client = ActionClient(node, MoveGroup, "/move_action")
    if not action_client.wait_for_server(timeout_sec=30.0):
        node.get_logger().error("/move_action server not available")
        rclpy.shutdown()
        sys.exit(1)

    goal_positions = [0.8, 0.4, -0.5]

    joint_constraints = [
        JointConstraint(
            joint_name=name,
            position=pos,
            tolerance_above=0.001,
            tolerance_below=0.001,
            weight=1.0,
        )
        for name, pos in zip(JOINT_NAMES, goal_positions)
    ]

    motion_request = MotionPlanRequest()
    motion_request.group_name = GROUP_NAME
    motion_request.goal_constraints = [Constraints(joint_constraints=joint_constraints)]
    motion_request.start_state.joint_state = JointState(
        name=JOINT_NAMES, position=[0.0, 0.0, 0.0]
    )
    motion_request.start_state.is_diff = False
    motion_request.num_planning_attempts = 10
    motion_request.allowed_planning_time = 10.0
    motion_request.max_velocity_scaling_factor = 1.0
    motion_request.max_acceleration_scaling_factor = 1.0

    planning_options = PlanningOptions()
    planning_options.plan_only = True

    goal_msg = MoveGroup.Goal()
    goal_msg.request = motion_request
    goal_msg.planning_options = planning_options

    send_goal_future = action_client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=30.0)
    goal_handle = send_goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("MoveGroup goal was rejected")
        rclpy.shutdown()
        sys.exit(1)

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=30.0)
    action_result = result_future.result()
    if action_result is None:
        node.get_logger().error("Did not receive a result from move_group")
        rclpy.shutdown()
        sys.exit(1)

    result = action_result.result
    if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
        node.get_logger().error(f"Motion planning failed with error code {result.error_code.val}")
        rclpy.shutdown()
        sys.exit(1)

    num_points = len(result.planned_trajectory.joint_trajectory.points)

    print(f"POINTS {num_points}")
    print(f"OBJECTS {num_objects}")

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
