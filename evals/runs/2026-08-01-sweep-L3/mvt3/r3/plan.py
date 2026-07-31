#!/usr/bin/env python3
"""Add a collision object to the planning scene, verify it is there, then
request a joint-space motion plan for the 'arm' MoveIt planning group.

Prints:
    POINTS <n>   - number of points in the returned trajectory
    OBJECTS <m>  - number of collision objects in the planning scene
and exits 0 on success.
"""
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
JOINT_NAMES = ["joint1", "joint2", "joint3"]
JOINT_GOAL = [0.5, 0.3, -0.4]
BOX_ID = "box1"
SERVICE_TIMEOUT_SEC = 30.0
PLAN_TIMEOUT_SEC = 30.0


def make_box_collision_object() -> CollisionObject:
    obj = CollisionObject()
    obj.header.frame_id = "base_link"
    obj.id = BOX_ID

    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [0.1, 0.1, 0.1]
    obj.primitives = [primitive]

    pose = Pose()
    pose.position.x = 0.3
    pose.position.y = 0.0
    pose.position.z = 0.4
    pose.orientation.w = 1.0
    obj.primitive_poses = [pose]

    obj.operation = CollisionObject.ADD
    return obj


def main() -> int:
    rclpy.init()
    node = Node("plan_py")

    apply_scene_client = node.create_client(ApplyPlanningScene, "/apply_planning_scene")
    get_scene_client = node.create_client(GetPlanningScene, "/get_planning_scene")
    move_group_client = ActionClient(node, MoveGroup, "/move_action")

    if not apply_scene_client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_SEC):
        node.get_logger().error("apply_planning_scene service not available")
        rclpy.shutdown()
        return 1
    if not get_scene_client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_SEC):
        node.get_logger().error("get_planning_scene service not available")
        rclpy.shutdown()
        return 1
    if not move_group_client.wait_for_server(timeout_sec=SERVICE_TIMEOUT_SEC):
        node.get_logger().error("move_action action server not available")
        rclpy.shutdown()
        return 1

    # 1. Add a box collision object to the planning scene.
    scene = PlanningScene()
    scene.is_diff = True
    scene.world.collision_objects = [make_box_collision_object()]

    apply_req = ApplyPlanningScene.Request()
    apply_req.scene = scene
    future = apply_scene_client.call_async(apply_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=SERVICE_TIMEOUT_SEC)
    apply_resp = future.result()
    if apply_resp is None or not apply_resp.success:
        node.get_logger().error("Failed to apply planning scene diff")
        rclpy.shutdown()
        return 1

    # 2. Verify the scene contains the box we just added.
    get_req = GetPlanningScene.Request()
    get_req.components.components = (
        PlanningSceneComponents.WORLD_OBJECT_NAMES
        | PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
    )
    future = get_scene_client.call_async(get_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=SERVICE_TIMEOUT_SEC)
    get_resp = future.result()
    if get_resp is None:
        node.get_logger().error("Failed to get planning scene")
        rclpy.shutdown()
        return 1

    collision_objects = get_resp.scene.world.collision_objects
    object_ids = [obj.id for obj in collision_objects]
    if BOX_ID not in object_ids:
        node.get_logger().error(
            f"Collision object '{BOX_ID}' not found in planning scene; found {object_ids}"
        )
        rclpy.shutdown()
        return 1

    # 3. Request a motion plan to a joint-space goal for the 'arm' group.
    goal_constraints = Constraints()
    for name, value in zip(JOINT_NAMES, JOINT_GOAL):
        jc = JointConstraint()
        jc.joint_name = name
        jc.position = value
        jc.tolerance_above = 0.01
        jc.tolerance_below = 0.01
        jc.weight = 1.0
        goal_constraints.joint_constraints.append(jc)

    goal_msg = MoveGroup.Goal()
    goal_msg.request.group_name = GROUP_NAME
    goal_msg.request.pipeline_id = "ompl"
    goal_msg.request.planner_id = "RRTConnect"
    goal_msg.request.goal_constraints = [goal_constraints]
    goal_msg.request.num_planning_attempts = 5
    goal_msg.request.allowed_planning_time = 5.0
    goal_msg.request.max_velocity_scaling_factor = 0.5
    goal_msg.request.max_acceleration_scaling_factor = 0.5
    goal_msg.planning_options.plan_only = True

    send_goal_future = move_group_client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=PLAN_TIMEOUT_SEC)
    goal_handle = send_goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("Motion plan goal was rejected")
        rclpy.shutdown()
        return 1

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=PLAN_TIMEOUT_SEC)
    result_wrapper = result_future.result()
    if result_wrapper is None:
        node.get_logger().error("Did not receive a motion plan result")
        rclpy.shutdown()
        return 1

    result = result_wrapper.result
    if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
        node.get_logger().error(f"Motion planning failed with error code {result.error_code.val}")
        rclpy.shutdown()
        return 1

    points = result.planned_trajectory.joint_trajectory.points
    n_points = len(points)

    # Re-check the scene so the reported object count reflects current state.
    future = get_scene_client.call_async(get_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=SERVICE_TIMEOUT_SEC)
    get_resp = future.result()
    n_objects = len(get_resp.scene.world.collision_objects) if get_resp else len(collision_objects)

    print(f"POINTS {n_points}")
    print(f"OBJECTS {n_objects}")

    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
