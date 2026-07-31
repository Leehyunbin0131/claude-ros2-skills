#!/usr/bin/env python3
"""Exercise the simple_arm MoveIt 2 setup started by bringup.sh.

1. Adds a box collision object to the planning scene.
2. Verifies (via /get_planning_scene) that the scene contains it.
3. Requests a motion plan to a joint-space goal for the 'arm' group.
4. Prints "POINTS <n>" (trajectory point count) then "OBJECTS <m>"
   (collision object count reported by the planning scene).
"""
import sys

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    CollisionObject,
    Constraints,
    JointConstraint,
    PlanningScene,
    PlanningSceneWorld,
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene
from moveit_msgs.msg import PlanningSceneComponents
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

PLANNING_FRAME = "base_link"
GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
GOAL_POSITIONS = [0.6, -0.4, 0.5]
BOX_ID = "box1"

SERVICE_TIMEOUT_SEC = 30.0
ACTION_TIMEOUT_SEC = 30.0


def make_box_collision_object() -> CollisionObject:
    box = CollisionObject()
    box.header.frame_id = PLANNING_FRAME
    box.id = BOX_ID
    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [0.1, 0.1, 0.1]
    box.primitives = [primitive]
    pose = Pose()
    pose.position.x = 0.5
    pose.position.y = 0.3
    pose.position.z = 0.2
    pose.orientation.w = 1.0
    box.primitive_poses = [pose]
    box.operation = CollisionObject.ADD
    return box


def main() -> int:
    rclpy.init()
    node = Node("plan_client")

    apply_scene_client = node.create_client(
        ApplyPlanningScene, "/apply_planning_scene"
    )
    get_scene_client = node.create_client(GetPlanningScene, "/get_planning_scene")
    move_action_client = ActionClient(node, MoveGroup, "/move_action")

    if not apply_scene_client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_SEC):
        node.get_logger().error("/apply_planning_scene service not available")
        return 1
    if not get_scene_client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_SEC):
        node.get_logger().error("/get_planning_scene service not available")
        return 1
    if not move_action_client.wait_for_server(timeout_sec=ACTION_TIMEOUT_SEC):
        node.get_logger().error("/move_action action server not available")
        return 1

    # 1. Add a box collision object to the planning scene.
    scene_diff = PlanningScene()
    scene_diff.is_diff = True
    scene_diff.world = PlanningSceneWorld(collision_objects=[make_box_collision_object()])

    apply_req = ApplyPlanningScene.Request(scene=scene_diff)
    future = apply_scene_client.call_async(apply_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=SERVICE_TIMEOUT_SEC)
    apply_resp = future.result()
    if apply_resp is None or not apply_resp.success:
        node.get_logger().error("Failed to apply planning scene diff")
        return 1

    # 2. Verify the scene contains it.
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
        return 1

    collision_objects = get_resp.scene.world.collision_objects
    object_ids = [obj.id for obj in collision_objects]
    if BOX_ID not in object_ids:
        node.get_logger().error(
            f"Box '{BOX_ID}' not found in planning scene, got: {object_ids}"
        )
        return 1

    # 3. Request a motion plan to a joint-space goal for the 'arm' group.
    goal_msg = MoveGroup.Goal()
    goal_msg.request.group_name = GROUP_NAME
    goal_msg.request.planner_id = ""
    goal_msg.request.num_planning_attempts = 5
    goal_msg.request.allowed_planning_time = 10.0
    goal_msg.request.max_velocity_scaling_factor = 1.0
    goal_msg.request.max_acceleration_scaling_factor = 1.0

    joint_constraints = [
        JointConstraint(
            joint_name=name,
            position=pos,
            tolerance_above=0.01,
            tolerance_below=0.01,
            weight=1.0,
        )
        for name, pos in zip(JOINT_NAMES, GOAL_POSITIONS)
    ]
    goal_msg.request.goal_constraints = [Constraints(joint_constraints=joint_constraints)]

    goal_msg.planning_options.plan_only = True
    goal_msg.planning_options.planning_scene_diff.is_diff = True
    goal_msg.planning_options.planning_scene_diff.robot_state.is_diff = True

    send_goal_future = move_action_client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=ACTION_TIMEOUT_SEC)
    goal_handle = send_goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("Motion plan goal was rejected")
        return 1

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=ACTION_TIMEOUT_SEC)
    result_wrapper = result_future.result()
    if result_wrapper is None:
        node.get_logger().error("No result received from move_action")
        return 1

    result = result_wrapper.result
    if result.error_code.val != 1:  # MoveItErrorCodes.SUCCESS
        node.get_logger().error(f"Planning failed with error code {result.error_code.val}")
        return 1

    num_points = len(result.planned_trajectory.joint_trajectory.points)
    num_objects = len(collision_objects)

    print(f"POINTS {num_points}")
    print(f"OBJECTS {num_objects}")

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
