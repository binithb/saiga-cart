#!/usr/bin/env python3
"""Interactive Bootstrapper & Workspace Generator for saiga-cart.

Scaffolds a customized, AI-native multi-repo workspace based on your
planning framework (SAFe PIs, Scrum Sprints, Shape Up, Kanban), issue tracker
(Jira, GitHub, GitLab, Azure DevOps), and AI tool preferences.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
CYAN = "\033[96m" if USE_COLOR else ""
GREEN = "\033[92m" if USE_COLOR else ""
YELLOW = "\033[93m" if USE_COLOR else ""
BLUE = "\033[94m" if USE_COLOR else ""
MAGENTA = "\033[95m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""
DIM = "\033[2m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""


def print_banner():
    banner = f"""
{CYAN}{BOLD}==================================================================={RESET}
{MAGENTA}{BOLD}      🛷 saiga-cart: Multi-Repo Workspace Bootstrapper             {RESET}
{CYAN}{BOLD}==================================================================={RESET}
{DIM}Generalize, standardize, and scale cross-repo AI development context.{RESET}
"""
    print(banner)


@dataclass
class SiblingRepo:
    name: str
    url: str
    role: str
    access: str = "active"  # active | read-only


@dataclass
class WorkspaceConfig:
    name: str = "saiga-cart Workspace"
    slug: str = "saiga-cart"
    description: str = "Cross-repository AI context and planning workspace"
    org: str = "acme-corp"
    
    # Planning
    planning_framework: str = "scrum"  # safe | scrum | shape-up | kanban
    cadence_duration: str = "2 weeks"
    threshold_for_split: str = "Large"
    enforce_dor: bool = True
    adr_enabled: bool = True

    # Tracker
    tracker_type: str = "github"  # jira | github | gitlab | azure-devops | none
    tracker_base_url: str = "https://github.com/acme-corp"
    tracker_project_key: str = "PROJ"
    bidirectional_links: bool = True

    # VCS
    vcs_platform: str = "github"  # github | gitlab | bitbucket | azure-repos
    default_branch: str = "main"
    consensus_review_enabled: bool = True
    dod_gate_enabled: bool = True

    # Sibling Repos
    siblings: list[SiblingRepo] = field(default_factory=list)

    # Agents
    copilot: bool = True
    claude: bool = True
    cursor: bool = True


def prompt_text(label: str, default: str = "") -> str:
    default_hint = f" [{CYAN}{default}{RESET}]" if default else ""
    try:
        val = input(f"{BOLD}{label}{RESET}{default_hint}: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Setup cancelled.{RESET}")
        sys.exit(0)


def prompt_choice(label: str, choices: list[tuple[str, str]], default: str) -> str:
    print(f"\n{BOLD}{label}{RESET}")
    for idx, (key, desc) in enumerate(choices, 1):
        indicator = f"{GREEN}*{RESET}" if key == default else " "
        print(f"  {indicator} {BOLD}{idx}){RESET} {CYAN}{key}{RESET} - {desc}")
    
    choice_map = {str(idx): key for idx, (key, _) in enumerate(choices, 1)}
    choice_map.update({key: key for key, _ in choices})
    
    while True:
        try:
            raw = input(f"Select choice [{CYAN}{default}{RESET}]: ").strip()
            if not raw:
                return default
            if raw in choice_map:
                return choice_map[raw]
            print(f"{YELLOW}Invalid choice, please select 1-{len(choices)} or enter choice key.{RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Setup cancelled.{RESET}")
            sys.exit(0)


def prompt_bool(label: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    try:
        raw = input(f"{BOLD}{label}{RESET} [{CYAN}{default_str}{RESET}]: ").strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes", "true", "1")
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Setup cancelled.{RESET}")
        sys.exit(0)


def prompt_secret(label: str) -> str:
    """Prompt for a sensitive token using masked input when connected to a TTY."""
    try:
        if sys.stdin.isatty():
            val = getpass.getpass(f"{BOLD}{label}{RESET} (input hidden): ").strip()
        else:
            val = input(f"{BOLD}{label}{RESET}: ").strip()
        return val.strip("'\"")
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Setup cancelled.{RESET}")
        sys.exit(0)


ENV_FILENAMES = (
    ".env.local",
    ".env.azure",
    ".env.jira",
    ".env.github",
    ".env.gitlab",
    ".env",
)


def default_env_filename(cfg: WorkspaceConfig) -> str:
    """Suggest the most descriptive local env filename for the workspace."""
    if cfg.tracker_type == "azure-devops" or cfg.vcs_platform == "azure-repos":
        return ".env.azure"
    if cfg.tracker_type == "jira":
        return ".env.jira"
    if cfg.tracker_type == "gitlab" or cfg.vcs_platform == "gitlab":
        return ".env.gitlab"
    if cfg.tracker_type == "github" or cfg.vcs_platform == "github":
        return ".env.github"
    return ".env.local"


def load_env_files(root: Path) -> dict[str, str]:
    """Load key-value pairs from local .env* files into os.environ if not already set."""
    loaded: dict[str, str] = {}
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


def write_env_vars(env_path: Path, updates: dict[str, str]) -> None:
    """Create or update key=value entries in a local .env file and set os.environ."""
    existing_lines: list[str] = []
    if env_path.is_file():
        try:
            existing_lines = env_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            existing_lines = []

    remaining = dict(updates)
    new_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key.startswith("export "):
                key = key[len("export "):].strip()
            if key in remaining:
                new_lines.append(f"{key}={remaining.pop(key)}")
                continue
        new_lines.append(line)

    if not new_lines:
        new_lines.append(f"# saiga-cart local credentials ({env_path.name})")
    for key, val in remaining.items():
        new_lines.append(f"{key}={val}")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    try:
        if os.name != "nt":
            env_path.chmod(0o600)
    except Exception:
        pass
    for key, val in updates.items():
        os.environ[key] = val


def normalize_ado_base_and_project(raw_url: str, fallback_org: str, fallback_project: str) -> tuple[str, str]:
    """Normalize an Azure DevOps URL into (base_url, project_key) and strip browser suffixes."""
    cleaned = raw_url.strip().rstrip("/")
    if not cleaned:
        return f"https://dev.azure.com/{fallback_org}/{fallback_project}", fallback_project
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        if "." not in cleaned and "/" not in cleaned:
            return f"https://dev.azure.com/{cleaned}/{fallback_project}", fallback_project
        cleaned = "https://" + cleaned.lstrip("/")

    parsed = urllib.parse.urlsplit(cleaned)
    host = parsed.netloc.lower()
    segments = [urllib.parse.unquote(s) for s in parsed.path.split("/") if s]
    # Strip trailing repo/board segments like _git, _boards, _workitems, _apis
    filtered: list[str] = []
    for seg in segments:
        if seg.startswith("_"):
            break
        filtered.append(seg)

    if host.endswith(".visualstudio.com"):
        project = filtered[0] if filtered else fallback_project
        base = f"{parsed.scheme}://{parsed.netloc}/{urllib.parse.quote(project)}"
        return base, project

    if host == "dev.azure.com" or "azure" in host:
        org = filtered[0] if len(filtered) >= 1 else fallback_org
        project = filtered[1] if len(filtered) >= 2 else fallback_project
        base = f"{parsed.scheme}://{parsed.netloc}/{urllib.parse.quote(org)}/{urllib.parse.quote(project)}"
        return base, project

    project = filtered[-1] if filtered else fallback_project
    return cleaned, project


def verify_provider_auth(
    provider: str,
    cfg: WorkspaceConfig,
    env: dict[str, str] | None = None,
    timeout: int = 10,
) -> tuple[bool, str]:
    """Verify credentials against the configured remote tracker or VCS provider."""
    lookup = dict(os.environ)
    if env:
        lookup.update(env)

    if provider in ("azure-devops", "azure-repos"):
        pat = lookup.get("AZURE_DEVOPS_EXT_PAT") or lookup.get("ADO_PAT") or ""
        base_url, project = normalize_ado_base_and_project(
            lookup.get("AZURE_DEVOPS_ORG_URL") or cfg.tracker_base_url,
            cfg.org,
            cfg.tracker_project_key or "project",
        )
        if pat:
            parsed = urllib.parse.urlsplit(base_url)
            segs = [s for s in parsed.path.split("/") if s and not s.startswith("_")]
            if parsed.netloc.lower().endswith(".visualstudio.com"):
                org_root = f"{parsed.scheme}://{parsed.netloc}"
            elif segs:
                org_root = f"{parsed.scheme}://{parsed.netloc}/{segs[0]}"
            else:
                org_root = base_url.rstrip("/")
            api_url = f"{org_root}/_apis/projects?%24top=1&api-version=7.0"
            b64 = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
            req = urllib.request.Request(
                api_url,
                headers={"Authorization": f"Basic {b64}", "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if 200 <= resp.status < 300:
                        return True, f"Verified Azure DevOps PAT against {org_root} (HTTP {resp.status})"
            except urllib.error.HTTPError as err:
                if err.code in (401, 403):
                    return False, f"Azure DevOps rejected token (HTTP {err.code}). Ensure PAT is valid and has Work Items & Code Read/Write scopes."
                if err.code == 404:
                    return False, f"Azure DevOps organization/project not found at {org_root} (HTTP 404)."
                return False, f"Azure DevOps API returned HTTP {err.code}: {err.reason}"
            except Exception as err:
                return False, f"Could not reach Azure DevOps ({org_root}): {err}"

        if shutil.which("az"):
            try:
                res = subprocess.run(
                    ["az", "account", "show"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if res.returncode == 0:
                    return True, "Verified Azure CLI session ('az account show' succeeded)"
            except Exception:
                pass
        return False, "No valid AZURE_DEVOPS_EXT_PAT or active 'az' CLI login detected."

    if provider == "jira":
        token = lookup.get("JIRA_API_TOKEN") or ""
        email = lookup.get("JIRA_USER_EMAIL") or ""
        base_url = (lookup.get("JIRA_BASE_URL") or cfg.tracker_base_url).rstrip("/")
        if not token or not email:
            return False, "Missing JIRA_API_TOKEN or JIRA_USER_EMAIL."
        api_url = f"{base_url}/rest/api/3/myself"
        b64 = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        req = urllib.request.Request(
            api_url,
            headers={"Authorization": f"Basic {b64}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    return True, f"Verified Jira credentials against {base_url}"
        except urllib.error.HTTPError as err:
            return False, f"Jira authentication failed (HTTP {err.code}). Check email, API token, and base URL."
        except Exception as err:
            return False, f"Could not connect to Jira ({base_url}): {err}"

    if provider == "github":
        token = lookup.get("GITHUB_TOKEN") or lookup.get("GH_TOKEN") or ""
        if token:
            req = urllib.request.Request(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "saiga-cart-bootstrap",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if 200 <= resp.status < 300:
                        return True, "Verified GITHUB_TOKEN against https://api.github.com/user"
            except urllib.error.HTTPError as err:
                return False, f"GitHub token rejected (HTTP {err.code}). Ensure PAT has 'repo' scope."
            except Exception as err:
                return False, f"Could not reach GitHub API: {err}"
        if shutil.which("gh"):
            try:
                res = subprocess.run(
                    ["gh", "auth", "status"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if res.returncode == 0:
                    return True, "Verified GitHub CLI session ('gh auth status' succeeded)"
            except Exception:
                pass
        return False, "No valid GITHUB_TOKEN or active 'gh auth login' session found."

    if provider == "gitlab":
        token = lookup.get("GITLAB_TOKEN") or lookup.get("GITLAB_PAT") or ""
        base_url = lookup.get("GITLAB_BASE_URL") or (
            cfg.tracker_base_url if cfg.tracker_type == "gitlab" else "https://gitlab.com"
        )
        parsed = urllib.parse.urlsplit(base_url if "://" in base_url else f"https://{base_url}")
        host_root = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "https://gitlab.com"
        if token:
            req = urllib.request.Request(
                f"{host_root}/api/v4/user",
                headers={"PRIVATE-TOKEN": token, "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if 200 <= resp.status < 300:
                        return True, f"Verified GITLAB_TOKEN against {host_root}"
            except urllib.error.HTTPError as err:
                return False, f"GitLab token rejected at {host_root} (HTTP {err.code}). Ensure token has 'api' scope."
            except Exception as err:
                return False, f"Could not reach GitLab API ({host_root}): {err}"
        if shutil.which("glab"):
            try:
                res = subprocess.run(
                    ["glab", "auth", "status"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if res.returncode == 0:
                    return True, "Verified GitLab CLI session ('glab auth status' succeeded)"
            except Exception:
                pass
        return False, "No valid GITLAB_TOKEN or active 'glab auth login' session found."

    return True, f"No API verification required for provider '{provider}'."


def normalize_git_repo_url(raw_url: str) -> str:
    """Clean and normalize user-entered Git URLs (browser suffixes, spaces, git clone prefixes)."""
    cleaned = raw_url.strip().strip("'\"")
    if cleaned.lower().startswith("git clone "):
        cleaned = cleaned[len("git clone "):].strip()
        # Strip leading CLI flags like `-b main` or `--depth 1` before the URL
        tokens = cleaned.split()
        for idx, tok in enumerate(tokens):
            if tok.startswith(("http://", "https://", "git@", "ssh://")):
                cleaned = " ".join(tokens[idx:])
                break

    if cleaned.startswith(("http://", "https://")):
        parsed = urllib.parse.urlsplit(cleaned)
        path = parsed.path
        # Strip common web UI suffixes pasted from browser address bars
        for marker in (
            "/pullrequest",
            "/commit/",
            "/commits",
            "/branches",
            "/branchCompare",
            "/-/tree/",
            "/-/blob/",
            "/-/merge_requests",
            "/tree/",
            "/blob/",
            "/src/",
        ):
            if marker in path:
                path = path.split(marker, 1)[0]
        path = path.rstrip("/")
        # Encode unescaped spaces in paths (common in Azure DevOps project/repo names)
        normalized_path = urllib.parse.quote(urllib.parse.unquote(path), safe="/:@._-~")
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))

    return cleaned


def derive_repo_name_from_url(url: str) -> str:
    """Extract a clean, safe directory slug from a Git URL or local path."""
    cleaned = normalize_git_repo_url(url).rstrip("/\\")
    if ":" in cleaned and not cleaned.startswith(("http://", "https://", "ssh://")):
        cleaned = cleaned.split(":", 1)[1]
    tail = re.split(r"[\\/]", cleaned)[-1]
    tail = urllib.parse.unquote(tail)
    if tail.endswith(".git"):
        tail = tail[:-4]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", tail).strip("-.")
    return slug or "sibling-repo"


def validate_sibling_name(name: str, existing: list[SiblingRepo], workspace_slug: str = "") -> tuple[bool, str]:
    """Validate that a sibling repository folder name is safe and non-conflicting."""
    cleaned = name.strip()
    if not cleaned:
        return False, "Repository directory name cannot be empty."
    if cleaned in (".", "..") or "/" in cleaned or "\\" in cleaned or ".." in cleaned:
        return False, "Repository name must be a single folder name without slashes or '..'."
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", cleaned):
        return False, "Repository name may only contain letters, numbers, '.', '_', and '-'."
    if workspace_slug and cleaned.lower() == workspace_slug.lower():
        return False, f"Sibling name '{cleaned}' conflicts with the workspace directory slug '{workspace_slug}'."
    if any(s.name.lower() == cleaned.lower() for s in existing):
        return False, f"A sibling repository named '{cleaned}' is already in the list."
    return True, cleaned


def _build_git_auth_args(url: str, env: dict[str, str]) -> list[str]:
    """Build transient git `-c http.extraHeader=...` arguments so tokens never leak into saved URLs."""
    if not url.startswith(("http://", "https://")):
        return []
    host = urllib.parse.urlsplit(url).netloc.lower()
    if ("dev.azure.com" in host or host.endswith(".visualstudio.com")) and (
        env.get("AZURE_DEVOPS_EXT_PAT") or env.get("ADO_PAT")
    ):
        pat = env.get("AZURE_DEVOPS_EXT_PAT") or env.get("ADO_PAT") or ""
        b64 = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        return ["-c", f"http.extraHeader=Authorization: Basic {b64}"]
    if "github.com" in host and (env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")):
        tok = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN") or ""
        b64 = base64.b64encode(f"x-access-token:{tok}".encode("utf-8")).decode("ascii")
        return ["-c", f"http.extraHeader=Authorization: Basic {b64}"]
    if "gitlab" in host and (env.get("GITLAB_TOKEN") or env.get("GITLAB_PAT")):
        tok = env.get("GITLAB_TOKEN") or env.get("GITLAB_PAT") or ""
        b64 = base64.b64encode(f"oauth2:{tok}".encode("utf-8")).decode("ascii")
        return ["-c", f"http.extraHeader=Authorization: Basic {b64}"]
    return []


def verify_git_repo_url(
    url: str,
    env: dict[str, str] | None = None,
    timeout: int = 15,
) -> tuple[bool, str]:
    """Probe a Git repository URL immediately using `git ls-remote` without hanging on prompts."""
    cleaned = normalize_git_repo_url(url)
    if not cleaned:
        return False, "Repository URL cannot be empty."
    if shutil.which("git") is None:
        return False, "git CLI is not installed or not in PATH."

    lookup = dict(os.environ)
    if env:
        lookup.update(env)

    run_env = dict(lookup)
    run_env["GIT_TERMINAL_PROMPT"] = "0"
    run_env["GCM_INTERACTIVE"] = "never"
    if "GIT_SSH_COMMAND" not in run_env:
        run_env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=10"

    auth_args = _build_git_auth_args(cleaned, lookup)
    cmd = ["git", *auth_args, "ls-remote", "--heads", cleaned]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=run_env,
            timeout=timeout,
        )
        if res.returncode == 0:
            return True, f"Repository reachable ({cleaned})"
        stderr = (res.stderr or res.stdout or "").strip()
        # Scrub any authorization headers from error output just in case
        stderr = re.sub(r"Authorization:\s*Basic\s+[A-Za-z0-9+/=]+", "Authorization: Basic ***", stderr)
        first_line = stderr.splitlines()[-1] if stderr else f"git ls-remote exited with code {res.returncode}"
        return False, first_line
    except subprocess.TimeoutExpired:
        return False, f"Timed out after {timeout}s while connecting to {cleaned}"
    except Exception as err:
        return False, f"Failed to run git ls-remote: {err}"


def run_interactive_auth_setup(cfg: WorkspaceConfig, root: Path) -> None:
    """Walk the user through configuring and testing tracker/VCS tokens interactively."""
    load_env_files(root)
    providers: list[str] = []
    if cfg.tracker_type != "none":
        providers.append(cfg.tracker_type)
    if cfg.vcs_platform == "azure-repos" and "azure-devops" not in providers:
        providers.append("azure-devops")
    elif cfg.vcs_platform in ("github", "gitlab") and cfg.vcs_platform not in providers:
        providers.append(cfg.vcs_platform)

    if not providers:
        return

    print(f"\n{BLUE}{BOLD}--- Section 4b: Authentication & Live Connection Check ---{RESET}")
    suggested_env = default_env_filename(cfg)
    print(f"{DIM}Credentials can be saved in a git-ignored env file (e.g. {suggested_env} or .env.local)")
    print(f"or managed in your local CLI / OS keyring (az devops login, gh auth login, glab auth login).{RESET}")

    for provider in providers:
        ok, msg = verify_provider_auth(provider, cfg)
        if ok:
            print(f"  {GREEN}✔{RESET} {msg}")
            if not prompt_bool(f"Reconfigure {provider} credentials anyway?", False):
                continue

        while True:
            storage_choices = [
                ("env-file", f"Save token in local env file ({suggested_env} / .env.local)"),
                ("keyring", "Use local CLI / OS keyring (I have logged in or will log in via CLI/keyring)"),
                ("skip", "Skip authentication setup for now"),
            ]
            mode = prompt_choice(f"How would you like to configure {provider} authentication?", storage_choices, "env-file")
            if mode == "skip":
                print(f"  {YELLOW}⚠{RESET} Skipping {provider} credential verification for now.")
                break

            if mode == "env-file":
                env_name = prompt_text("Local env file name", suggested_env)
                if not env_name.startswith(".env"):
                    env_name = f".env.{env_name.lstrip('.')}"
                env_path = root / env_name
                updates: dict[str, str] = {}

                if provider == "azure-devops":
                    print(f"  {DIM}Create PAT at: https://dev.azure.com/{cfg.org}/_usersSettings/tokens")
                    print(f"  Required scopes: Work Items (Read & write) and Code (Read & write){RESET}")
                    updates["AZURE_DEVOPS_ORG_URL"] = cfg.tracker_base_url
                    pat = ""
                    while not pat:
                        pat = prompt_secret("Enter Azure DevOps PAT (AZURE_DEVOPS_EXT_PAT)")
                        if not pat:
                            print(f"  {YELLOW}Token cannot be empty.{RESET}")
                    updates["AZURE_DEVOPS_EXT_PAT"] = pat
                elif provider == "jira":
                    print(f"  {DIM}Create API token at: https://id.atlassian.com/manage-profile/security/api-tokens{RESET}")
                    updates["JIRA_BASE_URL"] = cfg.tracker_base_url
                    email = ""
                    while not email or "@" not in email:
                        email = prompt_text("Jira Account Email (JIRA_USER_EMAIL)", os.environ.get("JIRA_USER_EMAIL", ""))
                        if not email or "@" not in email:
                            print(f"  {YELLOW}Please enter a valid email address.{RESET}")
                    tok = ""
                    while not tok:
                        tok = prompt_secret("Enter Jira API Token (JIRA_API_TOKEN)")
                        if not tok:
                            print(f"  {YELLOW}Token cannot be empty.{RESET}")
                    updates["JIRA_USER_EMAIL"] = email
                    updates["JIRA_API_TOKEN"] = tok
                elif provider == "github":
                    print(f"  {DIM}Create PAT at: https://github.com/settings/tokens (scope: repo){RESET}")
                    tok = ""
                    while not tok:
                        tok = prompt_secret("Enter GitHub PAT (GITHUB_TOKEN)")
                        if not tok:
                            print(f"  {YELLOW}Token cannot be empty.{RESET}")
                    updates["GITHUB_TOKEN"] = tok
                elif provider == "gitlab":
                    gl_url = cfg.tracker_base_url if cfg.tracker_type == "gitlab" else "https://gitlab.com"
                    print(f"  {DIM}Create PAT at: {gl_url.rstrip('/')}/-/user_settings/personal_access_tokens (scope: api){RESET}")
                    updates["GITLAB_BASE_URL"] = gl_url
                    tok = ""
                    while not tok:
                        tok = prompt_secret("Enter GitLab PAT (GITLAB_TOKEN)")
                        if not tok:
                            print(f"  {YELLOW}Token cannot be empty.{RESET}")
                    updates["GITLAB_TOKEN"] = tok

                write_env_vars(env_path, updates)
                print(f"  {GREEN}✔{RESET} Saved credentials to {CYAN}{env_name}{RESET} (git-ignored)")
            else:
                if provider == "azure-devops":
                    print(f"  {CYAN}ℹ{RESET} Run {BOLD}az login{RESET} or {BOLD}az devops login{RESET} (and configure Git Credential Manager) in another terminal.")
                elif provider == "github":
                    print(f"  {CYAN}ℹ{RESET} Run {BOLD}gh auth login{RESET} in another terminal.")
                elif provider == "gitlab":
                    print(f"  {CYAN}ℹ{RESET} Run {BOLD}glab auth login{RESET} in another terminal.")
                else:
                    print(f"  {CYAN}ℹ{RESET} Ensure {BOLD}JIRA_USER_EMAIL{RESET} and {BOLD}JIRA_API_TOKEN{RESET} are exported in your shell environment.")
                _ = prompt_text("Press Enter once ready to test connection", "")

            ok, msg = verify_provider_auth(provider, cfg)
            if ok:
                print(f"  {GREEN}✔{RESET} {msg}")
                break
            print(f"  {YELLOW}✖ Authentication check failed:{RESET} {msg}")
            if not prompt_bool("Try configuring credentials again?", True):
                print(f"  {YELLOW}⚠{RESET} Continuing without verified {provider} credentials.")
                break


def prompt_and_verify_siblings(cfg: WorkspaceConfig) -> list[SiblingRepo]:
    """Interactively prompt for sibling repositories and strictly verify each URL via git ls-remote."""
    siblings: list[SiblingRepo] = list(cfg.siblings)
    print(f"{DIM}Each sibling repository URL will be tested immediately with 'git ls-remote'.")
    print(f"Leave the Repository Git URL blank when you are finished adding repositories.{RESET}")

    while True:
        if siblings:
            print(f"\n  {CYAN}Configured sibling repositories ({len(siblings)}):{RESET}")
            for idx, sib in enumerate(siblings, 1):
                print(f"    {idx}. {BOLD}{sib.name}{RESET} ({sib.url}) [{sib.access}]")
            if not prompt_bool("Add another sibling repository?", False):
                break
        else:
            if not prompt_bool("Add a sibling repository to this workspace?", True):
                break

        # URL entry & strict verification loop
        verified_url = ""
        while True:
            if cfg.vcs_platform == "azure-repos":
                example_url = f"https://dev.azure.com/{cfg.org}/{cfg.tracker_project_key}/_git/my-service"
            elif cfg.vcs_platform == "gitlab":
                example_url = f"https://gitlab.com/{cfg.org}/my-service.git"
            else:
                example_url = f"https://github.com/{cfg.org}/my-service.git"

            raw_url = prompt_text(f"Sibling Repository Git URL (e.g. {example_url}; blank to skip)", "")
            if not raw_url:
                break

            candidate_url = normalize_git_repo_url(raw_url)
            if any(s.url.lower() == candidate_url.lower() for s in siblings):
                print(f"  {YELLOW}✖ Duplicate URL:{RESET} '{candidate_url}' is already in the sibling list.")
                continue

            print(f"  {DIM}Testing repository access: {candidate_url} ...{RESET}")
            ok, msg = verify_git_repo_url(candidate_url)
            if ok:
                print(f"  {GREEN}✔{RESET} {msg}")
                verified_url = candidate_url
                break

            print(f"  {YELLOW}✖ Repository URL check failed:{RESET} {msg}")
            print(f"  {DIM}Please verify the URL, repository permissions, or SSH/PAT credentials and try again (or leave blank to skip).{RESET}")

        if not verified_url:
            continue

        # Name entry & validation loop
        suggested_name = derive_repo_name_from_url(verified_url)
        repo_name = ""
        while True:
            raw_name = prompt_text("Local folder name (checked out beside workspace)", suggested_name)
            valid_name, name_or_err = validate_sibling_name(raw_name, siblings, cfg.slug)
            if valid_name:
                repo_name = name_or_err
                break
            print(f"  {YELLOW}✖ Invalid name:{RESET} {name_or_err}")

        role = prompt_text("Repository role / responsibility summary", f"Service repository ({repo_name})")
        access_choices = [
            ("active", "Active development (agents can read and edit code)"),
            ("read-only", "Read-only reference (agents can inspect contracts/schemas only)"),
        ]
        access = prompt_choice("Agent Access Mode", access_choices, "active")
        siblings.append(SiblingRepo(name=repo_name, url=verified_url, role=role, access=access))
        print(f"  {GREEN}✔{RESET} Added sibling repository {BOLD}{repo_name}{RESET}")

    return siblings


def run_interactive_wizard(root: Path | None = None) -> WorkspaceConfig:
    target_root = (root or Path.cwd()).resolve()
    cfg = WorkspaceConfig()
    
    print(f"\n{BLUE}{BOLD}--- Section 1: Workspace Identity ---{RESET}")
    cfg.name = prompt_text("Workspace / Project Display Name", "Acme Platform AI Workspace")
    suggested_slug = re.sub(r"[^a-z0-9]+", "-", cfg.name.lower()).strip("-")
    cfg.slug = prompt_text("Workspace Directory / File Slug", suggested_slug)
    cfg.description = prompt_text("Short Description", "Multi-repository AI planning and execution workspace")
    cfg.org = prompt_text("Organization / Company / Namespace", "acme-corp")

    print(f"\n{BLUE}{BOLD}--- Section 2: Planning Methodology & Cadence ---{RESET}")
    framework_choices = [
        ("scrum", "Scrum / Sprints (Sprints -> Epics -> Stories)"),
        ("safe", "Scaled Agile / PIs (Program Increments -> Goals -> Epics -> Stories)"),
        ("shape-up", "Shape Up (6-week Cycles -> Pitches -> Scopes)"),
        ("kanban", "Continuous Delivery / Kanban (Milestones -> Epics -> Tasks)"),
    ]
    cfg.planning_framework = prompt_choice("Planning Framework", framework_choices, "scrum")
    
    if cfg.planning_framework == "scrum":
        dur_choices = [("1 week", "1-week sprint"), ("2 weeks", "2-week sprint"), ("3 weeks", "3-week sprint"), ("4 weeks", "4-week sprint")]
        cfg.cadence_duration = prompt_choice("Sprint Duration", dur_choices, "2 weeks")
    elif cfg.planning_framework == "safe":
        dur_choices = [("8 weeks", "8-week PI (approx. 2 months)"), ("10 weeks", "10-week PI"), ("12 weeks", "12-week PI (quarterly)")]
        cfg.cadence_duration = prompt_choice("Program Increment Duration", dur_choices, "8 weeks")
    elif cfg.planning_framework == "shape-up":
        cfg.cadence_duration = "6 weeks"
    else:
        cfg.cadence_duration = "continuous"

    print(f"\n{BLUE}{BOLD}--- Section 3: Issue Tracking Tooling ---{RESET}")
    tracker_choices = [
        ("github", "GitHub Issues & Projects"),
        ("jira", "Jira Cloud / Server (Atlassian)"),
        ("gitlab", "GitLab Issues & Epics"),
        ("azure-devops", "Azure DevOps Boards"),
        ("none", "Local Markdown Only (no remote issue tracker sync)"),
    ]
    cfg.tracker_type = prompt_choice("Primary Task / Issue Tracker", tracker_choices, "github")
    
    if cfg.tracker_type == "jira":
        cfg.tracker_base_url = prompt_text("Jira Base URL", "https://company.atlassian.net")
        cfg.tracker_project_key = prompt_text("Jira Project Key", "PROJ")
        print(f"  {DIM}ℹ Note: Jira Cloud integration uses JIRA_API_TOKEN (scopes: read:jira-work, write:jira-work) configured in .env.jira / .env.local{RESET}")
    elif cfg.tracker_type == "github":
        cfg.tracker_base_url = prompt_text("GitHub Repository / Project URL", f"https://github.com/{cfg.org}/main-repo")
        print(f"  {DIM}ℹ Note: GitHub integration uses GITHUB_TOKEN (scope: repo) in .env.github / .env.local or 'gh auth login'{RESET}")
    elif cfg.tracker_type == "gitlab":
        cfg.tracker_base_url = prompt_text("GitLab Group / Project URL", f"https://gitlab.com/{cfg.org}/main-repo")
        print(f"  {DIM}ℹ Note: GitLab integration uses GITLAB_TOKEN (scope: api) in .env.gitlab / .env.local or 'glab auth login'{RESET}")
    elif cfg.tracker_type == "azure-devops":
        raw_ado_url = prompt_text("Azure DevOps Organization or Project URL", f"https://dev.azure.com/{cfg.org}/project")
        norm_base, inferred_proj = normalize_ado_base_and_project(raw_ado_url, cfg.org, "project")
        cfg.tracker_project_key = prompt_text("Azure DevOps Project Name / Key", inferred_proj)
        cfg.tracker_base_url, _ = normalize_ado_base_and_project(norm_base, cfg.org, cfg.tracker_project_key)
        print(f"  {DIM}ℹ Note: Azure DevOps integration uses AZURE_DEVOPS_EXT_PAT (Work Items & Code Read/Write) in .env.azure / .env.local or 'az devops login'{RESET}")

    print(f"\n{BLUE}{BOLD}--- Section 4: Version Control & Code Reviews ---{RESET}")
    vcs_choices = [
        ("github", "GitHub (Pull Requests, GitHub Actions)"),
        ("gitlab", "GitLab (Merge Requests, GitLab CI)"),
        ("azure-repos", "Azure Repos"),
        ("bitbucket", "Bitbucket"),
    ]
    default_vcs = (
        "azure-repos"
        if cfg.tracker_type == "azure-devops"
        else ("github" if cfg.tracker_type == "github" else "gitlab")
    )
    cfg.vcs_platform = prompt_choice("Version Control Platform", vcs_choices, default_vcs)
    cfg.consensus_review_enabled = prompt_bool("Enable Multi-Model Consensus Review Gate (consensus-check)?", True)
    cfg.dod_gate_enabled = prompt_bool("Enable Definition-of-Done Pre-Flight Gate in pr-create?", True)

    # Walk through token setup and live authentication verification before adding sibling repos
    run_interactive_auth_setup(cfg, target_root)

    print(f"\n{BLUE}{BOLD}--- Section 5: Multi-Repo Sibling Repositories ---{RESET}")
    print(f"{DIM}Define sibling repositories to include in this unified multi-root workspace.{RESET}")
    cfg.siblings = prompt_and_verify_siblings(cfg)

    print(f"\n{BLUE}{BOLD}--- Section 6: AI Agent Directives ---{RESET}")
    cfg.copilot = prompt_bool("Generate GitHub Copilot instructions (.github/copilot-instructions.md)?", True)
    cfg.claude = prompt_bool("Generate Claude Code instructions (CLAUDE.md)?", True)
    cfg.cursor = prompt_bool("Generate Cursor IDE rules (.cursorrules)?", True)

    return cfg


def render_template_str(template: str, context: dict[str, str]) -> str:
    result = template
    for key, val in context.items():
        pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"(?:\|default\([^)]*\))?\s*\}\}")
        result = pattern.sub(val, result)
    # Clear any remaining unmatched simple defaults
    result = re.sub(r"\{\{\s*([A-Za-z0-9_]+)\|default\(\"([^\"]*)\"\)\s*\}\}", r"\2", result)
    result = re.sub(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", "", result)
    return result


def yaml_quote(value: str) -> str:
    """Emit a JSON string, which is also a valid YAML scalar."""
    return json.dumps(value, ensure_ascii=False)


def render_workspace_config(cfg: WorkspaceConfig) -> str:
    lines = [
        "# Workspace Configuration",
        "version: 1",
        "workspace:",
        f"  name: {yaml_quote(cfg.name)}",
        f"  slug: {yaml_quote(cfg.slug)}",
        f"  description: {yaml_quote(cfg.description)}",
        f"  organization: {yaml_quote(cfg.org)}",
        "",
        "planning:",
        f"  framework: {yaml_quote(cfg.planning_framework)}",
        f"  cadence_duration: {yaml_quote(cfg.cadence_duration)}",
        "  story_sizing:",
        f"    threshold_for_split: {yaml_quote(cfg.threshold_for_split)}",
        f"    enforce_dor: {str(cfg.enforce_dor).lower()}",
        f"  adr_enabled: {str(cfg.adr_enabled).lower()}",
        "",
        "tracker:",
        f"  type: {yaml_quote(cfg.tracker_type)}",
        f"  base_url: {yaml_quote(cfg.tracker_base_url)}",
        f"  project_key: {yaml_quote(cfg.tracker_project_key)}",
        f"  bidirectional_links: {str(cfg.bidirectional_links).lower()}",
        "",
        "vcs:",
        f"  platform: {yaml_quote(cfg.vcs_platform)}",
        f"  default_branch: {yaml_quote(cfg.default_branch)}",
        f"  consensus_review_enabled: {str(cfg.consensus_review_enabled).lower()}",
        f"  dod_gate_enabled: {str(cfg.dod_gate_enabled).lower()}",
        "",
        "siblings:",
    ]
    if not cfg.siblings:
        lines.append("  []")
    for sibling in cfg.siblings:
        lines += [
            f"  - name: {yaml_quote(sibling.name)}",
            f"    url: {yaml_quote(sibling.url)}",
            f"    role: {yaml_quote(sibling.role)}",
            f"    access: {yaml_quote(sibling.access)}",
        ]
    lines += [
        "",
        "agents:",
        f"  copilot: {str(cfg.copilot).lower()}",
        f"  claude: {str(cfg.claude).lower()}",
        f"  cursor: {str(cfg.cursor).lower()}",
        "",
    ]
    return "\n".join(lines)


def strip_yaml_comment(line: str) -> str:
    """Strip comments starting with # outside quotes."""
    in_single = False
    in_double = False
    escape = False
    for i, ch in enumerate(line):
        if escape:
            escape = False
            continue
        if ch == "\\" and (in_double or in_single):
            escape = True
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def parse_yaml_scalar(val: str):
    """Parse a scalar YAML token to a Python primitive."""
    val = val.strip()
    if not val:
        return ""
    if val == "[]":
        return []
    if val == "{}":
        return {}
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        if val.startswith('"'):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val[1:-1]
        else:
            return val[1:-1]
    lowered = val.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "~", "none"):
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def parse_yaml_str(text: str) -> dict | list:
    """Safe standard-library parser for structured block-style YAML subset."""
    raw_lines = text.splitlines()
    parsed_lines: list[tuple[int, str]] = []
    for line in raw_lines:
        line_clean = line.expandtabs(2)
        stripped = strip_yaml_comment(line_clean).rstrip()
        if not stripped or stripped.isspace():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        parsed_lines.append((indent, stripped.strip()))

    if not parsed_lines:
        return {}

    def parse_block(index: int, base_indent: int):
        if index >= len(parsed_lines):
            return {}, index

        first_indent, first_content = parsed_lines[index]
        if first_content.startswith("- ") or first_content == "-":
            seq = []
            curr = index
            while curr < len(parsed_lines):
                indent, content = parsed_lines[curr]
                if indent < base_indent:
                    break
                if indent == base_indent and (content.startswith("- ") or content == "-"):
                    item_str = content[1:].strip()
                    if not item_str:
                        if curr + 1 < len(parsed_lines) and parsed_lines[curr + 1][0] > indent:
                            sub_val, curr = parse_block(curr + 1, parsed_lines[curr + 1][0])
                            seq.append(sub_val)
                        else:
                            seq.append(None)
                            curr += 1
                    elif ":" in item_str and not (item_str.startswith('"') or item_str.startswith("'")):
                        k, v = item_str.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
                            k = k[1:-1]
                        item_dict = {}
                        if v:
                            item_dict[k] = parse_yaml_scalar(v)
                            curr += 1
                        else:
                            if curr + 1 < len(parsed_lines) and parsed_lines[curr + 1][0] > indent:
                                sub_val, curr = parse_block(curr + 1, parsed_lines[curr + 1][0])
                                item_dict[k] = sub_val
                            else:
                                item_dict[k] = None
                                curr += 1
                        while curr < len(parsed_lines):
                            c_indent, c_content = parsed_lines[curr]
                            if c_indent <= indent:
                                break
                            if c_content.startswith("-"):
                                break
                            if ":" in c_content:
                                ck, cv = c_content.split(":", 1)
                                ck = ck.strip()
                                cv = cv.strip()
                                if (ck.startswith('"') and ck.endswith('"')) or (ck.startswith("'") and ck.endswith("'")):
                                    ck = ck[1:-1]
                                if cv:
                                    item_dict[ck] = parse_yaml_scalar(cv)
                                    curr += 1
                                else:
                                    if curr + 1 < len(parsed_lines) and parsed_lines[curr + 1][0] > c_indent:
                                        sub_val, curr = parse_block(curr + 1, parsed_lines[curr + 1][0])
                                        item_dict[ck] = sub_val
                                    else:
                                        item_dict[ck] = None
                                        curr += 1
                            else:
                                curr += 1
                        seq.append(item_dict)
                    else:
                        seq.append(parse_yaml_scalar(item_str))
                        curr += 1
                else:
                    break
            return seq, curr
        else:
            mapping = {}
            curr = index
            while curr < len(parsed_lines):
                indent, content = parsed_lines[curr]
                if indent < base_indent:
                    break
                if indent == base_indent:
                    if content == "[]":
                        return [], curr + 1
                    if content == "{}":
                        return {}, curr + 1
                    if ":" in content:
                        k, v = content.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
                            k = k[1:-1]
                        if v:
                            mapping[k] = parse_yaml_scalar(v)
                            curr += 1
                        else:
                            if curr + 1 < len(parsed_lines) and parsed_lines[curr + 1][0] > indent:
                                sub_val, curr = parse_block(curr + 1, parsed_lines[curr + 1][0])
                                mapping[k] = sub_val
                            else:
                                mapping[k] = None
                                curr += 1
                    else:
                        curr += 1
                elif indent > base_indent:
                    curr += 1
                else:
                    break
            return mapping, curr

    res, _ = parse_block(0, parsed_lines[0][0])
    return res


def load_workspace_config_from_dict(data: dict) -> WorkspaceConfig:
    """Validate and convert dictionary data into a WorkspaceConfig."""
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a YAML/JSON mapping")

    cfg = WorkspaceConfig()
    ws = data.get("workspace") or {}
    planning = data.get("planning") or {}
    tracker = data.get("tracker") or {}
    vcs = data.get("vcs") or {}
    agents = data.get("agents") or {}
    story_sizing = planning.get("story_sizing") if isinstance(planning, dict) else {}
    if not isinstance(story_sizing, dict):
        story_sizing = {}

    # 1. Workspace Identity
    name = ws.get("name") if isinstance(ws, dict) else data.get("name")
    if name is not None:
        cfg.name = str(name).strip()
        if not cfg.name:
            raise ValueError("workspace.name cannot be empty")

    slug = ws.get("slug") if isinstance(ws, dict) else data.get("slug")
    if slug is not None:
        cfg.slug = str(slug).strip()
    elif name is not None:
        cfg.slug = re.sub(r"[^a-z0-9]+", "-", cfg.name.lower()).strip("-")
    if not cfg.slug:
        cfg.slug = "ai-workspace"

    desc = ws.get("description") if isinstance(ws, dict) else data.get("description")
    if desc is not None:
        cfg.description = str(desc)

    org = (ws.get("organization") or ws.get("org")) if isinstance(ws, dict) else (data.get("organization") or data.get("org"))
    if org is not None:
        cfg.org = str(org)

    # 2. Planning
    framework = planning.get("framework") if isinstance(planning, dict) else (data.get("planning_framework") or data.get("framework"))
    if framework is not None:
        fw_clean = str(framework).strip().lower()
        valid_frameworks = ("safe", "scrum", "shape-up", "kanban")
        if fw_clean not in valid_frameworks:
            raise ValueError(f"Invalid planning.framework '{framework}'. Must be one of: {', '.join(valid_frameworks)}")
        cfg.planning_framework = fw_clean

    duration = planning.get("cadence_duration") if isinstance(planning, dict) else (data.get("cadence_duration") or data.get("duration"))
    if duration is not None:
        cfg.cadence_duration = str(duration).strip()

    split_th = story_sizing.get("threshold_for_split") if isinstance(story_sizing, dict) else data.get("threshold_for_split")
    if split_th is not None:
        cfg.threshold_for_split = str(split_th).strip()

    dor = story_sizing.get("enforce_dor") if isinstance(story_sizing, dict) else data.get("enforce_dor")
    if dor is not None:
        cfg.enforce_dor = bool(dor)

    adr = planning.get("adr_enabled") if isinstance(planning, dict) else data.get("adr_enabled")
    if adr is not None:
        cfg.adr_enabled = bool(adr)

    # 3. Tracker
    t_type = tracker.get("type") if isinstance(tracker, dict) else (data.get("tracker_type") or data.get("tracker"))
    if t_type is not None:
        t_clean = str(t_type).strip().lower()
        valid_trackers = ("jira", "github", "gitlab", "azure-devops", "none")
        if t_clean not in valid_trackers:
            raise ValueError(f"Invalid tracker.type '{t_type}'. Must be one of: {', '.join(valid_trackers)}")
        cfg.tracker_type = t_clean

    t_url = tracker.get("base_url") if isinstance(tracker, dict) else data.get("tracker_base_url")
    if t_url is not None:
        cfg.tracker_base_url = str(t_url).strip()

    t_key = tracker.get("project_key") if isinstance(tracker, dict) else data.get("tracker_project_key")
    if t_key is not None:
        cfg.tracker_project_key = str(t_key).strip()

    bidi = tracker.get("bidirectional_links") if isinstance(tracker, dict) else data.get("bidirectional_links")
    if bidi is not None:
        cfg.bidirectional_links = bool(bidi)

    # 4. VCS
    vcs_plat = vcs.get("platform") if isinstance(vcs, dict) else (data.get("vcs_platform") or data.get("vcs"))
    if vcs_plat is not None:
        plat_clean = str(vcs_plat).strip().lower()
        valid_vcs = ("github", "gitlab", "azure-repos", "bitbucket")
        if plat_clean not in valid_vcs:
            raise ValueError(f"Invalid vcs.platform '{vcs_plat}'. Must be one of: {', '.join(valid_vcs)}")
        cfg.vcs_platform = plat_clean

    def_branch = vcs.get("default_branch") if isinstance(vcs, dict) else data.get("default_branch")
    if def_branch is not None:
        cfg.default_branch = str(def_branch).strip()

    consensus = vcs.get("consensus_review_enabled") if isinstance(vcs, dict) else data.get("consensus_review_enabled")
    if consensus is not None:
        cfg.consensus_review_enabled = bool(consensus)

    dod = vcs.get("dod_gate_enabled") if isinstance(vcs, dict) else data.get("dod_gate_enabled")
    if dod is not None:
        cfg.dod_gate_enabled = bool(dod)

    # 5. Siblings
    siblings_raw = data.get("siblings")
    if siblings_raw is not None:
        if not isinstance(siblings_raw, list):
            raise ValueError("siblings must be a list of repository configurations")
        cfg.siblings = []
        for idx, s in enumerate(siblings_raw):
            if not isinstance(s, dict):
                raise ValueError(f"Sibling entry #{idx + 1} must be a mapping with name, url, and role")
            s_name = s.get("name")
            s_url = s.get("url")
            s_role = s.get("role", "")
            s_access = s.get("access", "active")
            if not s_name:
                raise ValueError(f"Sibling entry #{idx + 1} is missing required 'name'")
            if not s_url:
                raise ValueError(f"Sibling '{s_name}' is missing required 'url'")
            if s_access not in ("active", "read-only"):
                raise ValueError(f"Sibling '{s_name}' has invalid access '{s_access}'. Must be 'active' or 'read-only'")
            cfg.siblings.append(SiblingRepo(
                name=str(s_name).strip(),
                url=str(s_url).strip(),
                role=str(s_role).strip(),
                access=str(s_access).strip(),
            ))

    # 6. Agents
    if isinstance(agents, dict):
        if "copilot" in agents:
            cfg.copilot = bool(agents["copilot"])
        if "claude" in agents:
            cfg.claude = bool(agents["claude"])
        if "cursor" in agents:
            cfg.cursor = bool(agents["cursor"])
    else:
        if "copilot" in data:
            cfg.copilot = bool(data["copilot"])
        if "claude" in data:
            cfg.claude = bool(data["claude"])
        if "cursor" in data:
            cfg.cursor = bool(data["cursor"])

    return cfg


def load_workspace_config(config_path: Path) -> WorkspaceConfig:
    """Load and validate workspace configuration from a YAML or JSON file."""
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    text = config_path.read_text(encoding="utf-8")
    data = None

    try:
        import yaml  # type: ignore[import-not-found]
        data = yaml.safe_load(text)
    except Exception:
        data = None

    if data is None:
        try:
            data = json.loads(text)
        except Exception:
            data = parse_yaml_str(text)

    if not isinstance(data, dict):
        raise ValueError(f"Configuration file {config_path} did not produce a valid dictionary structure")

    return load_workspace_config_from_dict(data)


def clone_siblings_script() -> str:
    return '''#!/usr/bin/env python3
"""Clone configured sibling repositories beside this workspace."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path


ENV_FILENAMES = (
    ".env.local",
    ".env.azure",
    ".env.jira",
    ".env.github",
    ".env.gitlab",
    ".env",
)


def load_env_files(root: Path) -> None:
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
                    val = val.strip().strip("'\\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
            except Exception:
                pass


def build_git_auth_args(url: str) -> list[str]:
    if not url.startswith(("http://", "https://")):
        return []
    host = urllib.parse.urlsplit(url).netloc.lower()
    if ("dev.azure.com" in host or host.endswith(".visualstudio.com")) and (
        os.environ.get("AZURE_DEVOPS_EXT_PAT") or os.environ.get("ADO_PAT")
    ):
        pat = os.environ.get("AZURE_DEVOPS_EXT_PAT") or os.environ.get("ADO_PAT") or ""
        b64 = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        return ["-c", f"http.extraHeader=Authorization: Basic {b64}"]
    if "github.com" in host and (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")):
        tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        b64 = base64.b64encode(f"x-access-token:{tok}".encode("utf-8")).decode("ascii")
        return ["-c", f"http.extraHeader=Authorization: Basic {b64}"]
    if "gitlab" in host and (os.environ.get("GITLAB_TOKEN") or os.environ.get("GITLAB_PAT")):
        tok = os.environ.get("GITLAB_TOKEN") or os.environ.get("GITLAB_PAT") or ""
        b64 = base64.b64encode(f"oauth2:{tok}".encode("utf-8")).decode("ascii")
        return ["-c", f"http.extraHeader=Authorization: Basic {b64}"]
    return []


def main() -> int:
    workspace = Path(__file__).resolve().parents[1]
    load_env_files(workspace)
    manifest = Path(__file__).with_name("siblings.json")
    siblings = json.loads(manifest.read_text(encoding="utf-8"))
    for sibling in siblings:
        destination = workspace.parent / sibling["name"]
        if destination.exists():
            print(f"OK {sibling['name']} already exists at {destination}; skipping")
            continue
        print(f"Cloning {sibling['name']} into {destination}")
        auth_args = build_git_auth_args(sibling["url"])
        cmd = ["git", "clone", *auth_args, sibling["url"], str(destination)]
        try:
            subprocess.run(
                cmd,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            print(f"ERROR: git clone failed for {sibling['name']} ({error.returncode})", file=sys.stderr)
            return error.returncode
    workspace_files = sorted(workspace.glob("*.code-workspace"))
    if workspace_files:
        print(f"Done. Open the workspace with: code {workspace_files[0]}")
    else:
        print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def render_env_example(cfg: WorkspaceConfig) -> str:
    """Generate a tailored .env.example with instructions, links, and required permissions."""
    lines = [
        "# =====================================================================",
        "# saiga-cart Local Environment & API Credentials",
        "# =====================================================================",
        "# Copy this file to `.env.local` (or `.env`) in the workspace root:",
        "#   cp .env.example .env.local",
        "#",
        "# `.env.local` and `.env` are listed in .gitignore and will NEVER be committed.",
        "# These tokens enable autonomous agents, skills, and CLI scripts to interact",
        "# with your remote issue tracker and version control platforms.",
        "# =====================================================================",
        "",
    ]

    has_entries = False

    # Jira
    if cfg.tracker_type == "jira":
        has_entries = True
        lines.extend([
            "# ---------------------------------------------------------------------",
            "# Jira Cloud (Atlassian)",
            "# ---------------------------------------------------------------------",
            "# Where to create token:",
            "#   https://id.atlassian.com/manage-profile/security/api-tokens",
            "# Required permissions / scopes:",
            "#   - An Atlassian account API Token with read & write access to Jira",
            "#   - Required scopes: read:jira-work, write:jira-work",
            "# Used by skills: jira-story-onboard, jira-status-sync",
            f"JIRA_BASE_URL={cfg.tracker_base_url}",
            "JIRA_USER_EMAIL=your-email@company.com",
            "JIRA_API_TOKEN=your_jira_api_token_here",
            "",
        ])

    # GitLab
    if cfg.tracker_type == "gitlab" or cfg.vcs_platform == "gitlab":
        has_entries = True
        gl_url = cfg.tracker_base_url if cfg.tracker_type == "gitlab" else "https://gitlab.com"
        lines.extend([
            "# ---------------------------------------------------------------------",
            "# GitLab (Issues & Merge Requests)",
            "# ---------------------------------------------------------------------",
            "# Where to create token:",
            "#   GitLab -> Preferences / User Settings -> Access Tokens",
            "#   Direct link: https://gitlab.com/-/user_settings/personal_access_tokens",
            "# Required permissions / scopes:",
            "#   - `api` (full API access to create issues, query status, manage MRs)",
            "#   - Alternatively: `read_api` (read issues/MRs) + `write_repository` (push branches)",
            "# Local CLI alternative: run `glab auth login` to authenticate the GitLab CLI",
            "# Used by skills: gitlab-issue-onboard, pr-create",
            f"GITLAB_BASE_URL={gl_url}",
            "GITLAB_TOKEN=glpat-your_gitlab_pat_here",
            "",
        ])

    # Azure DevOps
    if cfg.tracker_type == "azure-devops" or cfg.vcs_platform == "azure-repos":
        has_entries = True
        lines.extend([
            "# ---------------------------------------------------------------------",
            "# Azure DevOps (Boards & Azure Repos)",
            "# ---------------------------------------------------------------------",
            "# Where to create token:",
            "#   Azure DevOps -> User Settings (top right gear/user icon) -> Personal access tokens",
            "#   Direct link: https://dev.azure.com/{organization}/_usersSettings/tokens",
            "# Required permissions / scopes:",
            "#   - Work Items: `Read & write` (for creating user stories/tasks and updating status)",
            "#   - Code: `Read & write` (for branches, pull requests, and sibling checkouts)",
            "# Local CLI alternative: run `az devops login`",
            "# Used by skills: ado-work-item-onboard",
            f"AZURE_DEVOPS_ORG_URL={cfg.tracker_base_url}",
            "AZURE_DEVOPS_EXT_PAT=your_azure_devops_pat_here",
            "",
        ])

    # GitHub
    if cfg.tracker_type == "github" or cfg.vcs_platform == "github":
        has_entries = True
        lines.extend([
            "# ---------------------------------------------------------------------",
            "# GitHub (Issues & Pull Requests)",
            "# ---------------------------------------------------------------------",
            "# Where to create token:",
            "#   GitHub -> Settings -> Developer settings -> Personal access tokens",
            "#   Direct link: https://github.com/settings/tokens",
            "# Required permissions / scopes:",
            "#   - Classic PAT: `repo` (Full control of private repositories)",
            "#   - Fine-grained PAT:",
            "#       * Issues: Read and write",
            "#       * Pull requests: Read and write",
            "#       * Contents: Read and write",
            "# Local CLI alternative: run `gh auth login` to authenticate the GitHub CLI",
            "# Used by skills: github-issue-onboard, github-status-sync, pr-create",
            "GITHUB_TOKEN=ghp_your_github_token_here",
            "",
        ])

    if not has_entries:
        lines.extend([
            "# (No external tracker or VCS configured that requires tokens)",
            "",
        ])

    return "\n".join(lines)


def print_token_setup_instructions(cfg: WorkspaceConfig) -> None:
    if cfg.tracker_type == "none" and cfg.vcs_platform not in ("github", "gitlab", "azure-repos"):
        return

    print(f"\n{BLUE}{BOLD}🔑 Authentication & Token Setup (for Agents & Skills):{RESET}")
    print(f"  A template file has been generated at: {CYAN}.env.example{RESET}")
    print(f"  To enable autonomous skills (ticket sync, issue onboarding, PR/MR creation):")
    print(f"    1. Copy template to local file: {CYAN}cp .env.example .env.local{RESET}  {DIM}(ignored by git){RESET}")
    print(f"    2. Generate a Personal Access Token (PAT) with required permissions:")

    if cfg.tracker_type == "jira":
        print(f"\n  {BOLD}• Jira Cloud API Token:{RESET}")
        print(f"    - URL: {CYAN}https://id.atlassian.com/manage-profile/security/api-tokens{RESET}")
        print(f"    - Required scopes: {BOLD}read:jira-work{RESET}, {BOLD}write:jira-work{RESET}")
        print(f"    - Set in .env.local: {CYAN}JIRA_API_TOKEN{RESET}, {CYAN}JIRA_USER_EMAIL{RESET}, and {CYAN}JIRA_BASE_URL{RESET}")

    if cfg.tracker_type == "gitlab" or cfg.vcs_platform == "gitlab":
        print(f"\n  {BOLD}• GitLab Personal Access Token:{RESET}")
        print(f"    - URL: {CYAN}https://gitlab.com/-/user_settings/personal_access_tokens{RESET} (or self-hosted)")
        print(f"    - Required scopes: {BOLD}api{RESET} (or {BOLD}read_api{RESET} + {BOLD}write_repository{RESET})")
        print(f"    - Set in .env.local: {CYAN}GITLAB_TOKEN{RESET}, or authenticate CLI: {CYAN}glab auth login{RESET}")

    if cfg.tracker_type == "azure-devops" or cfg.vcs_platform == "azure-repos":
        print(f"\n  {BOLD}• Azure DevOps Personal Access Token:{RESET}")
        print(f"    - URL: User Settings -> Personal Access Tokens ({CYAN}https://dev.azure.com/{cfg.org}/_usersSettings/tokens{RESET})")
        print(f"    - Required scopes: {BOLD}Work Items (Read & write){RESET} and {BOLD}Code (Read & write){RESET}")
        print(f"    - Set in .env.local: {CYAN}AZURE_DEVOPS_EXT_PAT{RESET}, or authenticate CLI: {CYAN}az devops login{RESET}")

    if cfg.tracker_type == "github" or cfg.vcs_platform == "github":
        print(f"\n  {BOLD}• GitHub Personal Access Token:{RESET}")
        print(f"    - URL: {CYAN}https://github.com/settings/tokens{RESET}")
        print(f"    - Required scopes: {BOLD}repo{RESET} (or Fine-grained: Issues, Pull requests, Contents Read & Write)")
        print(f"    - Set in .env.local: {CYAN}GITHUB_TOKEN{RESET}, or authenticate CLI: {CYAN}gh auth login{RESET}")


def render_onboarding_primer(cfg: WorkspaceConfig, py_cmd: str = "python") -> str:
    """Render a tailored onboarding primer and first-steps guide after bootstrapping."""
    cadence_map = {
        "safe": ("Program Increment (PI 01)", "Goals -> Epics -> Stories"),
        "scrum": ("Sprint 01", "Epics -> Stories"),
        "shape-up": ("Cycle 01", "Pitches -> Scopes"),
        "kanban": ("Milestone 01", "Epics -> Tasks"),
    }
    cadence_label, hierarchy_label = cadence_map.get(
        cfg.planning_framework, ("Sprint 01", "Epics -> Stories")
    )

    onboard_skill_map = {
        "azure-devops": "ado-work-item-onboard",
        "jira": "jira-story-onboard",
        "github": "github-issue-onboard",
        "gitlab": "gitlab-issue-onboard",
    }
    onboard_skill = onboard_skill_map.get(cfg.tracker_type)

    sibling_names = [s.name for s in cfg.siblings]
    sibling_hint = (
        f"across {', '.join(sibling_names)}"
        if sibling_names
        else "across your configured repositories"
    )

    lines = [
        f"\n{CYAN}{BOLD}==================================================================={RESET}",
        f"{MAGENTA}{BOLD}  🚀 Quick Primer: Getting Full Advantage of {cfg.name}{RESET}",
        f"{CYAN}{BOLD}==================================================================={RESET}",
        f"  {BOLD}1. Verify & Open Your Unified Workspace:{RESET}",
        f"     • Clone sibling repos : {CYAN}{py_cmd} scripts/clone_siblings.py{RESET}",
        f"     • Health diagnostics  : {CYAN}{py_cmd} scripts/workspace_doctor.py{RESET}",
        f"     • Add repos anytime   : {CYAN}{py_cmd} bootstrap.py --add-sibling{RESET}",
        f"     • Open multi-root IDE : {CYAN}code {cfg.slug}.code-workspace{RESET}",
        "",
        f"  {BOLD}2. How the Two-Mode AI Workflow Operates (AGENTS.md):{RESET}",
        f"     • {GREEN}Plan Mode (Durable Context){RESET}: Never leave decisions trapped in chat.",
        f"       Author plans in {CYAN}docs/planning/01/{RESET} ({cadence_label}: {hierarchy_label})",
        f"       and record binding architecture choices in {CYAN}docs/adr/{RESET}.",
        f"     • {GREEN}Agent Mode (Execution){RESET}: Only execute items whose {BOLD}Definition of Ready{RESET}",
        f"       is {BOLD}Done{RESET} and Effort is {BOLD}Small/Medium{RESET}. Keep {CYAN}docs/architecture.md{RESET} and",
        f"       {CYAN}GLOSSARY.md{RESET} updated as system contracts evolve.",
        "",
        f"  {BOLD}3. Try These First Prompts in Your AI Assistant (Copilot / Claude / Cursor):{RESET}",
        f"     • {CYAN}\"Use planning-scaffold to create our first epic and story in docs/planning/01/\"{RESET}",
        f"     • {CYAN}\"Run story-refiner on docs/planning/01/ to check Definition of Ready and sizing\"{RESET}",
    ]
    if onboard_skill:
        lines.append(
            f"     • {CYAN}\"Use {onboard_skill} to sync the ready story to {cfg.tracker_type} with bidirectional links\"{RESET}"
        )
    lines.extend([
        f"     • {CYAN}\"Inspect the contracts {sibling_hint} and update docs/architecture.md\"{RESET}",
        f"     • {CYAN}\"Run consensus-check before we finalize this cross-repo API change\"{RESET}",
        f"     • {CYAN}\"Use pr-create to run DoD + consensus checks and open our PR/MR\"{RESET}",
        f"{CYAN}{BOLD}==================================================================={RESET}\n",
    ])
    return "\n".join(lines)


def generate_workspace(cfg: WorkspaceConfig, root: Path) -> None:
    print(f"\n{GREEN}{BOLD}Scaffolding workspace in: {root}{RESET}")
    
    # 1. Prepare template context variables
    siblings_agents_md = ""
    for s in cfg.siblings:
        siblings_agents_md += f"### `{s.name}`\n- **URL**: `{s.url}`\n- **Role**: {s.role}\n- **Access Mode**: {s.access}\n\n"

    code_workspace_entries = ""
    for s in cfg.siblings:
        code_workspace_entries += f',\n    {{\n      "name": "{s.name}",\n      "path": "../{s.name}"\n    }}'

    siblings_yaml_lines = []
    if cfg.siblings:
        for s in cfg.siblings:
            siblings_yaml_lines += [
                f"  - name: {yaml_quote(s.name)}",
                f"    url: {yaml_quote(s.url)}",
                f"    role: {yaml_quote(s.role)}",
                f"    access: {yaml_quote(s.access)}",
            ]
    else:
        siblings_yaml_lines.append("  []")
    siblings_yaml_list = "\n".join(siblings_yaml_lines)

    context = {
        "WORKSPACE_NAME": cfg.name,
        "WORKSPACE_SLUG": cfg.slug,
        "WORKSPACE_DESC": cfg.description,
        "ORGANIZATION": cfg.org,
        "PLANNING_FRAMEWORK": cfg.planning_framework,
        "PLANNING_FRAMEWORK_NAME": cfg.planning_framework.upper(),
        "CADENCE_DURATION": cfg.cadence_duration,
        "SPRINT_DURATION": cfg.cadence_duration,
        "TRACKER_TYPE": cfg.tracker_type,
        "TRACKER_NAME": cfg.tracker_type.capitalize(),
        "TRACKER_BASE_URL": cfg.tracker_base_url,
        "TRACKER_PROJECT_KEY": cfg.tracker_project_key,
        "VCS_PLATFORM": cfg.vcs_platform,
        "SIBLING_REPOS_SECTION": siblings_agents_md or "*(No sibling repositories configured yet)*",
        "CODE_WORKSPACE_SIBLINGS": code_workspace_entries,
        "SIBLINGS_YAML_LIST": siblings_yaml_list,
    }

    # 2. Render core directive files
    def render_file(src_name: str, dest_name: str):
        src = root / src_name
        dest = root / dest_name
        if src.is_file():
            content = src.read_text(encoding="utf-8")
            rendered = render_template_str(content, context)
            dest.write_text(rendered, encoding="utf-8")
            print(f"  ✔ Created {dest_name}")

    render_file("AGENTS.md.template", "AGENTS.md")
    render_file("GLOSSARY.md.template", "GLOSSARY.md")
    render_file("workspace.code-workspace.template", f"{cfg.slug}.code-workspace")
    (root / "workspace.yaml").write_text(render_workspace_config(cfg), encoding="utf-8")
    print("  Created workspace.yaml")
    
    if cfg.claude:
        render_file("CLAUDE.md.template", "CLAUDE.md")
    if cfg.cursor:
        render_file(".cursorrules.template", ".cursorrules")
    if cfg.copilot:
        copilot_dir = root / ".github"
        copilot_dir.mkdir(exist_ok=True)
        render_file(".github/copilot-instructions.md.template", ".github/copilot-instructions.md")

    # 3. Setup planning directory from chosen framework template
    planning_dir = root / "docs" / "planning"
    template_dir = planning_dir / "templates"
    
    framework_map = {
        "safe": "pi-template",
        "scrum": "sprint-template",
        "shape-up": "cycle-template",
        "kanban": "kanban-template",
    }
    chosen_template = framework_map.get(cfg.planning_framework, "sprint-template")
    source_template_dir = template_dir / chosen_template
    
    first_timebox_dir = planning_dir / "01"
    if source_template_dir.is_dir() and not first_timebox_dir.exists():
        shutil.copytree(source_template_dir, first_timebox_dir)
        print(f"  ✔ Initialized first delivery increment: docs/planning/01/")

    # 4. Generate a cross-platform sibling clone utility.
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    clone_script = scripts_dir / "clone_siblings.py"
    clone_script.write_text(clone_siblings_script(), encoding="utf-8")
    (scripts_dir / "siblings.json").write_text(
        json.dumps([s.__dict__ for s in cfg.siblings], indent=2) + "\n",
        encoding="utf-8",
    )
    print("  Created scripts/clone_siblings.py")

    # 5. Generate .env.example with credential instructions and required permissions
    env_example = root / ".env.example"
    env_example.write_text(render_env_example(cfg), encoding="utf-8")
    print("  ✔ Created .env.example (template for local authentication tokens)")

    # 6. Prune irrelevant skill directories if requested
    skills_dir = root / ".github" / "skills"
    if skills_dir.is_dir():
        if cfg.tracker_type != "jira":
            for d in ("jira-story-onboard", "jira-status-sync"):
                p = skills_dir / d
                if p.exists():
                    shutil.rmtree(p)
        if cfg.tracker_type != "github":
            for d in ("github-issue-onboard", "github-status-sync"):
                p = skills_dir / d
                if p.exists():
                    shutil.rmtree(p)
        if cfg.tracker_type != "gitlab":
            p = skills_dir / "gitlab-issue-onboard"
            if p.exists():
                shutil.rmtree(p)
        if cfg.tracker_type != "azure-devops":
            p = skills_dir / "ado-work-item-onboard"
            if p.exists():
                shutil.rmtree(p)

        # Keep .github/skills/README.md and AGENTS.md skill routing synchronized with retained skills
        active_skill_names = {
            entry.name
            for entry in skills_dir.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        }
        skills_readme = skills_dir / "README.md"
        if skills_readme.is_file():
            filtered_lines = []
            for line in skills_readme.read_text(encoding="utf-8").splitlines():
                m_skill = re.search(r"\[([A-Za-z0-9_.-]+)\]\(\1/SKILL\.md\)", line)
                if m_skill and m_skill.group(1) not in active_skill_names:
                    continue
                filtered_lines.append(line)
            skills_readme.write_text("\n".join(filtered_lines) + "\n", encoding="utf-8")

        # Update .github/skills/harness2/profiles.json with workspace slug and active siblings
        profiles_path = skills_dir / "harness2" / "profiles.json"
        if profiles_path.is_file():
            try:
                profiles_data = json.loads(profiles_path.read_text(encoding="utf-8"))
                repos_map = profiles_data.setdefault("repositories", {})
                default_spec = repos_map.get("saiga-cart") or {
                    "domain": "Workspace planning, skills, and governance",
                    "default_verifier": "python3 .github/skills/harness2/scripts/validate_harness.py && python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py",
                    "verifier_paths": [
                        ".github/skills/harness2/scripts/validate_harness.py",
                        ".github/skills/planning-docs-audit/scripts/planning_docs_audit.py",
                    ],
                    "inv_levers": [
                        "Verify AGENTS.md budget, skill frontmatter, and README index parity.",
                        "Verify story metadata, Status vocabulary, and progress.md links.",
                    ],
                    "dom_levers": [
                        "Keep deterministic checks in stdlib-only Python scripts with unittest coverage.",
                        "Keep instructions concise and aligned with ASD-STE100 plain-language rules.",
                    ],
                }
                repos_map[cfg.slug] = default_spec
                for s in cfg.siblings:
                    if s.access != "read-only" and s.name not in repos_map:
                        repos_map[s.name] = {
                            "domain": s.role or f"Sibling repository {s.name}",
                            "default_verifier": "git status -sb",
                            "verifier_paths": ["README.md"],
                            "inv_levers": [
                                f"Preserve cross-repository contracts with {cfg.slug}.",
                                "Verify API/schema backward compatibility and error handling.",
                            ],
                            "dom_levers": [
                                f"Follow idiomatic module boundaries and existing test patterns in {s.name}.",
                                "Run targeted unit tests before proposing cross-repo changes.",
                            ],
                        }
                profiles_path.write_text(json.dumps(profiles_data, indent=2) + "\n", encoding="utf-8")
            except Exception:
                pass

    print(f"\n{GREEN}{BOLD}🎉 Workspace successfully bootstrapped!{RESET}")
    print_token_setup_instructions(cfg)
    print(render_onboarding_primer(cfg, Path(sys.executable).name))


def prepare_output_directory(source: Path, target: Path) -> Path:
    """Seed an empty standalone target from the template repository."""
    source = source.resolve()
    target = target.resolve()
    if target == source:
        return target
    if target.exists() and any(target.iterdir()):
        raise ValueError(
            f"Output directory must be empty for standalone generation: {target}"
        )
    if target.exists():
        target.rmdir()
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
    )
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a saiga-cart AI Workspace.")
    parser.add_argument("--config", type=Path, help="Path to existing workspace.yaml / config file")
    parser.add_argument("--output", type=Path, default=Path.cwd(), help="Target directory")
    parser.add_argument("--non-interactive", action="store_true", help="Run without prompts using defaults/presets")
    parser.add_argument(
        "--add-sibling",
        action="store_true",
        help="Interactively add and verify sibling repositories on an existing workspace.yaml",
    )
    parser.add_argument(
        "--preset",
        choices=["github-scrum", "jira-safe", "ado-scrum", "azure-devops"],
        help="Preset configuration",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print_banner()

    target_dir = args.output.resolve()

    if args.add_sibling:
        ws_path = args.config.resolve() if args.config else (target_dir / "workspace.yaml")
        if not ws_path.is_file():
            print(f"{YELLOW}ERROR: Cannot find workspace.yaml at {ws_path}. Run bootstrap.py first.{RESET}", file=sys.stderr)
            raise SystemExit(2)
        try:
            cfg = load_workspace_config(ws_path)
        except (ValueError, FileNotFoundError) as error:
            print(f"{YELLOW}ERROR loading config: {error}{RESET}", file=sys.stderr)
            raise SystemExit(2)
        load_env_files(ws_path.parent)
        run_interactive_auth_setup(cfg, ws_path.parent)
        print(f"\n{BLUE}{BOLD}--- Add Sibling Repositories ---{RESET}")
        cfg.siblings = prompt_and_verify_siblings(cfg)
        generate_workspace(cfg, ws_path.parent)
        if cfg.siblings and sys.stdin.isatty() and prompt_bool("Clone newly configured sibling repositories now?", True):
            subprocess.run([sys.executable, str(ws_path.parent / "scripts" / "clone_siblings.py")], check=False)
        return

    try:
        output = prepare_output_directory(Path(__file__).resolve().parent, target_dir)
    except ValueError as error:
        print(f"{YELLOW}ERROR: {error}{RESET}", file=sys.stderr)
        raise SystemExit(2)

    cfg: WorkspaceConfig
    is_interactive = False
    if args.config:
        config_path = args.config.resolve()
        try:
            cfg = load_workspace_config(config_path)
        except (ValueError, FileNotFoundError) as error:
            print(f"{YELLOW}ERROR loading config: {error}{RESET}", file=sys.stderr)
            raise SystemExit(2)
    elif args.preset == "github-scrum" or (args.non_interactive and not args.preset):
        cfg = WorkspaceConfig(
            name="Acme GitHub Scrum Workspace",
            slug="acme-workspace",
            planning_framework="scrum",
            cadence_duration="2 weeks",
            tracker_type="github",
            vcs_platform="github",
        )
    elif args.preset == "jira-safe":
        cfg = WorkspaceConfig(
            name="Acme Enterprise SAFe Workspace",
            slug="acme-enterprise",
            planning_framework="safe",
            cadence_duration="8 weeks",
            tracker_type="jira",
            vcs_platform="gitlab",
        )
    elif args.preset in ("ado-scrum", "azure-devops"):
        cfg = WorkspaceConfig(
            name="Acme Azure DevOps Workspace",
            slug="acme-ado-workspace",
            planning_framework="scrum",
            cadence_duration="2 weeks",
            tracker_type="azure-devops",
            tracker_base_url="https://dev.azure.com/acme-org",
            tracker_project_key="ACME",
            vcs_platform="azure-repos",
        )
    else:
        is_interactive = True
        cfg = run_interactive_wizard(output)

    generate_workspace(cfg, output)

    if is_interactive and cfg.siblings and sys.stdin.isatty():
        if prompt_bool("Clone configured sibling repositories now?", True):
            subprocess.run([sys.executable, str(output / "scripts" / "clone_siblings.py")], check=False)


if __name__ == "__main__":
    main()
