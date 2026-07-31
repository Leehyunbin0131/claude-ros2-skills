#!/usr/bin/env python3
"""Request a joint-space motion plan for the 'arm' MoveIt planning group.

Talks directly to the /move_group action (moveit_msgs/action/MoveGroup)
since no moveit_py bindings are available on this platform. Prints
"POINTS <n>" where n is the number of waypoints in the planned trajectory,
then exits 0.
"""
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MoveItErrorCodes,
    MotionPlanRequest,
    PlanningOptions,
    RobotState,
)
from sensor_msgs.msg import JointState

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
START_POSITIONS = [0.0, 0.0, 0.0]
GOAL_POSITIONS = [0.5, -0.3, 0.4]


def build_goal():
    goal_msg = MoveGroup.Goal()

    request = MotionPlanRequest()
    request.group_name = GROUP_NAME
    request.num_planning_attempts = 5
    request.allowed_planning_time = 10.0
    request.max_velocity_scaling_factor = 0.5
    request.max_acceleration_scaling_factor = 0.5

    start_state = RobotState()
    start_state.joint_state = JointState()
    start_state.joint_state.name = JOINT_NAMES
    start_state.joint_state.position = START_POSITIONS
    start_state.is_diff = False
    request.start_state = start_state

    goal_constraints = Constraints()
    for name, position in zip(JOINT_NAMES, GOAL_POSITIONS):
        jc = JointConstraint()
        jc.joint_name = name
        jc.position = position
        jc.tolerance_above = 0.001
        jc.tolerance_below = 0.001
        jc.weight = 1.0
        goal_constraints.joint_constraints.append(jc)
    request.goal_constraints.append(goal_constraints)

    goal_msg.request = request

    planning_options = PlanningOptions()
    planning_options.plan_only = True
    planning_options.look_around = False
    planning_options.replan = False
    goal_msg.planning_options = planning_options

    return goal_msg


def main():
    rclpy.init(args=None)
    node = Node("plan_request_client")
    client = ActionClient(node, MoveGroup, "move_action")

    if not client.wait_for_server(timeout_sec=30.0):
        node.get_logger().error("move_group action server not available")
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    goal_msg = build_goal()

    send_goal_future = client.send_goal_async(goal_msg)
    rclpy.spin_until_future_complete(node, send_goal_future)
    goal_handle = send_goal_future.result()

    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error("Goal was rejected by move_group")
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future)
    result = result_future.result().result

    if result.error_code.val != MoveItErrorCodes.SUCCESS:
        node.get_logger().error(
            f"Planning failed with error code {result.error_code.val}"
        )
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    n_points = len(result.planned_trajectory.joint_trajectory.points)

    node.destroy_node()
    rclpy.shutdown()

    print(f"POINTS {n_points}")
    sys.exit(0)


if __name__ == "__main__":
    main()
