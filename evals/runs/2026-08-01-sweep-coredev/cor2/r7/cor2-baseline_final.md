# Run summary — `cor2-baseline_result.jsonl`

- model: `claude-sonnet-5`
- turns: 5
- total_cost_usd: 0.2468568
- tool calls: **4**

## Tool calls, in order

1. `Write` — /tmp/eval-cor2-baseline-5D73/node.py
2. `Bash` — python3 -m py_compile /tmp/eval-cor2-baseline-5D73/node.py && echo OK
3. `Bash` — python3 -c "import rclpy" 2>&1 | head -5; source /opt/ros/jazzy/setup.bash 2>/dev/null && echo "jazzy sourced" || echo "no jazzy install found"
4. `Bash` — source /opt/ros/jazzy/setup.bash && timeout 5 python3 node.py; echo "EXIT_CODE=$?"

## Final message

Confirmed working: 20 `TF <t> <x>` lines at 20 Hz with x increasing at 0.05 m/s, followed by the `EXTRAP` line with the real tf2 extrapolation exception text, and a clean exit code 0.

`node.py` broadcasts `odom -> base_link` via `TransformBroadcaster` while also feeding a local `tf2_ros.Buffer` directly (avoiding a flaky race against its own `/tf` subscription), does a same-timestamp `lookup_transform` each cycle, and on the 20th cycle also attempts a lookup 5 s in the future, catching `TransformException` to log `EXTRAP <message>` instead of crashing.
