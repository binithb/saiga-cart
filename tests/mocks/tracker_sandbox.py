#!/usr/bin/env python3
"""Local Mock Sandbox for Jira Cloud, Azure DevOps, GitLab, and Sibling Git Repositories.

Provides:
1. An ephemeral multi-threaded HTTP server mocking:
   - Jira REST API v3 (`/rest/api/3/myself`, `/rest/api/3/issue`, `/rest/api/3/search`, remote links)
   - Azure DevOps REST API (`/<org>/_apis/projects`, `/<org>/<project>/_apis/wit/workitems`)
   - GitLab REST API v4 (`/api/v4/user`)
2. Local bare Git sibling repositories initialized with realistic code/manifests so
   `git ls-remote`, `scripts/clone_siblings.py`, and the `add-sibling` skill work 100% offline.
3. A cross-platform `az` CLI shim in a temporary `bin/` folder supporting `az account show`
   and `az boards work-item create` / `show`.
4. An interactive `--demo` CLI mode so developers can test `python3 bootstrap.py` hands-on
   as a new user against live local mock endpoints.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class SandboxState:
    """Thread-safe in-memory state shared by the mock HTTP server."""

    def __init__(
        self,
        *,
        jira_email: str = "dev@acme.example",
        jira_token: str = "mock-jira-token-123",
        ado_pat: str = "mock-ado-pat-456",
        gitlab_token: str = "mock-gitlab-token-789",
    ) -> None:
        self.lock = threading.Lock()
        self.jira_email = jira_email
        self.jira_token = jira_token
        self.ado_pat = ado_pat
        self.gitlab_token = gitlab_token

        self.jira_seq = 100
        self.jira_issues: dict[str, dict[str, Any]] = {}
        self.jira_remote_links: dict[str, list[dict[str, Any]]] = {}

        self.ado_seq = 41
        self.ado_work_items: dict[int, dict[str, Any]] = {}
        self.requests_log: list[dict[str, str]] = []

    def create_jira_issue(
        self,
        project_key: str,
        summary: str,
        description: Any = "",
        issue_type: str = "Story",
        status: str = "In progress",
        base_url: str = "",
    ) -> dict[str, Any]:
        with self.lock:
            self.jira_seq += 1
            key = f"{project_key}-{self.jira_seq}"
            issue_id = str(10000 + self.jira_seq)
            issue = {
                "id": issue_id,
                "key": key,
                "self": f"{base_url.rstrip('/')}/rest/api/3/issue/{issue_id}",
                "fields": {
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type},
                    "status": {"name": status},
                },
            }
            self.jira_issues[key] = issue
            return issue

    def add_jira_remote_link(self, key: str, url: str, title: str) -> dict[str, Any]:
        with self.lock:
            links = self.jira_remote_links.setdefault(key, [])
            entry = {"id": len(links) + 1, "object": {"url": url, "title": title}}
            links.append(entry)
            return entry

    def create_ado_work_item(
        self,
        org: str,
        project: str,
        title: str,
        work_item_type: str = "User Story",
        description: str = "",
        state: str = "Active",
        base_url: str = "",
    ) -> dict[str, Any]:
        with self.lock:
            self.ado_seq += 1
            wi_id = self.ado_seq
            item = {
                "id": wi_id,
                "rev": 1,
                "fields": {
                    "System.Id": wi_id,
                    "System.TeamProject": project,
                    "System.WorkItemType": work_item_type,
                    "System.State": state,
                    "System.Title": title,
                    "System.Description": description,
                },
                "url": f"{base_url.rstrip('/')}/{org}/{project}/_workitems/edit/{wi_id}",
            }
            self.ado_work_items[wi_id] = item
            return item


def _make_handler(state: SandboxState):
    class MockTrackerHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def _send_json(self, status_code: int, payload: Any) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> Any:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}

        def _check_jira_auth(self) -> bool:
            auth = self.headers.get("Authorization", "")
            expected_basic = base64.b64encode(
                f"{state.jira_email}:{state.jira_token}".encode("utf-8")
            ).decode("ascii")
            if auth == f"Basic {expected_basic}" or auth == f"Bearer {state.jira_token}":
                return True
            return False

        def _check_ado_auth(self) -> bool:
            auth = self.headers.get("Authorization", "")
            expected_basic = base64.b64encode(f":{state.ado_pat}".encode("utf-8")).decode("ascii")
            return auth == f"Basic {expected_basic}" or auth == f"Bearer {state.ado_pat}"

        def _base_url(self) -> str:
            host = self.headers.get("Host", f"127.0.0.1:{self.server.server_port}")
            return f"http://{host}"

        def do_GET(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)

            with state.lock:
                state.requests_log.append({"method": "GET", "path": path})

            # 1. Jira auth check: GET /rest/api/3/myself
            if path.endswith("/rest/api/3/myself"):
                if not self._check_jira_auth():
                    self._send_json(401, {"message": "Unauthorized Jira credentials"})
                    return
                self._send_json(
                    200,
                    {
                        "accountId": "mock-jira-account-01",
                        "emailAddress": state.jira_email,
                        "displayName": "Mock Jira Developer",
                        "active": True,
                    },
                )
                return

            # 2. Jira bulk search: GET /rest/api/3/search?jql=...
            if path.endswith("/rest/api/3/search"):
                if not self._check_jira_auth():
                    self._send_json(401, {"message": "Unauthorized Jira credentials"})
                    return
                jql = (query.get("jql") or [""])[0]
                matched = []
                with state.lock:
                    for key, issue in state.jira_issues.items():
                        if not jql or key in jql:
                            matched.append(issue)
                self._send_json(200, {"total": len(matched), "issues": matched})
                return

            # 3. GitLab auth check: GET /api/v4/user
            if path.endswith("/api/v4/user"):
                tok = self.headers.get("PRIVATE-TOKEN", "")
                if tok != state.gitlab_token:
                    self._send_json(401, {"message": "401 Unauthorized"})
                    return
                self._send_json(200, {"id": 1, "username": "mock-gitlab-dev"})
                return

            # 4. Azure DevOps auth / project check: GET /<org>/_apis/projects
            if "/_apis/projects" in path:
                if not self._check_ado_auth():
                    self._send_json(401, {"message": "Unauthorized Azure DevOps PAT"})
                    return
                segs = [s for s in path.split("/") if s]
                org = segs[0] if segs and segs[0] != "_apis" else "acme-org"
                self._send_json(
                    200,
                    {
                        "count": 1,
                        "value": [{"id": "proj-1", "name": "CorePlatform", "organization": org}],
                    },
                )
                return

            # 5. Azure DevOps work item fetch: GET /<org>/<project>/_apis/wit/workitems/<id>
            if "/_apis/wit/workitems/" in path:
                if not self._check_ado_auth():
                    self._send_json(401, {"message": "Unauthorized Azure DevOps PAT"})
                    return
                try:
                    wi_id = int(path.rstrip("/").split("/")[-1])
                except ValueError:
                    self._send_json(400, {"message": "Invalid work item ID"})
                    return
                with state.lock:
                    item = state.ado_work_items.get(wi_id)
                if not item:
                    self._send_json(404, {"message": "Work item not found"})
                    return
                self._send_json(200, item)
                return

            self._send_json(404, {"error": f"Unhandled GET path: {path}"})

        def do_POST(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            payload = self._read_json_body()

            with state.lock:
                state.requests_log.append({"method": "POST", "path": path})

            # 1. Jira create issue: POST /rest/api/3/issue
            if path.endswith("/rest/api/3/issue"):
                if not self._check_jira_auth():
                    self._send_json(401, {"message": "Unauthorized Jira credentials"})
                    return
                fields = payload.get("fields") or {}
                project_key = (fields.get("project") or {}).get("key") or "PROJ"
                summary = fields.get("summary") or "Untitled Story"
                description = fields.get("description") or ""
                issue_type = (fields.get("issuetype") or {}).get("name") or "Story"
                status = fields.get("status") or "In progress"
                issue = state.create_jira_issue(
                    project_key=project_key,
                    summary=summary,
                    description=description,
                    issue_type=issue_type,
                    status=status if isinstance(status, str) else "In progress",
                    base_url=self._base_url(),
                )
                self._send_json(201, issue)
                return

            # 2. Jira remote link: POST /rest/api/3/issue/<KEY>/remotelink
            if "/rest/api/3/issue/" in path and path.endswith("/remotelink"):
                if not self._check_jira_auth():
                    self._send_json(401, {"message": "Unauthorized Jira credentials"})
                    return
                parts = [p for p in path.split("/") if p]
                issue_key = parts[-2]
                obj = payload.get("object") or {}
                link = state.add_jira_remote_link(
                    issue_key,
                    url=obj.get("url", ""),
                    title=obj.get("title", "Repository Story"),
                )
                self._send_json(201, link)
                return

            # 3. ADO create work item: POST /<org>/<project>/_apis/wit/workitems/$<type>
            if "/_apis/wit/workitems" in path:
                if not self._check_ado_auth():
                    self._send_json(401, {"message": "Unauthorized Azure DevOps PAT"})
                    return
                segs = [urllib.parse.unquote(s) for s in path.split("/") if s]
                org = segs[0] if len(segs) >= 2 else "acme-org"
                project = segs[1] if len(segs) >= 3 and segs[1] != "_apis" else "CorePlatform"
                wi_type = "User Story"
                if segs[-1].startswith("$"):
                    wi_type = segs[-1][1:]

                title = "Untitled Work Item"
                description = ""
                if isinstance(payload, list):
                    for op in payload:
                        if op.get("path") == "/fields/System.Title":
                            title = str(op.get("value", title))
                        elif op.get("path") == "/fields/System.Description":
                            description = str(op.get("value", ""))
                elif isinstance(payload, dict):
                    title = str(payload.get("title", title))
                    description = str(payload.get("description", ""))
                    wi_type = str(payload.get("type", wi_type))

                item = state.create_ado_work_item(
                    org=org,
                    project=project,
                    title=title,
                    work_item_type=wi_type,
                    description=description,
                    base_url=self._base_url(),
                )
                self._send_json(200, item)
                return

            self._send_json(404, {"error": f"Unhandled POST path: {path}"})

    return MockTrackerHandler


class TrackerSandbox:
    """Context manager spinning up the mock HTTP server, sample bare Git repos, and `az` CLI shim."""

    def __init__(self, base_temp_dir: Path | None = None) -> None:
        self._own_temp = base_temp_dir is None
        self._tmp_obj = tempfile.TemporaryDirectory() if self._own_temp else None
        self.root = (base_temp_dir or Path(self._tmp_obj.name)).resolve()
        self.repos_dir = self.root / "remote-repos"
        self.bin_dir = self.root / "mock-bin"
        self.state = SandboxState()
        self.server: ThreadingHTTPServer | None = None
        self.server_thread: threading.Thread | None = None
        self.base_url: str = ""
        self.sibling_repos: dict[str, Path] = {}

    def start(self) -> "TrackerSandbox":
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)

        handler_cls = _make_handler(self.state)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        port = self.server.server_port
        self.base_url = f"http://127.0.0.1:{port}"

        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        # Initialize realistic bare sibling Git repositories
        self.sibling_repos["payments-api"] = self._create_sample_bare_repo(
            name="payments-api",
            stack_files={
                "README.md": (
                    "# payments-api\n\n"
                    "Payment authorization, capture, and settlement REST service.\n\n"
                    "## Verification\n"
                    "Run tests with `python3 -m unittest discover -s tests`.\n"
                ),
                "pyproject.toml": (
                    '[project]\nname = "payments-api"\nversion = "0.2.0"\n'
                    'description = "Payment Ledger & Settlement Service"\n'
                ),
                "openapi.yaml": (
                    "openapi: 3.0.3\ninfo:\n  title: Payments Ledger API\n  version: 0.2.0\n"
                    "paths:\n  /v1/settlements:\n    post:\n      summary: Create settlement batch\n"
                ),
                "tests/test_smoke.py": (
                    "import unittest\n\nclass TestPayments(unittest.TestCase):\n"
                    "    def test_ok(self):\n        self.assertTrue(True)\n"
                ),
            },
        )
        self.sibling_repos["inventory-service"] = self._create_sample_bare_repo(
            name="inventory-service",
            stack_files={
                "README.md": (
                    "# inventory-service\n\n"
                    "Warehouse stock reservation and SKU allocation microservice.\n\n"
                    "## Verification\n"
                    "Run tests with `python3 -m unittest discover -s tests`.\n"
                ),
                "pyproject.toml": (
                    '[project]\nname = "inventory-service"\nversion = "1.1.0"\n'
                    'description = "Warehouse Stock Reservation Service"\n'
                ),
                "openapi.yaml": (
                    "openapi: 3.0.3\ninfo:\n  title: Inventory Reservation API\n  version: 1.1.0\n"
                    "paths:\n  /v1/reservations:\n    post:\n      summary: Reserve SKU stock\n"
                ),
                "tests/test_smoke.py": (
                    "import unittest\n\nclass TestInventory(unittest.TestCase):\n"
                    "    def test_ok(self):\n        self.assertTrue(True)\n"
                ),
            },
        )

        self._install_az_cli_shim()
        return self

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self._tmp_obj is not None:
            self._tmp_obj.cleanup()
            self._tmp_obj = None

    def __enter__(self) -> "TrackerSandbox":
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.stop()

    @property
    def jira_base_url(self) -> str:
        return f"{self.base_url}/jira"

    @property
    def ado_org_url(self) -> str:
        return f"{self.base_url}/acme-org/CorePlatform"

    @property
    def gitlab_base_url(self) -> str:
        return f"{self.base_url}/gitlab"

    def env_with_mocks(self, base_env: dict[str, str] | None = None) -> dict[str, str]:
        """Return an environment dictionary with the mock `bin/` directory prepended to PATH."""
        env = dict(os.environ if base_env is None else base_env)
        env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env["MOCK_SANDBOX_BASE_URL"] = self.base_url
        env["MOCK_ADO_PAT"] = self.state.ado_pat
        for key in (
            "JIRA_API_TOKEN",
            "JIRA_USER_EMAIL",
            "JIRA_BASE_URL",
            "AZURE_DEVOPS_EXT_PAT",
            "ADO_PAT",
            "AZURE_DEVOPS_ORG_URL",
            "GITLAB_TOKEN",
            "GITLAB_PAT",
            "GITLAB_BASE_URL",
            "GITHUB_TOKEN",
            "GH_TOKEN",
        ):
            env.pop(key, None)
        return env

    def _create_sample_bare_repo(self, name: str, stack_files: dict[str, str]) -> Path:
        bare_path = self.repos_dir / f"{name}.git"
        work_path = self.repos_dir / f"{name}-seed"
        subprocess.run(["git", "init", "--bare", str(bare_path)], check=True, capture_output=True)
        subprocess.run(["git", "init", str(work_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(work_path), "config", "user.name", "Sandbox Bot"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work_path), "config", "user.email", "sandbox@acme.example"],
            check=True,
            capture_output=True,
        )
        for rel_path, content in stack_files.items():
            file_path = work_path / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        subprocess.run(["git", "-C", str(work_path), "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(work_path), "commit", "-m", f"Initial seed for {name}"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work_path), "branch", "-M", "main"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work_path), "remote", "add", "origin", str(bare_path)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work_path), "push", "-u", "origin", "main"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "--git-dir", str(bare_path), "symbolic-ref", "HEAD", "refs/heads/main"],
            check=True,
            capture_output=True,
        )
        shutil.rmtree(work_path, ignore_errors=True)
        return bare_path

    def _install_az_cli_shim(self) -> None:
        """Install a cross-platform `az` executable shim backed by the mock HTTP server."""
        py_script = self.bin_dir / "az_shim.py"
        py_script.write_text(
            '''#!/usr/bin/env python3
"""Mock Azure CLI (`az`) shim for offline E2E testing."""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request


def main() -> int:
    args = sys.argv[1:]
    base_url = os.environ.get("MOCK_SANDBOX_BASE_URL", "")
    pat = (
        os.environ.get("AZURE_DEVOPS_EXT_PAT")
        or os.environ.get("ADO_PAT")
        or os.environ.get("MOCK_ADO_PAT")
        or "mock-ado-pat-456"
    )

    if args[:2] == ["account", "show"]:
        if os.environ.get("MOCK_AZ_LOGGED_IN") == "1":
            print(json.dumps({"id": "mock-sub-01", "name": "Acme Mock Azure Subscription", "state": "Enabled"}))
            return 0
        print("ERROR: Please run 'az login' to setup account.", file=sys.stderr)
        return 1

    if args[:3] == ["boards", "work-item", "create"]:
        title = "Untitled"
        wi_type = "User Story"
        desc = ""
        project = "CorePlatform"
        org = "acme-org"
        i = 3
        while i < len(args):
            flag = args[i]
            val = args[i + 1] if i + 1 < len(args) else ""
            if flag == "--title":
                title = val
                i += 2
            elif flag == "--type":
                wi_type = val
                i += 2
            elif flag in ("--description", "-d"):
                desc = val
                i += 2
            elif flag in ("--project", "-p"):
                project = val
                i += 2
            elif flag in ("--organization", "--org"):
                # Extract first path segment after host (e.g. http://127.0.0.1:port/acme-org or .../acme-org/CorePlatform -> acme-org)
                if "://" in val:
                    path_segs = [s for s in urllib.parse.urlsplit(val).path.split("/") if s]
                    org = path_segs[0] if path_segs else "acme-org"
                else:
                    org = val.strip("/").split("/")[0] or "acme-org"
                i += 2
            else:
                i += 1

        b64 = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        req = urllib.request.Request(
            f"{base_url}/{org}/{project}/_apis/wit/workitems/${urllib.parse.quote(wi_type)}?api-version=7.0",
            data=json.dumps({"title": title, "type": wi_type, "description": desc}).encode("utf-8"),
            headers={"Authorization": f"Basic {b64}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(resp.read().decode("utf-8"))
        return 0

    print(json.dumps({"status": "ok", "args": args}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
            encoding="utf-8",
        )
        py_script.chmod(py_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        az_unix = self.bin_dir / "az"
        az_unix.write_text(
            f'#!/usr/bin/env sh\nexec "{sys.executable}" "{py_script}" "$@"\n',
            encoding="utf-8",
        )
        az_unix.chmod(az_unix.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        if os.name == "nt":
            az_cmd = self.bin_dir / "az.cmd"
            az_cmd.write_text(
                f'@echo off\r\n"{sys.executable}" "{py_script}" %*\r\n',
                encoding="utf-8",
            )

        # Install deterministic shims for `glab` and `gh` so host CLI login state never leaks into tests
        for cli_name, env_flag in (("glab", "MOCK_GLAB_LOGGED_IN"), ("gh", "MOCK_GH_LOGGED_IN")):
            shim_py = self.bin_dir / f"{cli_name}_shim.py"
            shim_py.write_text(
                f'#!/usr/bin/env python3\nimport os, sys\n'
                f'if os.environ.get("{env_flag}") == "1":\n    raise SystemExit(0)\n'
                f'print("Not logged in", file=sys.stderr)\nraise SystemExit(1)\n',
                encoding="utf-8",
            )
            shim_py.chmod(shim_py.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            cli_unix = self.bin_dir / cli_name
            cli_unix.write_text(
                f'#!/usr/bin/env sh\nexec "{sys.executable}" "{shim_py}" "$@"\n',
                encoding="utf-8",
            )
            cli_unix.chmod(cli_unix.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if os.name == "nt":
                cli_cmd = self.bin_dir / f"{cli_name}.cmd"
                cli_cmd.write_text(
                    f'@echo off\r\n"{sys.executable}" "{shim_py}" %*\r\n',
                    encoding="utf-8",
                )


def create_jira_ticket_via_api(
    base_url: str,
    email: str,
    token: str,
    project_key: str,
    summary: str,
    description: str,
    repo_story_permalink: str | None = None,
) -> dict[str, Any]:
    """Helper used in tests/demos to execute Step 1 & Step 3 of `jira-story-onboard` against the Jira REST API."""
    b64 = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {b64}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    create_req = urllib.request.Request(
        f"{base_url.rstrip('/')}/rest/api/3/issue",
        data=json.dumps(
            {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": "Story"},
                }
            }
        ).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(create_req, timeout=5) as resp:
        created = json.loads(resp.read().decode("utf-8"))

    if repo_story_permalink:
        link_req = urllib.request.Request(
            f"{base_url.rstrip('/')}/rest/api/3/issue/{created['key']}/remotelink",
            data=json.dumps(
                {
                    "object": {
                        "url": repo_story_permalink,
                        "title": f"Git Story Specification ({created['key']})",
                    }
                }
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(link_req, timeout=5) as _:
            pass

    return created


def run_interactive_demo(mode: str) -> int:
    """Spin up the local mock environment and print ready-to-paste values for hands-on testing."""
    repo_root = Path(__file__).resolve().parents[2]
    with TrackerSandbox() as sandbox:
        demo_ws_parent = sandbox.root / "demo-workspaces"
        demo_ws_parent.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 75)
        print("  🧪 saiga-cart Local Mock Onboarding Sandbox (Interactive Demo Mode)")
        print("=" * 75)
        print(f"  Mock HTTP Server running at : {sandbox.base_url}")
        print(f"  Sandbox workspace parent    : {demo_ws_parent}")
        print(f"  Mock `az` CLI shim folder   : {sandbox.bin_dir}")
        print("-" * 75)
        print("  📦 Local Bare Sibling Git Repositories (ready for `git ls-remote` & clone):")
        for name, path in sandbox.sibling_repos.items():
            print(f"    • {name:<18} : {path}")

        if mode in ("jira", "all"):
            print("\n  🟦 JIRA + SAFe / Scrum Interactive Walkthrough Credentials:")
            print(f"    • Jira Base URL             : {sandbox.jira_base_url}")
            print("    • Jira Project Key          : SAIGA")
            print(f"    • Jira Account Email        : {sandbox.state.jira_email}")
            print(f"    • Jira API Token            : {sandbox.state.jira_token}")
            print(f"    • GitLab PAT (if GitLab VCS): {sandbox.state.gitlab_token}")

        if mode in ("ado", "all"):
            print("\n  🟧 AZURE DEVOPS Interactive Walkthrough Credentials:")
            print(f"    • ADO Project/Repo URL      : {sandbox.ado_org_url}")
            print("    • ADO Project Key           : CorePlatform")
            print(f"    • ADO PAT                   : {sandbox.state.ado_pat}")

        print("\n  🚀 Try these flows in another terminal (or press Enter below to launch wizard):")
        print("    1) Full Interactive Wizard (no preset):")
        print(f"       PATH=\"{sandbox.bin_dir}:$PATH\" python3 {repo_root / 'bootstrap.py'} --output {demo_ws_parent / 'my-interactive-ws'}")
        print("\n    2) Preset First (no siblings at start) -> Add Sibling Skill later:")
        preset_name = "ado-scrum" if mode == "ado" else "jira-safe"
        ws_path = demo_ws_parent / f"my-{preset_name}-ws"
        sib_path = sandbox.sibling_repos["inventory-service" if mode == "ado" else "payments-api"]
        print(f"       python3 {repo_root / 'bootstrap.py'} --non-interactive --preset {preset_name} --output {ws_path}")
        print(f"       python3 {ws_path / 'bootstrap.py'} --add-sibling --sibling-url {sib_path} --clone")
        print("=" * 75)

        if sys.stdin.isatty():
            try:
                ans = input(
                    "\nLaunch interactive `bootstrap.py` wizard right now in this terminal? [Y/n]: "
                ).strip().lower()
                if ans in ("", "y", "yes"):
                    target = demo_ws_parent / f"interactive-{mode}-ws"
                    env = sandbox.env_with_mocks()
                    env["GITLAB_BASE_URL"] = sandbox.gitlab_base_url
                    subprocess.run(
                        [sys.executable, str(repo_root / "bootstrap.py"), "--output", str(target)],
                        env=env,
                        check=False,
                    )
                    print(f"\n✔ Interactive session finished. Inspect generated workspace at: {target}")
                    input("Press Enter to shut down the mock sandbox (or Ctrl+C)...")
                else:
                    print("\nMock server is staying alive for manual terminal testing. Press Ctrl+C to stop.")
                    while True:
                        time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down mock sandbox.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local mock tracker & Git sandbox for saiga-cart.")
    parser.add_argument(
        "--demo",
        choices=["jira", "ado", "all"],
        default="all",
        help="Start interactive demo server for Jira, Azure DevOps, or both",
    )
    args = parser.parse_args()
    return run_interactive_demo(args.demo)


if __name__ == "__main__":
    raise SystemExit(main())
