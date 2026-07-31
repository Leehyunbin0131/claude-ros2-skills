#!/usr/bin/env python3
"""Add a collision object, verify it, and plan a joint-space goal for the 'arm' group."""
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    CollisionObject,
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
    PlanningScene,
    PlanningSceneComponents,
)
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene
from shape_msgs.msg import SolidPrimitive

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
JOINT_GOAL = [0.6, -0.4, 0.5]
BOX_ID = "box1"


def make_box_collision_object() -> CollisionObject:
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

    box.primitives.append(primitive)
    box.primitive_poses.append(pose)
    box.operation = CollisionObject.ADD
    return box


class PlanClient(Node):
    def __init__(self):
        super().__init__("plan_py_client")
        self.apply_scene_client = self.create_client(
            ApplyPlanningScene, "/apply_planning_scene"
        )
        self.get_scene_client = self.create_client(
            GetPlanningScene, "/get_planning_scene"
        )
        self.move_action_client = ActionClient(self, MoveGroup, "/move_action")

    def wait_for(self, client, name, timeout_sec=30.0):
        if not client.wait_for_server(timeout_sec=timeout_sec):
            self.get_logger().error(f"Timed out waiting for {name}")
            sys.exit(1)

    def call_service(self, client, request):
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def add_box(self) -> None:
        if not self.apply_scene_client.wait_for_service(timeout_sec=30.0):
            self.get_logger().error("Timed out waiting for /apply_planning_scene")
            sys.exit(1)

        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects.append(make_box_collision_object())

        request = ApplyPlanningScene.Request()
        request.scene = scene
        response = self.call_service(self.apply_scene_client, request)
        if response is None or not response.success:
            self.get_logger().error("Failed to apply planning scene with box")
            sys.exit(1)

    def get_collision_objects(self):
        if not self.get_scene_client.wait_for_service(timeout_sec=30.0):
            self.get_logger().error("Timed out waiting for /get_planning_scene")
            sys.exit(1)

        request = GetPlanningScene.Request()
        request.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
        response = self.call_service(self.get_scene_client, request)
        if response is None:
            self.get_logger().error("Failed to get planning scene")
            sys.exit(1)
        return list(response.scene.world.collision_objects)

    def plan_joint_goal(self):
        self.wait_for(self.move_action_client, "/move_action")

        goal_constraints = Constraints()
        for name, value in zip(JOINT_NAMES, JOINT_GOAL):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = value
            jc.tolerance_above = 0.001
            jc.tolerance_below = 0.001
            jc.weight = 1.0
            goal_constraints.joint_constraints.append(jc)

        motion_request = MotionPlanRequest()
        motion_request.group_name = GROUP_NAME
        motion_request.goal_constraints.append(goal_constraints)
        motion_request.allowed_planning_time = 5.0
        motion_request.num_planning_attempts = 5
        motion_request.max_velocity_scaling_factor = 1.0
        motion_request.max_acceleration_scaling_factor = 1.0
        motion_request.pipeline_id = "ompl"

        planning_options = PlanningOptions()
        planning_options.plan_only = True
        planning_options.look_around = False
        planning_options.replan = False

        goal = MoveGroup.Goal()
        goal.request = motion_request
        goal.planning_options = planning_options

        send_goal_future = self.move_action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("MoveGroup goal was rejected")
            sys.exit(1)

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()
        if result is None:
            self.get_logger().error("MoveGroup action produced no result")
            sys.exit(1)

        move_result = result.result
        if move_result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
            self.get_logger().error(
                f"Planning failed with error code {move_result.error_code.val}"
            )
            sys.exit(1)

        return move_result.planned_trajectory.joint_trajectory.points


def main():
    rclpy.init()
    node = PlanClient()
    try:
        node.add_box()

        objects_after_add = node.get_collision_objects()
        object_ids = [obj.id for obj in objects_after_add]
        if BOX_ID not in object_ids:
            node.get_logger().error(
                f"Collision object '{BOX_ID}' not found in planning scene after adding it"
            )
            sys.exit(1)

        points = node.plan_joint_goal()

        final_objects = node.get_collision_objects()

        print(f"POINTS {len(points)}")
        print(f"OBJECTS {len(final_objects)}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == "__main__":
    main()
