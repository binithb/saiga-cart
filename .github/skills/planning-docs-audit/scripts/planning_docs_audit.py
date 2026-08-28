#!/usr/bin/env python3
"""Audit workspace planning documents, stories, DoR contracts, and ADR indexes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote


ALLOWED_STATUSES = {"Not started", "In progress", "Blocked", "Done"}
ALLOWED_EFFORTS = {"Small", "Medium", "Large"}
ALLOWED_DOR_STATUSES = {"Draft", "Pending Clarification", "Done"}
DEFAULT_TICKET_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b|#\d+\b")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PROGRESS_RE = re.compile(
    r"^\s*-\s+\[([ xX])\]\s+\[[^\]]+\]\(([^)]+)\)(?:\s+[—-]\s+(.+))?"
)


@dataclass(frozen=True)
class Finding:
    severity: str
    path: str
    message: str


class PlanningAuditor:
    def __init__(self, root: Path, scope_id: str | None = None, planning_dir_name: str = "planning") -> None:
        self.root = root.resolve()
        self.scope_id = scope_id
        self.planning_dir_name = planning_dir_name
        self.findings: list[Finding] = []
        self.tracker_stories: dict[str, list[Path]] = defaultdict(list)
        self.story_dependencies: dict[Path, list[Path]] = {}

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def add(self, severity: str, path: Path, message: str) -> None:
        self.findings.append(Finding(severity, self.relative(path), message))

    def audit(self) -> list[Finding]:
        planning_root = self.root / "docs" / self.planning_dir_name
        if not planning_root.is_dir():
            # Fallback check for docs/pi or docs/sprints
            for fallback in ("pi", "sprints", "cycles", "milestones"):
                if (self.root / "docs" / fallback).is_dir():
                    planning_root = self.root / "docs" / fallback
                    break

        if not planning_root.is_dir():
            self.add("WARNING", self.root / "docs", "No planning directory found under docs/")
            self.audit_adr_index()
            return self.findings

        scopes = [planning_root / self.scope_id] if self.scope_id else sorted(
            path for path in planning_root.iterdir()
            if path.is_dir() and not path.name.startswith((".", "templates", "pi-template", "sprint-template", "cycle-template", "kanban-template"))
        )
        for scope in scopes:
            if not scope.is_dir():
                self.add("ERROR", scope, f"Planning scope {scope.name} does not exist")
                continue
            for stories_dir in sorted(scope.rglob("stories")):
                if stories_dir.is_dir():
                    self.audit_epic_or_container(stories_dir)
            for tasks_dir in sorted(scope.rglob("tasks")):
                if tasks_dir.is_dir():
                    self.audit_epic_or_container(tasks_dir)
            for scopes_dir in sorted(scope.rglob("scopes")):
                if scopes_dir.is_dir():
                    self.audit_epic_or_container(scopes_dir)
            self.audit_local_links(scope)

        self.audit_duplicate_tracker_keys()
        self.audit_dependency_cycles()
        self.audit_adr_index()
        return sorted(self.findings, key=lambda item: (item.severity, item.path, item.message))

    def audit_epic_or_container(self, stories_dir: Path) -> None:
        progress = stories_dir.parent / "progress.md"
        if not progress.is_file():
            self.add("ERROR", stories_dir, f"{stories_dir.name} directory has no sibling progress.md")
            return

        story_files = sorted(stories_dir.glob("*.md"))
        for child in sorted(stories_dir.iterdir()):
            if child.name in {"backlog-scratchpad.txt", "notes.txt"}:
                continue
            if child.name.startswith(".") or child.name.lower() in {"thumbs.db", "desktop.ini"}:
                continue
            if child.is_file() and child.suffix.lower() != ".md":
                self.add("WARNING", child, f"unexpected non-Markdown file under {stories_dir.name}/")
            elif child.is_dir():
                self.add("WARNING", child, f"unexpected subdirectory under {stories_dir.name}/")

        progress_refs: Counter[Path] = Counter()
        checkbox_state: dict[Path, bool] = {}
        progress_labels: dict[Path, str] = {}
        for line_number, line in enumerate(progress.read_text(encoding="utf-8").splitlines(), 1):
            match = PROGRESS_RE.match(line)
            if not match:
                continue
            target_text = self.clean_link_target(match.group(2))
            if not (target_text.startswith(f"{stories_dir.name}/") or target_text.startswith("./")):
                continue
            target = (progress.parent / target_text).resolve()
            progress_refs[target] += 1
            checkbox_state[target] = match.group(1).lower() == "x"
            if match.group(3):
                progress_labels[target] = match.group(3).strip()
            if not target.is_file():
                self.add("ERROR", progress, f"line {line_number}: story link does not resolve: {target_text}")

        story_set = {path.resolve() for path in story_files}
        for story in story_files:
            resolved = story.resolve()
            count = progress_refs[resolved]
            if count == 0:
                self.add("ERROR", story, "story is not linked from its parent progress.md")
            elif count > 1:
                self.add("ERROR", progress, f"story is linked {count} times: {story.name}")
            status = self.audit_story(story)
            if status and resolved in checkbox_state:
                checked = checkbox_state[resolved]
                if status == "Done" and not checked:
                    self.add("WARNING", progress, f"{story.name} is Done but remains unchecked")
                elif status != "Done" and checked:
                    self.add("WARNING", progress, f"{story.name} is {status} but is checked")

    def audit_story(self, story: Path) -> str | None:
        text = story.read_text(encoding="utf-8")
        metadata = self.parse_metadata(text)

        status = metadata.get("Status")
        if status and status not in ALLOWED_STATUSES:
            self.add("ERROR", story, f"unsupported Status value: {status}")

        effort = metadata.get("Effort")
        dor_status = metadata.get("Definition of Ready")
        if effort is not None and dor_status is None:
            self.add("ERROR", story, "Effort metadata requires Definition of Ready metadata")
        if dor_status is not None and effort is None:
            self.add("ERROR", story, "Definition of Ready metadata requires Effort metadata")
        if effort and effort not in ALLOWED_EFFORTS:
            self.add("ERROR", story, f"unsupported Effort value: {effort}")
        if dor_status and dor_status not in ALLOWED_DOR_STATUSES:
            self.add("ERROR", story, f"unsupported Definition of Ready value: {dor_status}")
        if effort == "Large" and dor_status == "Done":
            self.add("ERROR", story, "Large story cannot have Definition of Ready set to Done")

        self.audit_story_dependencies(story, metadata)

        tracker_field = next(
            (v for k, v in metadata.items() if any(term in k.lower() for term in ("jira", "tracker", "issue", "github", "gitlab", "story")) and k not in {"Status", "Effort", "Definition of Ready", "Depends on", "Epic", "Pitch"}),
            None
        )
        if tracker_field and not tracker_field.upper().startswith("TBD"):
            keys = DEFAULT_TICKET_RE.findall(tracker_field)
            if keys:
                key = keys[0]
                self.tracker_stories[key].append(story)
        return status

    def audit_story_dependencies(self, story: Path, metadata: dict[str, str]) -> None:
        raw_value = metadata.get("Depends on")
        if raw_value is None:
            return

        resolved: list[Path] = []
        targets = LINK_RE.findall(raw_value)
        for raw_target in targets:
            target_text = self.clean_link_target(raw_target)
            if not target_text or self.is_external_link(target_text):
                continue
            target = (story.parent / target_text).resolve()
            if target == story.resolve():
                self.add("ERROR", story, "Depends on must not reference the story itself")
                continue
            if not target.is_file():
                self.add("ERROR", story, f"Depends on link does not resolve: {target_text}")
                continue
            if target.parent != story.parent:
                self.add("ERROR", story, f"Depends on must reference a story in the same container: {target_text}")
                continue
            resolved.append(target)
        self.story_dependencies[story.resolve()] = resolved

    def audit_dependency_cycles(self) -> None:
        visiting: set[Path] = set()
        settled: set[Path] = set()
        reported: set[Path] = set()

        def visit(node: Path, trail: list[Path]) -> None:
            if node in settled:
                return
            if node in visiting:
                cycle = trail[trail.index(node):] + [node]
                names = " -> ".join(item.name for item in cycle)
                for member in cycle:
                    if member not in reported:
                        reported.add(member)
                        self.add("ERROR", member, f"Depends on forms a dependency cycle: {names}")
                return
            visiting.add(node)
            for dependency in self.story_dependencies.get(node, []):
                visit(dependency, trail + [node])
            visiting.discard(node)
            settled.add(node)

        for story in sorted(self.story_dependencies):
            visit(story, [])

    def audit_duplicate_tracker_keys(self) -> None:
        for key, stories in sorted(self.tracker_stories.items()):
            if len(stories) > 1:
                paths = ", ".join(self.relative(path) for path in stories)
                for story in stories:
                    self.add("ERROR", story, f"Tracker key {key} is reused by: {paths}")

    def audit_local_links(self, scope: Path) -> None:
        for document in sorted(scope.rglob("*.md")):
            if document.name == "0000-template.md" or "templates" in document.parts:
                continue
            for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
                for raw_target in LINK_RE.findall(line):
                    target_text = self.clean_link_target(raw_target)
                    if not target_text or self.is_external_link(target_text):
                        continue
                    target = (document.parent / target_text).resolve()
                    if not target.exists():
                        self.add("ERROR", document, f"line {line_number}: local link does not resolve: {target_text}")

    def audit_adr_index(self) -> None:
        for adr_rel in ("docs/adr", "docs/ai/adr"):
            adr_root = self.root / adr_rel
            if adr_root.is_dir():
                index = adr_root / "README.md"
                if not index.is_file():
                    self.add("ERROR", index, "ADR index README.md does not exist")
                    continue
                text = index.read_text(encoding="utf-8")
                indexed = Counter(
                    target.split("#", 1)[0]
                    for target in LINK_RE.findall(text)
                    if re.fullmatch(r"\d{4}-[^)]+\.md", target.split("#", 1)[0])
                )
                for adr in sorted(adr_root.glob("[0-9][0-9][0-9][0-9]-*.md")):
                    if adr.name.startswith("0000-"):
                        continue
                    count = indexed[adr.name]
                    if count == 0:
                        self.add("ERROR", adr, "ADR is missing from ADR index")
                self.audit_local_links(adr_root)

    @staticmethod
    def parse_metadata(text: str) -> dict[str, str]:
        metadata: dict[str, str] = {}
        for line in text.splitlines():
            match = re.match(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$", line)
            if match and match.group(1) not in {"Field", "---"}:
                metadata[match.group(1)] = match.group(2)
        return metadata

    @staticmethod
    def clean_link_target(raw_target: str) -> str:
        target = raw_target.strip().split("#", 1)[0]
        return unquote(target.split(' "', 1)[0].strip("<>"))

    @staticmethod
    def is_external_link(target: str) -> bool:
        return target.startswith(("http://", "https://", "mailto:", "tel:", "#"))


def default_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "docs").is_dir():
        return cwd
    return Path(__file__).resolve().parents[4]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root(), help="workspace root directory")
    parser.add_argument("--scope", help="audit only this scope (e.g. PI number, Sprint number)")
    parser.add_argument("--planning-dir", default="planning", help="planning directory name under docs/")
    parser.add_argument("--json", action="store_true", help="output findings as JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings = PlanningAuditor(args.root, args.scope, args.planning_dir).audit()
    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        for item in findings:
            print(f"{item.severity}\t{item.path}\t{item.message}")
        errors = sum(item.severity == "ERROR" for item in findings)
        warnings = sum(item.severity == "WARNING" for item in findings)
        print(f"Summary: {errors} error(s), {warnings} warning(s)")
    return 1 if any(item.severity == "ERROR" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
