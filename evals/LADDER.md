# The difficulty ladder

How to find what the model cannot reach, without manufacturing it.

## Why this replaces the audit

Rounds 1–5 asked one question: *does the shipped line change anything?* That
question can only ever delete. Five rounds produced two keeps and 40 deleted
lines, and the two keeps were a bundled script and one paragraph of
`CLAUDE.md` — nothing that any `SKILL.md` says.

But a skill scoring 120/120 against no-skill on `t5` does not mean packaging is
easy. It means **that task** was inside what the model reaches unaided. The
useful question is the other one:

> **Where does the model stop being able to do this on its own?**

Find that point, and the content to write is whatever is on the far side of it.
Never find it, and the skill really is unnecessary. Either answer is a result.

## The thing that would make this worthless

Raising difficulty until the model fails is trivially easy. Any skill can be
"proved necessary" by asking for something absurd. A ladder that stops when the
answer is the one you wanted is not measurement — it is search dressed as
measurement, and it is a more seductive version of the error that caused the
reverted reduction.

Six rules, all fixed before any rung of a ladder runs.

1. **The whole ladder is written first.** Every rung, in full prompt text, before
   any cell runs. A written rung is frozen — it cannot be edited after it has
   been run, not even for a typo that changes nothing.

2. **Rungs are defined by mechanisms added, not by difficulty felt.** Each rung
   names the specific things it adds — a second build system, an interface that
   depends on another package's interface, a component registration, a test that
   must pass. "Harder" is not a definition. If you cannot list what a rung adds
   as a set of mechanisms, it is not a rung.

3. **The ladder has a fixed length: three rungs per skill.** Decided here, once,
   for every skill.

4. **Stop at the first rung that fails.** Not the rung with the biggest effect.
   If L2 fails, L3 is not run — the gap is at L2 and that is where the content
   gets written.

5. **An exhausted ladder is a verdict, not a prompt to extend it.** Baseline at
   ceiling through L3 means the skill is unnecessary and gets cut. **Adding a
   rung 4 is forbidden.** This is the rule the whole document exists for.

6. **The failure must be diagnosed mechanically.** Which real-outcome check
   dropped, in how many cells, and what the cells actually produced on disk. Not
   a story read out of transcripts.

## What a rung is

A task with **real-outcome graders only** — something built, run, or checked by
a tool, never a phrasing match. Rungs run **`baseline` only**, n=10: the question
is whether the model reaches it, and a real outcome answers that without a
comparison cell. That also halves the cost of climbing.

**Failure threshold, fixed:** a rung fails if any real-outcome check comes back
**≤ 7/10**. Three cells in ten getting it wrong is a gap; one is noise.

**Every rung's graders are validated against deliberately broken reference
material before the rung runs.** A grader that has only seen good answers is not
validated. This has already caught one design that would have passed three
broken packages, because all three exit `colcon build` with code 0.

## What happens after a rung fails

Finding the gap is half of it. The other half is finding out whether text fixes
it.

1. **Diagnose.** Which check, how many cells, what they produced.
2. **Write the smallest line** that addresses exactly that. Not the topic — the
   failure.
3. **Verify the line, on the same rung, n=10:** `baseline` vs
   `baseline + that line`. Nothing else installed. This is the only comparison
   in the new method, and it tests one line at a time.
4. **The line ships only if the check it targets moves significantly.** If it
   does not, text is not the fix. The gap may need a bundled script — that is
   category 2, the one thing already measured to work (round 2, q<0.001) — or it
   may not be fixable, which is also worth writing down.

A line that fails step 4 is not shipped with an argument attached. That is how
622 lines happened.

### `patch` must not contain `CLAUDE.md`

The `patch` cell installs the candidate line **and nothing else** — no
`CLAUDE.md`, no other skill, no scripts. This is not a detail; it is the one way
phase 2 can go wrong, and it has already gone wrong once at task level.

`run_ab.sh`'s `skills` cell copies `CLAUDE.md` in alongside the skills, and
`CLAUDE.md` contains, verbatim, several of the behaviours the graders measure:

| `CLAUDE.md` says | which is the grader |
| :--- | :--- |
| "Do NOT answer ... from memorized knowledge ... verify against local `/opt/ros/jazzy/`" | `t1_searched_or_read` |
| "Ask when the request doesn't say" | `t3_asked_before_writing` |
| "Report what you actually observed — a build succeeding, `ros2 topic echo` showing data, a check script passing" | `t2_exit_code_read`, and the shape of `t5`/`t6` |

Round 4 caught this for `t1` and had to retract an attribution. **The flaw is
systemic, not a `t1` quirk.** It did not produce a false published claim
elsewhere — `t3` was null, round 2's `t2` comparison had no `CLAUDE.md` in either
cell, and `t5` was 120/120 in both — but every one of those was luck, not design.

A `patch` cell that shipped `CLAUDE.md` would make every candidate line look
effective, because `CLAUDE.md` would be doing the work. Any future condition that
needs `CLAUDE.md` present must have it present in **both** cells.

## The ladders

Three rungs per skill, all written before running. `L1` for `ros2-package` is
`t5`, already run.

### `ros2-package`

| Rung | Mechanisms added | Status |
| :--- | :--- | :--- |
| **L1** | `ament_python` node package; `ament_cmake` interface package with one `.msg`; launch file; params file | **run — 10/10 on all six checks** |
| **L2** | + a C++ node package (`ament_cmake` with an executable, which L1 never had); + a `.srv` consumed by both the C++ and the Python node; + a launch file that includes the other package's launch file | pending |
| **L3** | + a message field typed by another package's message (`DEPENDENCIES`); + a composable node registered through `rclcpp_components` and loaded into a container at launch; + a `colcon test` that must pass | pending |

L2 exists because L1 left two claims in the file unexercised — the `ament_cmake`
`lib/${PROJECT_NAME}` install rule and `install(DIRECTORY ...)` — for the
specific reason that L1 had no C++ executable. That is a mechanism gap, not a
difficulty preference, which is what rule 2 requires.

**L2's graders, validated before the rung ran** (`t6_check.sh`), against a
correct workspace and two carrying one real defect each:

| variant | `builds` | `srv` | `cpp_run` | `py_run` | `composed` | `service` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| correct | pass | pass | pass | pass | pass | pass |
| C++ installed to `bin/` | pass | pass | **FAIL** | pass | FAIL | FAIL |
| C++ `launch/` not installed | pass | pass | pass | pass | **FAIL** | FAIL |

Both defects **build with rc=0**, as at L1. The two leave different signatures,
which is what makes rule 6 possible:

- `cpp_run_works` fails → wrong install destination
- `cpp_run_works` passes but `composed_launch` fails → `launch/` never installed

### A silent failure found while building the L2 fixtures

Not part of any rung, recorded because it is a real property of this install and
was found the hard way. The first L2 reference workspace scored 2/6 on the
*correct* variant. The cause was in the fixture, not the checker: its
`package.xml` files were missing
`<export><build_type>ament_cmake</build_type></export>`.

Without that export, colcon identifies the package as **catkin**, generates
catkin-style environment hooks, and **never puts the package on
`AMENT_PREFIX_PATH`**. Consequences, in order of how much they mislead:

- `colcon build` exits **0** and reports the package finished.
- The files are all installed, in the right places.
- `ros2 interface show <pkg>/...` says `Unknown package`.
- `ros2 run <pkg> <exe>` says `Package not found`, with the executable sitting
  at `install/<pkg>/lib/<pkg>/<exe>`.

It is not a rung mechanism because `ros2 pkg create --build-type ament_cmake`
writes the export, so a task cannot force an agent into it without asking for
something artificial. It is exactly the shape of thing this project is looking
for, and it is here so it is not lost.

### The remaining six

Ladders get written when each skill's turn comes, under the same six rules, and
before any of its cells run. Recorded here as they are written so the order
cannot be rearranged after the fact.

| Skill | Ladder |
| :--- | :--- |
| `gazebo-sim` | not yet written |
| `ros2-troubleshooting` | not yet written |
| `ros2-perception` | not yet written |
| `ros2-core` | not yet written |
| `ros2-testing` | not yet written |
| `ros2-dev` | not yet written |
| `ros2-moveit` | not yet written |

## What the files become

The current shape of a `SKILL.md` — architecture paragraph, documentation entry
point table, symptom/cause/action table, tuning baselines — is a textbook's
shape. Five rounds say a textbook is what the model already has.

New content is written in one shape only:

```
## <the failing case, in one line>

**Measured:** <check> failed <n>/10 unaided, at ladder rung <L>.
<The minimum thing to do differently.>
```

Two kinds of content do **not** get written, because they have been measured and
belong elsewhere:

- **Documentation entry points.** No measured effect anywhere.
- **"Verify against the install before writing it."** Round 4: `CLAUDE.md` alone
  produces this 10/10, and adding all ten skills on top moves nothing. It stays
  in `CLAUDE.md`, once.

Existing files are **not** rewritten into this shape ahead of their ladder.
Converting ten files on the strength of a method that has produced one measured
gap so far would be the reverted reduction again, with better prose.
