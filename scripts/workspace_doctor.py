#!/usr/bin/env python3
"""Workspace Doctor: Diagnostic & Environment Verification Utility."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def check(status: bool, message: str, is_warning: bool = False):
    if status:
        print(f"  {GREEN}✔{RESET} {message}")
        return True
    elif is_warning:
        print(f"  {YELLOW}⚠{RESET} {message}")
        return True
    else:
        print(f"  {RED}✖{RESET} {message}")
        return False


def load_env_file(root: Path) -> dict[str, str]:
    """Load key-value pairs from .env.local or .env into os.environ if not already set."""
    loaded = {}
    for filename in (".env.local", ".env"):
        env_path = root / filename
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key:
                        if key not in os.environ:
                            os.environ[key] = val
                        loaded[key] = val
            except Exception:
                pass
    return loaded


def get_workspace_settings(root: Path) -> dict[str, str]:
    """Extract tracker type and VCS platform from workspace.yaml."""
    settings = {"tracker_type": "", "vcs_platform": ""}
    ws_yaml = root / "workspace.yaml"
    if ws_yaml.is_file():
        in_tracker = False
        in_vcs = False
        for line in ws_yaml.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("tracker:"):
                in_tracker = True
                in_vcs = False
            elif stripped.startswith("vcs:"):
                in_vcs = True
                in_tracker = False
            elif line and not line.startswith(" ") and not line.startswith("\t"):
                in_tracker = False
                in_vcs = False

            if in_tracker and stripped.startswith("type:"):
                settings["tracker_type"] = stripped.split(":", 1)[1].strip().strip("'\"")
            elif in_vcs and stripped.startswith("platform:"):
                settings["vcs_platform"] = stripped.split(":", 1)[1].strip().strip("'\"")
    return settings


def run_diagnostics(root: Path) -> int:
    load_env_file(root)
    print(f"\n{BOLD}{CYAN}=== saiga-cart Diagnostics ==={RESET}\n")
    errors = 0

    # 1. Python Environment
    print(f"{BOLD}1. Runtime & Environment:{RESET}")
    py_ok = sys.version_info >= (3, 8)
    if not check(py_ok, f"Python version {sys.version.split()[0]} (>= 3.8 required)"):
        errors += 1

    # 2. CLI Tools
    print(f"\n{BOLD}2. Developer CLI Tools:{RESET}")
    for tool in ("git", "gh", "glab", "code"):
        present = shutil.which(tool) is not None
        check(present, f"CLI tool: {tool}", is_warning=(tool != "git"))

    # 3. Workspace Core Files
    print(f"\n{BOLD}3. Workspace Directives & Configuration:{RESET}")
    for req_file in ("AGENTS.md", "docs/workflow.md", "docs/architecture.md", "workspace.yaml"):
        p = root / req_file
        if not check(p.is_file(), f"Workspace file: {req_file}"):
            errors += 1

    # 4. Sibling Repositories Checkout
    print(f"\n{BOLD}4. Sibling Repositories:{RESET}")
    parent = root.parent
    sibling_manifest = root / "scripts" / "siblings.json"
    found_siblings = False
    if sibling_manifest.is_file():
        try:
            siblings = json.loads(sibling_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            siblings = []
            if not check(False, f"Invalid sibling manifest: {error}"):
                errors += 1
        for sibling in siblings:
            name = sibling["name"]
            found_siblings = True
            dest = parent / name
            exists = dest.is_dir()
            check(exists, f"Sibling repo '{name}' at {dest}", is_warning=not exists)
    if not found_siblings:
        print(f"  {CYAN}ℹ{RESET} No sibling repositories declared in workspace.yaml yet.")

    # 5. Planning Document Integrity
    print(f"\n{BOLD}5. Planning Document Audit:{RESET}")
    audit_script = root / ".github" / "skills" / "planning-docs-audit" / "scripts" / "planning_docs_audit.py"
    if audit_script.is_file():
        res = subprocess.run([sys.executable, str(audit_script), "--root", str(root)], capture_output=True, text=True)
        audit_ok = res.returncode == 0
        if not check(audit_ok, "Planning document structure & links audit"):
            print(f"{DIM}{res.stdout}{RESET}")
            errors += 1
    else:
        check(False, "Planning docs audit script not found", is_warning=True)

    # 6. Integrations & Authentication
    print(f"\n{BOLD}6. Authentication & API Tokens (for Agents & Skills):{RESET}")
    settings = get_workspace_settings(root)
    tracker_type = settings["tracker_type"]
    vcs_platform = settings["vcs_platform"]

    env_file_exists = (root / ".env.local").is_file() or (root / ".env").is_file()
    if env_file_exists:
        check(True, "Local environment file present (.env.local / .env)")
    else:
        check(False, "No local .env.local or .env file found (copy from .env.example to configure tokens)", is_warning=True)

    if tracker_type == "jira":
        jira_token = os.environ.get("JIRA_API_TOKEN")
        jira_email = os.environ.get("JIRA_USER_EMAIL")
        if jira_token and jira_email:
            check(True, "Jira credentials configured (JIRA_API_TOKEN & JIRA_USER_EMAIL)")
        else:
            check(
                False,
                "Jira credentials missing. Required: JIRA_API_TOKEN (scopes: read:jira-work, write:jira-work) & JIRA_USER_EMAIL in .env.local",
                is_warning=True,
            )

    if tracker_type == "gitlab" or vcs_platform == "gitlab":
        gl_token = os.environ.get("GITLAB_TOKEN")
        glab_auth = False
        if shutil.which("glab"):
            try:
                res = subprocess.run(["glab", "auth", "status"], capture_output=True, text=True)
                glab_auth = (res.returncode == 0)
            except Exception:
                pass
        if gl_token or glab_auth:
            check(True, "GitLab credentials configured (GITLAB_TOKEN or glab CLI logged in)")
        else:
            check(
                False,
                "GitLab token not configured (set GITLAB_TOKEN with scope 'api' in .env.local or run 'glab auth login')",
                is_warning=True,
            )

    if tracker_type == "azure-devops" or vcs_platform == "azure-repos":
        ado_pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        az_auth = False
        if shutil.which("az"):
            try:
                res = subprocess.run(["az", "account", "show"], capture_output=True, text=True)
                az_auth = (res.returncode == 0)
            except Exception:
                pass
        if ado_pat or az_auth:
            check(True, "Azure DevOps credentials configured (AZURE_DEVOPS_EXT_PAT or az CLI logged in)")
        else:
            check(
                False,
                "Azure DevOps PAT missing (set AZURE_DEVOPS_EXT_PAT with Work Items & Code Read/Write in .env.local or run 'az devops login')",
                is_warning=True,
            )

    if tracker_type == "github" or vcs_platform == "github":
        gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        gh_auth = False
        if shutil.which("gh"):
            try:
                res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
                gh_auth = (res.returncode == 0)
            except Exception:
                pass
        if gh_token or gh_auth:
            check(True, "GitHub credentials configured (GITHUB_TOKEN or gh CLI logged in)")
        else:
            check(
                False,
                "GitHub token not configured (set GITHUB_TOKEN with scope 'repo' in .env.local or run 'gh auth login')",
                is_warning=True,
            )

    print(f"\n{BOLD}Summary:{RESET}")
    if errors == 0:
        print(f"  {GREEN}{BOLD}All essential workspace checks passed successfully!{RESET}\n")
        return 0
    else:
        print(f"  {RED}{BOLD}{errors} check(s) failed. Please review the items marked with ✖.{RESET}\n")
        return 1


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parents[1]
    sys.exit(run_diagnostics(root_dir))
