# Authoring useful ROS 2 skills

The objective of this repository is to package focused domain knowledge,
workflows, and diagnostic tools to help developers and agents verify ROS 2
software.

Neither an exhaustive manual nor an empty skill is useful by default.
Choose the smallest amount of guidance that addresses a concrete development
or diagnostic problem, and test what it claims.

## Core Architectural Hypothesis

This project does not claim that providing skills improves the fundamental
reasoning or code generation capabilities of frontier language models. Instead,
it tests an engineering hypothesis: **packaging environment-specific evidence
checks and structured handoff records can reduce verification ambiguity and
context-transfer overhead between sessions or collaborators.**

While the functionality of individual diagnostic and evidence tools has been
verified on concrete fixtures, **reduced handoff cost and overall developer
performance gains remain unproven.**

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
  tests and all-skipped runs. An optional evidence tracking tool captures
  workspace snapshots for handoff.
- `ros2-troubleshooting`: topic visibility does not establish endpoint QoS
  compatibility, and raw IMU axes do not establish the base-frame gravity
  direction. Scripts use native policy checks, TF and validated data.
- `ros2-microros`: retained guidance is explicitly unverified on MCU hardware.
  Its presence is an informational starting point, not evidence of a measured benefit.

## Keep routing and context proportional

The description should name the developer task that benefits. Automatic skill
discovery allows agents to locate skills relevant to the task; do not force
every skill to activate for every generic ROS inquiry. Keep detailed references
out of the main body until their topic is needed.

The shared `CLAUDE.md` supplies the general verification protocol once. Skill
bodies should add concrete task-specific procedures rather than repeat that
protocol. Verify commands against the installed Jazzy environment or official
sources and explain the limits of each result.

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

The project permits focused development workflows with explicit operational
validation and clearly labelled limits before a model benchmark exists. This
is a change in product criteria, not a new performance result. Historical
transcripts, frozen prompts and comparison thresholds remain unchanged; future
experiments must record their own conditions and results.
