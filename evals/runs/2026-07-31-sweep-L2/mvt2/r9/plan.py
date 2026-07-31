#!/usr/bin/env python3
"""Request a joint-space motion plan for the 'arm' MoveIt 2 planning group and
print `POINTS <n>` where n is the number of points in the planned trajectory."""

import os
import sys
from pathlib import Path

# This host may run several unrelated ROS 2 graphs side by side (other sessions
# sharing the same network namespace). bringup.sh pins the 'arm' stack to a
# domain ID derived from this directory and writes it to .ros_domain_id; match
# it here so plan.py talks to *our* move_group and not one from elsewhere on
# the host. Must happen before rclpy is imported/initialized.
_domain_id_file = Path(__file__).resolve().parent / ".ros_domain_id"
if _domain_id_file.exists():
    os.environ["ROS_DOMAIN_ID"] = _domain_id_file.read_text().strip()

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
    WorkspaceParameters,
)

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
JOINT_GOAL = [0.6, -0.4, 0.5]
PLANNING_FRAME = "base_link"


class PlanClient(Node):
    def __init__(self):
        super().__init__("plan_client")
        self._client = ActionClient(self, MoveGroup, "move_action")

    def plan(self):
        if not self._client.wait_for_server(timeout_sec=60.0):
            self.get_logger().error("move_action action server not available")
            return None

        request = MotionPlanRequest()
        request.group_name = GROUP_NAME
        request.num_planning_attempts = 10
        request.allowed_planning_time = 5.0
        request.max_velocity_scaling_factor = 1.0
        request.max_acceleration_scaling_factor = 1.0
        request.start_state.is_diff = True

        workspace = WorkspaceParameters()
        workspace.header.frame_id = PLANNING_FRAME
        workspace.min_corner.x = workspace.min_corner.y = workspace.min_corner.z = -1.0
        workspace.max_corner.x = workspace.max_corner.y = workspace.max_corner.z = 1.0
        request.workspace_parameters = workspace

        goal_constraints = Constraints()
        goal_constraints.name = "joint_space_goal"
        for name, value in zip(JOINT_NAMES, JOINT_GOAL):
            constraint = JointConstraint()
            constraint.joint_name = name
            constraint.position = value
            constraint.tolerance_above = 0.001
            constraint.tolerance_below = 0.001
            constraint.weight = 1.0
            goal_constraints.joint_constraints.append(constraint)
        request.goal_constraints = [goal_constraints]

        goal_msg = MoveGroup.Goal()
        goal_msg.request = request
        goal_msg.planning_options = PlanningOptions()
        goal_msg.planning_options.plan_only = True
        goal_msg.planning_options.planning_scene_diff.is_diff = True

        send_goal_future = self._client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("Goal was rejected by move_group")
            return None

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        wrapped_result = result_future.result()
        if wrapped_result is None:
            self.get_logger().error("No result returned by move_group")
            return None

        move_result = wrapped_result.result
        if move_result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
            self.get_logger().error(
                f"Planning failed, error_code={move_result.error_code.val}"
            )
            return None

        return move_result.planned_trajectory.joint_trajectory.points


def main():
    rclpy.init()
    node = PlanClient()
    try:
        points = node.plan()
    finally:
        node.destroy_node()
        rclpy.shutdown()

    if not points:
        print("ERROR: no trajectory points returned", file=sys.stderr)
        sys.exit(1)

    print(f"POINTS {len(points)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
