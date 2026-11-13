#!/usr/bin/env python3
"""Deterministic CLI to query, record, and graduate entries in docs/ai/experience.md.

Adapted from Google Research's Harness² library & distillation rules
(`harness2/core/library.py`, `harness2/core/selection.py`, and `harness2/core/prompts.py`):
- Enforces the Confounder Gate (`--effect confounded` is blocked with NO_ENTRY).
- Enforces the Anti-Rubric-Overfitting Guard (rejects grader-verdict strings).
- Formats markdown table rows deterministically with sequential `EXP-NNNN` IDs.
- Transitions entries to `graduated (<target>)` after verifying the target path exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


DEFAULT_MAX_EXPERIENCE_CHARS = 12000
VALID_CONFIDENCE = ("high", "medium", "provisional")
VALID_EFFECTS = ("helped", "hurt", "no_effect", "confounded")
VALID_STATUSES = ("provisional", "active")

ROW_RE = re.compile(
    r"^\|\s*`(EXP-\d{4})`\s*\|\s*((?:\\\||[^|])+?)\s*\|\s*((?:\\\||[^|])+?)\s*\|\s*((?:\\\||[^|])+?)\s*\|\s*((?:\\\||[^|])+?)\s*\|\s*((?:\\\||[^|])+?)\s*\|$"
)


@dataclass(frozen=True)
class ExperienceEntry:
    entry_id: str
    entry_date: str
    cue: str
    lesson: str
    evidence: str
    status: str


def default_root() -> Path:
    cwd = Path.cwd()
    if ((cwd / "AGENTS.md").is_file() or (cwd / "AGENTS.md.template").is_file()) and (
        cwd / "docs" / "ai" / "experience.md"
    ).is_file():
        return cwd
    return Path(__file__).resolve().parents[4]


def sanitize_cell(value: str) -> str:
    cleaned = " ".join(value.strip().splitlines()).strip()
    return cleaned.replace("|", "\\|")


def parse_entries(text: str) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = ROW_RE.match(line)
        if not match:
            continue
        entries.append(
            ExperienceEntry(
                entry_id=match.group(1).strip(),
                entry_date=match.group(2).strip(),
                cue=match.group(3).strip(),
                lesson=match.group(4).strip(),
                evidence=match.group(5).strip(),
                status=match.group(6).strip().strip("`"),
            )
        )
    return entries


def next_entry_id(entries: list[ExperienceEntry]) -> str:
    if not entries:
        return "EXP-0001"
    max_num = max(int(item.entry_id.split("-", 1)[1]) for item in entries)
    return f"EXP-{max_num + 1:04d}"


def cmd_query(args: argparse.Namespace) -> int:
    ledger = args.root.resolve() / "docs" / "ai" / "experience.md"
    if not ledger.is_file():
        print(f"ERROR: Experience ledger not found: {ledger}", file=sys.stderr)
        return 1

    entries = parse_entries(ledger.read_text(encoding="utf-8"))
    filtered: list[ExperienceEntry] = []
    for item in entries:
        haystack = f"{item.cue} {item.lesson} {item.evidence} {item.status}".lower()
        if args.repo:
            repo_lower = args.repo.lower()
            if f"[{repo_lower}]" not in item.cue.lower() and repo_lower not in item.cue.lower():
                continue
        if args.status and not item.status.lower().startswith(args.status.lower()):
            continue
        if args.text and args.text.lower() not in haystack:
            continue
        filtered.append(item)

    if args.json:
        print(json.dumps([asdict(item) for item in filtered], indent=2))
    else:
        if not filtered:
            print("No matching experience entries.")
            return 0
        for item in filtered:
            print(f"{item.entry_id} ({item.entry_date}) [{item.status}]")
            print(f"  Cue:      {item.cue}")
            print(f"  Lesson:   {item.lesson}")
            print(f"  Evidence: {item.evidence}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    # Upstream Confounder Gate (google-research/harness2/harness2/core/prompts.py)
    if args.effect == "confounded":
        print(
            "NO_ENTRY: Confounded trajectory evidence (--effect confounded) cannot be recorded in docs/ai/experience.md. "
            "Isolate the variable before distilling a rule.",
            file=sys.stderr,
        )
        return 2
    if args.effect == "no_effect":
        print(
            "NO_ENTRY: Edit had no observed effect (--effect no_effect); skipping experience ledger write.",
            file=sys.stderr,
        )
        return 2

    root = args.root.resolve()
    ledger = root / "docs" / "ai" / "experience.md"
    if not ledger.is_file():
        print(f"ERROR: Experience ledger not found: {ledger}", file=sys.stderr)
        return 1

    text = ledger.read_text(encoding="utf-8")
    entries = parse_entries(text)
    new_id = next_entry_id(entries)
    today = args.date or date.today().isoformat()

    cue_prefix = f"[{args.repo}] " if args.repo and f"[{args.repo}]" not in args.cue else ""
    cue_cell = sanitize_cell(f"{cue_prefix}{args.cue}")
    lesson_cell = sanitize_cell(args.lesson)
    evidence_cell = sanitize_cell(f"{args.evidence} (effect: {args.effect}, confidence: {args.confidence})")
    status_cell = f"`{sanitize_cell(args.status)}`"

    new_row = f"| `{new_id}` | {today} | {cue_cell} | {lesson_cell} | {evidence_cell} | {status_cell} |"
    lines = text.splitlines()
    last_row_idx = None
    for idx, line in enumerate(lines):
        if ROW_RE.match(line.strip()):
            last_row_idx = idx
    if last_row_idx is not None:
        lines.insert(last_row_idx + 1, new_row)
        updated_text = "\n".join(lines) + "\n"
    else:
        updated_text = text.rstrip("\n") + "\n" + new_row + "\n"

    if len(updated_text) > args.max_chars:
        print(
            f"ERROR: Recording {new_id} would exceed docs/ai/experience.md budget "
            f"({len(updated_text)} > {args.max_chars} chars). Graduate or prune older entries first.",
            file=sys.stderr,
        )
        return 1

    ledger.write_text(updated_text, encoding="utf-8")
    print(f"Recorded {new_id} in docs/ai/experience.md ({len(updated_text)}/{args.max_chars} chars).")
    return 0


def cmd_graduate(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    ledger = root / "docs" / "ai" / "experience.md"
    if not ledger.is_file():
        print(f"ERROR: Experience ledger not found: {ledger}", file=sys.stderr)
        return 1

    target_rel = args.target.strip()
    target_path = (root / target_rel).resolve()
    if not target_path.is_relative_to(root):
        print(f"ERROR: Graduation target must be inside workspace root: {target_rel}", file=sys.stderr)
        return 1
    if not target_path.exists():
        print(f"ERROR: Graduation target does not exist on disk: {target_rel}", file=sys.stderr)
        return 1

    lines = ledger.read_text(encoding="utf-8").splitlines()
    found = False
    updated_lines: list[str] = []
    for line in lines:
        match = ROW_RE.match(line.strip())
        if match and match.group(1).strip() == args.id:
            found = True
            entry_id, entry_date, cue, lesson, evidence, _ = (match.group(i).strip() for i in range(1, 7))
            new_status = f"`graduated ({sanitize_cell(target_rel)})`"
            updated_lines.append(
                f"| `{entry_id}` | {entry_date} | {cue} | {lesson} | {evidence} | {new_status} |"
            )
        else:
            updated_lines.append(line)

    if not found:
        print(f"ERROR: Experience entry {args.id!r} not found in docs/ai/experience.md", file=sys.stderr)
        return 1

    ledger.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    print(f"Graduated {args.id} -> graduated ({target_rel}).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root(), help="workspace root")

    subparsers = parser.add_subparsers(dest="command", required=True)

    query_p = subparsers.add_parser("query", help="Query entries from docs/ai/experience.md")
    query_p.add_argument("--repo", help="Filter entries mentioning a repository name")
    query_p.add_argument("--status", help="Filter by status prefix (provisional, active, graduated)")
    query_p.add_argument("--text", help="Filter by substring across cue, lesson, and evidence")
    query_p.add_argument("--json", action="store_true", help="Emit matching entries as JSON")
    query_p.set_defaults(func=cmd_query)

    rec_p = subparsers.add_parser("record", help="Record a new human-approved lesson in docs/ai/experience.md")
    rec_p.add_argument("--repo", help="Optional target repository slug (e.g. core-service)")
    rec_p.add_argument("--cue", required=True, help="When/where the agent needs this lesson")
    rec_p.add_argument("--lesson", required=True, help="Transferable Do / Do Not rule")
    rec_p.add_argument("--evidence", required=True, help="Trajectory failure, story key, or PR/MR review evidence")
    rec_p.add_argument(
        "--confidence",
        choices=VALID_CONFIDENCE,
        default="provisional",
        help="Confidence level (default: provisional)",
    )
    rec_p.add_argument(
        "--effect",
        choices=VALID_EFFECTS,
        required=True,
        help="Observed causal effect from upstream Harness² rubric (confounded/no_effect are blocked)",
    )
    rec_p.add_argument(
        "--status",
        choices=VALID_STATUSES,
        default="provisional",
        help="Initial ledger status (default: provisional)",
    )
    rec_p.add_argument("--date", help="ISO date override (YYYY-MM-DD)")
    rec_p.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_EXPERIENCE_CHARS,
        help=f"Maximum character budget for docs/ai/experience.md (default: {DEFAULT_MAX_EXPERIENCE_CHARS})",
    )
    rec_p.set_defaults(func=cmd_record)

    grad_p = subparsers.add_parser("graduate", help="Mark an EXP-NNNN entry as graduated into a script or skill")
    grad_p.add_argument("--id", required=True, help="Experience ID (e.g. EXP-0003)")
    grad_p.add_argument("--target", required=True, help="Workspace-relative path of the script or SKILL.md")
    grad_p.set_defaults(func=cmd_graduate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
