#!/usr/bin/env python3
"""Decide what `isolate_cell.sh` hides from a cell, or refuse to run.

    python3 isolation.py plan --workdir <dir>     # prints "d <path>" / "f <path>" lines

A cell must not be able to read the eval design, a scenario source that names
the answer, or -- in a `baseline` cell -- this pack's protocol and skills. It
also must not start with the host's own Claude instructions loaded, because
those differ between machines and between the operator's sessions. Everything
listed here is bind-mounted over with an empty file or directory inside the
cell's mount namespace; nothing on the host is touched.

Hidden:
  * this checkout and every git worktree of it;
  * copies found by a bounded scan of $HOME and /tmp: repository clones
    (evals/harness/isolate_cell.sh), protocol copies (a CLAUDE.md carrying this
    pack's heading), skill copies (ros2-troubleshooting/SKILL.md) and script
    copies (check_imu_gravity.py), e.g. an earlier `skills` cell's directory;
  * every path in EVAL_MASK_PATHS (colon-separated) -- what no scan can
    recognise, such as a directory of transcripts that quote this repository;
  * the host's Claude instruction sources under CLAUDE_CONFIG_DIR (default
    ~/.claude): CLAUDE.md, rules/, skills/, agents/, commands/, output-styles/,
    plugins/. Credentials stay visible, or no cell can log in;
  * CLAUDE.md, CLAUDE.local.md, AGENTS.md and .claude/ in every ancestor of the
    workdir, which Claude Code loads at launch.

Refused (non-zero exit, nothing runs):
  2  an EVAL_MASK_PATHS entry that does not exist (a typo would silently unmask)
  5  managed policy present (EVAL_MANAGED_POLICY_DIR, default /etc/claude-code):
     it loads into every session and cannot be excluded. EVAL_ALLOW_MANAGED_POLICY=1
     proceeds, on the operator's word that it is identical across conditions.
  6  a mask that would hide the workdir itself, or Claude's config dir as a whole
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

MARKER = "READ THIS FIRST — ROS 2 verification protocol"
CONFIG_DIRS = ("rules", "skills", "agents", "commands", "output-styles", "plugins")
ANCESTOR_FILES = ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md")
PRUNE = {".git", "node_modules", ".cache", "__pycache__", "build", "install", "log"}


class Refuse(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code


def _real(p: str | Path) -> str:
    return os.path.realpath(p)


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def worktrees(repo: str) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", repo, "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    paths = [line[len("worktree "):] for line in out.splitlines()
             if line.startswith("worktree ")]
    return [p for p in paths if os.path.isdir(p)] or [repo]


def scan(root: str, maxdepth: int, skip: set[str]) -> list[tuple[str, str]]:
    """Copies of this repository's content under `root`, depth-bounded."""
    found: list[tuple[str, str]] = []
    root = _real(root)
    if not os.path.isdir(root):
        return found
    base = root.rstrip("/").count("/")
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        depth = dirpath.rstrip("/").count("/") - base
        dirnames[:] = [d for d in dirnames
                       if d not in PRUNE and _real(os.path.join(dirpath, d)) not in skip
                       and not os.path.islink(os.path.join(dirpath, d))]
        if depth >= maxdepth:
            dirnames[:] = []
        if dirpath.endswith("/evals/harness") and "isolate_cell.sh" in filenames:
            found.append(("d", dirpath[: -len("/evals/harness")]))
        if dirpath.endswith("/ros2-troubleshooting") and "SKILL.md" in filenames:
            found.append(("d", os.path.dirname(dirpath)))
        if "check_imu_gravity.py" in filenames:
            found.append(("d", dirpath))
        if "CLAUDE.md" in filenames:
            f = os.path.join(dirpath, "CLAUDE.md")
            try:
                with open(f, encoding="utf-8", errors="ignore") as fh:
                    if MARKER in fh.read(4096):
                        found.append(("f", f))
            except OSError:
                pass
    return found


def plan(*, repo: str, workdir: str, cfg: str, home: str, tmp: str = "/tmp",
         extra: str = "", managed: str = "/etc/claude-code",
         allow_managed: bool = False, home_depth: int = 6,
         tmp_depth: int = 5) -> list[tuple[str, str]]:
    workdir, cfg = _real(workdir), _real(cfg)

    if os.path.isdir(managed) and os.listdir(managed) and not allow_managed:
        raise Refuse(5, f"managed policy in {managed} loads into every session and "
                        f"cannot be excluded; set EVAL_ALLOW_MANAGED_POLICY=1 only if "
                        f"it is identical for every condition")

    cand: list[tuple[str, str]] = [("d", _real(w)) for w in worktrees(repo)]
    cand.append(("d", _real(repo)))

    for e in [x for x in extra.split(":") if x]:
        if not os.path.exists(e):
            raise Refuse(2, f"EVAL_MASK_PATHS entry {e!r} does not exist -- refusing "
                            f"rather than silently leaving something visible")
        cand.append(("d" if os.path.isdir(e) else "f", _real(e)))

    if os.path.isfile(os.path.join(cfg, "CLAUDE.md")):
        cand.append(("f", os.path.join(cfg, "CLAUDE.md")))
    for d in CONFIG_DIRS:
        if os.path.isdir(os.path.join(cfg, d)):
            cand.append(("d", os.path.join(cfg, d)))

    d = os.path.dirname(workdir)
    while True:
        for n in ANCESTOR_FILES:
            if os.path.isfile(os.path.join(d, n)):
                cand.append(("f", os.path.join(d, n)))
        dotc = os.path.join(d, ".claude")
        if os.path.isdir(dotc) and _real(dotc) != cfg:
            cand.append(("d", _real(dotc)))
        if d == "/":
            break
        d = os.path.dirname(d)

    skip = {os.path.join(cfg, "projects")}
    for root, depth in ((home, home_depth), (tmp, tmp_depth)):
        cand.extend(scan(root, depth, skip))

    # The cell's own treatment files are meant to be there.
    cand = [(k, p) for k, p in cand if not _under(p, workdir) or p == workdir]

    for k, p in cand:
        if k == "d" and _under(workdir, p):
            raise Refuse(6, f"{p} would be hidden, and the workdir {workdir} is inside it")
        if k == "d" and _under(cfg, p):
            raise Refuse(6, f"{p} would hide Claude's whole config dir {cfg}, "
                            f"credentials included -- no cell could log in")

    # Deduplicate; a path inside a hidden directory is already hidden.
    dirs = sorted({p for k, p in cand if k == "d"})
    kept_dirs: list[str] = []
    for p in dirs:
        if not any(_under(p, q) for q in kept_dirs):
            kept_dirs.append(p)
    files = sorted({p for k, p in cand if k == "f"
                    and not any(_under(p, q) for q in kept_dirs)})
    return [("d", p) for p in kept_dirs] + [("f", p) for p in files]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--workdir", required=True)
    p.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    a = ap.parse_args(argv)
    home = os.environ.get("HOME", "")
    try:
        masks = plan(
            repo=a.repo, workdir=a.workdir, home=home,
            cfg=os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude"),
            extra=os.environ.get("EVAL_MASK_PATHS", ""),
            managed=os.environ.get("EVAL_MANAGED_POLICY_DIR", "/etc/claude-code"),
            allow_managed=os.environ.get("EVAL_ALLOW_MANAGED_POLICY") == "1",
            tmp=os.environ.get("EVAL_SCAN_TMP", "/tmp"))
    except Refuse as e:
        print(f"isolate_cell.sh: REFUSING: {e}", file=sys.stderr)
        return e.code
    for k, path in masks:
        if "\n" in path:
            print(f"isolate_cell.sh: REFUSING: newline in path {path!r}", file=sys.stderr)
            return 6
        print(f"{k} {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
