#!/usr/bin/env python3
"""Add a collision object, verify it, plan a joint-space goal for the "arm"
group, and report the results.

Talks directly to move_group's ROS 2 interfaces (no moveit_py dependency):
  - /apply_planning_scene (moveit_msgs/srv/ApplyPlanningScene) to add a box
  - /get_planning_scene   (moveit_msgs/srv/GetPlanningScene) to verify it
  - /move_action          (moveit_msgs/action/MoveGroup) to request a plan
"""

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    CollisionObject,
    Constraints,
    JointConstraint,
    PlanningScene,
    PlanningSceneComponents,
    MotionPlanRequest,
    PlanningOptions,
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
GOAL_POSITIONS = [0.6, 0.4, -0.5]


def make_box_collision_object() -> CollisionObject:
    obj = CollisionObject()
    obj.header.frame_id = "world"
    obj.id = "box1"

    box = SolidPrimitive()
    box.type = SolidPrimitive.BOX
    box.dimensions = [0.1, 0.1, 0.1]
    obj.primitives = [box]

    pose = Pose()
    pose.position.x = 0.3
    pose.position.y = 0.0
    pose.position.z = 0.5
    pose.orientation.w = 1.0
    obj.primitive_poses = [pose]

    obj.operation = CollisionObject.ADD
    return obj


def main():
    rclpy.init()
    node = Node("plan_py")

    apply_scene_client = node.create_client(
        ApplyPlanningScene, "/apply_planning_scene"
    )
    get_scene_client = node.create_client(GetPlanningScene, "/get_planning_scene")

    if not apply_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("apply_planning_scene service not available")
        rclpy.shutdown()
        sys.exit(1)
    if not get_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("get_planning_scene service not available")
        rclpy.shutdown()
        sys.exit(1)

    # 1. Add a box collision object to the planning scene.
    scene = PlanningScene()
    scene.is_diff = True
    scene.world.collision_objects = [make_box_collision_object()]

    apply_req = ApplyPlanningScene.Request()
    apply_req.scene = scene
    future = apply_scene_client.call_async(apply_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
    if future.result() is None or not future.result().success:
        node.get_logger().error("Failed to apply planning scene diff")
        rclpy.shutdown()
        sys.exit(1)

    # 2. Verify the scene contains it.
    get_req = GetPlanningScene.Request()
    get_req.components.components = PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
    future = get_scene_client.call_async(get_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
    result = future.result()
    if result is None:
        node.get_logger().error("Failed to get planning scene")
        rclpy.shutdown()
        sys.exit(1)

    collision_objects = result.scene.world.collision_objects
    object_ids = [o.id for o in collision_objects]
    if "box1" not in object_ids:
        node.get_logger().error(
            f"box1 not found in planning scene, got: {object_ids}"
        )
        rclpy.shutdown()
        sys.exit(1)

    num_objects = len(collision_objects)

    # 3. Request a motion plan to a joint-space goal for the "arm" group.
    action_client = ActionClient(node, MoveGroup, "/move_action")
    if not action_client.wait_for_server(timeout_sec=30.0):
        node.get_logger().error("move_action action server not available")
        rclpy.shutdown()
        sys.exit(1)

    goal_constraints = Constraints()
    for name, position in zip(JOINT_NAMES, GOAL_POSITIONS):
        jc = JointConstraint()
        jc.joint_name = name
        jc.position = position
        jc.tolerance_above = 0.001
        jc.tolerance_below = 0.001
        jc.weight = 1.0
        goal_constraints.joint_constraints.append(jc)

    request = MotionPlanRequest()
    request.group_name = GROUP_NAME
    request.goal_constraints = [goal_constraints]
    request.num_planning_attempts = 10
    request.allowed_planning_time = 5.0
    request.max_velocity_scaling_factor = 1.0
    request.max_acceleration_scaling_factor = 1.0

    planning_options = PlanningOptions()
    planning_options.plan_only = True
    planning_options.planning_scene_diff.is_diff = True

    goal_msg = MoveGroup.Goal()
    goal_msg.request = request
    goal_msg.planning_options = planning_options

    send_goal_future = action_client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=15.0)
    goal_handle = send_goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("Motion plan goal was rejected")
        rclpy.shutdown()
        sys.exit(1)

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=15.0)
    action_result = result_future.result()
    if action_result is None:
        node.get_logger().error("Timed out waiting for plan result")
        rclpy.shutdown()
        sys.exit(1)

    move_result = action_result.result
    if move_result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes SUCCESS
        node.get_logger().error(
            f"Planning failed with error code {move_result.error_code.val}"
        )
        rclpy.shutdown()
        sys.exit(1)

    num_points = len(move_result.planned_trajectory.joint_trajectory.points)

    print(f"POINTS {num_points}")
    print(f"OBJECTS {num_objects}")

    rclpy.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
