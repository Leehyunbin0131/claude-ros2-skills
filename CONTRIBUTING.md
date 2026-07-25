# Contributing

Fixes for outdated links, wrong symbol names, and new skills are all welcome.
The bar for everything: **verifiable over plausible**.

## Ground rules

- Target is **Ubuntu 24.04 / ROS 2 Jazzy** only. No Gazebo Classic, no
  pre-Jazzy APIs, no "works on Humble too" hedging inside a skill.
- Skills are **entry-point links + exact symbol names + failure modes**, not
  tutorials. If a section reads like a blog post, cut it to the symbols.
- Every class, method, message, topic, and parameter name you write must be
  checked against the linked Jazzy docs or a local `/opt/ros/jazzy/`
  (`ros2 interface show`, `ros2 topic list -t`). Never from memory.

## What earns its tokens

Every line of a `SKILL.md` is context the agent pays for on load, so the test
for new content is **"could the agent have derived this itself?"**

| Prefer | Over |
| :--- | :--- |
| One entry point the agent navigates from (`https://docs.nav2.org/configuration/index.html`) | Twenty deep per-page URLs, each with a description restating its title |
| Exact symbol names (`nav2_mppi_controller::MPPIController`, `16UC1` = mm) | Prose explaining what the component does |
| A symptom → root cause → action row | A paragraph of background |
| Local ground-truth paths (`/opt/ros/jazzy/share/...`) | Anything reachable by a web search |

Symptom tables and calibration baselines are the highest-value content here:
they are not in any single doc page, they don't rot on a release, and they map
straight onto a failure someone actually hit. Grow those.

Boilerplate that repeats what `CLAUDE.md` already says (target distro, "verify
before writing") does not belong in a skill — it is paid for on every load, and
twice over when a task loads two skills.

## Adding or editing a skill

1. `mkdir skills/<name>` with a `SKILL.md`. Frontmatter needs `name` and
   `description` — **quote the description if it contains a colon**, or the
   YAML silently breaks.
2. The `description` **is** the routing mechanism: it is always in context, so
   make it list the concrete triggers (tools, file names, symbols) a user would
   mention. There is no master-router skill and no index table in `CLAUDE.md` —
   don't add one back.
3. Add a row to the skills table in `README.md` (and ideally the translations).

## Adding a verification script

Scripts live in `skills/ros2-troubleshooting/scripts/` so they ship with the
skill on every install path. They follow one pattern (see `check_imu_gravity.py`):

- Pure decision logic in module-level functions — no `rclpy` import outside
  `main()` — so it's unit-testable without ROS.
- Add tests for that logic to `test_checks.py` in the same directory.
- Exit codes: `0` PASS, `1` FAIL, `2` could not sample (no data / no ROS).
- The failure message must say what's physically wrong and what to do, not
  just "check failed".

## Before opening a PR

```bash
python3 -m py_compile skills/ros2-troubleshooting/scripts/*.py
python3 skills/ros2-troubleshooting/scripts/test_checks.py
```

CI additionally link-checks every URL in every `.md` (lychee, weekly cron) —
a dead docs link fails the build.

If your change claims to improve agent output, consider attaching a graded
transcript per [`evals/README.md`](./evals/README.md).
