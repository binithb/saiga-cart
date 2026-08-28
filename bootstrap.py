#!/usr/bin/env python3
"""Interactive Bootstrapper & Workspace Generator for saiga-cart.

Scaffolds a customized, AI-native multi-repo workspace based on your
planning framework (SAFe PIs, Scrum Sprints, Shape Up, Kanban), issue tracker
(Jira, GitHub, GitLab, Azure DevOps), and AI tool preferences.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
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


def run_interactive_wizard() -> WorkspaceConfig:
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
    elif cfg.tracker_type == "github":
        cfg.tracker_base_url = prompt_text("GitHub Repository / Project URL", f"https://github.com/{cfg.org}/main-repo")
    elif cfg.tracker_type == "gitlab":
        cfg.tracker_base_url = prompt_text("GitLab Group / Project URL", f"https://gitlab.com/{cfg.org}/main-repo")
    elif cfg.tracker_type == "azure-devops":
        cfg.tracker_base_url = prompt_text("Azure DevOps Project URL", f"https://dev.azure.com/{cfg.org}/project")

    print(f"\n{BLUE}{BOLD}--- Section 4: Version Control & Code Reviews ---{RESET}")
    vcs_choices = [
        ("github", "GitHub (Pull Requests, GitHub Actions)"),
        ("gitlab", "GitLab (Merge Requests, GitLab CI)"),
        ("azure-repos", "Azure Repos"),
        ("bitbucket", "Bitbucket"),
    ]
    cfg.vcs_platform = prompt_choice("Version Control Platform", vcs_choices, "github" if cfg.tracker_type == "github" else "gitlab")
    cfg.consensus_review_enabled = prompt_bool("Enable Multi-Model Consensus Review Gate (consensus-check)?", True)
    cfg.dod_gate_enabled = prompt_bool("Enable Definition-of-Done Pre-Flight Check (pr-readiness-check)?", True)

    print(f"\n{BLUE}{BOLD}--- Section 5: Multi-Repo Sibling Repositories ---{RESET}")
    print(f"{DIM}Define sibling repositories to include in this unified multi-root workspace.{RESET}")
    
    add_sample = prompt_bool("Add example sibling repositories to start?", True)
    if add_sample:
        cfg.siblings.append(SiblingRepo(
            name="core-service",
            url=f"git@{cfg.vcs_platform}.com:{cfg.org}/core-service.git",
            role="Core backend microservice and API",
            access="active"
        ))
        cfg.siblings.append(SiblingRepo(
            name="infra-platform",
            url=f"git@{cfg.vcs_platform}.com:{cfg.org}/infra-platform.git",
            role="Terraform infrastructure, Helm charts, and CI pipelines",
            access="active"
        ))

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

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    workspace = Path(__file__).resolve().parents[1]
    manifest = Path(__file__).with_name("siblings.json")
    siblings = json.loads(manifest.read_text(encoding="utf-8"))
    for sibling in siblings:
        destination = workspace.parent / sibling["name"]
        if destination.exists():
            print(f"OK {sibling['name']} already exists at {destination}; skipping")
            continue
        print(f"Cloning {sibling['name']} into {destination}")
        try:
            subprocess.run(
                ["git", "clone", sibling["url"], str(destination)],
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

    # 5. Prune irrelevant skill directories if requested
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

    print(f"\n{GREEN}{BOLD}🎉 Workspace successfully bootstrapped!{RESET}")
    print(f"\nNext steps:")
    print(f"  1. Run {CYAN}{Path(sys.executable).name} scripts/clone_siblings.py{RESET} to checkout sibling repos.")
    print(f"  2. Open the multi-root workspace: {CYAN}code {cfg.slug}.code-workspace{RESET}")
    print(f"  3. Run diagnostics: {CYAN}{Path(sys.executable).name} scripts/workspace_doctor.py{RESET}\n")


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
        "--preset",
        choices=["github-scrum", "jira-safe", "ado-scrum", "azure-devops"],
        help="Preset configuration",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print_banner()

    cfg: WorkspaceConfig
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
        cfg = run_interactive_wizard()

    try:
        output = prepare_output_directory(Path(__file__).resolve().parent, args.output)
    except ValueError as error:
        print(f"{YELLOW}ERROR: {error}{RESET}", file=sys.stderr)
        raise SystemExit(2)

    generate_workspace(cfg, output)


if __name__ == "__main__":
    main()
