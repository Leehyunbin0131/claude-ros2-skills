#!/usr/bin/env python3
"""Request a joint-space motion plan from MoveIt 2's move_group for the
'arm' planning group and print the number of points in the resulting
trajectory as `POINTS <n>`.
"""

import os
import sys

# The loopback interface on this host has multicast disabled, which breaks
# Fast-DDS's default multicast-based discovery. Force discovery over unicast
# to localhost instead, matching what bringup.sh set for move_group.
os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "LOCALHOST"
os.environ["ROS_STATIC_PEERS"] = "127.0.0.1"

# Use the same private ROS_DOMAIN_ID that bringup.sh assigned to move_group,
# so we talk to our own graph even if this host has other, unrelated ROS 2
# sessions running concurrently on the default domain.
_DOMAIN_ID_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".bringup", "ros_domain_id"
)
if os.path.exists(_DOMAIN_ID_FILE):
    with open(_DOMAIN_ID_FILE) as _f:
        os.environ["ROS_DOMAIN_ID"] = _f.read().strip()

# If the ROS 2 environment hasn't been sourced by the caller, re-exec this
# script through a shell that sources it, so `python3 plan.py` works
# regardless of the caller's shell state.
try:
    import rclpy  # noqa: F401
except ImportError:
    ros_setup = "/opt/ros/jazzy/setup.bash"
    if os.path.exists(ros_setup) and not os.environ.get("_PLAN_PY_REEXEC"):
        os.environ["_PLAN_PY_REEXEC"] = "1"
        os.execvpe(
            "bash",
            [
                "bash",
                "-c",
                f'source "{ros_setup}" && exec python3 "$0" "$@"',
                os.path.abspath(__file__),
                *sys.argv[1:],
            ],
            os.environ,
        )
    raise

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MotionPlanRequest, PlanningOptions

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
# Joint-space goal, clearly different from the all-zero start state.
GOAL_POSITIONS = [1.0, 0.5, -0.7]


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
            jc.tolerance_above = 0.001
            jc.tolerance_below = 0.001
            jc.weight = 1.0
            goal_constraints.joint_constraints.append(jc)

        request = MotionPlanRequest()
        request.group_name = GROUP_NAME
        request.pipeline_id = "ompl"
        request.planner_id = "RRTConnectkConfigDefault"
        request.num_planning_attempts = 5
        request.allowed_planning_time = 5.0
        request.max_velocity_scaling_factor = 1.0
        request.max_acceleration_scaling_factor = 1.0
        request.goal_constraints.append(goal_constraints)

        planning_options = PlanningOptions()
        planning_options.plan_only = True

        goal_msg = MoveGroup.Goal()
        goal_msg.request = request
        goal_msg.planning_options = planning_options

        send_goal_future = self._client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future, timeout_sec=30.0)
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("Goal was rejected by move_group")
            return None

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=30.0)
        result_response = result_future.result()
        if result_response is None:
            self.get_logger().error("Timed out waiting for planning result")
            return None

        return result_response.result


def main():
    rclpy.init()
    node = PlanClient()
    try:
        result = node.request_plan()
        if result is None:
            print("PLAN FAILED: no result from move_group", file=sys.stderr)
            sys.exit(1)

        if result.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS
            print(
                f"PLAN FAILED: error_code={result.error_code.val} "
                f"message={result.error_code.message}",
                file=sys.stderr,
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
