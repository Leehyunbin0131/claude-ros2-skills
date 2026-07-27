<!-- Detailed write-up for this run. The status row that cites it is in
     ../../RESULTS.md; artifacts sit next to this file. -->

# Per-claim ablation — `ros2-security`, 2026-07-27

Second skill through the harness, chosen for size: 6 claims against `ros2-core`'s
26, and its two examples (a CLI command sequence, an XML access-control policy)
need no live scenario infrastructure — a probe is one prompt, graded on the text
it returns.

| | |
| :--- | :--- |
| Method | every claim ablated individually; content injected via `--append-system-prompt`; `--tools ""` |
| Probes | 3, covering all 6 claims: `sros2-keystore` (CLI block + the 3 doc-pointer lines as interference extras), `sros2-access-policy` (XML block), `sros2-mechanism` (the architecture sentence) |
| Sample | 152 cells at n=8, then a targeted top-up to n=16 on `sros2-mechanism` once one check looked like the same shape as the `ros2-core` false negative. 176 cells total, $1.49 |
| Grading | 812/824 check results gradable; ungradable never counted as a failure |

## Headline

| Comparison | Pass rate | p |
| :--- | :--- | ---: |
| **skill body vs nothing** | 0.596 → **1.000** | **<0.0001** |
| `CLAUDE.md` alone vs nothing | 0.596 → 0.550 | 0.507 |
| body + `CLAUDE.md` vs body alone | 1.000 → 1.000 | 1.00 |

Same shape as the `ros2-core` result: the body has a large, clean effect; the
always-loaded protocol changes nothing on its own; no contamination from adding
it on top of the body.

## One check hid the same mistake `ros2-core` did

At n=8, the architecture sentence (`1architecture:01` — DDS-Security, X.509 PKI,
which RMW implementations carry it) looked like a cut: `dds_security` and `pki`
sat at ceiling naked and stayed there ablated (Δ=0.00), and `rmw_backend` moved
only 0.75→1.00 minus the naked 0.88, p=0.467 — not significant, and the ablated
score (0.75) sitting *below* the naked baseline (0.88) is the exact shape that
turned out to be a real regression in `ros2-core`'s `tf-lookup` probe, not noise.

Topped `sros2-mechanism` up to n=16 on `naked`, `full`, and
`ablate:ros2-security:1architecture:01` rather than re-running the whole suite:

| | naked | full | ablate |
| :--- | ---: | ---: | ---: |
| `rmw_backend` | 13/16 = 0.81 | 16/16 = 1.00 | 9/16 = **0.56** |

full vs ablate: p = 0.0068. The sentence is load-bearing — but, as with
`ros2-core`'s cross-host row, for only one clause out of three. `DDS-Security`
and `X.509 PKI` are things the model already states unaided; naming *which* RMW
implementations (Fast DDS, Cyclone DDS) actually carry DDS-Security is not.
Since the claim is one prose sentence, it cannot be partially cut — the whole
line stays.

## Claim verdicts

| Claim | Kind | Verdict | Evidence |
| :--- | :--- | :--- | :--- |
| `1architecture:01` | fact | **KEEP** | `rmw_backend` Δ=+0.44, p=0.007 (n=16, after top-up) |
| `a-sros2-cli-commands:01` | fact (code block) | **KEEP** | `enclave_flag` Δ=+0.62, p=0.026 (n=8) |
| `b-high-level-access-control-policy-polic:01` | fact (code block) | **KEEP** | 4 of 5 checks Δ=+1.00, p<0.001 (n=8) |
| `2documentation-entry-points:01/02/03` | nav | untested | structurally untestable with tools off — see `ros2-core`'s same finding |

Zero cuts. Every ablatable claim in this skill is load-bearing, so the 52-line
body is already the smallest one the harness can find — the efficiency axis
closes without editing `SKILL.md`, unlike `ros2-core` where five lines came out.

## Interference and contamination

No ablation moved a check it doesn't own, and `full` vs `shipped` (body +
`CLAUDE.md`) is 1.00 vs 1.00, p=1.00 — no sign of the always-loaded protocol
overriding or degrading this body either.

## What this run does NOT establish

- **The 3 doc-pointer lines are unverified for effect**, same limitation as
  `ros2-core`: this harness measures what the model writes with tools off, and a
  navigational line's entire purpose is to be followed with tools on.
- **One model, one temperature, tools off.** Same caveat as every run so far.
- **`create_keystore` / `create_enclave` / `env_strategy` checks are individually
  noisy** (p=0.077–1.00) but did not need a top-up: they share an atomic claim
  with `enclave_flag`, which already cleared significance, so the code block as a
  whole is decided regardless of the noisier sibling checks.

`ros2-security` moves to ✅ in [`RESULTS.md`](../../RESULTS.md) — both axes
closed on the first run: effect (this run) and efficiency (nothing to cut).
