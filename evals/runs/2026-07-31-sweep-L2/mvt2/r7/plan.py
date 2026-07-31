#!/usr/bin/env python3
"""Request a joint-space motion plan for the 'arm' MoveIt planning group
by talking directly to move_group's /move_action action server, then print
POINTS <n> where n is the number of points in the returned trajectory.
"""
import os
import sys

try:
    import rclpy
except ImportError:
    # Re-exec under a sourced ROS 2 Jazzy environment in case the caller's
    # shell didn't source /opt/ros/jazzy/setup.bash before invoking us.
    ros_setup = "/opt/ros/jazzy/setup.bash"
    if os.environ.get("_PLAN_PY_REEXEC") != "1" and os.path.exists(ros_setup):
        os.environ["_PLAN_PY_REEXEC"] = "1"
        cmd = f"source {ros_setup} && exec python3 {sys.argv[0]} " + " ".join(
            sys.argv[1:]
        )
        os.execvpe("bash", ["bash", "-c", cmd], os.environ)
    raise

from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
)
from sensor_msgs.msg import JointState

GROUP_NAME = "arm"
JOINT_NAMES = ["joint1", "joint2", "joint3"]
GOAL_POSITIONS = [0.8, -0.6, 0.4]


class PlanRequester(Node):
    def __init__(self):
        super().__init__("plan_requester")
        self._client = ActionClient(self, MoveGroup, "/move_action")
        self._joint_state = None
        self._js_sub = self.create_subscription(
            JointState, "/joint_states", self._joint_state_cb, 10
        )

    def _joint_state_cb(self, msg):
        self._joint_state = msg

    def wait_for_joint_state(self, timeout_sec=15.0):
        end_time = self.get_clock().now().nanoseconds + int(timeout_sec * 1e9)
        while rclpy.ok() and self._joint_state is None:
            rclpy.spin_once(self, timeout_sec=0.5)
            if self.get_clock().now().nanoseconds > end_time:
                break
        return self._joint_state

    def request_plan(self):
        if not self._client.wait_for_server(timeout_sec=30.0):
            self.get_logger().error("move_group action server not available")
            return None

        current_state = self.wait_for_joint_state()

        request = MotionPlanRequest()
        request.group_name = GROUP_NAME
        request.pipeline_id = "ompl"
        request.planner_id = "RRTConnect"
        request.num_planning_attempts = 10
        request.allowed_planning_time = 10.0
        request.max_velocity_scaling_factor = 1.0
        request.max_acceleration_scaling_factor = 1.0

        if current_state is not None:
            request.start_state.joint_state = current_state

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

        planning_options = PlanningOptions()
        planning_options.plan_only = True
        planning_options.look_around = False
        planning_options.replan = False

        goal_msg = MoveGroup.Goal()
        goal_msg.request = request
        goal_msg.planning_options = planning_options

        send_goal_future = self._client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("Motion plan goal was rejected")
            return None

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        return result_future.result()


def main():
    rclpy.init()
    node = PlanRequester()
    try:
        result_response = node.request_plan()
        if result_response is None:
            print("PLAN FAILED: no result from move_group", file=sys.stderr)
            sys.exit(1)

        result = result_response.result
        error_code = result.error_code.val
        points = result.planned_trajectory.joint_trajectory.points

        if error_code != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS == 1
            print(
                f"PLAN FAILED: error_code={error_code}",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"POINTS {len(points)}")
        sys.exit(0)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
