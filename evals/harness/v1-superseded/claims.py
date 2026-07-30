#!/usr/bin/env python3
"""Split every SKILL.md into atomic, stably-IDed claims — and put them back.

Two operations, and the second is why the first exists:

    inventory()  SKILL.md -> [Claim]   every table row, list item and bullet,
                                       with the exact line span it occupies
    ablate(id)   [Claim]   -> SKILL.md  the same body with one claim removed

Ablation is the only way to ask "does this line change what the agent writes?"
so the split has to be reversible: dropping a claim must leave a body that looks
like it was authored that way, not one with a hole in it. Numbered lists are
renumbered on removal for exactly that reason — a jump from 3. to 5. is a signal
to the model that something was taken out, which would confound the measurement.

    python3 claims.py inventory                 # write claims.jsonl
    python3 claims.py show <claim-id>
    python3 claims.py ablate <claim-id>         # patched body to stdout
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills"
OUT = REPO / "evals" / "claims" / "claims.jsonl"

# --- what kind of statement is this? -----------------------------------------
# The taxonomy is not decoration: it decides which bar a line has to clear.
#   nav   — a pointer to a doc. Cannot be ablation-tested (its effect is that the
#           agent fetches something); judged by whether the URL resolves.
#   fact  — a claim about what exists in Jazzy. Judged by verification, free.
#   rule  — a claim about what the agent should DO. The only ablation target,
#           because it is the only kind that predicts an output difference.
NAV_SECTION = re.compile(r"documentation|entry point|reference|further reading", re.I)
FACT_SECTION = re.compile(r"symbols?|interfaces?|ground truth|inspection", re.I)
RULE_SECTION = re.compile(r"rule|symptom|checklist|gate|workflow|pattern|recipe|do |never", re.I)

URL = re.compile(r"https?://\S+")
CODE = re.compile(r"`([^`]+)`")
IMPERATIVE = re.compile(
    r"^\s*(never|always|do not|don't|use |run |check |verify |prefer |avoid |match |ask |confirm |keep |wrap |catch |declare |install |source |rebuild |state )",
    re.I,
)


@dataclass
class Claim:
    id: str
    skill: str
    path: str
    section: str
    kind: str          # table_row | list_item | bullet | prose
    klass: str         # nav | fact | rule
    line_start: int    # 1-indexed, inclusive
    line_end: int      # 1-indexed, inclusive
    text: str
    sha: str
    symbols: list[str] = field(default_factory=list)
    ablatable: bool = True


def _classify(section: str, text: str, kind: str) -> str:
    if URL.search(text) and len(URL.sub("", text).strip(" |`-")) < 60:
        return "nav"
    if NAV_SECTION.search(section):
        return "nav"
    if RULE_SECTION.search(section):
        return "rule"
    if FACT_SECTION.search(section):
        return "fact"
    if IMPERATIVE.search(text):
        return "rule"
    return "fact"


def _slug(s: str) -> str:
    s = re.sub(r"^#+\s*", "", s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"^(\d+)-", r"\1", s)[:40] or "body"


def inventory_file(path: Path) -> list[Claim]:
    skill = path.parent.name if path.name == "SKILL.md" else f"{path.parent.parent.name}/{path.stem}"
    lines = path.read_text(encoding="utf-8").splitlines()

    claims: list[Claim] = []
    section = "frontmatter"
    in_front = False
    in_fence = False
    seq: dict[str, int] = {}

    def add(kind: str, i0: int, i1: int, text: str) -> None:
        sec = _slug(section)
        seq[sec] = seq.get(sec, 0) + 1
        cid = f"{skill}:{sec}:{seq[sec]:02d}"
        claims.append(
            Claim(
                id=cid,
                skill=skill,
                path=str(path.relative_to(REPO)),
                section=section,
                kind=kind,
                klass=_classify(section, text, kind),
                line_start=i0 + 1,
                line_end=i1 + 1,
                text=text.strip(),
                sha=hashlib.sha256(text.strip().encode()).hexdigest()[:12],
                symbols=sorted({m for m in CODE.findall(text) if len(m) > 2}),
            )
        )

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        if i == 0 and stripped == "---":
            in_front = True
            i += 1
            continue
        if in_front:
            if stripped == "---":
                in_front = False
            i += 1
            continue

        if stripped.startswith("```"):
            # A fenced block is one claim: splitting a code sample by line would
            # produce units that mean nothing on their own.
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            add("code_block", i, min(j, len(lines) - 1), "\n".join(lines[i : j + 1]))
            i = j + 1
            continue

        if stripped.startswith("#"):
            section = stripped
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        # Table: header + separator are structure, not claims; only rows count.
        if stripped.startswith("|"):
            if i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
                i += 2
                continue
            if re.match(r"^\s*\|[\s:|-]+\|\s*$", stripped):
                i += 1
                continue
            add("table_row", i, i, raw)
            i += 1
            continue

        if re.match(r"^\s*\d+\.\s", raw):
            j = i
            while j + 1 < len(lines) and lines[j + 1].startswith(("   ", "\t")) and lines[j + 1].strip():
                j += 1
            add("list_item", i, j, "\n".join(lines[i : j + 1]))
            i = j + 1
            continue

        if re.match(r"^\s*[-*]\s", raw):
            j = i
            while j + 1 < len(lines) and lines[j + 1].startswith(("   ", "\t")) and lines[j + 1].strip():
                j += 1
            add("bullet", i, j, "\n".join(lines[i : j + 1]))
            i = j + 1
            continue

        j = i
        while j + 1 < len(lines) and lines[j + 1].strip() and not re.match(
            r"^\s*([-*#|]|\d+\.)", lines[j + 1]
        ):
            j += 1
        add("prose", i, j, "\n".join(lines[i : j + 1]))
        i = j + 1

    return claims


def inventory() -> list[Claim]:
    paths = sorted(SKILLS.glob("*/SKILL.md")) + sorted(SKILLS.glob("*/references/*.md"))
    out: list[Claim] = []
    for p in paths:
        out.extend(inventory_file(p))
    return out


def _renumber(lines: list[str]) -> list[str]:
    """Close the gap a removed list item leaves behind.

    Only consecutive runs at the same indent are renumbered, so a body with two
    separate numbered lists does not get merged into one sequence.
    """
    out = list(lines)
    i = 0
    while i < len(out):
        m = re.match(r"^(\s*)(\d+)\.\s", out[i])
        if not m:
            i += 1
            continue
        indent = m.group(1)
        run = []
        j = i
        while j < len(out):
            mm = re.match(rf"^{re.escape(indent)}(\d+)\.\s", out[j])
            if mm:
                run.append(j)
                j += 1
            elif out[j].startswith(indent + " ") or (not out[j].strip() and run):
                j += 1
            else:
                break
        for n, idx in enumerate(run, 1):
            out[idx] = re.sub(r"^(\s*)\d+\.", rf"\g<1>{n}.", out[idx])
        i = j
    return out


HEADING_RE = re.compile(r"^(#{2,6})\s+\S")


def _drop_orphaned_headings(lines: list[str]) -> list[str]:
    """Remove headings the ablation emptied out.

    Deleting the only claim under a `### A. cv_bridge ...` subheading leaves the
    heading standing over nothing — a seam announcing that something used to be
    here, which is a different stimulus from a body that never mentioned the
    topic. `_renumber` already closes the equivalent gap in numbered lists; this
    closes it for sections.

    A heading survives if any non-blank line precedes the next heading, or if
    the next heading is *deeper* than it (a parent whose subsections carry the
    content is not empty).
    """
    heads = [i for i, l in enumerate(lines) if HEADING_RE.match(l)]
    drop: set[int] = set()
    for pos, i in enumerate(heads):
        level = len(HEADING_RE.match(lines[i]).group(1))
        nxt = heads[pos + 1] if pos + 1 < len(heads) else len(lines)
        if any(lines[j].strip() for j in range(i + 1, nxt)):
            continue
        if nxt < len(lines) and len(HEADING_RE.match(lines[nxt]).group(1)) > level:
            continue
        drop.add(i)
        # Trailing blank lines belonged to the heading, not to what follows.
        for j in range(i + 1, nxt):
            drop.add(j)
    return [l for n, l in enumerate(lines) if n not in drop]


SECTION_RE = re.compile(r"^## (\d+)\. (.+)$")


def reorder_sections(path: Path, new_order: list[int]) -> str:
    """Return the file with its numbered `## N. Title` sections reordered.

    Content within each section is untouched; only its position and the `## N.`
    prefix change, so this measures placement, not wording — the same claims,
    read in a different order.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [(i, int(m.group(1)), m.group(2))
              for i, l in enumerate(lines) if (m := SECTION_RE.match(l))]
    if not starts:
        raise ValueError(f"no numbered `## N. Title` sections in {path}")
    sections: dict[int, list[str]] = {}
    for idx, (start, num, _title) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        sections[num] = lines[start:end]
    missing = set(new_order) - set(sections)
    if missing:
        raise ValueError(f"reorder references sections not in {path}: {missing}")
    out = list(lines[:starts[0][0]])
    for new_num, orig_num in enumerate(new_order, 1):
        body = sections[orig_num]
        header = SECTION_RE.match(body[0])
        out.append(f"## {new_num}. {header.group(2)}")
        out.extend(body[1:])
    return "\n".join(out) + "\n"


def ablate(claim: Claim, drop_ids: list[str] | None = None, all_claims: list[Claim] | None = None) -> str:
    """Return the claim's source file with that claim (or several) removed."""
    targets = [claim]
    if drop_ids and all_claims:
        by_id = {c.id: c for c in all_claims}
        targets = [by_id[d] for d in drop_ids]

    path = REPO / targets[0].path
    lines = path.read_text(encoding="utf-8").splitlines()
    kill = set()
    for t in targets:
        kill.update(range(t.line_start - 1, t.line_end))
    kept = [l for n, l in enumerate(lines) if n not in kill]
    if any(t.kind == "list_item" for t in targets):
        kept = _renumber(kept)
    kept = _drop_orphaned_headings(kept)
    return "\n".join(kept) + "\n"


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "inventory"
    claims = inventory()

    if cmd == "inventory":
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8") as fh:
            for c in claims:
                fh.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        by_class: dict[str, int] = {}
        by_skill: dict[str, int] = {}
        for c in claims:
            by_class[c.klass] = by_class.get(c.klass, 0) + 1
            by_skill[c.skill] = by_skill.get(c.skill, 0) + 1
        print(f"{len(claims)} claims -> {OUT.relative_to(REPO)}")
        print("\nby class:")
        for k, v in sorted(by_class.items(), key=lambda kv: -kv[1]):
            print(f"  {k:6} {v:4}")
        print("\nby skill:")
        for k, v in sorted(by_skill.items()):
            print(f"  {k:34} {v:4}")
        return 0

    by_id = {c.id: c for c in claims}
    target = by_id.get(sys.argv[2]) if len(sys.argv) > 2 else None
    if target is None:
        print(f"unknown claim id: {sys.argv[2] if len(sys.argv) > 2 else '(none given)'}", file=sys.stderr)
        return 2

    if cmd == "show":
        print(json.dumps(asdict(target), indent=2, ensure_ascii=False))
        return 0
    if cmd == "ablate":
        sys.stdout.write(ablate(target))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
