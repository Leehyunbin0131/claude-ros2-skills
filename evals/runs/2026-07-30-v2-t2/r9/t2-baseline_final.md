# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 12
- total_cost_usd: 0.5773685
- tool calls: **11**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-vZGb/ 2>&1 | head -50
2. `Bash` — which ros2 rosrun roscore 2>&1; echo "---"; command -v ros2 2>&1; echo "---catkin/colcon ws probes---"; ls -la ~ 2>&1 | head -20
3. `Bash` — echo "--- home subdir ---"; find ~/home -maxdepth 4 2>&1 | head -60
echo "--- gz dir ---"; find ~/.gz -maxdepth 3 2>&1 | head -30
echo "--- bash history grep fo
4. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "--- nodes ---"; timeout 5 ros2 node list 2>&1
echo "--- topics ---"; timeout 5 ros2 topic list 2>&1
echo "---
5. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== imu/data frame_id + one message ==="
timeout 4 ros2 topic echo /imu/data --once 2>&1
echo "=== tf_static 
6. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== tf2_echo base_link -> imu_link ==="
timeout 4 ros2 run tf2_ros tf2_echo base_link imu_link 2>&1 | grep -v
7. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== full node list (no truncation) ==="
timeout 5 ros2 node list 2>&1 | grep -v RTPS_TRANSPORT
echo "=== robo
8. `Bash` — ls -lat /tmp/ 2>&1 | grep -E "^d|t1-ddrive|t2" | head -20
echo "---"
ls -la /tmp/ 2>&1 | grep -iE "t2|imu|ekf"
9. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
echo "=== 3 more imu samples (accel only) ==="
timeout 6 ros2 topic echo /imu/data --field linear_acceleration 2>&1
10. `Bash` — find /home/hyunlee/home/claude-ros2-skills -iname "*check_imu*" 2>/dev/null
11. `Bash` — source /opt/ros/jazzy/setup.bash 2>/dev/null
cd /home/hyunlee/home/claude-ros2-skills
timeout 15 python3 skills/ros2-troubleshooting/scripts/check_imu_gravity.p

## Final message

Settled — with actual measurement, not a hunch.

## Evidence

I sampled `/imu/data` live (the robot at rest) directly, and also ran the repo's `check_imu_gravity.py` checker as an independent cross-check. Both agree:

```
mean linear_acceleration ≈ (+9.81, ~0.00, ~-0.01) m/s²   |a| = 9.81
```

With the robot stationary and level, gravity reaction should load almost entirely on **Z** (REP-103: X-forward, Y-left, Z-up). Instead it's loading almost entirely on **X**, across 170+ live samples, well outside noise (noise is ~±0.05-0.1 m/s² on the other two axes). That's not sensor noise or bias — it's the full 9.81 m/s² sitting on the wrong axis. This is exactly the signature of a mount rotated **90° about the Y (pitch) axis**: what the sensor calls "up" is actually the robot's forward/backward direction.

Why this was invisible everywhere else you looked:
- **Orientation field** is reported as identity `(0,0,0,w=1)` — the driver isn't computing attitude, so nothing looks "tilted."
- **Topics, QoS, rates** are all fine — no dropped messages, no errors, no diagnostics complaint.
- Nothing in a URDF or log inspection would show this — the declared TF frame and the physical mount silently disagree. The only way to catch it is to sample the raw data at rest and check where gravity lands, which is what I did.

## Why this produces your exact symptoms

- **Drift**: Any EKF config that removes gravity for accel integration assumes it's on Z. Here it subtracts nothing meaningful from X (the true gravity axis) while treating Z as free of it — the residual gets integrated into spurious linear velocity/position, i.e. drift, even when the robot sits still.
- **Spin on the spot**: the same 90° rotation applies to the gyro triad. The channel the EKF trusts for yaw rate is actually sampling the physical pitch/roll axis, and vice versa. Any real pitch motion (bumps, acceleration/braking) gets fused in as phantom yaw, and true yaw gets under- or mis-weighted — producing exactly the "spins on the spot" behavior with wheel odometry disagreeing.

## Fix

The IMU is mounted rotated 90° about Y relative to what it's declared as in TF/config. Either:
1. Physically remount the sensor so its silkscreen Z points up and X points forward, or
2. If remounting isn't possible, correct the `base_link → imu_link` static transform to reflect the true physical rotation (not identity), so downstream consumers (robot_localization) rotate the data into `base_link` correctly before fusing it.

After either fix, re-run `check_imu_gravity.py --topic /imu/data` at rest — it should report gravity on Z within tolerance before you trust the EKF output again.
