#!/usr/bin/env python3
"""Exercise the simple_arm MoveIt 2 setup:

1. Add a box collision object to the planning scene.
2. Verify (via GetPlanningScene) that the scene actually contains it.
3. Request a motion plan to a joint-space goal for the 'arm' group.
4. Print POINTS <n> (trajectory waypoint count) and OBJECTS <m> (collision
   object count reported by the planning scene), then exit 0.
"""
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    CollisionObject,
    PlanningScene,
    PlanningSceneWorld,
    PlanningSceneComponents,
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose


GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
JOINT_GOAL = [0.6, 0.4, -0.3]
PLANNING_FRAME = "world"


def make_box_collision_object():
    obj = CollisionObject()
    obj.header.frame_id = PLANNING_FRAME
    obj.id = "box1"

    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [0.2, 0.2, 0.2]

    pose = Pose()
    pose.position.x = 1.0
    pose.position.y = 1.0
    pose.position.z = 0.3
    pose.orientation.w = 1.0

    obj.primitives = [primitive]
    obj.primitive_poses = [pose]
    obj.operation = CollisionObject.ADD
    return obj


def main():
    rclpy.init()
    node = Node("plan_py")

    apply_scene_client = node.create_client(ApplyPlanningScene, "apply_planning_scene")
    get_scene_client = node.create_client(GetPlanningScene, "get_planning_scene")
    move_action_client = ActionClient(node, MoveGroup, "move_action")

    if not apply_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("apply_planning_scene service not available")
        sys.exit(1)
    if not get_scene_client.wait_for_service(timeout_sec=30.0):
        node.get_logger().error("get_planning_scene service not available")
        sys.exit(1)

    # 1. Add a box collision object to the planning scene.
    scene_diff = PlanningScene()
    scene_diff.is_diff = True
    scene_diff.world = PlanningSceneWorld(collision_objects=[make_box_collision_object()])

    apply_req = ApplyPlanningScene.Request()
    apply_req.scene = scene_diff
    future = apply_scene_client.call_async(apply_req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
    if future.result() is None or not future.result().success:
        node.get_logger().error("apply_planning_scene call failed")
        sys.exit(1)

    # 2. Verify the scene contains it (retry briefly for propagation).
    num_objects = 0
    object_ids = []
    for _ in range(20):
        get_req = GetPlanningScene.Request()
        get_req.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
        future = get_scene_client.call_async(get_req)
        rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
        result = future.result()
        if result is not None:
            object_ids = [o.id for o in result.scene.world.collision_objects]
            num_objects = len(object_ids)
            if "box1" in object_ids:
                break
        time.sleep(0.5)

    if "box1" not in object_ids:
        node.get_logger().error(f"box1 not found in planning scene; objects={object_ids}")
        sys.exit(1)

    # 3. Request a motion plan to a joint-space goal for the 'arm' group.
    if not move_action_client.wait_for_server(timeout_sec=60.0):
        node.get_logger().error("move_action server not available")
        sys.exit(1)

    joint_constraints = [
        JointConstraint(
            joint_name=name,
            position=pos,
            tolerance_above=0.001,
            tolerance_below=0.001,
            weight=1.0,
        )
        for name, pos in zip(JOINT_NAMES, JOINT_GOAL)
    ]

    goal_msg = MoveGroup.Goal()
    goal_msg.request.group_name = GROUP_NAME
    goal_msg.request.goal_constraints = [Constraints(joint_constraints=joint_constraints)]
    goal_msg.request.num_planning_attempts = 5
    goal_msg.request.allowed_planning_time = 10.0
    goal_msg.request.max_velocity_scaling_factor = 1.0
    goal_msg.request.max_acceleration_scaling_factor = 1.0
    goal_msg.planning_options.plan_only = True

    send_goal_future = move_action_client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=15.0)
    goal_handle = send_goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("MoveGroup goal was rejected")
        sys.exit(1)

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=30.0)
    action_result = result_future.result()
    if action_result is None:
        node.get_logger().error("MoveGroup action did not return a result")
        sys.exit(1)

    move_result = action_result.result
    if move_result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes SUCCESS
        node.get_logger().error(f"Planning failed with error code {move_result.error_code.val}")
        sys.exit(1)

    num_points = len(move_result.planned_trajectory.joint_trajectory.points)

    print(f"POINTS {num_points}")
    print(f"OBJECTS {num_objects}")

    rclpy.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
