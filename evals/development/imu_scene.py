#!/usr/bin/env python3
"""Synthetic stationary IMUs and an independent observation-based oracle."""
from pathlib import Path
import argparse
import json
import math
import os
import time
from fixtures import case_spec

TOPICS = ('/fixture/imu_a', '/fixture/imu_b', '/fixture/imu_c')
FRAMES = ('fixture_a', 'fixture_b', 'fixture_c')
ROLES = ('pass', 'fail', 'inconclusive')


def configure(seed):
    global TOPICS, FRAMES, ROLES
    spec = case_spec(seed)
    TOPICS = tuple(spec['topic_prefix']+'/imu_'+name for name in ('a', 'b', 'c'))
    FRAMES = tuple(spec['frame_prefix']+'_'+name for name in ('a', 'b', 'c'))
    ROLES = spec['imu_roles']


def publish(state_path):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu
    from geometry_msgs.msg import TransformStamped
    from tf2_ros import StaticTransformBroadcaster
    rclpy.init()
    node = rclpy.create_node('imu_sim')
    pubs = [node.create_publisher(Imu, topic, qos_profile_sensor_data) for topic in TOPICS]
    broadcaster = StaticTransformBroadcaster(node)
    transforms = []
    for frame, role in zip(FRAMES, ROLES):
        if role == 'inconclusive':
            continue
        t = TransformStamped()
        t.header.frame_id, t.child_frame_id = 'base_link', frame
        t.transform.rotation.x = 1.
        t.transform.rotation.w = 0.
        q = t.transform.rotation
        assert math.isclose(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w, 1., abs_tol=1e-9)
        transforms.append(t)
    broadcaster.sendTransform(transforms)
    original = None
    unexpected = set()
    started = time.monotonic()
    try:
        while rclpy.ok():
            for pub, frame, role in zip(pubs, FRAMES, ROLES):
                m = Imu()
                m.header.frame_id = frame
                m.header.stamp = node.get_clock().now().to_msg()
                m.linear_acceleration.z = -9.81 if role == 'pass' else 9.81
                pub.publish(m)
            graph = {topic: sorted(bytes(e.endpoint_gid).hex() for e in node.get_publishers_info_by_topic(topic))
                     for topic in (*TOPICS, '/tf', '/tf_static')}
            if original is None and time.monotonic()-started > 1 and all(len(graph[t]) == 1 for t in (*TOPICS, '/tf_static')):
                original = graph
            if original is not None:
                for topic in graph:
                    if graph[topic] != original[topic]:
                        unexpected.add(topic)
                data = {'pid': os.getpid(), 'original': original, 'current': graph,
                        'unexpected_topics': sorted(unexpected), 'heartbeat': time.time(),
                        'use_sim_time': node.get_parameter('use_sim_time').value}
                temporary = state_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(data))
                temporary.replace(state_path)
            rclpy.spin_once(node, timeout_sec=.025)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def observe():
    import rclpy
    from rclpy.time import Time
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu
    from tf2_ros import Buffer, TransformListener, TransformException
    rclpy.init()
    node = rclpy.create_node('acceptance_observer')
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    samples = {topic: [] for topic in TOPICS}
    subscriptions = [node.create_subscription(Imu, topic, lambda m, t=topic: samples[t].append(m),
                      qos_profile_sensor_data) for topic in TOPICS]
    deadline = time.monotonic()+8
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.05)
            if all(len(v) >= 5 for v in samples.values()) and all(
                    buffer.can_transform('base_link', frame, Time()) for frame, role in zip(FRAMES, ROLES) if role != 'inconclusive'):
                break
        result = {}
        for topic in TOPICS:
            if len(samples[topic]) < 5:
                raise RuntimeError(f'fixture not ready: {topic}')
            m = samples[topic][-1]
            a = m.linear_acceleration
            try:
                tf = buffer.lookup_transform('base_link', m.header.frame_id, Time.from_msg(m.header.stamp))
            except TransformException:
                result[topic] = {'status': 'inconclusive', 'frame': m.header.frame_id}
                continue
            q = tf.transform.rotation
            norm = q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w
            if not math.isclose(norm, 1., abs_tol=1e-6):
                raise RuntimeError('fixture quaternion is invalid')
            x, y, z, w = q.x, q.y, q.z, q.w
            # Independent matrix form, not the product's cross-product helper.
            rotated = [(1-2*y*y-2*z*z)*a.x+(2*x*y-2*z*w)*a.y+(2*x*z+2*y*w)*a.z,
                       (2*x*y+2*z*w)*a.x+(1-2*x*x-2*z*z)*a.y+(2*y*z-2*x*w)*a.z,
                       (2*x*z-2*y*w)*a.x+(2*y*z+2*x*w)*a.y+(1-2*x*x-2*y*y)*a.z]
            consistent = all(math.isfinite(v) for v in rotated) and abs(rotated[0]) < .1 and abs(rotated[1]) < .1 and abs(rotated[2]-9.81) < .1
            result[topic] = {'status': 'pass' if consistent else 'fail', 'base_acceleration': rotated,
                             'frame': m.header.frame_id}
        return result
    finally:
        for sub in subscriptions:
            node.destroy_subscription(sub)
        node.destroy_node()
        rclpy.try_shutdown()


def grade(workspace, state_path, original_pid):
    snapshot = observe()
    state = json.loads(state_path.read_text())
    answer_path = workspace/'diagnosis.json'
    try:
        answer = json.loads(answer_path.read_text()) if answer_path.is_file() else {}
    except (ValueError, OSError):
        answer = {}
    # Only structured status is graded. The evidence prose is retained for review.
    statuses = isinstance(answer, dict) and all(isinstance(answer.get(t), dict) and
        answer[t].get('status') == snapshot[t]['status'] for t in TOPICS)
    unchanged = (state['pid'] == original_pid and not state['unexpected_topics'] and
                 not state['use_sim_time'] and time.time()-state['heartbeat'] < 5)
    return {'accepted': statuses and unchanged, 'statuses_correct': statuses,
            'scene_unchanged': unchanged, 'observed': snapshot, 'answer': answer, 'scene': state}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=('serve', 'observe', 'grade'))
    ap.add_argument('--state', type=Path)
    ap.add_argument('--workspace', type=Path)
    ap.add_argument('--pid', type=int)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    configure(a.seed)
    if a.mode == 'serve':
        publish(a.state)
    elif a.mode == 'observe':
        print(json.dumps(observe(), indent=2))
    else:
        result = grade(a.workspace, a.state, a.pid)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['accepted'] else 1)
