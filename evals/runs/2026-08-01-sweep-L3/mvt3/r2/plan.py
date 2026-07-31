#!/usr/bin/env python3
"""Add a collision box to the planning scene and plan a joint-space motion
for the 'arm' group served by the move_group started by bringup.sh."""

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import Pose
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    CollisionObject,
    Constraints,
    JointConstraint,
    PlanningScene,
    PlanningSceneComponents,
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene

GROUP_NAME = "arm"
BOX_ID = "box1"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
JOINT_GOAL = [0.6, 0.4, -0.5]


def make_box_collision_object():
    box = CollisionObject()
    box.header.frame_id = "base_link"
    box.id = BOX_ID

    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [0.1, 0.1, 0.1]

    pose = Pose()
    pose.position.x = 0.3
    pose.position.y = 0.0
    pose.position.z = 0.3
    pose.orientation.w = 1.0

    box.primitives = [primitive]
    box.primitive_poses = [pose]
    box.operation = CollisionObject.ADD
    return box


def main():
    rclpy.init()
    node = Node("plan_py")

    apply_scene_client = node.create_client(ApplyPlanningScene, "/apply_planning_scene")
    get_scene_client = node.create_client(GetPlanningScene, "/get_planning_scene")
    move_action_client = ActionClient(node, MoveGroup, "/move_action")

    if not apply_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("Service /apply_planning_scene not available")
        sys.exit(1)
    if not get_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("Service /get_planning_scene not available")
        sys.exit(1)
    if not move_action_client.wait_for_server(timeout_sec=30.0):
        node.get_logger().error("Action /move_action not available")
        sys.exit(1)

    # 1. Add a box collision object to the planning scene.
    apply_request = ApplyPlanningScene.Request()
    apply_request.scene = PlanningScene()
    apply_request.scene.is_diff = True
    apply_request.scene.world.collision_objects = [make_box_collision_object()]

    future = apply_scene_client.call_async(apply_request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=15.0)
    apply_response = future.result()
    if apply_response is None or not apply_response.success:
        node.get_logger().error("Failed to apply planning scene diff")
        sys.exit(1)

    # 2. Verify the scene contains the box.
    get_request = GetPlanningScene.Request()
    get_request.components = PlanningSceneComponents()
    get_request.components.components = (
        PlanningSceneComponents.WORLD_OBJECT_NAMES
        | PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
    )

    future = get_scene_client.call_async(get_request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=15.0)
    get_response = future.result()
    if get_response is None:
        node.get_logger().error("Failed to get planning scene")
        sys.exit(1)

    object_ids = [obj.id for obj in get_response.scene.world.collision_objects]
    if BOX_ID not in object_ids:
        node.get_logger().error(f"Box '{BOX_ID}' not found in planning scene: {object_ids}")
        sys.exit(1)

    # 3. Request a motion plan to a joint-space goal for the 'arm' group.
    goal_msg = MoveGroup.Goal()
    goal_msg.request.group_name = GROUP_NAME
    goal_msg.request.num_planning_attempts = 5
    goal_msg.request.allowed_planning_time = 10.0
    goal_msg.request.max_velocity_scaling_factor = 1.0
    goal_msg.request.max_acceleration_scaling_factor = 1.0
    goal_msg.request.start_state.is_diff = True

    constraints = Constraints()
    for name, position in zip(JOINT_NAMES, JOINT_GOAL):
        jc = JointConstraint()
        jc.joint_name = name
        jc.position = position
        jc.tolerance_above = 0.01
        jc.tolerance_below = 0.01
        jc.weight = 1.0
        constraints.joint_constraints.append(jc)
    goal_msg.request.goal_constraints = [constraints]

    goal_msg.planning_options.plan_only = True

    send_goal_future = move_action_client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=15.0)
    goal_handle = send_goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("Motion plan goal was rejected")
        sys.exit(1)

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=30.0)
    result_wrapper = result_future.result()
    if result_wrapper is None:
        node.get_logger().error("Did not receive a result for the motion plan")
        sys.exit(1)

    result = result_wrapper.result
    if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
        node.get_logger().error(f"Motion planning failed with error code {result.error_code.val}")
        sys.exit(1)

    points = result.planned_trajectory.joint_trajectory.points
    n_points = len(points)

    # 4. Report how many collision objects the planning scene reports.
    future = get_scene_client.call_async(get_request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=15.0)
    final_scene_response = future.result()
    n_objects = len(final_scene_response.scene.world.collision_objects)

    print(f"POINTS {n_points}")
    print(f"OBJECTS {n_objects}")

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
