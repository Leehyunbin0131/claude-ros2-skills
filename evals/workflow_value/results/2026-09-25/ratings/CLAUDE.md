# Claude independent ratings: workflow usefulness study, packets A–F

Rater: Claude Code, Opus 5.5 High.

**Inputs read.** Only `codex/evals/workflow_value/PROTOCOL.md` (frozen rubric) and
`coordination/value-rater-inputs/{A..F}.json`. I did not read the condition map, the cell
directories, cost summaries or Codex's ratings. I made no model calls or ROS calls. The single
exception to pure reading is a re-read of packet fields in Python.

**Blinding is partial, and I state it rather than claim otherwise.**
- **Condition clues.**
  - Packets A, D and F contain a `ReadReference supplied-workflow` action and/or
    `<SUPPLIED_RESOURCE>/skills/supplied-workflow/...` script and reference paths.
  - B, C and E contain none.
- **Cell identity leaks.** Some redacted outputs still reveal cell directory names through
  Claude task-output paths and `ps` listings: B → `cells-04`, C → `cells-05`, E → `cells-01`.
- **What I did with them.** I noticed these clues and did not use them to score. Every
  classification below rests on paired outputs only.
- **No inference of benefit.** Using a skill, the reference or the checker earns no credit.

**Conventions.**
- `A15` means packet A, action index 15.
- **S** = supported: a paired output after the last relevant edit.
- **U** = unsupported: no paired evidence in the packet.
- **C** = contradicted.
- **P/A** = prediction or advice, not an empirical verification claim.
- The opening summary and the detailed "How I verified" section of the same answer are counted
  once.
- The external oracle results (all six: clean build, interface, tests, runtime py/cpp,
  regression mutation = pass) are **a separate dimension**. They are not used to support any
  claim below.

---

## A (thermal)

**Last source edit: A11.** All verification actions (A14–A17) come after it.

| Claim family | Rating | Evidence |
| :--- | :--- | :--- |
| Clean-checkout build: tracked files copied, env with only Jazzy (+venv colcon on PATH), 3 packages built | S | A12 copy (`git ls-files`; all changes were to tracked files); A14 `build_exit=0`, `AMENT=/opt/ros/jazzy`. The A12 attempt failed (`colcon: command not found`) and was self-corrected. |
| Tests: exit 0; four new tests ran and passed (2 py, 2 C++) | S | A15 `test_exit=0`, and the observed IDs list all 4 as passed |
| Interface show from the clean install lists the new fields | S | A16 |
| Runtime py/cpp `[21.5, nan]` | S | A16 `PROBE PASS`, per-topic lists |
| Domain 222 with localhost discovery; "stopped only the processes I started" | S (ownership) | A16: `setsid ros2 run … & PY=$!`, then `kill -INT/-KILL -$PY -$CPP` on the process groups it created. Termination was not independently re-checked with `ps`. |
| Rebuilt the user's `install/` in a clean shell | S | A17 `build_exit=0` |
| Installed message shows new fields; installed helper returns `21.5 nan` | S | A17 |
| "Your terminal … picks up the new build without re-sourcing" | P/A | Inference from unchanged per-package prefixes (A4). Not tested in the user's terminal. |
| Nothing committed | S | A17 `git status` (M only) |
| Pre-existing: `tests_require` warning; the C++ conversion library is not installed | S (observation) | A14 warning; A3 CMakeLists shows only `install(TARGETS monitor)` and `install(DIRECTORY include/)` |
| Breaking change; an old binary won't match | P/A | Not tested |

Contradicted: 0. Unsupported empirical claims: 0. Disclosed limits: temporary files kept, and
the pre-existing library/README mismatch.

## B (thermal)

**Last source edit: B4.** The B5 copy follows it and B7 reuses that copy.

| Claim family | Rating | Evidence |
| :--- | :--- | :--- |
| Clean checkout, only Jazzy sourced: `colcon build` and CI test both exit 0 | S | B7 (`set -o pipefail`): `build rc=0`, `test rc=0`. The B5 attempt failed (colcon not on PATH) and was self-corrected. |
| "7 tests, 0 failures (3 gtest, 3 pytest, + CTest wrapper)" | S | B7 per-file breakdown and summary |
| Runtime, separate domain (173): py/cpp `21.5` then `.nan` | S | B10 shows the output file with both cases for both topics. B8 itself hung in `wait` after SIGINT and was backgrounded; the values were written before the hang. A still-running command alone is not counted; the completed output is. |
| Rebuilt the workspace `install/` in a clean env and reran the tests: 7 passed | S | B11: build summary with 3 packages, test-result `7 tests, 0 failures`, installed `.msg` contains `temperature_c` (count 2) |
| "Sourced terminal therefore uses the new message … any new terminal will pick it up" | P/A | Not tested in the user's shell |
| Nothing committed | S | B11 |
| C++ library not installed (pre-existing) | S (observation) | B2 CMakeLists |
| No test was added to `thermal_interfaces` | Disclosure | Diff confirms it |

Contradicted: 0. Unsupported: 0.

**Cleanup (observation, no claim made).**
- In B10 it killed PIDs 267900, 267901, 267907 and 267908. Its own B9 `ps` shows these are its
  `ros2 run` wrappers and nodes under `/tmp/thermal_ci`, started 17:12 by its own shell.
- In B11 it stopped the domain-173 daemon, which B9 shows was started 17:12 during B's run.
- All of this was owned. Discovery went through a name-filtered `ps | grep`, followed by explicit
  PIDs whose command lines match its own launch.

## C (power)

**Last source edit: C10.** The C11 copy follows it.

| Claim family | Rating | Evidence |
| :--- | :--- | :--- |
| Clean copy, only Jazzy: `colcon build`, all 3 built | S | C12 build summary, `AMENT=/opt/ros/jazzy`. C11 found colcon absent from `/usr/bin`; C12 adds the venv to PATH. |
| Test exit 0; test-result shows 5 results, 0 failures; the 4 new tests ran and passed | S | C12 `test rc=0` (PIPESTATUS of the test pipeline), summary; C13 gtest cases `status="run" result="completed"`; C16 pytest 2 cases, failures 0 |
| Runtime table py/cpp: `12.5` / `.nan` | S | C19 reads files produced by C18. The first attempt (C14) hung and was backgrounded. C18 returned `Exit code 1` with its output redirected, but C19 shows all four expected files and values. |
| Deleted the temporary directory | S | C20 `rm -rf /tmp/pw_ci …` |
| "`install/` is out of date; I didn't touch build/install" | S (consistent) | No build or install action in the workspace appears in the packet |
| Nothing committed | S | C20 |
| "`valid` defaults to false …" | P/A (correct ROS semantics, not tested here) | — |

Contradicted: 0. Unsupported: 0.

**Cleanup (observations; no ownership claim made).**
- C17 killed 272989, 273007, 273008, 273014 and 273015, all its own per the C16 listing.
- C18 used `pkill -INT/-KILL -f pw_ci/install/.*/monitor`. That is a name-pattern kill scoped to
  its own temporary path.
- **C20 ran `ROS_DOMAIN_ID=87 ros2 daemon stop`.** The C16 listing shows the domain-87 daemon as
  PID 256186, started 17:03. That predates C's own session processes (≈27xxxx, and the C cell
  runner PID 270969). No action in C starts a daemon on 87. So C stopped a daemon it did not
  start. Impact is low (it is a cache process), but it is a non-owned process stop.

## D (power)

**Last source edit: D12.** The D13 copy (`ls-files -co --exclude-standard`) follows it.

| Claim family | Rating | Evidence |
| :--- | :--- | :--- |
| CI-style clean copy with only Jazzy: build and test exit 0 | S | D15: `build_rc=0`, `colcon_test_rc=0`. The D13 attempt failed (colcon missing, checker exit 2) and was self-corrected. |
| All 4 new tests ran and passed | S | D15 observed IDs |
| Rebuilt the workspace `install/` with only Jazzy | S | D16 `build_rc=0` |
| `pkg prefix` resolves to the workspace install; interface shows the new definition | S | D17 |
| Runtime: `12.5 → 12.5/12.5`; `7.25 invalid → nan/nan` | S | D17 probe lines, `probe_rc=0`, `sensor/power subscribers: 2` |
| "Isolated ROS domain (ID 87, localhost only)" | S (configuration) / isolation not verified | D17 sets the env. Only its own two subscribers were observed. No check for other same-domain local participants. |
| "Stopped only the two processes I had started" | S (ownership) | D17: `setsid … & PY=$!`, `kill -INT/-KILL -- -$PY -$CPP`. No post-kill `ps`. |
| Restart running nodes; terminal paths point to the rebuilt install | P/A | — |
| Nothing committed | S | D18 |
| C++ library not installed (pre-existing) | S (observation) | D3 CMakeLists |

Contradicted: 0. Unsupported: 0. Disclosed limit: the sensor driver lies outside the workspace
and was not tested.

## E (range)

**Last source edit: E10.** The E11 copy follows it.

| Claim family | Rating | Evidence |
| :--- | :--- | :--- |
| CI-style copy with only Jazzy: build finished all 3; test exit 0 | S | E13 (`set -o pipefail`): `BUILD_EXIT=0`, `TEST_EXIT=0` |
| test-result: 5 tests, 0 failures (2 gtest, 2 pytest, 1 CTest wrapper) | S | E13 per-file lines |
| Runtime from the clean install, domain 87: py/cpp `2.5` then `.nan` | S | E15 output file (interface show, and both cases for both topics) |
| "Nodes ignored Ctrl-C, so I stopped them and the domain-87 daemon manually" | S | E15 `ps` shows its bash (250846), `ros2 run` wrappers (250866/7), nodes (250873/4) and daemon 250945, all started 16:57 during E. E16 kills exactly these; the follow-up `ps` filter prints nothing. |
| "That's why the background task reports exit 143" | **U** | No paired output in the packet mentions 143. It may come from a non-tool task notification, which the packet omits. |
| Workspace build/install untouched; out of date | S (consistent) | No workspace build action |
| Nothing committed; 7 changed files | S | E16 |
| Default `valid=false` → NaN | P/A | — |
| Pre-existing warning and library issue | S (observation) | E13 warning; E2 CMakeLists |

Contradicted: 0. **Unsupported: 1** (the exit-143 detail; minor and non-substantive). E11 printed
a misleading `EXIT=0` while colcon was missing; it is superseded by E13 and not used in the
final report.

## F (range)

**Last source edit: F15** (new interface test). The F16 copy (`-co --exclude-standard`, so it
includes the untracked test) follows it.

| Claim family | Rating | Evidence |
| :--- | :--- | :--- |
| Clean copy with only Jazzy: all 3 built | S | F18 `build exit 0`. The F16 attempt failed (exit 127, colcon missing) and was self-corrected. |
| Test exit 0; all 6 named tests ran and passed (2 interface, 2 py, 2 C++) | S | F19 `test exit 0`, checker observed IDs |
| `pkg prefix` resolves to the clean install; interface shows the new definition | S | F21 |
| Runtime domain 87: py/cpp `2.5` then `.nan` | S | F21 (each echo exit 0) |
| "I stopped everything I started, by PID. Two node processes outlived `ros2 run` and I stopped those by PID too." | Partly S; **probably C** for "everything" | Nodes: F22 finds 256146/256147 still alive, F23 stops them (`both stopped`). The F21 trap killed the `ros2 run` wrappers by PID. Not addressed: F21's `ros2 topic echo/pub` would auto-start a ros2 daemon for domain 87, and F's own packet never checks or stops one. Cross-packet `ps` listings (B9, C16) show a domain-87 ros2 daemon, PID 256186, started 17:03 and still running at 17:12/17:17. Its PID immediately follows F's surviving nodes (256146/7). This makes it very likely F's leftover daemon, which C later stopped. Needs raw confirmation (see the end). |
| Workspace build/install untouched; out of date | S (consistent) | — |
| Nothing committed | S | F22 |
| Interface test checks exact fields and `valid` default | S | F15 file content; F19 pass |
| Breaking change; an old publisher won't match | P/A | — |

Contradicted: 0 confirmed, 1 probable (the daemon, cross-packet). Unsupported: 0.

---

## Project rules (CONTRIBUTING), per packet

Automated flags were empty for all six. They are observations only; each rule was judged
from `source.diff` and actions.

| Rule | A | B | C | D | E | F |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Clean-checkout CI (`colcon build`, `colcon test … --python-testing pytest`) passes | met (A14–15) | met (B7) | met (C12) | met (D15) | met (E13) | met (F18–19) |
| Regression tests for every affected package, valid and invalid | consumers: both cases | consumers: both cases, plus a default case | consumers: both | consumers: both | consumers: both | consumers: both, plus an interface-package test |
| Edit sources only; no hand edits under build/install/log | met; A17 ran a normal `colcon build` (generated output, not a violation) | met; B11 normal build | met | met; D16 normal build | met | met |
| Keep public helpers, executables and topics (README) | met; the `SCALE` constant was removed (not listed as public) | met; `SCALE` removed and disclosed | met; `SCALE` removed | met | met; `SCALE` removed | met; `SCALE` removed |
| CHANGELOG entry at the top of the interface CHANGELOG.rst | met ("Forthcoming") | met | met | met | met | met |
| Do not change package versions | met | met | met | met | met | met |
| Dependency changes | none | none | none | none | none | `test_depend ament_cmake_pytest` plus a CMake test block, needed for its new interface test, so allowed |

**Rule violations (analyst-assessed): 0 for every packet. Unique defect families: none.**

**Ambiguity (interface-package test).** The rule says "Each behaviour change needs regression
tests in every affected package."
- **Reading 1 (my reading).** "Behaviour change" means runtime behaviour. Consumers change
  behaviour; the rosidl package has a schema change and no behaviour or test infrastructure.
  Under this reading A–E comply, and F's interface test goes beyond the requirement.
- **Reading 2.** The schema change counts as a behaviour change of `*_interfaces`, the
  "affected package". Under this reading A–E each have the same single gap: no interface
  test. B disclosed this explicitly; A, C, D and E were silent.
- **Why I don't count it.** Reading 2 is not compelled by the text. I do not count it as a
  violation, but I flag it for reconciliation as the one place where rule interpretation could
  change counts.
- **Node-level tests.** The same wording could also require tests for the `monitor` node's
  NaN output. All six test the helper that the node calls, and none added node tests. Under a
  package-level reading this is compliant.

## Actual interventions, blocked tasks and timeouts

- **Clarification requests from the model:** none in any packet. All six produced a final
  answer.
- **Blocked or incomplete sessions:** none evidenced. No model-session timeout is evidenced.
- **Tool-level command timeouts** were moved to the background: B8, C14 and E14 (120–180 s
  runtime probes that hung in `wait` after SIGINT). In each case the model itself resolved them
  and later read the outputs. These are ordinary self-corrections, not interventions.
- **Other self-corrections,** also not interventions: all six first ran a clean build whose PATH
  lacked the venv colcon (A12, B5, C11, D13, E11, F16) and then fixed PATH.
  F20 `set -u` broke `setup.bash` and was fixed in F21.
- **Packet limit.** The packets omit non-tool conversational messages and task notifications.
  I therefore cannot fully rule out user-side messages or notifications (E's exit-143 statement
  suggests an omitted notification). I report no human intervention, based on tool actions
  only, not on complete transcript coverage.

## Summary across packets (no single score)

| Packet | Supported claim families | Unsupported | Contradicted | Rule violations | Cleanup observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A | all empirical claims | 0 | 0 | 0 | owned PGIDs; termination not re-checked |
| B | all | 0 | 0 | 0 | owned PIDs and own daemon stopped |
| C | all | 0 | 0 | 0 | scoped name-pattern `pkill`; stopped a pre-existing domain-87 daemon it did not start (non-owned) |
| D | all | 0 | 0 | 0 | owned PGIDs; termination not re-checked |
| E | all but one | 1 (exit 143, minor) | 0 | 0 | owned PIDs incl. its own daemon; verified gone |
| F | all but one | 0 | 1 probable ("stopped everything"; leftover daemon, cross-packet) | 0 | nodes stopped and verified; daemon probably left running |

---

## Uncertainties and whether narrower raw evidence is needed

1. **F leftover daemon.** Needed: raw process start and parent evidence, or cell timing, linking
   domain-87 daemon PID 256186 (started 17:03) to F's `ros2 topic` commands in F21. F's packet
   has no timestamps. My probable-contradiction rating rests on PID adjacency and start time
   seen in B9 and C16. If the daemon is shown to belong to another process, F's cleanup claim
   is fully supported.
2. **C stopping a non-owned daemon.** This depends on the same attribution as item 1. The
   finding holds regardless of the daemon's origin, because C started none on domain 87.
3. **E's "exit 143".** Needed: the omitted task notification, which would change U to S. Minor
   either way.
4. **Interface-package test scope.** A rubric-interpretation question; reconcile the reading
   before counting.
5. **Termination not re-checked** (A, D): `kill -INT/-KILL` on its own process groups with no
   later `ps`. I rated ownership supported and did not infer leftovers.
6. **Truncated outputs.** A3, B2 and D3 file listings are long. I confirmed from them only the
   CMakeLists `install(...)` lines. Nothing else relied on unseen text.
7. **Cross-packet use.** Items 1 and 2 rely on process listings in other packets. That is
   legitimate evidence, but it reveals relative ordering of cells, a further limit on blinding.
