# Odometry calibration on real hardware

For `diff_drive_controller`. Nothing here can be settled from a config file or
a simulator — it needs a tape measure and a floor.

Parameter names and their `1.0` baselines verified against
`/opt/ros/jazzy/include/diff_drive_controller/diff_drive_controller_parameters.hpp`
(2026-08-01).

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
Take reported ÷ actual and correct via `left_wheel_radius_multiplier` /
`right_wheel_radius_multiplier` (both baseline `1.0`).

**2. `wheel_separation`** — rotate the robot exactly 5 full turns in place. The
error in reported yaw corrects via `wheel_separation_multiplier` (baseline
`1.0`). Five turns rather than one so the per-turn error is large enough to
read.

**3. Re-verify** with `scripts/check_odom_direction.py` after every tire or load
change. Straight-line drift to one side usually means the two radius
multipliers need to differ slightly.

## Status

**Unverified by this project's ladders**, and unverifiable by them: `ctl1`–`ctl3`
measured `mock_components`, a second controller claiming interfaces, and a
custom C++ `SystemInterface` — none of which touch physical calibration, because
no container can. It is kept for the same reason `frames.md` is: the robot is
not its CAD model, and no doc holds this robot's real geometry.
