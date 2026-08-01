# Contributing

Fixes for outdated links, wrong symbol names, and new skills are all welcome.
The bar for everything: **verifiable over plausible**.

Two things decide what ships here, and [`evals/AUTHORING.md`](./evals/AUTHORING.md)
keeps them apart: a measurement in this repository, which licenses a change to
*this* pack, and Anthropic's
[context-engineering guidance for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models),
which is a strong prior about *any* pack. Read that file before proposing a
structural change — it also records which of the guidance's shifts this pack has
actually tested and which it merely follows.

## What the pack is for

Not teaching the model ROS 2 — it already knows a great deal, and eight domains
of ladder measurement failed to find a single thing it did not. The failures
worth preventing are not gaps in knowledge, they are gaps in **protocol**: with
WebFetch, Read and Bash allowed throughout, only **2 of 10** baseline cells
verified anything against the install before writing. One reported a fully
working build for a package `ros2 run` cannot find.

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
- Skills are **runnable scripts + what only this repository knows**, not
  tutorials and not symbol catalogues. The two that survived measurement are a
  script bundle and one unverifiable-here domain; if a section reads like
  documentation, the install already has it.
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
| A script with an exit code | A paragraph describing what that script would tell you |
| Local ground-truth paths (`/opt/ros/jazzy/share/...`) | Anything reachable by a web search |
| One entry point the agent navigates from | Twenty deep per-page URLs, each with a description restating its title |
| A behaviour the agent measurably omits | A fact it recites correctly when asked cold |

**Symptom → root cause → action tables were the pack's central bet, and it
lost.** They read as the highest-value content — not in any single doc page,
release-stable, mapped to a real failure. Measured against a baseline agent
across eight domains and 24 ladder rungs, not one of them changed an outcome.
Every table in this repository has now been deleted. If you are about to add
one, the burden is on the measurement, not on how useful it looks.

### Three layers, three price tags

| Layer | Paid | Put here |
| :--- | :--- | :--- |
| `description` frontmatter | always, every session | trigger words only |
| `SKILL.md` body | when the skill fires | the script paths, and what only this repo knows |
| `references/*.md` in the skill dir | **only when read** | the detail behind a check |

A body that is growing past ~40 lines is almost always accumulating content the
model already has. The two surviving skill bodies are 45 and 65 lines, and the
larger of the two is the unverified one.

Boilerplate that repeats what `CLAUDE.md` already says (target distro, "verify
before writing") does not belong in a skill — it is paid for on every load, and
twice over when a task loads two skills. This is measured, not stylistic:
`CLAUDE.md` alone moved "verified against the install" from 2/10 to 10/10, and
stacking ten skills on top of it moved nothing further.

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
answer in — copied symbols rot silently on the next release.

The apparent exception is behaviour, and it is worth knowing why it did not
survive. "Keep a `LaserScan` reading only when finite and within
`[range_min, range_max]`" is not written as a rule on any doc page, and it once
measured as one of the two smallest effective additions ever made here — it
appeared near-verbatim in generated code and turned a wrong answer into a right
one. **Those numbers were graded on haiku**, which this project later found does
not transfer, and no sonnet-era rung ever covered it. So it is not in the pack:
a behavioural rule still has to clear the bar on the model that ships, and an old
number is not a smaller version of a current one.

### What the measurement actually taught

Every domain in this pack has now been through a three-rung ladder against the
model it ships against. [`evals/CAPABILITIES.md`](./evals/CAPABILITIES.md) is
the result — what the baseline reaches unaided and where it stops — and
[`evals/LADDER.md`](./evals/LADDER.md) is the method, including the ten grader
defects it had to survive. These are the parts that change how you should write
a line.

**Correct is not the same as useful, and it is not even close.** Most lines that
get cut are true, well-written, and reproduce exactly what the model already
says unaided. Being right is not a reason to keep a line. Before you write one,
ask the model the question cold and read what it gives you — if the answer is
already there, so is the line's fate.

**The failure a line targets can disappear.** `ros2-dev` opened by calling a
dropped package prefix "the single most common startup-killing error"; measured,
every plugin string the model emits unaided is one pluginlib really registers.
`ros2-package` had two lines added earlier because the model kept omitting a
`package.xml` export tag and a `setup.cfg` path — it now supplies both without
help. Content expires. A line that earned its place two releases ago has to
re-earn it, and this pack has now deleted eight skills to that rule.

**A skill can be a liability, not merely inert.** `ros2-moveit` told readers to
call `/servo_node/start_servo`, an interface Jazzy removed; the model prescribes
the same dead service 4 times in 4, so the file was confirming an error rather
than correcting one. Ablation cannot see this — measuring a wrong line only asks
whether the model repeats it, and it does. Only checking the claim against the
install separates "this line is working" from "this line and the model are wrong
together". **Every factual line needs a source you can point at in
`/opt/ros/jazzy/`, not a memory.**

#### Craft lessons from the first-generation method

The three below came from per-line ablation graded on **haiku**, under a method
this project has since retired. They are about *how a line is written* rather
than about any ROS 2 fact, which is why they are kept — but they have not been
re-measured on the shipping model, so treat them as priors, not as results.

**Keep the reason, not just the instruction.** A body that explains a cause and then gives a fix compresses very
naturally into the fix alone — and measurably loses, because the model then
reproduces the action without the diagnosis. "A single-threaded executor cannot
process service responses while executing a blocking callback, so use
`MultiThreadedExecutor`" is worth more than "use `MultiThreadedExecutor`". Cut
the worked example before you cut the *because*.

**A terse summary can be worse than saying nothing.** Not merely worse than the
full text — worse than omission. Omit a topic and the model answers from its own
knowledge, completely. Summarise it badly and your summary becomes the frame the
answer is built on, and whatever you dropped is dropped from the answer too. If
a section cannot be shortened without losing its reasoning, deleting it outright
is the better option.

**Prose often beats a worked example.** Replacing a 23-line `launch_testing`
block with one descriptive sentence tied on every check and *gained* four correct
API details the example never showed; the same substitution worked on a CMake
reference block. A worked example appears to act as a ceiling the model
reproduces and stops at. This only holds when the prose names the specifics —
the exact install path, the exact flag, the exact ordering constraint.

#### What the current method measured

**The lines that survive hardest are the ones the model cannot know.** Filenames
and paths local to this repository, behaviours of scripts shipped beside the
skill, project conventions, and the geometry of a physical robot. Those score
near zero unaided and 1.00 with the file. Everything else competes with what the
model already has — and after eight ladders, *everything else* turned out to be
everything else.

**Every gap found in eight domains was behavioural, not informational.** Four of
them, and what closed each: verifying against the install rather than answering
from memory (2/10 → 10/10, one `CLAUDE.md` paragraph); producing an exit-coded
verdict rather than "looks right" (0/10 → 10/10, a bundled script); running the
QoS code it writes (5/10 → 9/10, `CLAUDE.md`'s "done means it ran"); running the
Nav2 config it writes (0/10 → 30/30, a task that requires reaching `active`).
Nothing was fixed by supplying a fact.

**The cleanest result in the project is a control, and it is worth internalising
before you write anything.** Asked for a Nav2 parameter file, 10/10 cells wrote
one their own servers refuse to configure — valid YAML, correct plugin strings,
`robot_radius` in exactly the right place, and `consider_footprint: true` with
no polygon to consider. Asked for the same file *plus* the stack reaching
`active`, every cell hit the identical error, read it in the log, fixed it, and
passed. **Same model, same wrong belief, zero difference in information.** A
skill documenting `consider_footprint` would have looked like a triumph; what
actually closed the gap was requiring the thing to run.

So the question to ask about a proposed line is not "is the model wrong about
this?" — it may well be — but **"would running the code have told it?"** If yes,
the line is not the fix.

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
  silently and is emitted verbatim when wrong — that has happened here. The
  install and the official docs are the strategy.
- **Re-adding a deleted domain skill without a ladder that fails.** Eight were
  removed on measurement. Restoring one needs a rung the baseline agent does not
  clear, not an argument that the content is correct or useful.
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
3. Add a row to the skills table in `README.md`.
4. **Attach the measurement.** A new skill needs a ladder — three rungs, each
   adding a named mechanism, graded by running the artifact rather than reading
   it. [`evals/LADDER.md`](./evals/LADDER.md) has the rules, including the ones
   that stop a ladder from being tuned until it produces a result. A skill with
   no ladder can still be merged, but it ships labelled unverified, as
   `ros2-microros` does.

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

If your change claims to improve agent output, attach a graded transcript. The
harness is in [`evals/harness/`](./evals/harness/) and its README covers running
a round; [`evals/LADDER.md`](./evals/LADDER.md) covers designing one that cannot
be tuned into agreeing with you.
