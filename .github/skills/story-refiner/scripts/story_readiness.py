#!/usr/bin/env python3
"""Report story readiness and the implementation queue for a planning scope.

Used by the story-refiner skill to produce:
- Readiness dashboard: every non-Done story, its effort, and any missing DoR items.
- Implementation queue: stories ready for autonomous implementation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

READY_EFFORTS = {"Small", "Medium"}
SPLIT_EFFORT = "Large"
DEFAULT_TICKET_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b|#\d+\b")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PROGRESS_RE = re.compile(r"^\s*-\s+\[([ xX])\]\s+\[[^\]]+\]\(([^)]+)\)")
READINESS_GAPS_SECTION_RE = re.compile(
    r"^## Readiness gaps\s*$([\s\S]*?)(?=^## |\Z)", re.MULTILINE
)
READINESS_GAP_RE = re.compile(r"^\s*-\s+(.+?)\s*$", re.MULTILINE)

AVAILABLE = "Available now"
NEEDS_TRACKER = "Needs tracker onboarding"
WAITING = "Waiting for prerequisite"


@dataclass
class Story:
    path: Path
    title: str
    status: str | None
    effort: str | None
    dor: str | None
    tracker_key: str | None
    depends_on: list[Path] = field(default_factory=list)
    readiness_gaps: list[str] = field(default_factory=list)
    order: int = 0

    @property
    def is_done(self) -> bool:
        return self.status in {"Done", "Closed", "Resolved"}

    @property
    def is_unstarted(self) -> bool:
        return self.status in {None, "Not started", "Open", "Backlog", "To Do", "Refined"}

    def blocking_reason(self) -> str | None:
        if self.effort is None or self.dor is None:
            return "not yet refined (missing Effort / Definition of Ready)"
        if self.effort == SPLIT_EFFORT:
            return "split required: Large is not independently executable"
        if self.effort not in READY_EFFORTS:
            return f"unsupported Effort value: {self.effort}"
        if self.dor == "Pending Clarification":
            detail = f": {'; '.join(self.readiness_gaps)}" if self.readiness_gaps else ""
            return f"pending clarification{detail}"
        if self.dor != "Done":
            detail = f": {'; '.join(self.readiness_gaps)}" if self.readiness_gaps else ""
            return f"Definition of Ready is not Done{detail}"
        if self.readiness_gaps:
            return "Definition of Ready is Done but readiness gaps remain"
        return None

    @property
    def is_ready(self) -> bool:
        return self.blocking_reason() is None


def read_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$", line)
        if match and match.group(1) not in {"Field", "---"}:
            metadata[match.group(1)] = match.group(2)
    return metadata


def clean_link_target(raw_target: str) -> str:
    target = raw_target.strip().split("#", 1)[0]
    return unquote(target.split(' "', 1)[0].strip("<>"))


def read_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(?:Story:\s*|Task:\s*|Scope:\s*)?(.+?)\s*$", text, re.MULTILINE)
    return match.group(1) if match else fallback


def progress_order(stories_dir: Path) -> dict[Path, int]:
    progress = stories_dir.parent / "progress.md"
    order: dict[Path, int] = {}
    if not progress.is_file():
        return order
    index = 0
    for line in progress.read_text(encoding="utf-8").splitlines():
        match = PROGRESS_RE.match(line)
        if not match:
            continue
        target_text = clean_link_target(match.group(2))
        if not (target_text.startswith(f"{stories_dir.name}/") or target_text.startswith("./")):
            continue
        order[(progress.parent / target_text).resolve()] = index
        index += 1
    return order


def load_story(path: Path, order: int) -> Story:
    text = path.read_text(encoding="utf-8")
    metadata = read_metadata(text)

    tracker_key = None
    for k, v in metadata.items():
        if any(term in k.lower() for term in ("jira", "tracker", "issue", "github", "gitlab", "story", "task")) and k not in {"Status", "Effort", "Definition of Ready", "Depends on", "Epic", "Pitch"}:
            if not v.upper().startswith("TBD"):
                keys = DEFAULT_TICKET_RE.findall(v)
                if keys:
                    tracker_key = keys[0]
                    break

    depends_on: list[Path] = []
    for raw_target in LINK_RE.findall(metadata.get("Depends on", "")):
        target_text = clean_link_target(raw_target)
        if target_text and not target_text.startswith(("http://", "https://")):
            depends_on.append((path.parent / target_text).resolve())

    gaps_section = READINESS_GAPS_SECTION_RE.search(text)
    readiness_gaps = (
        READINESS_GAP_RE.findall(gaps_section.group(1))
        if gaps_section
        else []
    )

    return Story(
        path=path.resolve(),
        title=read_title(text, path.stem),
        status=metadata.get("Status"),
        effort=metadata.get("Effort"),
        dor=metadata.get("Definition of Ready"),
        tracker_key=tracker_key,
        depends_on=depends_on,
        readiness_gaps=readiness_gaps,
        order=order,
    )


def collect_stories(scopes: list[Path]) -> list[Story]:
    stories: list[Story] = []
    seen: set[Path] = set()
    epic_index = 0
    for scope in scopes:
        container_dirs = []
        for name in ("stories", "tasks", "scopes"):
            if scope.name == name:
                container_dirs.append(scope)
            else:
                container_dirs.extend(sorted(scope.rglob(name)))

        for stories_dir in container_dirs:
            if not stories_dir.is_dir():
                continue
            order = progress_order(stories_dir)
            fallback = len(order)
            for story_path in sorted(stories_dir.glob("*.md")):
                resolved = story_path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                position = order.get(resolved)
                if position is None:
                    position = fallback
                    fallback += 1
                stories.append(load_story(story_path, epic_index * 1000 + position))
            epic_index += 1
    return sorted(stories, key=lambda item: (item.order, item.path.as_posix()))


def find_cycles(stories: list[Story]) -> set[Path]:
    edges = {story.path: story.depends_on for story in stories}
    in_cycle: set[Path] = set()
    visiting: set[Path] = set()
    settled: set[Path] = set()

    def visit(node: Path, trail: list[Path]) -> None:
        if node in settled or node not in edges:
            return
        if node in visiting:
            in_cycle.update(trail[trail.index(node):])
            return
        visiting.add(node)
        for dependency in edges[node]:
            visit(dependency, trail + [node])
        visiting.discard(node)
        settled.add(node)

    for story in stories:
        visit(story.path, [])
    return in_cycle


def order_queue(candidates: list[Story]) -> list[Story]:
    positions = {story.path: index for index, story in enumerate(candidates)}
    emitted: set[Path] = set()
    queue: list[Story] = []

    def emit(story: Story, guard: set[Path]) -> None:
        if story.path in emitted or story.path in guard:
            return
        guard.add(story.path)
        for dependency in sorted(
            story.depends_on, key=lambda item: positions.get(item, -1)
        ):
            if dependency in positions:
                emit(candidates[positions[dependency]], guard)
        emitted.add(story.path)
        queue.append(story)

    for story in candidates:
        emit(story, set())
    return queue


def build_report(stories: list[Story], root: Path) -> dict:
    def relative(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return path.as_posix()

    active = [story for story in stories if not story.is_done]
    done_paths = {story.path for story in stories if story.is_done}
    known = {story.path for story in stories}
    cycles = find_cycles(active)

    dashboard = [
        {
            "story": story.title,
            "path": relative(story.path),
            "status": story.status,
            "effort": story.effort,
            "definition_of_ready": story.dor,
            "blocking_reason": (
                "dependency cycle" if story.path in cycles else story.blocking_reason()
            ),
        }
        for story in active
    ]

    ordered = order_queue(
        [
            story
            for story in active
            if story.is_ready and story.is_unstarted and story.path not in cycles
        ]
    )

    queue = []
    for index, story in enumerate(ordered, 1):
        unmet = [
            dependency
            for dependency in story.depends_on
            if dependency in known and dependency not in done_paths
        ]
        if unmet:
            state = WAITING
        elif story.tracker_key is None:
            state = NEEDS_TRACKER
        else:
            state = AVAILABLE
        queue.append(
            {
                "position": index,
                "story": story.title,
                "path": relative(story.path),
                "tracker": story.tracker_key or "TBD",
                "effort": story.effort,
                "depends_on": [relative(item) for item in story.depends_on],
                "availability": state,
            }
        )

    return {
        "readiness": dashboard,
        "queue": queue,
        "cycles": sorted(relative(path) for path in cycles),
    }


def render(report: dict) -> str:
    lines: list[str] = ["### Readiness summary", ""]
    if report["readiness"]:
        lines += [
            "| Story | Path | Status | Effort | DoR | Blocking reason |",
            "|---|---|---|---|---|---|",
        ]
        for row in report["readiness"]:
            lines.append(
                "| {story} | `{path}` | {status} | {effort} | {dor} | {reason} |".format(
                    story=row["story"],
                    path=row["path"],
                    status=row["status"] or "—",
                    effort=row["effort"] or "—",
                    dor=row["definition_of_ready"] or "—",
                    reason=row["blocking_reason"] or "ready",
                )
            )
    else:
        lines.append("_No active stories in scope._")

    lines += ["", "### Implementation queue", ""]
    if report["queue"]:
        lines += [
            "| # | Story | Path | Tracker | Effort | Depends on | Availability |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in report["queue"]:
            lines.append(
                "| {position} | {story} | `{path}` | {tracker} | {effort} | {deps} | {availability} |".format(
                    position=row["position"],
                    story=row["story"],
                    path=row["path"],
                    tracker=row["tracker"],
                    effort=row["effort"],
                    deps=", ".join(row["depends_on"]) or "—",
                    availability=row["availability"],
                )
            )
    else:
        lines.append("_No stories are ready for implementation._")

    if report["cycles"]:
        lines += ["", "### Blockers", ""]
        for path in report["cycles"]:
            lines.append(f"- Dependency cycle involves `{path}`")

    return "\n".join(lines)


def resolve_scopes(root: Path, args: argparse.Namespace) -> list[Path]:
    if args.path:
        scope = args.path if args.path.is_absolute() else root / args.path
        return [scope.resolve()]
    for p_name in ("planning", "pi", "sprints", "cycles", "milestones"):
        p_root = root / "docs" / p_name
        if p_root.is_dir():
            if args.scope:
                return [(p_root / args.scope).resolve()]
            return sorted(
                path.resolve()
                for path in p_root.iterdir()
                if path.is_dir() and not path.name.startswith((".", "templates", "pi-template", "sprint-template", "cycle-template", "kanban-template"))
            )
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report story readiness and implementation queue.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace root directory")
    parser.add_argument("--scope", help="planning scope number or name (e.g. 01, sprint-1)")
    parser.add_argument("--path", type=Path, help="specific epic, goal, or stories directory")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    scopes = resolve_scopes(root, args)

    for scope in scopes:
        if not scope.is_dir():
            print(f"ERROR: scope does not exist: {scope}", file=sys.stderr)
            return 1

    report = build_report(collect_stories(scopes), root)
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
