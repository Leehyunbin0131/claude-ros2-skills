#!/usr/bin/env python3
"""Add a collision object, verify it, and plan a joint-space motion for the 'arm' group."""
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import Pose
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.msg import (
    CollisionObject,
    PlanningScene,
    PlanningSceneComponents,
    Constraints,
    JointConstraint,
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene
from moveit_msgs.action import MoveGroup

GROUP_NAME = "arm"
PLANNING_FRAME = "base_link"
BOX_ID = "box1"

# Joint-space goal (radians), well within the URDF joint limits.
JOINT_GOAL = {
    "joint1": 0.6,
    "joint2": 0.4,
    "joint3": -0.5,
}


def make_box_collision_object() -> CollisionObject:
    obj = CollisionObject()
    obj.header.frame_id = PLANNING_FRAME
    obj.id = BOX_ID
    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [0.1, 0.1, 0.1]
    pose = Pose()
    pose.position.x = 0.3
    pose.position.y = 0.3
    pose.position.z = 0.5
    pose.orientation.w = 1.0
    obj.primitives.append(primitive)
    obj.primitive_poses.append(pose)
    obj.operation = CollisionObject.ADD
    return obj


def main() -> int:
    rclpy.init()
    node = Node("plan_py")

    apply_scene_client = node.create_client(ApplyPlanningScene, "/apply_planning_scene")
    get_scene_client = node.create_client(GetPlanningScene, "/get_planning_scene")
    move_action_client = ActionClient(node, MoveGroup, "/move_action")

    if not apply_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("apply_planning_scene service not available")
        return 1
    if not get_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("get_planning_scene service not available")
        return 1
    if not move_action_client.wait_for_server(timeout_sec=30.0):
        node.get_logger().error("move_action action server not available")
        return 1

    # 1. Add a box collision object to the planning scene.
    scene = PlanningScene()
    scene.is_diff = True
    scene.world.collision_objects.append(make_box_collision_object())

    apply_req = ApplyPlanningScene.Request()
    apply_req.scene = scene
    future = apply_scene_client.call_async(apply_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
    if future.result() is None or not future.result().success:
        node.get_logger().error("Failed to apply planning scene diff")
        return 1

    # 2. Verify the scene contains the box.
    components = PlanningSceneComponents()
    components.components = (
        PlanningSceneComponents.WORLD_OBJECT_NAMES
        | PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
    )
    get_req = GetPlanningScene.Request()
    get_req.components = components
    future = get_scene_client.call_async(get_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
    result = future.result()
    if result is None:
        node.get_logger().error("Failed to get planning scene")
        return 1

    object_ids = [obj.id for obj in result.scene.world.collision_objects]
    if BOX_ID not in object_ids:
        node.get_logger().error(f"Box '{BOX_ID}' not found in planning scene: {object_ids}")
        return 1

    # 3. Request a motion plan to a joint-space goal for the 'arm' group.
    goal_msg = MoveGroup.Goal()
    goal_msg.request.group_name = GROUP_NAME
    goal_msg.request.num_planning_attempts = 10
    goal_msg.request.allowed_planning_time = 10.0
    goal_msg.request.max_velocity_scaling_factor = 1.0
    goal_msg.request.max_acceleration_scaling_factor = 1.0

    constraints = Constraints()
    for joint_name, position in JOINT_GOAL.items():
        jc = JointConstraint()
        jc.joint_name = joint_name
        jc.position = position
        jc.tolerance_above = 0.001
        jc.tolerance_below = 0.001
        jc.weight = 1.0
        constraints.joint_constraints.append(jc)
    goal_msg.request.goal_constraints.append(constraints)

    goal_msg.planning_options.plan_only = True
    goal_msg.planning_options.planning_scene_diff.is_diff = True
    goal_msg.planning_options.planning_scene_diff.robot_state.is_diff = True

    send_goal_future = move_action_client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=15.0)
    goal_handle = send_goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("Motion plan goal was rejected")
        return 1

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=30.0)
    action_result = result_future.result()
    if action_result is None:
        node.get_logger().error("Did not receive a planning result")
        return 1

    move_result = action_result.result
    if move_result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
        node.get_logger().error(f"Planning failed with error code {move_result.error_code.val}")
        return 1

    n_points = len(move_result.planned_trajectory.joint_trajectory.points)
    m_objects = len(object_ids)

    print(f"POINTS {n_points}")
    print(f"OBJECTS {m_objects}")

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
