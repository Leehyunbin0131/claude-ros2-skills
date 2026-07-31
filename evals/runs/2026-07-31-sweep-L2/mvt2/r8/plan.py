#!/usr/bin/env python3
"""Request a joint-space motion plan for the 'arm' MoveIt planning group and
print `POINTS <n>`, where n is the number of points in the planned
trajectory."""
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    MoveItErrorCodes,
    PlanningOptions,
)

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
JOINT_GOAL = [0.6, 0.4, -0.5]


def main():
    rclpy.init()
    node = Node("plan_client")
    client = ActionClient(node, MoveGroup, "/move_action")

    if not client.wait_for_server(timeout_sec=30.0):
        node.get_logger().error("move_action server not available")
        rclpy.shutdown()
        sys.exit(1)

    goal_constraints = Constraints()
    for joint_name, position in zip(JOINT_NAMES, JOINT_GOAL):
        jc = JointConstraint()
        jc.joint_name = joint_name
        jc.position = position
        jc.tolerance_above = 0.001
        jc.tolerance_below = 0.001
        jc.weight = 1.0
        goal_constraints.joint_constraints.append(jc)

    request = MotionPlanRequest()
    request.group_name = GROUP_NAME
    request.goal_constraints.append(goal_constraints)
    request.num_planning_attempts = 5
    request.allowed_planning_time = 10.0
    request.max_velocity_scaling_factor = 1.0
    request.max_acceleration_scaling_factor = 1.0

    planning_options = PlanningOptions()
    planning_options.plan_only = True

    goal_msg = MoveGroup.Goal()
    goal_msg.request = request
    goal_msg.planning_options = planning_options

    send_goal_future = client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future, timeout_sec=30.0)
    goal_handle = send_goal_future.result()

    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("Motion plan goal was rejected")
        rclpy.shutdown()
        sys.exit(1)

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future, timeout_sec=30.0)
    result_wrapper = result_future.result()

    if result_wrapper is None:
        node.get_logger().error("Timed out waiting for planning result")
        rclpy.shutdown()
        sys.exit(1)

    result = result_wrapper.result
    if result.error_code.val != MoveItErrorCodes.SUCCESS:
        node.get_logger().error(
            f"Planning failed with MoveItErrorCodes {result.error_code.val}"
        )
        rclpy.shutdown()
        sys.exit(1)

    n_points = len(result.planned_trajectory.joint_trajectory.points)
    print(f"POINTS {n_points}")

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
