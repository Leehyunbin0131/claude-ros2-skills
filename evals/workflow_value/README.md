# Interface-migration usefulness study

The [protocol](PROTOCOL.md) compares the unchanged 0.1.2 pack with no pack in six
fresh Opus 5.5 Low sessions. Three variants exercise one existing-workspace
interface migration, each with Python and C++ consumers. This is a descriptive
study of that workflow; successful release acceptance does not establish added
value over the baseline.

## Reproduce the controls first

Use Ubuntu 24.04 with Jazzy, colcon, rosidl_default_generators,
ament_cmake_gtest and pytest. The tested local Python runtime lives at
`/tmp/ros2-skill-validation-venv`; `WV_VENV_BIN` overrides its `bin` for the grader.
No command below installs system packages or contacts a model.

```bash
source /opt/ros/jazzy/setup.bash
export PATH=/tmp/ros2-skill-validation-venv/bin:$PATH
python3 evals/workflow_value/test_runner.py
python3 evals/workflow_value/test_oracle.py
# Requires Linux unprivileged user/mount namespaces and that local runtime:
WORKFLOW_ISOLATION_TEST=1 python3 evals/workflow_value/test_runner.py
# All variants; choose a fresh evidence path. This takes several minutes.
WV_ORACLE_CONTROLS=1 WV_SEEDS=0,1,2 \
  WV_CONTROL_OUTPUT=/path/to/new/control-evidence \
  python3 evals/workflow_value/test_oracle.py Controls
```

Pure tests check report parsing, failure classification, instrumentation and
process/environment invariants. ROS controls pass a reference implementation and
reject omitted consumer updates, runtime bypass, weak tests and test failures
that are not assertions. CI runs variant 0; the study requires all three variants
before its first model call. An interrupted control run is not a passed suite.

## Frozen model calls

These commands **make real Claude calls** using the current authenticated
account. They are for an explicitly authorized evaluation. They do not copy or
publish credentials. Review the protocol, validate controls and choose unused
paths first. Keep outputs outside the cell parent and keep cells outside `/tmp`.

```bash
python3 evals/workflow_value/run.py freeze /path/to/new/freeze.json
python3 evals/workflow_value/run.py 1 \
  /path/to/cells/01 /path/to/private-results/01 \
  --freeze /path/to/new/freeze.json \
  --runtime /tmp/ros2-skill-validation-venv \
  --mask /path/to/control-evidence
```

Run cells 1 through 6 sequentially in the protocol's fixed order. Use a separate
new cell/output directory for each. Cells 2, 4, and 6 also require
`--pair-manifest` pointing to the preceding cell's `manifest.json`; the runner
refuses a model call if task/source hashes or declared settings differ.
A per-user lock prevents concurrent model
cells. The runner prebuilds the original workspace, verifies isolation, loads the
pack outside the workspace only for treatment, and retains the final project,
paired tool actions, delivery evidence and independent grader output. The
original overlay is inherited by model tool shells; the grader starts from a
clean underlay and source copy. An artifact pass alone does not establish valid
delivery, clean action audit, accurate reporting, or compliance with project rules.

Private `private-session.jsonl` may contain model reasoning. **Do not publish it.**
Review and sanitize paired actions, final answers, manifests and submitted sources
before publishing evidence. Action logs exclude thinking blocks but can still
contain paths or secrets from tools; sanitization remains necessary. All attempts
and infrastructure failures belong in the report. Do not silently relabel an
invalid cell as a model failure or a passing cell as proof that skills helped.
