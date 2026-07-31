#!/usr/bin/env python3
"""Request a joint-space motion plan for the 'arm' MoveIt planning group
and print the number of points in the returned trajectory.
"""
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MotionPlanRequest, PlanningOptions

GROUP_NAME = "arm"
# Joint-space goal (radians), well within the URDF joint limits.
JOINT_GOAL = {
    "joint1": 0.6,
    "joint2": -0.4,
    "joint3": 0.5,
}


class PlanRequester(Node):
    def __init__(self):
        super().__init__("plan_requester")
        self._client = ActionClient(self, MoveGroup, "/move_action")

    def request_plan(self):
        if not self._client.wait_for_server(timeout_sec=30.0):
            self.get_logger().error("move_group action server not available")
            return None

        goal_constraints = Constraints()
        for joint_name, position in JOINT_GOAL.items():
            jc = JointConstraint()
            jc.joint_name = joint_name
            jc.position = position
            jc.tolerance_above = 0.001
            jc.tolerance_below = 0.001
            jc.weight = 1.0
            goal_constraints.joint_constraints.append(jc)

        request = MotionPlanRequest()
        request.group_name = GROUP_NAME
        request.goal_constraints = [goal_constraints]
        request.start_state.is_diff = True
        request.num_planning_attempts = 5
        request.allowed_planning_time = 5.0
        request.max_velocity_scaling_factor = 1.0
        request.max_acceleration_scaling_factor = 1.0

        planning_options = PlanningOptions()
        planning_options.plan_only = True
        planning_options.planning_scene_diff.is_diff = True

        goal = MoveGroup.Goal()
        goal.request = request
        goal.planning_options = planning_options

        send_goal_future = self._client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_goal_future, timeout_sec=30.0)
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("Goal was rejected")
            return None

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=30.0)
        result_response = result_future.result()
        if result_response is None:
            self.get_logger().error("Timed out waiting for plan result")
            return None

        return result_response.result


def main():
    rclpy.init()
    node = PlanRequester()
    result = node.request_plan()
    node.destroy_node()
    rclpy.shutdown()

    if result is None:
        print("PLAN FAILED: no result received", file=sys.stderr)
        sys.exit(1)

    if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
        print(f"PLAN FAILED: error_code={result.error_code.val}", file=sys.stderr)
        sys.exit(1)

    points = result.planned_trajectory.joint_trajectory.points
    print(f"POINTS {len(points)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
