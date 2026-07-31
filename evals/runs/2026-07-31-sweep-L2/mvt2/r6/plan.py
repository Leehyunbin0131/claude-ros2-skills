#!/usr/bin/env python3
"""Request a joint-space motion plan for the 'arm' planning group from
move_group and print the number of points in the returned trajectory."""

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
)

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
# Joint-space goal (radians), well within each joint's URDF limits.
GOAL_POSITIONS = [0.8, 0.5, -0.6]


class PlanClient(Node):
    def __init__(self):
        super().__init__("plan_client")
        self._client = ActionClient(self, MoveGroup, "/move_action")

    def request_plan(self):
        if not self._client.wait_for_server(timeout_sec=30.0):
            self.get_logger().error("move_group action server not available")
            return None

        goal_constraints = Constraints()
        for name, position in zip(JOINT_NAMES, GOAL_POSITIONS):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = position
            jc.tolerance_above = 0.01
            jc.tolerance_below = 0.01
            jc.weight = 1.0
            goal_constraints.joint_constraints.append(jc)

        request = MotionPlanRequest()
        request.group_name = GROUP_NAME
        request.goal_constraints = [goal_constraints]
        request.pipeline_id = "ompl"
        request.planner_id = "RRTConnectkConfigDefault"
        request.num_planning_attempts = 5
        request.allowed_planning_time = 10.0
        request.max_velocity_scaling_factor = 1.0
        request.max_acceleration_scaling_factor = 1.0

        goal_msg = MoveGroup.Goal()
        goal_msg.request = request
        goal_msg.planning_options = PlanningOptions()
        goal_msg.planning_options.plan_only = True

        send_goal_future = self._client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("goal rejected")
            return None

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result_response = result_future.result()
        if result_response is None:
            self.get_logger().error("no result received")
            return None

        return result_response.result


def main():
    rclpy.init()
    node = PlanClient()
    try:
        result = node.request_plan()
        if result is None:
            sys.exit(1)

        if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes SUCCESS == 1
            node.get_logger().error(
                f"planning failed with error code {result.error_code.val}"
            )
            sys.exit(1)

        points = result.planned_trajectory.joint_trajectory.points
        print(f"POINTS {len(points)}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == "__main__":
    main()
