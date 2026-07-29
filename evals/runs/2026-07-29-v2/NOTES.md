<!-- First v2 round. Design in ../../DESIGN.md, tasks and pre-registered
     decisions in ../../TASKS.md, machine output in ./ANALYSIS.md. -->

# v2 round 1 — tools on, real environment

45 cells, four tasks, n=5 per cell. First measurement under the criterion in
[`DESIGN.md`](../../DESIGN.md): a skill supplies what the agent **cannot reach on
its own**, with model knowledge, web search and a live install all available.

**Headline: nothing reached significance, and the one thing that came closest is
the shipped scripts rather than any skill text.**

## The control gate passed

`t4` — a task the model handles cold — is **5/5 vs 5/5 on both checks**. The
harness is not tilted toward the skills condition, so the rest can be read. This
gate was fixed in advance precisely because a v1-style result would otherwise be
unfalsifiable.

## Results against the predictions

`TASKS.md` recorded three predictions before the round. Two held, one did not.

| Prediction | Outcome |
| :--- | :--- |
| T1 null — the agent searches and gets it right unprompted | **half right.** It gets the answer right without searching |
| T2: `scripts-only` ≈ `skills` — the files matter, the text does not | **held exactly** |
| T3 largest effect of the three | **wrong.** T3 is null |

### T1 — the answer is reachable; the *habit* is not

| Check | baseline | skills | Δ | q |
| :--- | ---: | ---: | ---: | ---: |
| `t1_correct_type` (names `TwistStamped`) | **5/5** | 5/5 | 0.00 | 1.000 |
| `t1_searched_or_read` | 0/5 | 4/5 | +0.80 | 0.254 |
| `t1_no_invented_param` | 0/5 | 3/5 | +0.60 | 0.667 |

The baseline gets the *right answer* every time — `TwistStamped` — with **zero**
searches and zero reads of the install. It knows.

What it does not do is verify, and it pays for that: 0/5 on
`t1_no_invented_param`, meaning every baseline cell also volunteered
`use_stamped_vel` as a fix. It has the correct fact and an incorrect one side by
side, and no habit of checking which is which.

Both differences point the right way and neither clears the bar at n=5. Recorded
as UNDERPOWERED, not topped up — sampling until a number crosses is
manufacturing, and that was fixed in advance too.

### T2 — the scripts earn their place; the text does not

| Check | baseline | scripts-only | skills |
| :--- | ---: | ---: | ---: |
| `t2_ran_script` | 0/5 | **5/5** | 5/5 |
| `t2_exit_code_read` | 0/5 | **5/5** | 5/5 |
| `t2_evidence_not_guess` | 4/5 | 5/5 | 5/5 |
| `t2_no_ros2_run` | — | 5/5 | 5/5 |

`scripts-only` vs `baseline` is +1.00 on two checks (p=0.008, q=0.063).
`skills` vs `scripts-only` is **+0.00 on every check**.

This is what the three-cell design was for. Shipping `check_imu_gravity.py`
changes behaviour completely — the agent finds it by reading the directory, runs
it, and reports the measured verdict. The `SKILL.md` text describing it adds
**nothing measurable on top**. Category 2 content is real; the prose around it is
not the part doing the work.

The baseline is not useless here — 4/5 on `t2_evidence_not_guess`, because it
writes its own throwaway subscriber and samples the topic. It gets to evidence
by a longer route. What it never does is find a script that is not there to find.

### T3 — the prediction was wrong, and this is the important one

| Check | baseline | skills |
| :--- | ---: | ---: |
| `t3_asked_before_writing` | **4/5** | 5/5 |
| `t3_asked_footprint` | **4/5** | 5/5 |
| `t3_asked_drive_type` | **4/5** | 5/5 |
| `t3_read_shipped_defaults` | 1/5 | **0/5** |

All null. **The baseline already asks for footprint and drive type before
writing config, 4 times out of 5.**

In v1 the same behaviour measured 1/7 against 5/7 and was written up as the
highest-value content in the pack. That gap was an artifact of the tools-off
harness: an agent that cannot ask, look anything up, or do anything but emit text
in one turn will emit a config file. Given a real session it stops and asks on
its own.

`t3_read_shipped_defaults` goes the *wrong* way — 0/5 with skills against 1/5
without. Δ=-0.20, not significant, but the sign is worth recording rather than
ignoring: the skills cell spends its first turn loading skills and asking
questions, and never gets as far as reading `nav2_params.yaml`.

## What the tool counts show

| Task | baseline | skills |
| :--- | :--- | :--- |
| t1 | `Bash` | `Bash`, `Grep`, **`Skill`** |
| t2 | `Bash` | `Bash`, `Grep`, `Read`, **`Skill`** |
| t3 | `Bash`, `Edit`, `Read`, `Write`, … | `Bash`, **`Skill`** |
| t4 | `Bash`, `Write` | `Bash`, `Write`, **`Skill`** |

`Skill` loads in 5/5 of every skills cell, so routing is not the problem — the
content is reaching the agent and mostly not changing the outcome.

The t3 row is the interesting one in the other direction: the **baseline** used
more tools (`Edit`, `Read`, `Write`, `TaskCreate`) than the skills cell. The
skills cell talked; the baseline acted. On a task whose right answer is "ask
first", talking is correct — but it is a reminder that "more tool calls" is not
itself a quality signal, which the v1 smoke test had implied.

## What this round establishes

- **The v1 verdicts were measuring the restriction, not the skills.** Two of
  three targeted effects vanish once the agent can search and act. The reset was
  correct and did not go far enough: the two lines added by v1 (the
  `TwistStamped` row and the servo row) are now expected to fail as well.
- **Category 2 is the only category with support so far.** Files the agent
  cannot reach change behaviour outright. The text describing them does not.
- **Category 3 has no support in this round.** The behaviour it targets happens
  anyway in a real session.
- **Nothing reached q<0.05.** At n=5 a clean 5/5 vs 0/5 gives p=0.008, which is
  q=0.063 after correction across 16 tests. That is the cost of testing 16
  things honestly, and the fix is more replicates on the two checks that matter
  rather than more checks.

## Next

One decision, and it is not "top up until it crosses". The two `t2` checks at
q=0.063 are the only place a real-outcome grader moved, so a second round should
be **narrow**: `t2` only, `baseline` vs `scripts-only`, n=10. Fewer tests means
less correction, and it answers the one question this round left open — whether
shipping the scripts is worth it — without paying for fifteen tests nobody needs.
