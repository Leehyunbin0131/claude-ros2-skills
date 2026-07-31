#!/usr/bin/env python3
"""Add a collision object to the planning scene, verify it, and plan a
joint-space motion for the 'arm' MoveIt planning group.

Prints:
    POINTS <n>   - number of points in the planned trajectory
    OBJECTS <m>  - number of collision objects in the planning scene
and exits 0 on success.
"""

import os
import sys
from pathlib import Path

_domain_id_file = Path(__file__).resolve().parent / ".ros_domain_id"
if _domain_id_file.exists():
    os.environ["ROS_DOMAIN_ID"] = _domain_id_file.read_text().strip()

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
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

GROUP_NAME = "arm"
PLANNING_FRAME = "world"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
JOINT_GOAL = [0.6, -0.4, 0.8]


def make_box_collision_object() -> CollisionObject:
    obj = CollisionObject()
    obj.header.frame_id = PLANNING_FRAME
    obj.id = "box1"

    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [0.1, 0.1, 0.1]

    pose = Pose()
    pose.position.x = 0.3
    pose.position.y = 0.0
    pose.position.z = 0.3
    pose.orientation.w = 1.0

    obj.primitives.append(primitive)
    obj.primitive_poses.append(pose)
    obj.operation = CollisionObject.ADD
    return obj


class PlanNode(Node):
    def __init__(self):
        super().__init__("plan_client")
        self.apply_scene_client = self.create_client(
            ApplyPlanningScene, "/apply_planning_scene"
        )
        self.get_scene_client = self.create_client(
            GetPlanningScene, "/get_planning_scene"
        )
        self.move_action_client = ActionClient(self, MoveGroup, "/move_action")

    def wait_for_services(self, timeout_sec=30.0):
        for client, name in (
            (self.apply_scene_client, "/apply_planning_scene"),
            (self.get_scene_client, "/get_planning_scene"),
        ):
            if not client.wait_for_service(timeout_sec=timeout_sec):
                raise RuntimeError(f"Service {name} not available")
        if not self.move_action_client.wait_for_server(timeout_sec=timeout_sec):
            raise RuntimeError("Action server /move_action not available")

    def add_box(self) -> bool:
        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects.append(make_box_collision_object())

        request = ApplyPlanningScene.Request()
        request.scene = scene

        future = self.apply_scene_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        response = future.result()
        return bool(response and response.success)

    def get_num_collision_objects(self) -> int:
        request = GetPlanningScene.Request()
        request.components.components = (
            PlanningSceneComponents.WORLD_OBJECT_NAMES
            | PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
        )
        future = self.get_scene_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        response = future.result()
        if response is None:
            return 0
        return len(response.scene.world.collision_objects)

    def plan_joint_goal(self):
        goal_msg = MoveGroup.Goal()
        goal_msg.request.group_name = GROUP_NAME
        goal_msg.request.num_planning_attempts = 10
        goal_msg.request.allowed_planning_time = 5.0
        goal_msg.request.max_velocity_scaling_factor = 1.0
        goal_msg.request.max_acceleration_scaling_factor = 1.0

        constraints = Constraints()
        for name, value in zip(JOINT_NAMES, JOINT_GOAL):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = value
            jc.tolerance_above = 0.001
            jc.tolerance_below = 0.001
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
        goal_msg.request.goal_constraints.append(constraints)

        goal_msg.planning_options.plan_only = True
        goal_msg.planning_options.planning_scene_diff.is_diff = True

        send_goal_future = self.move_action_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError("MoveGroup goal was rejected")

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result
        return result


def main():
    rclpy.init()
    node = PlanNode()
    try:
        node.wait_for_services()

        if not node.add_box():
            print("Failed to apply planning scene", file=sys.stderr)
            sys.exit(1)

        num_objects = node.get_num_collision_objects()
        if num_objects < 1:
            print("Planning scene does not contain the collision object", file=sys.stderr)
            sys.exit(1)

        result = node.plan_joint_goal()
        if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
            print(f"Planning failed with error code {result.error_code.val}", file=sys.stderr)
            sys.exit(1)

        num_points = len(result.planned_trajectory.joint_trajectory.points)

        print(f"POINTS {num_points}")
        print(f"OBJECTS {num_objects}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == "__main__":
    main()
