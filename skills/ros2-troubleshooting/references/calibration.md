# Odometry calibration on real hardware

For `diff_drive_controller`. Nothing here can be settled from a config file or
a simulator — it needs a tape measure and a floor.

Parameter names and their `1.0` baselines were checked against the installed
Jazzy header (2026-08-01). The correction direction below follows Jazzy's
[odometry equations](https://github.com/ros-controls/ros2_controllers/blob/jazzy/diff_drive_controller/src/odometry.cpp)
and [application of multipliers](https://github.com/ros-controls/ros2_controllers/blob/jazzy/diff_drive_controller/src/diff_drive_controller.cpp).

## Why the CAD numbers are wrong

Tire deformation under load makes the *effective* wheel radius and separation
differ from the measured chassis. Correct with the controller's built-in
multipliers rather than editing the geometry, so the URDF keeps describing the
robot and the correction stays visible as a correction.

## Order matters

**Radius first.** `wheel_separation` has no effect on straight-line driving, so
a radius error contaminates the separation test but not the other way round. Run
these in order or the second measurement is meaningless.

**1. `wheel_radius`** — drive a tape-measured straight line, e.g. 2.0 m.
With encoder feedback (`open_loop=false`), update both radius multipliers as
`new = old × actual_distance / reported_distance` (default `1.0`). For example,
2.2 m reported over 2.0 m actual needs a factor of `2.0/2.2`, not `2.2/2.0`.
The parameters are `left_wheel_radius_multiplier` and `right_wheel_radius_multiplier`.

**2. `wheel_separation`** — rotate the robot exactly 5 full turns in place. The
error in accumulated, unwrapped yaw corrects `wheel_separation_multiplier`:
`new = old × reported_angle / actual_angle` (default `1.0`). Five turns rather
than one makes the per-turn error easier to read; a single quaternion yaw wraps
at ±π and cannot count full turns.

**3. Re-verify** the distance and angle measurements after tire or load changes.
`scripts/check_odom_direction.py` checks direction only: a PASS does not verify
distance scale or wheel separation. Straight-line drift to one side can require
different radius multipliers; also inspect slip and mechanical alignment.

## Status

**Unverified by this project's ladders**, and unverifiable by them: `ctl1`–`ctl3`
measured `mock_components`, a second controller claiming interfaces, and a
custom C++ `SystemInterface` — none of which touch physical calibration, because
no container can. It is kept for the same reason `frames.md` is: the robot is
not its CAD model, and no doc holds this robot's real geometry.
