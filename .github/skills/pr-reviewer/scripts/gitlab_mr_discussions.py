#!/usr/bin/env python3
"""Fetch, reply to, resolve, and create GitLab Merge Request discussion threads.

Stdlib-only helper for `.github/skills/pr-reviewer/SKILL.md`.
Reads credentials from environment variables (`GITLAB_TOKEN` / `GITLAB_PAT`),
workspace `.env.local` / `.env`, or `~/.copilot/skills/gitlab/.env`.
All mutating subcommands (`reply`, `resolve`, `comment`) require `--confirm`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


MR_URL_RE = re.compile(
    r"^https?://(?P<host>[^/]+)/(?P<project>.+?)/-/merge_requests/(?P<iid>\d+)(?:\b|/|$)"
)
GIT_SSH_RE = re.compile(r"^git@(?P<host>[^:]+):(?P<project>.+?)(?:\.git)?$")
GIT_HTTPS_RE = re.compile(r"^https?://(?P<host>[^/]+)/(?P<project>.+?)(?:\.git)?$")


def load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.is_file():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, val = line.split("=", 1)
        values[key.strip()] = val.strip().strip("'\"")
    return values


def resolve_credentials(env_file: Path | None = None) -> tuple[str, str]:
    merged: dict[str, str] = {}
    candidates = [
        Path.home() / ".copilot" / "skills" / "gitlab" / ".env",
        Path.cwd() / ".env",
        Path.cwd() / ".env.gitlab",
        Path.cwd() / ".env.local",
    ]
    if env_file is not None:
        candidates.append(env_file)
    for candidate in candidates:
        merged.update(load_env_file(candidate))
    merged.update(os.environ)

    token = (
        merged.get("GITLAB_PAT")
        or merged.get("GITLAB_TOKEN")
        or merged.get("GITLAB_PRIVATE_TOKEN")
        or ""
    ).strip()
    host_url = (
        merged.get("GITLAB_URL")
        or merged.get("GITLAB_HOST")
        or "https://gitlab.com"
    ).strip().rstrip("/")
    if host_url and not host_url.startswith(("http://", "https://")):
        host_url = f"https://{host_url}"
    return host_url, token


def parse_git_remote(repo_dir: Path) -> tuple[str | None, str | None]:
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None, None
    if proc.returncode != 0:
        return None, None
    remote = proc.stdout.strip()
    m_ssh = GIT_SSH_RE.match(remote)
    if m_ssh:
        return f"https://{m_ssh.group('host')}", m_ssh.group("project")
    m_https = GIT_HTTPS_RE.match(remote)
    if m_https:
        return f"https://{m_https.group('host')}", m_https.group("project")
    return None, None


def resolve_mr_target(
    mr_ref: str,
    *,
    project: str | None = None,
    repo_dir: Path | None = None,
    default_host: str = "https://gitlab.com",
) -> tuple[str, str, int]:
    m_url = MR_URL_RE.match(mr_ref.strip())
    if m_url:
        host = f"https://{m_url.group('host')}"
        return host, m_url.group("project"), int(m_url.group("iid"))

    iid_str = mr_ref.strip().lstrip("!")
    if not iid_str.isdigit():
        raise ValueError(
            f"Invalid MR reference {mr_ref!r}: expected full GitLab MR URL or numeric IID (e.g. '42' or '!42')"
        )
    iid = int(iid_str)
    remote_host, remote_project = parse_git_remote(repo_dir or Path.cwd())
    resolved_project = (project or remote_project or "").strip()
    if not resolved_project:
        raise ValueError(
            "Could not determine GitLab project path; pass --project <group/project> or a full MR URL"
        )
    resolved_host = remote_host or default_host
    return resolved_host.rstrip("/"), resolved_project, iid


class GitLabClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/api/v4{path}"
        if query:
            qs = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
            if qs:
                url = f"{url}?{qs}"
        headers = {
            "Accept": "application/json",
        }
        if self.token:
            headers["PRIVATE-TOKEN"] = self.token
        data: bytes | None = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitLab API {method} {path} failed ({exc.code}): {err_body}") from exc


def summarize_discussions(
    discussions: list[dict[str, Any]],
    *,
    unresolved_only: bool = False,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for disc in discussions:
        notes = [
            n
            for n in disc.get("notes", [])
            if isinstance(n, dict) and not n.get("system", False)
        ]
        if not notes:
            continue
        resolvable = any(bool(n.get("resolvable")) for n in notes)
        resolved = all(bool(n.get("resolved")) for n in notes if n.get("resolvable"))
        if unresolved_only and (not resolvable or resolved):
            continue

        first = notes[0]
        pos = first.get("position") or {}
        file_path = pos.get("new_path") or pos.get("old_path")
        line_no = pos.get("new_line") or pos.get("old_line")
        summaries.append(
            {
                "discussion_id": disc.get("id"),
                "resolvable": resolvable,
                "resolved": resolved,
                "file": file_path,
                "line": line_no,
                "position": pos if pos else None,
                "notes": [
                    {
                        "note_id": n.get("id"),
                        "author": (n.get("author") or {}).get("username")
                        or (n.get("author") or {}).get("name"),
                        "created_at": n.get("created_at"),
                        "resolved": n.get("resolved"),
                        "body": n.get("body", ""),
                    }
                    for n in notes
                ],
            }
        )
    return summaries


def build_inline_discussion_payload(
    body: str,
    *,
    diff_refs: dict[str, Any],
    new_path: str,
    new_line: int | None = None,
    old_path: str | None = None,
    old_line: int | None = None,
) -> dict[str, Any]:
    position: dict[str, Any] = {
        "position_type": "text",
        "base_sha": diff_refs["base_sha"],
        "start_sha": diff_refs["start_sha"],
        "head_sha": diff_refs["head_sha"],
        "new_path": new_path,
        "old_path": old_path or new_path,
    }
    if new_line is not None:
        position["new_line"] = new_line
    if old_line is not None:
        position["old_line"] = old_line
    return {"body": body, "position": position}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="Optional path to .env file")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_list = sub.add_parser("list", help="List MR discussions and diff_refs")
    p_list.add_argument("--mr", required=True, help="GitLab MR URL or IID")
    p_list.add_argument("--project", help="GitLab project path (group/project)")
    p_list.add_argument("--repo-dir", type=Path, default=Path.cwd(), help="Local repo directory")
    p_list.add_argument("--unresolved-only", action="store_true", help="Filter to unresolved threads")
    p_list.add_argument("--json", action="store_true", help="Emit JSON output")

    p_reply = sub.add_parser("reply", help="Reply to an existing MR discussion thread")
    p_reply.add_argument("--mr", required=True, help="GitLab MR URL or IID")
    p_reply.add_argument("--project", help="GitLab project path (group/project)")
    p_reply.add_argument("--repo-dir", type=Path, default=Path.cwd(), help="Local repo directory")
    p_reply.add_argument("--discussion-id", required=True, help="Target discussion ID")
    p_reply.add_argument("--body", required=True, help="Reply markdown body")
    p_reply.add_argument("--resolve", action="store_true", help="Also mark discussion resolved")
    p_reply.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm explicit human approval (ask_user) before mutating GitLab",
    )

    p_resolve = sub.add_parser("resolve", help="Resolve or unresolve a discussion thread")
    p_resolve.add_argument("--mr", required=True, help="GitLab MR URL or IID")
    p_resolve.add_argument("--project", help="GitLab project path (group/project)")
    p_resolve.add_argument("--repo-dir", type=Path, default=Path.cwd(), help="Local repo directory")
    p_resolve.add_argument("--discussion-id", required=True, help="Target discussion ID")
    p_resolve.add_argument("--unresolve", action="store_true", help="Unresolve instead of resolve")
    p_resolve.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm explicit human approval (ask_user) before mutating GitLab",
    )

    p_comment = sub.add_parser("comment", help="Create a new inline diff discussion or MR note")
    p_comment.add_argument("--mr", required=True, help="GitLab MR URL or IID")
    p_comment.add_argument("--project", help="GitLab project path (group/project)")
    p_comment.add_argument("--repo-dir", type=Path, default=Path.cwd(), help="Local repo directory")
    p_comment.add_argument("--body", required=True, help="Comment markdown body")
    p_comment.add_argument("--new-path", help="File path in the MR for an inline diff comment")
    p_comment.add_argument("--new-line", type=int, help="New line number for an inline diff comment")
    p_comment.add_argument("--old-path", help="Old file path (defaults to --new-path)")
    p_comment.add_argument("--old-line", type=int, help="Old line number for deleted-line comment")
    p_comment.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm explicit human approval (ask_user) before mutating GitLab",
    )

    return parser.parse_args(argv)


def require_confirmation(args: argparse.Namespace) -> None:
    if not getattr(args, "confirm", False):
        raise PermissionError(
            f"Refusing to run mutating subcommand {args.subcommand!r} without --confirm "
            "(obtain explicit user approval via ask_user first)."
        )


def main(argv: list[str] | None = None, *, client: GitLabClient | None = None) -> int:
    args = parse_args(argv)
    if args.subcommand in ("reply", "resolve", "comment"):
        try:
            require_confirmation(args)
        except PermissionError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    default_host, token = resolve_credentials(args.env_file)
    try:
        host, project, iid = resolve_mr_target(
            args.mr,
            project=args.project,
            repo_dir=args.repo_dir,
            default_host=default_host,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if client is None:
        if not token:
            print(
                "ERROR: Missing GITLAB_TOKEN / GITLAB_PAT in environment or .env file.",
                file=sys.stderr,
            )
            return 1
        client = GitLabClient(host, token)

    encoded_project = urllib.parse.quote(project, safe="")
    mr_base = f"/projects/{encoded_project}/merge_requests/{iid}"

    if args.subcommand == "list":
        mr_info = client.request("GET", mr_base)
        discussions = client.request("GET", f"{mr_base}/discussions", query={"per_page": 100})
        items = summarize_discussions(discussions, unresolved_only=args.unresolved_only)
        payload = {
            "project": project,
            "iid": iid,
            "title": mr_info.get("title"),
            "state": mr_info.get("state"),
            "web_url": mr_info.get("web_url"),
            "diff_refs": mr_info.get("diff_refs"),
            "discussion_count": len(items),
            "discussions": items,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"MR !{iid}: {mr_info.get('title')} ({len(items)} discussion thread(s))")
            for item in items:
                loc = f"{item['file']}:{item['line']}" if item["file"] else "general"
                status = "resolved" if item["resolved"] else "unresolved"
                first_note = item["notes"][0]
                print(
                    f"- [{item['discussion_id']}] ({status}, {loc}) @{first_note['author']}: "
                    f"{first_note['body'].splitlines()[0] if first_note['body'] else ''}"
                )
        return 0

    if args.subcommand == "reply":
        note = client.request(
            "POST",
            f"{mr_base}/discussions/{args.discussion_id}/notes",
            payload={"body": args.body},
        )
        if args.resolve:
            client.request(
                "PUT",
                f"{mr_base}/discussions/{args.discussion_id}",
                payload={"resolved": True},
            )
        print(json.dumps({"ok": True, "discussion_id": args.discussion_id, "note_id": note.get("id")}))
        return 0

    if args.subcommand == "resolve":
        resolved_val = not args.unresolve
        client.request(
            "PUT",
            f"{mr_base}/discussions/{args.discussion_id}",
            payload={"resolved": resolved_val},
        )
        print(json.dumps({"ok": True, "discussion_id": args.discussion_id, "resolved": resolved_val}))
        return 0

    if args.subcommand == "comment":
        if args.new_path:
            mr_info = client.request("GET", mr_base)
            diff_refs = mr_info.get("diff_refs") or {}
            if not all(diff_refs.get(k) for k in ("base_sha", "start_sha", "head_sha")):
                print("ERROR: MR diff_refs are missing base_sha/start_sha/head_sha", file=sys.stderr)
                return 1
            payload = build_inline_discussion_payload(
                args.body,
                diff_refs=diff_refs,
                new_path=args.new_path,
                new_line=args.new_line,
                old_path=args.old_path,
                old_line=args.old_line,
            )
            created = client.request("POST", f"{mr_base}/discussions", payload=payload)
            print(json.dumps({"ok": True, "discussion_id": created.get("id"), "inline": True}))
        else:
            created = client.request("POST", f"{mr_base}/notes", payload={"body": args.body})
            print(json.dumps({"ok": True, "note_id": created.get("id"), "inline": False}))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
