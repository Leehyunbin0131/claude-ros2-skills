# How a skill in this pack is written

Two things shaped this pack, and **the whole point of this file is keeping them
apart**:

- **A measurement in this repository** licenses a change to *this* pack.
- **Anthropic's [context-engineering guidance for Claude 5 generation
  models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)**
  is a strong prior about *any* pack.

They agreed almost everywhere, which is why this pack ended up so small. But
they are not the same kind of evidence, and this project has already reverted
one mass rewrite that rested on a prior instead of a number.

## What the guidance actually says

Worth stating precisely, because it is easy to overclaim on its behalf.

It diagnoses **over-constraining** — "we were overconstraining Claude Code, both
through our system prompt and in our CLAUDE.md files and skills" — and
**conflicting instructions**, where a system prompt, a skill and a user request
clash inside one request and "Claude must think more carefully about these
overlapping and conflicting messages before deciding what to do."

Its one quantitative claim is that over 80% of Claude Code's system prompt was
removed **"with no measurable loss"** on coding evaluations.

**That is evidence the content was unnecessary, not evidence it was harmful.**
The post does not claim old-style skills degrade Claude 5's output, and neither
does this repository. The measured cost is context, tokens, and the judgement
spent reconciling contradictions — not accuracy.

It also does not say the old advice was wrong at the time. Constraints "were
once needed to avoid worst case scenarios"; what changed is that "newer models
have better judgement and can handle these decisions well without explicit
rules." An expired prescription, not a past mistake — which is why the response
is periodic re-measurement rather than embarrassment.

## The six shifts, and which ones this pack actually tested

| Guidance | Tested here? | Result |
| :--- | :--- | :--- |
| Rules → judgement | **yes** | 24 rungs, 8 domains; the baseline reached every mechanism asked of it |
| Repeat yourself → single source | **yes** | `CLAUDE.md` alone 2/10 → 10/10 (q=0.002); ten skills stacked on top moved **nothing** |
| Simple specs → rich references | **yes** | a bundled script 0/10 → 10/10 (q<0.001); prose describing that same script, +0.00 |
| Examples → interface design | no | little in this pack turns on tool design |
| Put it all upfront → progressive disclosure | **no** | see below |
| `CLAUDE.md` memory → auto-memory | no | out of scope here |

**Progressive disclosure is followed but unmeasured.** `references/` files load
only when the symptom points at them, which is what the guidance recommends —
but **every round in this repository measured whether *content* changes an
outcome, never how content is *arranged*.** So the layout rests on the prior and
the absence of a counter-example, not on a number. Recorded here so the gap is
deliberate rather than invisible.

## The rules that survived

1. **Point at a runnable artifact, never describe one.** The only content in
   this pack that ever cleared the bar. A script with an exit code, with a path
   and an invocation — not a paragraph about what it would tell you.
2. **Say nothing `CLAUDE.md` already says.** No "verify before writing", no "ask
   about hardware vs simulation", no "done means it ran". Those live in
   `CLAUDE.md`, once. Duplicating them is exactly the conflicting-instruction
   problem the guidance describes, paid for on every load and twice over when a
   task loads two skills.
3. **No fact the model can look up.** Measured to exhaustion: every symptom →
   cause → action table this pack shipped was deleted after a ladder showed the
   baseline already reaching it.
4. **Keep what is genuinely local and unreachable.** The residue: a bundled
   script, this robot's real wheel radius, a physical mounting no container can
   check. Nothing on the web or in `/opt/ros/jazzy` contains it.
5. **Only claim what has been run.** Content decays. §3C once told readers a
   nested `spin_until_future_complete` "hangs the entire node"; on Jazzy it
   raises loudly in about a second. A wrong line is worse than a missing one.

## The shape

```markdown
---
name: <skill>
description: "<what routes here — no promises the body does not keep>"
---

# <Title>

## Bundled checks
<only if scripts/ exists: path, invocation, what the exit code means>

## <Local fact or convention that is genuinely unreachable>

## References
<one line each, loaded only when the symptom points at them>
```

Sections with nothing measured to put in them are **left out**, not filled.

## Status

All eight domains have been through a ladder. Six domain skills were deleted on
the results, joining two deleted earlier; `ros2-troubleshooting` survives as the
script bundle, and `ros2-microros` survives **labelled unverified** because no
ladder is possible without an MCU. See [`CAPABILITIES.md`](./CAPABILITIES.md)
for the result and [`LADDER.md`](./LADDER.md) for the method.

One warning from that sweep, because it is the same failure this file guards
against: an exhausted ladder licenses removing **what the ladder tested**, not
everything sharing a file with it. Deleting `ros2-control` nearly took its
wheel-calibration procedure with it — content `ctl1`–`ctl3` never tested and
could not, there being no floor in a container.
