# Verify the artifact a developer will actually use

Apply the row that matches the change; these are alternatives, not a checklist
to execute on every request. Match names and launch arguments to the workspace.
Use its existing simulation or test fixture when runtime verification is needed.

| Changed artifact | Evidence to collect | What a successful build misses |
| :--- | :--- | :--- |
| Python or C++ executable | After sourcing the new install in a separate shell, `ros2 pkg executables <package>` lists it; the actual entry point starts and produces the requested output | A module may import from the source tree while its console entry point or installed library is missing |
| Custom message/service/action | `ros2 interface show <package>/<msg\|srv\|action>/<Name>` resolves; a consuming node imports/links and exchanges the interface | Generator configuration, exported dependencies and runtime type support are separate from compiling the producer |
| Launch or YAML | The installed package share directory contains the files; invoking the installed launch entry point loads the intended parameters | Files beside source code are not automatically installed; valid YAML may have the wrong node namespace |
| Lifecycle component (e.g. Nav2) | Required nodes reach the requested state and their functional output is observed | A started process or discovered node does not imply successful `configure` or `activate` |
| Subscriber or sensor processing | Inspect the producer **and consumer** endpoint QoS, then run the real callback on representative data | `ros2 topic echo` negotiates its own QoS and does not prove the application's subscription works |
| Interface or library consumed elsewhere | Build and exercise affected consumers, with the intended install prefix visible | Testing only the producer can miss a downstream import or ABI/API mismatch |

For QoS or TF/IMU/odometry diagnosis, use the installed `ros2-troubleshooting`
skill's checks. Those runtime diagnostics do not replace a package's tests.
For physical calibration, record external measurements; simulated or internally
consistent odometry cannot establish the robot's actual distance or direction.

Inspect installed Jazzy message definitions and package APIs before adapting an
example. [Colcon's workspace guide](https://colcon.readthedocs.io/en/released/user/what-is-a-workspace.html)
explains why build and runtime shells should be separate. Reports should name
the package, relevant command, observed output and anything left unverified.
