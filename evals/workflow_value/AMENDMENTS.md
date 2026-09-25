# Execution amendments

The primary study uses Opus 5.5 **High**, as in the original frozen protocol.

After High cells 01 and 02 completed their model calls, the user requested Low.
The runner and protocol were changed in commit `91760d0`, and a fresh Low cell 01
started. The user then requested High again. The Low runner was interrupted by
its exact owned PID; its child processes were cleaned up by its ownership tag.
This incomplete Low attempt is preserved separately and excluded from every
High comparison. It is not a completed trial, a timeout, or a model failure.

The runner, protocol, tests and freeze were restored byte-for-byte from
`d4db751`, and High cells 03–06 continue the original declared order. The task,
pack, rubric, and validated control sources have not changed. Subsequent cells
also mask the interrupted Low workspace. The extra Low call can affect cache
warmth; all timing/token comparisons remain descriptive. The intermediate Low
configuration is available in git history, not an additional completed study.
