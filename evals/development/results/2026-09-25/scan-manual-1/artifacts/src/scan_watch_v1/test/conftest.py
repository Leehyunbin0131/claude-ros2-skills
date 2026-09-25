import rclpy
import pytest


@pytest.fixture
def ros_context():
    context = rclpy.context.Context()
    rclpy.init(context=context)
    yield context
    rclpy.try_shutdown(context=context)
