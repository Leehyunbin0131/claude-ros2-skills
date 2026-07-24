# Contributing

Fixes for outdated links, wrong symbol names, and new skills are all welcome.
The bar for everything: **verifiable over plausible**.

## Ground rules

- Target is **Ubuntu 24.04 / ROS 2 Jazzy** only. No Gazebo Classic, no
  pre-Jazzy APIs, no "works on Humble too" hedging inside a skill.
- Skills are **doc-link catalogs + exact symbol names**, not tutorials. If a
  section reads like a blog post, cut it down to the link and the symbols.
- Every class, method, message, topic, and parameter name you write must be
  checked against the linked Jazzy docs or a local `/opt/ros/jazzy/`
  (`ros2 interface show`, `ros2 topic list -t`). Never from memory.

## Adding or editing a skill

1. `mkdir skills/<name>` with a `SKILL.md`. Frontmatter needs `name` and
   `description` — **quote the description if it contains a colon**, or the
   YAML silently breaks.
2. Keep the structure of the existing skills: numbered sections, official doc
   URLs with one-line descriptions, a symptom table where the domain has
   classic failure modes.
3. Add a routing row to the tables in `README.md` **and** `CLAUDE.md`.

## Adding a verification script

Scripts in `scripts/` follow one pattern (see `check_imu_gravity.py`):

- Pure decision logic in module-level functions — no `rclpy` import outside
  `main()` — so it's unit-testable without ROS.
- Add tests for that logic to `scripts/test_checks.py`.
- Exit codes: `0` PASS, `1` FAIL, `2` could not sample (no data / no ROS).
- The failure message must say what's physically wrong and what to do, not
  just "check failed".

## Before opening a PR

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_checks.py
```

CI additionally link-checks every URL in every `.md` (lychee, weekly cron) —
a dead docs link fails the build.

If your change claims to improve agent output, consider attaching a graded
transcript per [`evals/README.md`](./evals/README.md).
