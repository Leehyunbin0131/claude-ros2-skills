# Run summary — `t2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 2
- total_cost_usd: 0.1078004
- tool calls: **1**

## Tool calls, in order

1. `Bash` — ls -la /tmp/eval-t2-baseline-iHvN && find /tmp/eval-t2-baseline-iHvN -maxdepth 3 -iname "*ekf*" -o -iname "*imu*" -o -iname "*.urdf*" -o -iname "*.xacro" 2>/dev

## Final message

There's nothing in this working directory to inspect (it's empty, not a git repo), so I can't grep your actual URDF/EKF config from here. But "settle it with evidence, not a hunch" is exactly the right instinct — here's how to get a smoking gun rather than a guess.

**The three tests that actually distinguish "IMU mounted wrong" from other causes:**

1. **Static gravity-vector test** (catches axis swap/rotation about x or y)
   Sit the robot dead flat and still, then echo `/imu/data` for a few seconds.
   - `linear_acceleration.z` should read ~±9.81, and `x`/`y` should be ~0.
   - If instead `x` or `y` is showing ~9.8, the IMU is physically rotated 90° from what your URDF/static transform claims (e.g. mounted on its side, or a pitch/roll of 90° not reflected in the `base_link → imu_link` transform).
   - Also check `orientation` (as roll/pitch, not raw quaternion) — should be ~0/0 when flat. A steady nonzero bias here (e.g. constant 5-10° pitch) is a physical mounting offset, not noise.

2. **Manual 90° yaw test** (catches sign/axis convention errors — this is the classic cause of "spins on the spot")
   Disable motors, rotate the chassis by hand exactly +90° (CCW viewed from above, per REP-103), and watch `angular_velocity.z` sign during the turn and the resulting yaw change in `/imu/data`.
   - Should be positive during a CCW turn, and orientation yaw should increase by ~90°.
   - If the sign is flipped, or the delta comes out as e.g. -90° or shows up on a different axis, that's a wiring/frame convention bug — and it explains the spin: the EKF gets a yaw-rate that's inverted or wrong-axis relative to what the URDF's static transform says, so the filter's Jacobian fights itself and can converge to spinning to "explain" heading residual from wheel odom vs IMU.

3. **Isolated pure-rotation command** (catches whether the mounting error is bleeding rotation into translation)
   Command `cmd_vel` with angular-only (zero linear x/y), then compare wheel odom (should show ~0 translation) against `/odometry/filtered` from the EKF.
   - If the EKF output shows the robot translating while both wheel odom and ground truth show pure rotation in place, that is direct evidence the IMU's linear acceleration axes are misaligned with `base_link` — off-axis mounting means centripetal/angular acceleration during rotation gets read on the wrong accelerometer axis and the EKF fuses it as real translational acceleration, producing drift that correlates with rotation, not distance traveled.

**Also worth pulling once you have data:**
- The actual RPY in the `static_transform_publisher` (or URDF joint) between `base_link` and your IMU frame — compare that number against a straightedge/level on the physical mount. A mismatch between the claimed and real mounting angle is your root cause.
- Whether `imu_link`'s frame_id in the driver output matches the frame your EKF config (`imu0_config` in `ekf.yaml`) expects — a correct-looking transform pointed at the wrong frame produces identical symptoms.

If you paste the `/imu/data` echo from test 1, your static transform/URDF snippet for the IMU joint, and your `ekf.yaml` `imu0_config`/`imu0_remove_gravitational_acceleration` settings, I can tell you definitively which axis is wrong and what the fix is — rather than both of us guessing.
