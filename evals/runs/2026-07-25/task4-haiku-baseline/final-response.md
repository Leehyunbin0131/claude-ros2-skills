Done! I've created `controller_server.yaml` with a complete MPPI controller configuration for a differential-drive robot on Nav2/ROS 2 Jazzy.

**Key highlights:**

- **MPPI Controller** configured as the main path-following controller
- **Differential drive** setup with 2000 batch samples and 25 time steps
- **Velocity constraints**: max 0.5 m/s forward, 1.0 rad/s angular
- **Cost weights**: prioritizes obstacle avoidance (35.0) and goal reaching (5.0)
- **Critics enabled**: ConstraintCritic, CollisionCritic, GoalCritic, PathFollowingCritic, and PreferForwardCritic
- **Collision detection** with 0.10m margin distance
- **Controller frequency**: 20 Hz (typical for Nav2)

The file is ready to use with Nav2's controller server. Adjust the `temperature` (0.1), `gamma` (0.015), and cost weights based on your robot's behavior—increase temperature for more exploration, tune weights for your specific navigation priorities.
