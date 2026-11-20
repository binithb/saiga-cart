#!/usr/bin/env python3
"""Workspace Doctor: Diagnostic & Environment Verification Utility."""

from __future__ import annotations

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


ENV_FILENAMES = (
    ".env.local",
    ".env.azure",
    ".env.jira",
    ".env.github",
    ".env.gitlab",
    ".env",
)


def load_env_file(root: Path) -> dict[str, str]:
    """Load key-value pairs from local .env* files into os.environ if not already set."""
    loaded = {}
    for filename in ENV_FILENAMES:
        env_path = root / filename
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[len("export "):].strip()
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


SKILL_DIR_CANDIDATES = (
    ".github/skills",
    ".claude/skills",
    ".agents/skills",
)


def _find_skill_script(root: Path, skill_subpath: str) -> Path | None:
    for rel in SKILL_DIR_CANDIDATES:
        candidate = root / rel / skill_subpath
        if candidate.is_file():
            return candidate
    return None


def get_workspace_settings(root: Path) -> dict[str, object]:
    """Extract tracker type, VCS platform, and enabled agents from workspace.yaml."""
    settings: dict[str, object] = {
        "tracker_type": "",
        "vcs_platform": "",
        "agents": {},
    }
    ws_yaml = root / "workspace.yaml"
    if ws_yaml.is_file():
        section = ""
        agents_dict: dict[str, bool] = {}
        for line in ws_yaml.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line.startswith((" ", "\t")):
                section = stripped.rstrip(":")
                continue

            if section == "tracker" and stripped.startswith("type:"):
                settings["tracker_type"] = stripped.split(":", 1)[1].strip().strip("'\"")
            elif section == "vcs" and stripped.startswith("platform:"):
                settings["vcs_platform"] = stripped.split(":", 1)[1].strip().strip("'\"")
            elif section == "agents" and ":" in stripped:
                k, v = stripped.split(":", 1)
                val_clean = v.split("#", 1)[0].strip().lower()
                if val_clean in ("true", "false"):
                    agents_dict[k.strip()] = val_clean == "true"
        settings["agents"] = agents_dict
    return settings


def run_diagnostics(root: Path) -> int:
    load_env_file(root)
    print(f"\n{BOLD}{CYAN}=== saiga-cart Diagnostics ==={RESET}\n")
    errors = 0
    settings = get_workspace_settings(root)

    # 1. Python Environment
    print(f"{BOLD}1. Runtime & Environment:{RESET}")
    py_ok = sys.version_info >= (3, 8)
    if not check(py_ok, f"Python version {sys.version.split()[0]} (>= 3.8 required)"):
        errors += 1

    # 2. CLI Tools
    print(f"\n{BOLD}2. Developer CLI Tools:{RESET}")
    for tool in ("git", "gh", "glab", "az", "code"):
        present = shutil.which(tool) is not None
        check(present, f"CLI tool: {tool}", is_warning=(tool != "git"))

    # 3. Workspace Core Files & Configured AI Assistant Artifacts
    print(f"\n{BOLD}3. Workspace Directives & Configuration:{RESET}")
    for req_file in ("AGENTS.md", "docs/workflow.md", "docs/architecture.md", "workspace.yaml"):
        p = root / req_file
        if not check(p.is_file(), f"Workspace file: {req_file}"):
            errors += 1

    active_skill_dirs = [rel for rel in SKILL_DIR_CANDIDATES if (root / rel).is_dir()]
    if not check(
        bool(active_skill_dirs),
        f"Active skills directory ({', '.join(active_skill_dirs) if active_skill_dirs else 'none found'})",
    ):
        errors += 1

    agents_cfg = settings.get("agents")
    if isinstance(agents_cfg, dict):
        if agents_cfg.get("copilot") is True:
            if not check((root / ".github" / "copilot-instructions.md").is_file(), "GitHub Copilot instructions (.github/copilot-instructions.md)"):
                errors += 1
            if not check((root / ".github" / "skills").is_dir(), "GitHub Copilot skills (.github/skills/)"):
                errors += 1
        if agents_cfg.get("claude") is True:
            if not check((root / "CLAUDE.md").is_file(), "Claude Code instructions (CLAUDE.md)"):
                errors += 1
            if not check((root / ".claude" / "skills").is_dir(), "Claude Code skills (.claude/skills/)"):
                errors += 1
        if agents_cfg.get("codex") is True:
            if not check((root / ".agents" / "skills").is_dir(), "OpenAI Codex skills (.agents/skills/)"):
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
    audit_script = _find_skill_script(root, "planning-docs-audit/scripts/planning_docs_audit.py")
    if audit_script is not None:
        res = subprocess.run([sys.executable, str(audit_script), "--root", str(root)], capture_output=True, text=True)
        audit_ok = res.returncode == 0
        if not check(audit_ok, "Planning document structure & links audit"):
            print(f"{DIM}{res.stdout}{RESET}")
            errors += 1
    else:
        check(False, "Planning docs audit script not found", is_warning=True)

    harness_script = _find_skill_script(root, "harness2/scripts/validate_harness.py")
    if harness_script is not None:
        h_res = subprocess.run([sys.executable, str(harness_script), "--root", str(root)], capture_output=True, text=True)
        h_ok = h_res.returncode == 0
        if not check(h_ok, "Harness² context budget & skill/script parity audit"):
            print(f"{DIM}{h_res.stdout}{RESET}")
            errors += 1

    # 6. Integrations & Authentication
    print(f"\n{BOLD}6. Authentication & API Tokens (for Agents & Skills):{RESET}")
    tracker_type = str(settings.get("tracker_type", ""))
    vcs_platform = str(settings.get("vcs_platform", ""))

    present_env_files = [f for f in ENV_FILENAMES if (root / f).is_file()]
    if present_env_files:
        check(True, f"Local environment file present ({', '.join(present_env_files)})")
    else:
        check(False, "No local .env* file found (run bootstrap.py or copy from .env.example to configure tokens)", is_warning=True)

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
        glab_exe = shutil.which("glab")
        if glab_exe:
            try:
                res = subprocess.run([glab_exe, "auth", "status"], capture_output=True, text=True)
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
        az_exe = shutil.which("az")
        if az_exe:
            try:
                az_env = dict(os.environ)
                az_env.setdefault("AZURE_CORE_COLLECT_TELEMETRY", "0")
                res = subprocess.run(
                    [az_exe, "account", "show"],
                    cwd=Path.home(),
                    env=az_env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
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
        gh_exe = shutil.which("gh")
        if gh_exe:
            try:
                res = subprocess.run([gh_exe, "auth", "status"], capture_output=True, text=True)
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
