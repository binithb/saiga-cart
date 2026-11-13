#!/usr/bin/env python3
"""Unit tests for gitlab_mr_discussions.py."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitlab_mr_discussions as gmd  # noqa: E402


class FakeGitLabClient(gmd.GitLabClient):
    def __init__(self) -> None:
        super().__init__("https://gitlab.example.com", "test-token")
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        self.calls.append((method, path, payload))
        if method == "GET" and path.endswith("/merge_requests/42"):
            return {
                "iid": 42,
                "title": "Add telemetry validation",
                "state": "opened",
                "web_url": "https://gitlab.example.com/group/sub/repo/-/merge_requests/42",
                "diff_refs": {
                    "base_sha": "aaa111",
                    "start_sha": "bbb222",
                    "head_sha": "ccc333",
                },
            }
        if method == "GET" and path.endswith("/merge_requests/42/discussions"):
            return [
                {
                    "id": "disc-1",
                    "notes": [
                        {
                            "id": 101,
                            "system": False,
                            "resolvable": True,
                            "resolved": False,
                            "author": {"username": "alice"},
                            "created_at": "2026-04-19T10:00:00Z",
                            "body": "Please guard against empty input.",
                            "position": {"new_path": "src/handler.py", "new_line": 27},
                        }
                    ],
                },
                {
                    "id": "disc-2",
                    "notes": [
                        {
                            "id": 102,
                            "system": False,
                            "resolvable": True,
                            "resolved": True,
                            "author": {"username": "bob"},
                            "created_at": "2026-04-19T09:00:00Z",
                            "body": "Nit: rename variable.",
                            "position": {"new_path": "src/handler.py", "new_line": 10},
                        }
                    ],
                },
            ]
        if method == "POST" and "/notes" in path:
            return {"id": 999}
        if method == "POST" and path.endswith("/discussions"):
            return {"id": "disc-new"}
        return {"ok": True}


class GitLabMrDiscussionsTests(unittest.TestCase):
    def test_resolve_mr_target_from_full_url(self) -> None:
        host, project, iid = gmd.resolve_mr_target(
            "https://gitlab.example.com/org/team/service/-/merge_requests/42/diffs"
        )
        self.assertEqual(host, "https://gitlab.example.com")
        self.assertEqual(project, "org/team/service")
        self.assertEqual(iid, 42)

    def test_list_unresolved_filters_resolved_threads(self) -> None:
        client = FakeGitLabClient()
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gmd.main(
                [
                    "list",
                    "--mr",
                    "https://gitlab.example.com/group/sub/repo/-/merge_requests/42",
                    "--unresolved-only",
                    "--json",
                ],
                client=client,
            )
        self.assertEqual(rc, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["discussion_count"], 1)
        self.assertEqual(data["discussions"][0]["discussion_id"], "disc-1")
        self.assertEqual(data["discussions"][0]["file"], "src/handler.py")
        self.assertEqual(data["discussions"][0]["line"], 27)

    def test_mutating_commands_require_confirm_flag(self) -> None:
        client = FakeGitLabClient()
        err = io.StringIO()
        with redirect_stderr(err):
            rc = gmd.main(
                [
                    "reply",
                    "--mr",
                    "https://gitlab.example.com/group/sub/repo/-/merge_requests/42",
                    "--discussion-id",
                    "disc-1",
                    "--body",
                    "Fixed in latest commit.",
                ],
                client=client,
            )
        self.assertEqual(rc, 2)
        self.assertIn("--confirm", err.getvalue())
        self.assertEqual(client.calls, [])

    def test_reply_and_resolve_with_confirm_succeeds(self) -> None:
        client = FakeGitLabClient()
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gmd.main(
                [
                    "reply",
                    "--mr",
                    "https://gitlab.example.com/group/sub/repo/-/merge_requests/42",
                    "--discussion-id",
                    "disc-1",
                    "--body",
                    "Fixed in latest commit.",
                    "--resolve",
                    "--confirm",
                ],
                client=client,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0][0], "POST")
        self.assertEqual(client.calls[1][0], "PUT")
        self.assertEqual(client.calls[1][2], {"resolved": True})

    def test_inline_comment_uses_diff_refs(self) -> None:
        client = FakeGitLabClient()
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gmd.main(
                [
                    "comment",
                    "--mr",
                    "https://gitlab.example.com/group/sub/repo/-/merge_requests/42",
                    "--body",
                    "Consider validating the schema version here.",
                    "--new-path",
                    "src/handler.py",
                    "--new-line",
                    "45",
                    "--confirm",
                ],
                client=client,
            )
        self.assertEqual(rc, 0)
        post_call = client.calls[-1]
        self.assertEqual(post_call[0], "POST")
        assert post_call[2] is not None
        self.assertEqual(post_call[2]["position"]["base_sha"], "aaa111")
        self.assertEqual(post_call[2]["position"]["head_sha"], "ccc333")
        self.assertEqual(post_call[2]["position"]["new_path"], "src/handler.py")
        self.assertEqual(post_call[2]["position"]["new_line"], 45)

    def test_load_env_file_parses_export_and_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_p = Path(tmp) / ".env"
            env_p.write_text(
                "# comment\nexport GITLAB_PAT='glpat-secret'\nGITLAB_URL=\"https://git.internal.example\"\n",
                encoding="utf-8",
            )
            host, token = gmd.resolve_credentials(env_p)
            self.assertTrue(token)
            self.assertTrue(host.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
