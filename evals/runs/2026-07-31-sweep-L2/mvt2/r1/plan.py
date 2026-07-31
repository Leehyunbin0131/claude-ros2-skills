#!/usr/bin/env python3
"""Request a joint-space motion plan for the `arm` MoveIt planning group and
print `POINTS <n>` where n is the number of points in the planned trajectory."""
import sys

import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetMotionPlan
from moveit_msgs.msg import MotionPlanRequest, Constraints, JointConstraint, RobotState
from sensor_msgs.msg import JointState

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
START_POSITIONS = [0.0, 0.0, 0.0]
GOAL_POSITIONS = [1.0, 0.6, -0.8]


def main():
    rclpy.init()
    node = Node("plan_client")
    client = node.create_client(GetMotionPlan, "/plan_kinematic_path")

    if not client.wait_for_service(timeout_sec=60.0):
        node.get_logger().error("Service /plan_kinematic_path not available")
        rclpy.shutdown()
        sys.exit(1)

    request = GetMotionPlan.Request()
    mpr = MotionPlanRequest()
    mpr.group_name = GROUP_NAME
    mpr.planner_id = "RRTConnect"
    mpr.num_planning_attempts = 5
    mpr.allowed_planning_time = 5.0
    mpr.max_velocity_scaling_factor = 1.0
    mpr.max_acceleration_scaling_factor = 1.0

    start_state = RobotState()
    start_state.joint_state = JointState()
    start_state.joint_state.name = list(JOINT_NAMES)
    start_state.joint_state.position = list(START_POSITIONS)
    start_state.is_diff = False
    mpr.start_state = start_state

    goal = Constraints()
    for name, pos in zip(JOINT_NAMES, GOAL_POSITIONS):
        jc = JointConstraint()
        jc.joint_name = name
        jc.position = pos
        jc.tolerance_above = 0.001
        jc.tolerance_below = 0.001
        jc.weight = 1.0
        goal.joint_constraints.append(jc)
    mpr.goal_constraints = [goal]

    request.motion_plan_request = mpr

    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=30.0)

    if not future.done() or future.result() is None:
        node.get_logger().error("Planning service call failed or timed out")
        rclpy.shutdown()
        sys.exit(1)

    response = future.result().motion_plan_response
    if response.error_code.val != 1:
        node.get_logger().error(
            f"Planning failed with MoveItErrorCode {response.error_code.val}"
        )
        rclpy.shutdown()
        sys.exit(1)

    n_points = len(response.trajectory.joint_trajectory.points)
    print(f"POINTS {n_points}")

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
