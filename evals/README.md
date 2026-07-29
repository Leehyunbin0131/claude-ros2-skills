# Evals — measure the skills instead of trusting them

Current per-skill status: [`RESULTS.md`](./RESULTS.md).

## What is being measured

Two questions, and a skill is verified only when both are answered:

| Axis | Question | Method |
| :--- | :--- | :--- |
| **Effect** | Does this skill change what the agent produces on a task that exercises **its own** content? | A/B pair — identical prompt, same model, once without the skills and once with them |
| **Efficiency** | Is this the **smallest** body that produces that effect? | per-line ablation — remove one line, re-run, see whether the outcome moves |

Grading is mechanical wherever possible, so it can be checked without trusting
us: does the symbol exist in `/opt/ros/jazzy` (`ros2 interface show`,
`ros2 pkg prefix`)? does the command succeed when the grader re-runs it? does the
generated node print the right number against a live publisher? A check returns
pass, fail, or **ungradable** — and ungradable is never scored as a failure.

Cost is a first-class result. A skill that buys +2% quality for +5k tokens is a
bad trade, and without the number "should this content stay?" is an opinion.

## Ground rules

- Fresh headless session per cell, same model in both, tools allowed in both.
- Runs against a **live ROS 2 Jazzy install**, not a machine without ROS. A skill
  whose first instruction is "read the installed defaults" cannot be measured
  where those defaults do not exist.
- **n≥5.** Single runs generate mechanisms that do not survive testing — that has
  already happened here once, and the conclusion had to be retracted.
- Every symbol the agent wrote is checked against the install. One that isn't
  there counts as a hallucination regardless of how plausible it looks.

## Running a pair

```bash
# needs a sourced ROS 2 Jazzy install; ros-jazzy-ros-base is enough for tasks 1-3
MODEL=sonnet ./harness/run_ab.sh 1 runs/$(date +%F)-native
```

Each task brings up the live scenario it needs, and the **same** scenario is up
for both cells, so the only difference stays the skills:

| Task | Skill | Scenario | Graded by |
| :--- | :--- | :--- | :--- |
| 1 | `ros2-core` | `/scan` at 5 Hz, BEST_EFFORT, containing `inf`, `nan`, and readings outside `[range_min, range_max]` | running both generated nodes — the correct minimum is 0.45 m |
| 2 | `ros2-troubleshooting` | `map→odom→base_link` only; writing the sensor TF is the agent's job | publishing each agent's transform and running `check_tf_tree.py` on it |
| 3 | `ros2-core` / `ros2-troubleshooting` | BEST_EFFORT camera at 30 Hz plus a default-RELIABLE subscriber | transcript — reproduces "30 Hz but the subscriber receives 0" exactly |
| 4 | `ros2-dev` | container with `nav2-bringup` installed | mechanical key diff against the shipped `nav2_params.yaml`, then loading the output into Gazebo |
| 5 | `ros2-package` | empty workspace | binary: does `ros2 run` / `ros2 launch` / `ros2 topic echo` work when the grader re-runs them |

Tooling, including the per-line ablation harness:
[`harness/README.md`](./harness/README.md).

## Artifacts

Each run commits its transcripts, generated code and logs under `runs/<date>-<name>/`
with a `NOTES.md` describing what it covered, so any result can be re-graded
independently. PRs attaching graded transcripts are welcome.

`runs/` is currently empty: the first measurement round was deleted along with
its verdicts when the criterion changed. See
[`RESULTS.md`](./RESULTS.md) for what was kept and why, and
[`DESIGN.md`](./DESIGN.md) for the criterion that replaced it.
