# Frames, axes, and physical misalignment

Ground truth for any frame or TF question, per REP 103 (units and coordinate
conventions) and REP 105 (frame relations).

- REP 103: `https://www.ros.org/reps/rep-0103.html`
- REP 105: `https://www.ros.org/reps/rep-0105.html`
- tf2 concepts: `https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html`

## REP 103 body axes

| Axis | Direction |
| :--- | :--- |
| `+X` | Forward — `cmd_vel.linear.x > 0` **must** move the body forward |
| `+Y` | Left |
| `+Z` | Up |
| `+Yaw` | Counter-clockwise, i.e. turning left |

Code math agreeing with itself proves nothing about which way the hardware
faces. A frame claim is settled by a measurement — `scripts/check_tf_tree.py`,
`check_imu_gravity.py`, `check_odom_direction.py` — or it is not settled.

## Misalignment symptoms

**Robot moves backward when commanded forward (`cmd_vel.linear.x > 0`)**
Motor wiring or PWM sign inverted in the hardware interface or the diff drive
controller; wheel encoder direction reversed; or `base_link` rotated 180°
(`yaw = 3.14159`) relative to `odom`. Inspect the controller's `wheel_radius` /
`left_wheel_radius_multiplier` / joint command signs, then push the robot
forward by hand and confirm body-frame displacement is positive.

**Nav2 costmap upside down, or obstacles spawn behind the robot**
The `base_link` -> `laser_frame` transform carries an inverted roll or yaw
because the sensor is mounted upside-down or backwards. `ros2 run tf2_ros
tf2_echo base_link laser_frame` and compare RPY against the physical mount.

**EKF odometry (`robot_localization`) diverges or spins**
IMU `angular_velocity.z` has the opposite sign to wheel-odometry yaw rate
during turns, or the stationary gravity vector sits on `+X`/`+Y` instead of
`+Z`. `ros2 topic echo /imu/data` at rest: `linear_acceleration.z` must be
~`+9.81` m/s².

## Diagnostic order for a direction fault

1. Push the robot forward 1 m by hand. `ros2 topic echo /odom` — displacement
   along body heading must be positive.
2. Turn the robot left by hand. `ros2 topic echo /imu/data` —
   `angular_velocity.z` must be positive.
3. `ros2 run tf2_ros tf2_echo base_link laser_frame` — static mount matches
   hardware.

## Prevention

- Fix an inverted motor in the `ros2_control` config or the hardware interface.
  Flipping a sign in application logic moves the fault somewhere harder to find.
- Frame IDs carry no leading slash: `map`, `odom`, `base_link`, `laser_frame`.
