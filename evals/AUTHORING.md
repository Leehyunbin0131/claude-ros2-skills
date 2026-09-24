# Authoring useful ROS 2 skills

The current objective is to help an agent produce and verify working ROS 2
software. Neither a large manual nor an empty skill is useful by default.
Choose the smallest amount of guidance that addresses a concrete development
problem, and test what it claims.

## Choose the intervention from the failure

A failure can arise from missing context, an incorrect API assumption, an
unexecuted development step, a packaging defect or a physical mismatch. Do not
assume every failure needs another rule, or that every failure is merely
behavioural. Inspect the workspace and observations before choosing between
source pointers, a workflow, a focused reference and a runnable diagnostic.

Examples in the current pack:

- `ros2-development`: building a package does not establish that its entry point
  was installed or that its tests ran. The workflow checks the installed
  artifact, and a bundled report check distinguishes executed tests from zero
  tests and all-skipped runs.
- `ros2-troubleshooting`: topic visibility does not establish endpoint QoS
  compatibility, and raw IMU axes do not establish the base-frame gravity
  direction. Scripts use native policy checks, TF and validated data.
- `ros2-microros`: retained guidance is explicitly unverified on MCU hardware.
  Its presence is not evidence of a measured benefit.

## Keep routing and context proportional

The description should name the developer task that benefits. Do not make every
skill activate for every ROS question. Keep detailed references out of the main
body until their topic is needed. A short table may be useful when it changes a
verification choice; a large catalogue of facts the agent can look up usually
is not.

The shared `CLAUDE.md` supplies the general protocol once. Skill bodies should
add concrete task-specific procedures rather than repeat that protocol. Verify
commands against the installed Jazzy environment or official sources and explain
the limits of each result. An inconclusive check does not prove a robot defect.

## State the evidence level

Operational tests and model evaluations answer different questions. Validate a
new script with realistic passing, failing and absent-data cases. Exercise a
new workflow on representative artifacts. Record this as **tool/workflow
validation**, not as proof that prose improves an agent.

Before claiming improved model performance, run a controlled comparison: the
same tasks, environment, model/settings and tools, varying only the candidate
change. Preserve all results, including errors and excluded cells, and use the
predeclared [evaluation method](LADDER.md). A single successful session is a
useful example, not a quantitative generalization.

## Historical evidence and the change in direction

Earlier revisions favoured removing all content the baseline could derive
unaided and described the ladders as exhausted. The [artifact reconciliation](CAPABILITIES.md)
shows that several published totals are not reproducible and some historical
transcripts no longer exist. Those records remain useful observations, but do
not justify a universal rule that domain prose cannot help.

The project now permits focused development workflows with explicit operational
validation and clearly labelled limits before a model benchmark exists. This
is a change in product criteria, not a new performance result. Historical
transcripts, frozen prompts and comparison thresholds remain unchanged; future
experiments must record their own conditions and results.
