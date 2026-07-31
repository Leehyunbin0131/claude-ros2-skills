#!/usr/bin/env python3
"""Add a collision object to the MoveIt planning scene, plan a joint-space
motion for the 'arm' group, and report the trajectory/scene sizes."""

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
JOINT_GOAL = {"joint1": 0.8, "joint2": 0.6, "joint3": -0.6}
SERVICE_TIMEOUT_SEC = 30.0


class PlanClient(Node):
    def __init__(self):
        super().__init__("plan_py")
        self.apply_scene_client = self.create_client(
            ApplyPlanningScene, "/apply_planning_scene"
        )
        self.get_scene_client = self.create_client(
            GetPlanningScene, "/get_planning_scene"
        )
        self.move_action_client = ActionClient(self, MoveGroup, "/move_action")

    def wait_ready(self):
        if not self.apply_scene_client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_SEC):
            raise RuntimeError("/apply_planning_scene service not available")
        if not self.get_scene_client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_SEC):
            raise RuntimeError("/get_planning_scene service not available")
        if not self.move_action_client.wait_for_server(timeout_sec=SERVICE_TIMEOUT_SEC):
            raise RuntimeError("/move_action action server not available")

    def add_box(self):
        box = CollisionObject()
        box.header.frame_id = PLANNING_FRAME
        box.id = BOX_ID
        box.operation = CollisionObject.ADD

        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [0.2, 0.2, 0.2]
        box.primitives = [primitive]

        pose = Pose()
        pose.position.x = 1.5
        pose.position.y = 1.5
        pose.position.z = 0.5
        pose.orientation.w = 1.0
        box.primitive_poses = [pose]

        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects = [box]

        request = ApplyPlanningScene.Request()
        request.scene = scene

        future = self.apply_scene_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=SERVICE_TIMEOUT_SEC)
        response = future.result()
        if response is None or not response.success:
            raise RuntimeError("failed to apply planning scene diff")

    def get_object_count(self):
        request = GetPlanningScene.Request()
        request.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES

        future = self.get_scene_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=SERVICE_TIMEOUT_SEC)
        response = future.result()
        if response is None:
            raise RuntimeError("failed to get planning scene")

        objects = response.scene.world.collision_objects
        ids = [obj.id for obj in objects]
        if BOX_ID not in ids:
            raise RuntimeError(f"box '{BOX_ID}' not found in planning scene: {ids}")
        return len(objects)

    def plan_joint_goal(self):
        goal_constraints = Constraints()
        for name, value in JOINT_GOAL.items():
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = value
            jc.tolerance_above = 0.01
            jc.tolerance_below = 0.01
            jc.weight = 1.0
            goal_constraints.joint_constraints.append(jc)

        goal_msg = MoveGroup.Goal()
        goal_msg.request.group_name = GROUP_NAME
        goal_msg.request.num_planning_attempts = 5
        goal_msg.request.allowed_planning_time = 5.0
        goal_msg.request.max_velocity_scaling_factor = 1.0
        goal_msg.request.max_acceleration_scaling_factor = 1.0
        goal_msg.request.goal_constraints = [goal_constraints]
        goal_msg.planning_options.plan_only = True

        send_future = self.move_action_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=SERVICE_TIMEOUT_SEC)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError("move_group rejected the planning goal")

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=SERVICE_TIMEOUT_SEC)
        result_wrapper = result_future.result()
        if result_wrapper is None:
            raise RuntimeError("no result received from /move_action")

        result = result_wrapper.result
        if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
            raise RuntimeError(f"planning failed with error code {result.error_code.val}")

        return result.planned_trajectory.joint_trajectory.points


def main():
    rclpy.init()
    node = PlanClient()
    try:
        node.wait_ready()
        node.add_box()
        num_objects = node.get_object_count()
        points = node.plan_joint_goal()

        print(f"POINTS {len(points)}")
        print(f"OBJECTS {num_objects}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
