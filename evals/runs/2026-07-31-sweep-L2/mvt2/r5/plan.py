#!/usr/bin/env python3
"""Request a joint-space motion plan for the 'arm' planning group from
move_group's /plan_kinematic_path service and print the number of
points in the resulting trajectory."""

import sys
import time

import rclpy
from rclpy.node import Node

from moveit_msgs.srv import GetMotionPlan
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
GOAL_POSITIONS = [1.0, -0.8, 1.2]

SERVICE_WAIT_TIMEOUT_SEC = 60.0
PLAN_CALL_TIMEOUT_SEC = 30.0


def build_request():
    req = GetMotionPlan.Request()
    mp_req = req.motion_plan_request

    mp_req.group_name = GROUP_NAME
    mp_req.start_state.is_diff = True

    goal_constraints = Constraints()
    for name, position in zip(JOINT_NAMES, GOAL_POSITIONS):
        jc = JointConstraint()
        jc.joint_name = name
        jc.position = position
        jc.tolerance_above = 0.001
        jc.tolerance_below = 0.001
        jc.weight = 1.0
        goal_constraints.joint_constraints.append(jc)
    mp_req.goal_constraints = [goal_constraints]

    mp_req.pipeline_id = "ompl"
    mp_req.num_planning_attempts = 10
    mp_req.allowed_planning_time = 5.0
    mp_req.max_velocity_scaling_factor = 1.0
    mp_req.max_acceleration_scaling_factor = 1.0

    return req


def main():
    rclpy.init()
    node = Node("plan_client")

    client = node.create_client(GetMotionPlan, "/plan_kinematic_path")

    deadline = time.monotonic() + SERVICE_WAIT_TIMEOUT_SEC
    while not client.wait_for_service(timeout_sec=2.0):
        if time.monotonic() > deadline:
            print("ERROR: /plan_kinematic_path service not available", file=sys.stderr)
            node.destroy_node()
            rclpy.shutdown()
            sys.exit(1)

    request = build_request()
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=PLAN_CALL_TIMEOUT_SEC)

    if not future.done() or future.result() is None:
        print("ERROR: motion plan service call did not complete", file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    response = future.result().motion_plan_response
    error_code = response.error_code.val

    if error_code != MoveItErrorCodes.SUCCESS:
        print(f"ERROR: planning failed with error code {error_code}", file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    n_points = len(response.trajectory.joint_trajectory.points)
    print(f"POINTS {n_points}")

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
