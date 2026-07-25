Here's a controller server YAML configuration for Nav2 with the MPPI controller on Jazzy for a differential-drive robot:

```yaml
controller_server:
  ros__parameters:
    use_sim_time: false
    controller_frequency: 20.0
    min_x_velocity_threshold: 0.001
    min_theta_velocity_threshold: 0.001
    failure_tolerance: 0.3

    # MotionControllerServer configuration
    motion_model_type: "DiffDrive"

    # MPPI Controller
    FollowPath:
      plugin: "mppi_generic::ControllerServer"
      parameters:
        # Model parameters
        model_name: "DiffDrive"
        batch_size: 2000
        time_steps: 15
        
        # Dynamics
        model_dt: 0.1
        vx_std: 0.2
        wz_std: 0.4
        vx_max: 0.5
        vx_min: -0.5
        wz_max: 1.0
        wz_min: -1.0

        # Controller
        temperature: 0.0015
        gamma: 0.015
        
        # Costs
        path_tracking_cost: 1.0
        goal_cost: 5.0
        smooth_cost: 0.0
        collision_cost: 100.0
        near_goal_max_lin_vel: 0.3
        
        # Map resolution for collision checking
        map_downsample_factor: 1
        
        # Visualizations
        visualize: true
        visualize_scale: 1.0

        # Constraints
        max_robot_pose_search_dist: 2.0
        prune_plan: true
        prune_distance: 2.0

        # Safety/recovery
        use_feedforward: true
        allow_reversing: true

controller_out:
  ros__parameters:
    use_sim_time: false
```

**Key parameters to adjust for your robot:**

- `vx_max`, `vx_min`: Maximum/minimum linear velocity
- `wz_max`, `wz_min`: Maximum/minimum angular velocity  
- `batch_size`: Number of trajectories to sample (2000 is good baseline)
- `time_steps`: Prediction horizon (15 steps at 0.1s dt = 1.5s prediction)
- `temperature`: Controls trajectory diversity (lower = more focused)
- `collision_cost`: Penalizes collisions with obstacles
- `allow_reversing`: Set to `false` if your robot can't go backwards

**Installation check:**
```bash
# Verify MPPI is installed on Jazzy
apt-cache search ros-jazzy-mppi
```

Place this in your Nav2 params file (e.g., `nav2_params.yaml`) or split into a dedicated controller config file. The plugin name assumes you have `ros-jazzy-nav2-mppi-controller` installed.