# READ THIS FIRST — ROS 2 verification protocol

This protocol guides verification for ROS 2, Gazebo, Nav2, MoveIt, ros2_control, and perception tasks on **Ubuntu 24.04 LTS / ROS 2 Jazzy Jalisco**.

## Environment-Dependent Facts

Do not guess environment-dependent facts (such as exact message fields, parameter names, QoS profiles, topic names, and TF frames) from memory. Pretrained API details are frequently outdated or divergent between distributions.

When implementing or modifying ROS 2 code:

1. **Verify uncertain or distribution-specific APIs** against the local installation (`/opt/ros/jazzy/` via `ros2 interface show`, `ros2 topic list -t`, `ros2 pkg prefix`, `ros2 param list`) or official Jazzy documentation. General ROS concepts and established programming patterns do not require repetitive tool lookups when the API is already unambiguous.
2. **Resolve frame and TF conventions** against REP 103 and REP 105 as ground truth. Refer to `references/frames.md` located inside the loaded `ros2-troubleshooting` skill directory (resolved relative to that skill's path, not the project CWD).
3. **Diagnose silent failures with targeted checks**: When nodes appear running but communication fails, run relevant troubleshooting checks (e.g., QoS compatibility). An exit code of 0 or 1 applies strictly to the checked property; code 2 indicates an inconclusive or invalid request. A diagnostic check does not establish whole-system correctness.

**`rclcpp` is C++ only; `rclpy` is Python only.** They are distinct libraries with different conventions and type signatures. An example in one language translates as an architectural concept, never as a literal namespace import. Use the language appropriate for the task, and verify symbol presence when uncertain.

## Establish Relevant Context Before Writing

Before modifying or writing code, clarify facts relevant to the task if they are not already supplied by the user or workspace:

- **Real hardware, simulation, or both?** Affects `use_sim_time`, physical sensor expectations, and tuning validity.
- **Existing workspace conventions**: Follow the package layout, naming, and launch patterns already present in the workspace rather than imposing new structures.
- **Existing publishers and TF authorities**: Avoid creating duplicate publishers on the same topic or transform frame without coordination.
- **Physical geometry**: Sensor mounting orientations and wheel dimensions must reflect actual hardware, not unverified CAD assumptions.

## Done means it ran

Writing the code is not the deliverable. Report what you actually observed — a build succeeding, `ros2 topic echo` showing data, a lifecycle node reaching `active`, a check script passing — or state plainly that you could not verify and what you would need to.

This is the single highest-value line here. Config that reads correctly and is never started is this pack's most reproducible failure: a Nav2 parameter file that names every plugin correctly and puts every value in the right place, which the servers then refuse to configure. Bringing the same file up once finds it in one sitting. Run what you wrote.

- **State unverified boundaries plainly**: When execution is not possible (e.g., missing hardware, unavailable runtime environment, or execution permission limits), state clearly what could not be run and what would be required to verify it. Do not manufacture passing claims from unexecuted code.
- **Respect execution permissions**: Do not demand or force arbitrary command execution when the operating environment restricts permissions.
- **Safe process management**: When launching runtime probes, bound them with a timeout and record the specific PID or process group. Terminate only processes started during the probe. Never use broad pattern-based cleanup (`pkill -f` or `killall`), which risks killing user or robot system processes. Leave existing publishers and transforms running unless the user requested their modification.

Target: **Ubuntu 24.04 LTS / ROS 2 Jazzy Jalisco**. Legacy (Gazebo Classic, pre-Jazzy APIs) is out of scope unless explicitly asked.
