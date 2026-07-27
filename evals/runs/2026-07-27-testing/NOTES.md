<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Per-claim ablation — `ros2-testing`, 2026-07-27

Third skill, and the first run to test three manipulation types instead of one:
**deletion** (`ablate:<id>`, and `ablate:<id>+<id>+...` for claims that look like
they restate the same behaviour), **addition** (`only:<id>` — does this one claim,
alone, with nothing else in context, already produce the effect), and **position**
(`reorder:4,1,2,3` — the same 14 claims, with the symptom table moved ahead of the
doc pointers instead of after the code examples). Requested explicitly: cover all
three case types, but hold the repeat count to the minimum that can still resolve
anything.

| | |
| :--- | :--- |
| Method | every claim ablated singly; two redundancy groups declared *before* running, from reading the body, not discovered after the fact from Δ=0 collisions; every claim also run `only:` (alone) and the whole body run `reorder:`; content injected via `--append-system-prompt`; `--tools ""` |
| Probes | 4, covering all 14 claims: `colcon-trust`, `rosbag2-write`, `launch-testing-node`, `testing-diagnose` |
| Sample | initial sweep at **n=4** — the floor for this design: n=3 can never reach p<0.05 even on a perfect 0/3 vs 3/3 split, so n=4 is the smallest n where the method can say anything at all. 208 cells, $2.20. Several claims came back ambiguous or below the project's n≥5 bar for a "worth it" call — topped up to n≥8 (one to n=16). 328 cells total, $3.56 |
| Confirmation | the two claims that came back CUT were removed from `skills/ros2-testing/SKILL.md` (78 → 76 lines) and the live body re-measured whole in a separate run dir, [`../2026-07-27-testing-confirm/`](../2026-07-27-testing-confirm/NOTES.md) — old-full 124/124 vs new-full 104/104, p=1.00 |
| Total | 392 cells, $4.14 |

## Position: a clean null, not a noisy one

`full` vs `reorder:4,1,2,3` (symptom table moved to open the document, doc
pointers moved to close it) pooled over all 4 probes at n=4: **52/52 vs 52/52,
p=1.00.** This is not underpowered — both sides are already at the ceiling with
zero variance on either side, so no additional n would move it. For a body this
size, section order inside `SKILL.md` does not measurably change what the model
writes. No further top-up attempted; there is nothing for one to resolve.

## Addition: most claims are independently sufficient — and that sharpens the redundancy story

`only:<id>` keeps the probe's task prompt (it is never part of the system
prompt) and replaces the system-prompt content with just that one claim's raw
text — "does this single line, alone, already produce its own effect." 0/196
`only:` cells came back ungradable, so unlike `protocol` (11.5% ungradable) this
condition graded cleanly.

For 17 of the 18 claim→check pairs a claim owns, `only:<claim>` matched or
nearly matched `full`'s ceiling on its own check — mostly a clean 4/4 — even for
claims whose `naked` baseline was low:

| Claim | Check | naked | **only** | full |
| :--- | :--- | ---: | ---: | ---: |
| `a-programmatic-rosbag2-writer:01` | `writer_create_topic` | 2/8 | **4/4** | 8/8 |
| `4symptom:06` | `simtime_cause` | 2/16 | **4/4** | 16/16 |
| `b-integration-testing:01` | `exit_code_check` | 0/3 | **4/4** | 4/4 |

The one exception is the claim already flagged as the safer of the two cuts:

| Claim | Check | naked | **only** | full |
| :--- | :--- | ---: | ---: | ---: |
| `4symptom:03` | `hang_cause` | 0/16 | **2/4** | 16/16 |

This is a second, independent line of evidence for the same conclusion the
deletion side reached, not a new finding on its own: the RUN and READY groups'
members are each *individually sufficient* (this table) **and** *individually
unnecessary once another member is present* (the deletion section above) — the
textbook definition of redundancy, now shown from both directions instead of
deletion alone. And `4symptom:03` is weak on both sides — 2/4 alone, and Δ=0.00
when removed from a body that still has the READY group — which is a more
confident cut than either measurement would be by itself.

## Deletion — declared groups, not discovered ones

Two clusters looked like the same behaviour stated twice, from reading the body
before running anything — same shape as `ros2-core`'s QoS/bounds/shutdown groups,
but declared up front here instead of noticed after single-ablation collisions:

| Group | Members | Behaviour |
| :--- | :--- | :--- |
| RUN | `2running-tests:01`, `2running-tests:02`, `4symptom:01`, `4symptom:02` | "don't trust the `colcon test` summary — check the count, use `--verbose`" |
| READY | `b-integration-testing:01` (code), `b-integration-testing:02` (prose) | `ReadyToTest()` marks the launch/test boundary |

Both confirmed the pattern: every member alone measured Δ≈0 (INERT), and the
group removed together broke real checks.

| Group | Check | P(full) | P(drop all) | p |
| :--- | :--- | ---: | ---: | ---: |
| RUN | `checks_test_count` | 8/8 | 2/8 | **0.007** |
| RUN | `names_test_result` | 8/8 | 3/8 | **0.026** |
| READY | `post_shutdown` | 11/11 | 4/12 | **0.001** |
| READY | `exit_code_check` | 11/11 | 4/12 | **0.001** |

Both groups: **KEEP all members.** As with `ros2-core`, this only proves the
declared group as a whole is load-bearing — it does not identify whether a
strict subset of 3-of-4 (RUN) or a different split would be equally sufficient,
and that question was not pursued given the repeat-count budget for this run.

## The "ablate below naked" shape, twice more — one noise, one real

Two claims showed the specific pattern that turned out to be a real, hidden
regression in both prior runs — ablated score sitting *below* naked, not just
below full, despite p>0.05 at low n. This time the two cases split:

| Claim | Check | n | naked | full | ablate | Δ | p |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `4symptom:05` (QoS mismatch in a test fixture) | `qos_test_cause` | 8 | 0.62 | 1.00 | 0.50 | +0.50 | 0.077 |
| `4symptom:05` — topped up | `qos_test_cause` | 16 | 0.56 | 1.00 | **0.62** | +0.38 | **0.018** |

At n=16 the "below naked" reading reversed (ablate 0.625 > naked 0.5625) — this
one was noise from n=8, not a hidden regression, but it still needed the top-up
to tell the difference: **KEEP**, p=0.018.

| Claim | Check | n | naked | full | ablate | Δ | p |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `a-programmatic-rosbag2-writer:01` (C++ writer) | `writer_create_topic` | 8 | 0.25 | 1.00 | **0.12** | +0.88 | **0.001** |

This one was already significant at n=8 — the "below naked" shape here was a
real regression, not noise, and reached p<0.05 without a top-up. **KEEP.**

`4symptom:06` (rosbag2 `use_sim_time`) is a related but different shape worth
noting separately: `simtime_cause` never dipped below naked (ablate 0.25 sat
*above* naked's 0.12), it just had a large Δ (+0.75) that n=4–8 couldn't clear
significance on until the top-up reached n=16 (p<0.001). Underpowered, but
never the concerning shape — **KEEP**.

## The two cut candidates, and why single ablation alone was not trusted here

`4symptom:03` (`launch_testing` hangs forever) and `4symptom:04` (tests pass
locally, fail in CI) live in `testing-diagnose`, the one probe that answers four
scenarios in a single response. Single-ablating each one *looked* clean at
first pass (n=4) and got messier, not cleaner, once topped up to the project's
n≥5 floor — which is exactly why the confirmation run below, not this section,
is what the cut decision actually rests on.

| Claim removed | Its own check | Δ, p | A check it does **not** own |
| :--- | :--- | :--- | :--- |
| `4symptom:03` | `hang_cause`: 12/12 vs full 16/16 | Δ=0.00, clean | `qos_test_cause` dropped 16/16 → **7/12**, p=0.008 |
| `4symptom:04` | `ci_cause`: 9/12 vs full 16/16 | Δ=+0.25, p=0.067 | `simtime_cause` dropped 16/16 → **5/12**, p=0.001 |

Two problems with trusting this table on its own:

1. **`4symptom:04`'s own check is not a clean tie at n=12** — `ci_cause` under
   `ablate:04` (9/12=0.75) lands almost exactly on the naked baseline (12/16=0.75),
   the classic "this claim carries real weight" shape, just short of p<0.05.
2. **Both ablations moved a check that isn't theirs.** `ablate()` here removes
   one row from a six-row table, leaving an asymmetric five-row table that no
   shipped version of this skill would ever contain — and that specific,
   never-shipped intermediate state is what the model was actually responding
   to. A result against a state nobody ships is not evidence about the state
   that will be.

What actually matters is the *real* candidate: both rows removed together,
which is what `skills/ros2-testing/SKILL.md` would actually contain. That is a
`full`-vs-`full` comparison against the live (edited) file, not a single or
joint `ablate:` condition, so it is the confirmation run below, not this table.

Both rows were removed from `skills/ros2-testing/SKILL.md` (78 → 76 lines) and
the whole body re-measured in
[`../2026-07-27-testing-confirm/`](../2026-07-27-testing-confirm/NOTES.md):
**old-full 124/124 vs new-full 104/104, p=1.00 — every one of the 13 checks at
ceiling, including `hang_cause` (8/8), `ci_cause` (8/8), `qos_test_cause` (8/8)
and `simtime_cause` (8/8).** The asymmetric-table artifact above does not
survive into the real, symmetric, six-minus-two body. The cut stands, but on
the confirmation run's evidence, not the single-ablation table's.

## Claim verdicts — summary

| Claim | Verdict |
| :--- | :--- |
| `1documentation-entry-points:01/02/03` | untested — nav, structurally untestable with tools off |
| `2running-tests:01`, `2running-tests:02`, `4symptom:01`, `4symptom:02` | **KEEP** (RUN group) |
| `b-integration-testing:01`, `b-integration-testing:02` | **KEEP** (READY group) |
| `a-programmatic-rosbag2-writer-c:01` | **KEEP** (`writer_create_topic`, p=0.001) |
| `4symptom:05` | **KEEP** (`qos_test_cause`, p=0.018 at n=16) |
| `4symptom:06` | **KEEP** (`simtime_cause`, p<0.001 at n=16) |
| `4symptom:03` | **CUT** — validated by confirmation run, not single ablation |
| `4symptom:04` | **CUT** — validated by confirmation run, not single ablation |

11 of 11 ablatable claims resolved; 2 cut (78 → 76 lines, −3%); the 3 nav lines
stay unverified for effect, same limitation noted on both prior skills.

## A third failure mode, distinct from the two prior runs' false negatives

`ros2-core` and `ros2-security` each caught single-ablation Δ=0 hiding a real
effect (a false *negative* — power too low to see it). This run's `4symptom:03`/
`:04` pair is a different mistake shape: single-ablation showed a real-looking
signal — `ci_cause` regressing to the naked baseline, and both removals dragging
down a check they don't own — that was an artifact of the *specific state
tested* (an odd, never-shippable five-of-six-row table), not of the claim's
content. Testing the real candidate (both rows gone, the actual 76-line body)
made it vanish. Same lesson as joint ablation for redundancy groups, generalized:
**when more than one candidate cut exists, the state that matters is the one
that will actually ship, not any single-claim intermediate along the way** —
measure that directly rather than trusting what single or pairwise ablation
implies about it.

## What this run does NOT establish

- **The RUN and READY groups' minimal sufficient subset is untested** — only
  "the whole declared group vs. nothing" was measured, same limitation `ros2-core`
  left open for its own three groups.
- **One model, one temperature, tools off, n≤16.** Same caveats as every run so
  far.

`ros2-testing` moves to ✅ in [`RESULTS.md`](../../RESULTS.md) — effect (this
run), efficiency (this run + confirmation), and a first, clean answer on
whether section order in `SKILL.md` matters at all (it didn't, here).
