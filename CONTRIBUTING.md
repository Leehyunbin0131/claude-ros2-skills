# Contributing

Fixes for outdated links, wrong symbol names, and new skills are all welcome.
The bar for everything: **verifiable over plausible**.

## What the pack is for

Not teaching the model ROS 2 — it already knows a great deal. The failures worth
preventing are not gaps in knowledge, they are gaps in **protocol**: across every
measured run, no baseline cell verified anything before writing, with WebFetch,
Read and Bash allowed throughout. One of them reported a fully working build for a
package `ros2 run` cannot find.

So the position is: **trust the training, supply the minimum direction.** Don't
hand the agent answers — hand it the authoritative source and make it open one.
Three jobs, and nothing else earns space:

1. **Name the source precisely enough to open** — `/opt/ros/jazzy/share/<pkg>/`,
   one doc entry point.
2. **Make opening it a required step with an exit condition.** A bare link is
   inert. The lookup fires when the agent is about to *write* and the skill names
   a specific file or command; it does not fire when the agent is only *answering*.
   "Check this" is weaker than "you are not done until you have shown the output".
3. **State the judgements that exist nowhere as a rule.** Everything else is cost.

## Ground rules

- Target is **Ubuntu 24.04 / ROS 2 Jazzy** only. No Gazebo Classic, no
  pre-Jazzy APIs, no "works on Humble too" hedging inside a skill.
- Skills are **entry-point links + exact symbol names + failure modes**, not
  tutorials. If a section reads like a blog post, cut it to the symbols.
- Every class, method, message, topic, and parameter name you write must be
  checked against the linked Jazzy docs or a local `/opt/ros/jazzy/`
  (`ros2 interface show`, `ros2 topic list -t`). Never from memory.

## What earns its tokens

Every line of a `SKILL.md` is context the agent pays for on load, so the test for
new content is **"could the agent have derived this itself?"**

Three kinds of line, three different treatments:

| Kind | What it is | Treatment | Why |
| :--- | :--- | :--- | :--- |
| **navigational** | one entry point to navigate from, a local ground-truth path | **maximise** | cannot rot into a wrong answer — the agent fetches current truth instead of our copy of it |
| **factual** | symbol names, parameter keys, encodings | **minimise; prefer a pointer** | most numerous, rots every release, and a wrong one gets emitted verbatim |
| **behavioural** | what to do, what to establish before writing | **keep only what survives ablation** | not written as a rule on any doc page; a link will not produce it |

| Prefer | Over |
| :--- | :--- |
| One entry point the agent navigates from (`https://docs.nav2.org/configuration/index.html`) | Twenty deep per-page URLs, each with a description restating its title |
| Local ground-truth paths (`/opt/ros/jazzy/share/...`) | Anything reachable by a web search |
| A symptom → root cause → action row | A paragraph of background |
| Exact symbol names where the model's memory is demonstrably weak | A catalogue of symbols it already knows |

Symptom tables and calibration baselines are the highest-value content here: they
are not in any single doc page, they don't rot on a release, and they map straight
onto a failure someone actually hit. Grow those.

### Three layers, three price tags

| Layer | Paid | Put here |
| :--- | :--- | :--- |
| `description` frontmatter | always, every session | trigger words only |
| `SKILL.md` body | when the skill fires | what to establish first, the loop, symptom table, "done" criterion |
| `references/*.md` in the skill dir | **only when read** | symbol catalogs, per-component detail, tuning tables |

Bulk reference material goes in `references/` and gets a one-line pointer from
the body — see `skills/ros2-dev/`. This is what lets the repo add depth without
taxing every user who loads the skill: a reader asking "why does AMCL diverge"
should not pay for the behavior-tree node list.

Keep bodies around 60–80 lines. If a body is growing past that, the new content
is almost always reference material in disguise.

Boilerplate that repeats what `CLAUDE.md` already says (target distro, "verify
before writing") does not belong in a skill — it is paid for on every load, and
twice over when a task loads two skills.

### Two bars, and which one your line has to clear

| Bar | Question | How | Applies to |
| :--- | :--- | :--- | :--- |
| **True** | Is this correct right now, on Jazzy? | `ros2 interface show`, `ros2 pkg prefix`, grep the installed source | **every line, no exceptions** |
| **Worth it** | Does the agent do this *worse* without the line? | ablate it: run the task with the line and without it, n≥5, mechanical grade | **every line that tells the agent what to do** |

True is the floor, not the bar. The question that decides whether a line ships is
the second one, and it has a direction most people guess wrong: a statement can be
true, non-obvious *to a human*, and still worth nothing, because the model already
produces that behaviour unaided. Measured — on the one task the model knew cold,
the skills bought nothing and cost ~1.4×.

Three outcomes, and only one of them is "keep":

- The model already does it → **cut.** True but free. It is paid for on every load.
- The model does not do it, and the line fixes that → **keep.** This is the payload.
- The model does it *better without the line* → **cut immediately.** Contamination
  is real here: a wrong critic name in `references/symbols.md` was emitted
  **verbatim** by the agent, so the file manufactured the hallucination it existed
  to prevent. **A wrong line is worse than a missing one.**

Intuition about where an agent errs is unreliable. This project has already
had to retract one finding: a plausible failure mechanism was inferred from a
single run and then disconfirmed by a controlled one — the error it claimed to
explain turned out to occur once in 13 cells. If you add a rule
*because* you believe the model errs there, say so in the PR and attach the
failing cell.

**Facts belong behind pointers; rules belong stated.** Prefer naming where the
answer lives (`/opt/ros/jazzy/share/<pkg>/`, one doc entry point) over copying the
answer in — copied symbols rot silently on the next release. The exception is
behaviour: "keep a `LaserScan` reading only when finite and within
`[range_min, range_max]`" is not written as a rule on any doc page, and a link will
not produce it. That rule and the shutdown pattern are the two smallest additions
ever made here, and both appeared near-verbatim in generated code and turned a
wrong answer into the right one.

### Where a rule lives is a correctness decision

Routing is not guaranteed. Measured: one identical prompt selected three
different skills across five runs, and in a stripped install the agent loaded no
skill at all in 4 of 8 cells. So:

- A rule that can be wrong in **several domains** belongs in `CLAUDE.md`, where
  routing cannot miss it — the `rclcpp` is C++ / `rclpy` is Python separation is
  there for this reason.
- A rule that only matters **inside one domain** belongs in that skill.

Promoting to `CLAUDE.md` is not free: it is paid on every session. Keep it to
rules that are short, general, and cheap to state.

### Out of scope — PRs that will be declined

- **Multi-distro support.** Jazzy only, by design. A skill that hedges toward
  Humble is a skill that is wrong on both.
- **Embedding API snippets to raise offline accuracy.** Embedded content rots
  silently and is emitted verbatim when wrong — that has happened here. Entry
  points plus exact symbol names stay the strategy.
- **A router skill, or an index table in `CLAUDE.md`.** Routing happens through
  `description` frontmatter. It is measured, not replaced.

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
