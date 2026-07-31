# How a SKILL.md in this pack is written

The shape every skill here converges to, and — for each rule — whether it comes
from a measurement in this repository or from Anthropic's
[context-engineering guidance for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models).

Keeping those two apart is the point of this file. A measurement licenses a
change to *this* pack. External guidance is a strong prior about *any* pack, and
this project has already reverted one mass rewrite that was justified by a prior
rather than a number.

## The five rules

### 1. Point at a runnable artifact, never describe one

**Measured, and it is the only thing in this pack that has ever cleared the
bar.** Round 2: shipping `check_imu_gravity.py` took "reported a checked
pass/fail verdict" from **0/10 to 10/10, q<0.001**. The prose describing that
same script was **+0.00 on every check**. The baseline is not ignorant — it
scores 9/10 on citing a measured number, because it writes its own throwaway
subscriber. What it never produces is an exit-coded verdict.

The guidance calls the same thing *"Simple Specs → Rich References"*: reference
real code, test suites and artifacts rather than simplified markdown
descriptions.

So: a script in `scripts/`, with a path and an invocation. Not a paragraph about
what the script would tell you.

### 2. Say nothing `CLAUDE.md` already says

**Measured.** Round 4: `CLAUDE.md` alone moved "verified against the install
rather than answering from memory" from **2/10 to 10/10, q=0.002**. Installing
all ten skills on top of it moved **nothing** — 10/10 vs 10/10, 6/10 vs 6/10.

The guidance calls this *"Repetition → Single Source"*, and warns specifically
against the system prompt, skills and `CLAUDE.md` carrying conflicting messages
in one request.

So: no "verify before writing", no "ask about hardware vs simulation", no "done
means it ran". Those live in `CLAUDE.md`, once.

### 3. No fact the model can look up

**Measured, repeatedly.** Round 3: the `TwistStamped` fact that v1 added after
the tools-off model failed it 4/4 is **10/10 unaided** in a real session.
`ros2-package`'s entire wiring section: **190/190 unaided** across three ladder
rungs. `gazebo-sim`: **108/110**. Every symptom row those ladders touched —
bridge direction characters, a rendering sensor with no `gz-sim-sensors-system`,
`/clock` and `use_sim_time`, `<model>/<link>/<sensor>` frame composition — was
**0/10 wrong**.

The guidance's *"Rules → Judgment"* and *"Examples → Interface Design"* say the
same thing from the other side: the model reasons well enough that prescribing
the answer is worse than letting it find one.

So: no API tables, no parameter lists, no code examples, no symptom→cause→fix
rows for anything a live install will answer.

### 4. Keep what is genuinely local and unreachable

**Measured as a category** (round 2, above). This is the residue: a bundled
script, a project's real wheel radius, this workspace's conventions. Nothing on
the web or in `/opt/ros/jazzy` contains it.

The guidance: skills should *"encode particular opinions, knowledge, or best
practices that are particular to you, your team, or product."*

### 5. Only claim what has been run

**Measured the hard way.** `ros2-troubleshooting` §3C told readers that a nested
`spin_until_future_complete` "hangs the entire node". On Jazzy it raises
`RuntimeError("Executor is already spinning")` in about a second — loud and
immediate — while the two cases that *do* hang silently were not mentioned. The
`README`'s headline "silent failure" example is likewise not silent: rclpy logs
`offering incompatible QoS ... Last incompatible policy: RELIABILITY`.

Content decays. A line that was true two releases ago is a liability now, and
this pack shipped two such lines without noticing.

## What this pack does NOT adopt from the guidance yet

**Progressive disclosure by splitting into many files.** The guidance recommends
it for long skills. **This pack has no measurement on file layout at all** — every
round here measured whether *content* changes an outcome, never how content is
arranged. v1 deleted `ros2-dev/references/` (134 lines) on an argument rather
than a number, and that was part of the reduction this project reverted.

It stays unadopted until a ladder tests it. Recorded here so the omission is
deliberate rather than an oversight.

## The shape

```markdown
---
name: <skill>
description: "<what routes here — no promises the body does not keep>"
---

# <Title>

## Bundled checks
<only if scripts/ exists: path, invocation, what the exit code means>

## <Local fact / convention that is genuinely unreachable>
<one line each, or omit the section>

## Verified-against-install notes
<only claims re-run on this install, dated. Otherwise omit.>
```

Sections with nothing measured to put in them are **left out**, not filled.

## Status of each skill against these rules

| Skill | Ladder coverage | Rewritten to this shape? |
| :--- | :--- | :--- |
| `ros2-troubleshooting` | §3C cut (110/110); QoS rung failed → gap is `CLAUDE.md`'s, not the skill's; scripts measured keeper | **yes** — the pack's exemplar |
| `ros2-control`, `ros2-core`, `ros2-dev`, `ros2-moveit`, `ros2-perception`, `ros2-testing`, `ros2-microros` | none, beyond `t1` touching `ros2-control` | **rule 2 only** — `CLAUDE.md` duplication removed, which round 4 measured directly. Domain content untouched pending its own ladder. |

Rewriting an unmeasured skill's domain content on the strength of this document
would be the reverted reduction again, with a better bibliography.
