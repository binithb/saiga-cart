#!/usr/bin/env python3
"""Validate a saiga-cart workspace's Harness² surface, budgets, skills, scripts, and governance zones."""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote


DEFAULT_MAX_AGENTS_CHARS = 14000
DEFAULT_MAX_CORE_CHARS = 55000
DEFAULT_MAX_EXPERIENCE_CHARS = 12000
DEFAULT_MAX_SIBLING_AGENTS_CHARS = 8000

RED_ZONE_PATTERNS = (
    "AGENTS.md",
    "AGENTS.md.template",
    "docs/workflow.md",
    "docs/architecture.md",
    "docs/adr/*",
    "docs/ai/adr/*",
    "docs/ai/wow-adr/*",
    ".gitlab-ci.yml",
    ".github/workflows/*",
)

GREEN_ZONE_PATTERNS = (
    ".github/skills/*",
    "scripts/*",
    "docs/ai/experience.md",
)

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PYTHON_REF_RE = re.compile(
    r"(?:python3?(?:\s+-[A-Za-z]+)*\s+)((?:\.github/skills/[A-Za-z0-9_.-]+/scripts/|scripts/)[A-Za-z0-9_.-]+\.py)\b"
)
HARDCODED_HOME_RE = re.compile(r"/home/[A-Za-z0-9_.-]+/")
JIRA_MUTATING_SCRIPT_RE = re.compile(
    r"\b(?:jira_create_issue\.py|jira_log_work\.py|jira_remote_links\.py\s+[^\n]*(?:--add|--delete))\b"
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str


class HarnessValidator:
    def __init__(
        self,
        root: Path,
        *,
        max_agents_chars: int = DEFAULT_MAX_AGENTS_CHARS,
        max_core_chars: int = DEFAULT_MAX_CORE_CHARS,
        max_experience_chars: int = DEFAULT_MAX_EXPERIENCE_CHARS,
        max_sibling_agents_chars: int = DEFAULT_MAX_SIBLING_AGENTS_CHARS,
        check_siblings: bool = False,
        check_pi_compaction: bool = False,
        check_zones: bool = False,
        base_ref: str | None = None,
        sibling_repos: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.max_agents_chars = max_agents_chars
        self.max_core_chars = max_core_chars
        self.max_experience_chars = max_experience_chars
        self.max_sibling_agents_chars = max_sibling_agents_chars
        self.check_siblings = check_siblings
        self.check_pi_compaction = check_pi_compaction
        self.check_zones = check_zones
        self.base_ref = base_ref or os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA") or "HEAD"
        self.sibling_repos: tuple[str, ...] = (
            tuple(sibling_repos) if sibling_repos is not None else self._discover_siblings()
        )
        self.workspace_slug: str = self._discover_workspace_slug()
        self.findings: list[Finding] = []
        self.metrics: dict[str, object] = {}

    def _discover_workspace_slug(self) -> str:
        ws_yaml = self.root / "workspace.yaml"
        if ws_yaml.is_file():
            for line in ws_yaml.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("slug:"):
                    val = stripped.split(":", 1)[1].strip().strip("'\"")
                    if val and "{{" not in val:
                        return val
        return self.root.name

    def _discover_siblings(self) -> tuple[str, ...]:
        manifest = self.root / "scripts" / "siblings.json"
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return tuple(
                        str(item["name"])
                        for item in data
                        if isinstance(item, dict)
                        and item.get("name")
                        and item.get("access", "active") != "read-only"
                    )
            except Exception:
                pass
        return ()

    def _resolve_agents_file(self) -> Path:
        agents_md = self.root / "AGENTS.md"
        if agents_md.is_file():
            return agents_md
        agents_tmpl = self.root / "AGENTS.md.template"
        if agents_tmpl.is_file():
            return agents_tmpl
        return agents_md

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            try:
                return path.resolve().relative_to(self.root.parent).as_posix()
            except ValueError:
                return path.as_posix()

    def add(self, severity: str, code: str, path: Path, message: str) -> None:
        self.findings.append(Finding(severity, code, self.relative(path), message))

    def validate(self) -> list[Finding]:
        self.audit_context_budgets()
        self.audit_skills()
        self.audit_profiles()
        self.audit_scripts_and_references()
        self.audit_experience_ledger()
        self.audit_wow_adr_index()
        if self.check_zones:
            self.audit_zones_and_frozen_verifiers()
        if self.check_pi_compaction:
            self.audit_closed_pi_compaction()
        if self.check_siblings:
            self.audit_sibling_pointers()
        return sorted(
            self.findings,
            key=lambda item: (
                0 if item.severity == "ERROR" else 1 if item.severity == "WARNING" else 2,
                item.path,
                item.code,
                item.message,
            ),
        )

    def audit_context_budgets(self) -> None:
        agents_md = self._resolve_agents_file()
        workflow_md = self.root / "docs" / "workflow.md"
        architecture_md = self.root / "docs" / "architecture.md"

        if not agents_md.is_file():
            self.add("ERROR", "AGENTS_MISSING", self.root / "AGENTS.md", "AGENTS.md does not exist")
            return

        agents_text = agents_md.read_text(encoding="utf-8")
        agents_chars = len(agents_text)
        self.metrics["agents_md_chars"] = agents_chars
        self.metrics["agents_md_budget"] = self.max_agents_chars

        if agents_chars == 0:
            self.add("ERROR", "AGENTS_EMPTY", agents_md, f"{agents_md.name} is empty")
        elif agents_chars > self.max_agents_chars:
            self.add(
                "ERROR",
                "AGENTS_BUDGET_EXCEEDED",
                agents_md,
                f"{agents_md.name} is {agents_chars} chars (exceeds max budget of {self.max_agents_chars} chars); graduate prose to skills or scripts",
            )

        core_chars = agents_chars
        for doc in (workflow_md, architecture_md):
            if doc.is_file():
                core_chars += len(doc.read_text(encoding="utf-8"))
            else:
                self.add("ERROR", "CORE_DOC_MISSING", doc, f"Required core document is missing: {self.relative(doc)}")

        self.metrics["core_surface_chars"] = core_chars
        self.metrics["core_surface_budget"] = self.max_core_chars
        if core_chars > self.max_core_chars:
            self.add(
                "ERROR",
                "CORE_BUDGET_EXCEEDED",
                agents_md,
                f"Combined core surface ({agents_md.name} + workflow.md + architecture.md) is {core_chars} chars (exceeds {self.max_core_chars})",
            )

    def audit_skills(self) -> None:
        skills_root = self.root / ".github" / "skills"
        skills_readme = skills_root / "README.md"
        agents_md = self._resolve_agents_file()

        if not skills_root.is_dir():
            self.add("ERROR", "SKILLS_DIR_MISSING", skills_root, ".github/skills directory does not exist")
            return
        if not skills_readme.is_file():
            self.add("ERROR", "SKILLS_INDEX_MISSING", skills_readme, ".github/skills/README.md does not exist")
            return

        readme_text = skills_readme.read_text(encoding="utf-8")
        agents_text = agents_md.read_text(encoding="utf-8") if agents_md.is_file() else ""

        skill_count = 0
        for entry in sorted(skills_root.iterdir()):
            if entry.name == "README.md" or entry.name.startswith("."):
                continue
            if entry.is_symlink() and not entry.exists():
                self.add("ERROR", "SKILL_BROKEN_SYMLINK", entry, f"Broken symlink in .github/skills: {entry.name}")
                continue
            if not entry.is_dir():
                continue

            skill_md = entry / "SKILL.md"
            if skill_md.is_symlink() and not skill_md.exists():
                self.add("ERROR", "SKILL_BROKEN_SYMLINK", skill_md, f"Broken SKILL.md symlink in {entry.name}")
                continue
            if not skill_md.is_file():
                self.add("ERROR", "SKILL_MD_MISSING", entry, f"Skill directory {entry.name} is missing SKILL.md")
                continue

            skill_count += 1
            text = skill_md.read_text(encoding="utf-8")
            frontmatter = self.parse_frontmatter(text)
            if frontmatter is None:
                self.add("ERROR", "SKILL_FRONTMATTER_MISSING", skill_md, "SKILL.md is missing YAML frontmatter (--- ... ---)")
            else:
                name_val = frontmatter.get("name", "").strip()
                desc_val = frontmatter.get("description", "").strip()
                if name_val != entry.name:
                    self.add(
                        "ERROR",
                        "SKILL_NAME_MISMATCH",
                        skill_md,
                        f"SKILL.md frontmatter name {name_val!r} does not match directory {entry.name!r}",
                    )
                if not desc_val:
                    self.add("ERROR", "SKILL_DESCRIPTION_EMPTY", skill_md, "SKILL.md frontmatter description is empty")

            expected_link = f"{entry.name}/SKILL.md"
            if expected_link not in readme_text:
                self.add(
                    "ERROR",
                    "SKILL_UNINDEXED",
                    skills_readme,
                    f"Skill {entry.name!r} is not linked in .github/skills/README.md ({expected_link})",
                )
            if agents_text and entry.name not in agents_text:
                desc_summary = (frontmatter.get("description", "").strip() if frontmatter else "") or "on-demand skill"
                suggested_line = f"- Use `{entry.name}` — {desc_summary}"
                self.add(
                    "WARNING",
                    "SKILL_UNROUTED_IN_AGENTS",
                    agents_md,
                    f"Skill {entry.name!r} is not mentioned in {agents_md.name} routing rules (propose via h2 distill: {suggested_line})",
                )

        self.metrics["skills_count"] = skill_count

    def audit_profiles(self) -> None:
        harness_dir = self.root / ".github" / "skills" / "harness2"
        profiles_path = harness_dir / "profiles.json"
        if not harness_dir.is_dir() and not profiles_path.exists():
            return
        if not profiles_path.is_file():
            self.add(
                "ERROR",
                "PROFILES_MISSING",
                profiles_path,
                "Harness² multi-repo INV/DOM profile file (.github/skills/harness2/profiles.json) is missing",
            )
            return

        try:
            payload = json.loads(profiles_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.add("ERROR", "PROFILES_INVALID_JSON", profiles_path, f"Invalid JSON in profiles.json: {exc}")
            return

        repos = payload.get("repositories")
        if not isinstance(repos, dict):
            self.add("ERROR", "PROFILES_SCHEMA_ERROR", profiles_path, "profiles.json must define a 'repositories' object")
            return

        primary_repo_key = self.workspace_slug
        if primary_repo_key not in repos and "saiga-cart" in repos:
            primary_repo_key = "saiga-cart"

        expected_repos = (primary_repo_key, *self.sibling_repos)
        for repo_name in expected_repos:
            spec = repos.get(repo_name)
            if not isinstance(spec, dict):
                self.add(
                    "ERROR",
                    "PROFILE_REPO_MISSING",
                    profiles_path,
                    f"profiles.json is missing DomainSpec entry for repository {repo_name!r}",
                )
                continue
            for str_key in ("domain", "default_verifier"):
                val = spec.get(str_key)
                if not isinstance(val, str) or not val.strip():
                    self.add(
                        "ERROR",
                        "PROFILE_FIELD_INVALID",
                        profiles_path,
                        f"profiles.json[{repo_name!r}].{str_key} must be a non-empty string",
                    )
            for list_key in ("inv_levers", "dom_levers", "verifier_paths"):
                items = spec.get(list_key)
                min_len = 1 if list_key == "verifier_paths" else 2
                if (
                    not isinstance(items, list)
                    or len(items) < min_len
                    or not all(isinstance(x, str) and x.strip() for x in items)
                ):
                    self.add(
                        "ERROR",
                        "PROFILE_FIELD_INVALID",
                        profiles_path,
                        f"profiles.json[{repo_name!r}].{list_key} must be a list of at least {min_len} non-empty string(s)",
                    )

            verifier_paths = spec.get("verifier_paths")
            if isinstance(verifier_paths, list):
                is_self = repo_name in (self.workspace_slug, self.root.name, "saiga-cart")
                repo_root = self.root if is_self else (self.root.parent / repo_name)
                should_check_disk = is_self or (self.check_siblings and repo_root.is_dir())
                if should_check_disk:
                    for rel_p in verifier_paths:
                        if isinstance(rel_p, str) and not (repo_root / rel_p).exists():
                            self.add(
                                "ERROR",
                                "PROFILE_VERIFIER_PATH_MISSING",
                                profiles_path,
                                f"profiles.json[{repo_name!r}] verifier_path does not exist on disk: {repo_name}/{rel_p}",
                            )

        self.metrics["profiled_repos_count"] = len(repos)

    def audit_scripts_and_references(self) -> None:
        script_files: list[Path] = []
        root_scripts = self.root / "scripts"
        if root_scripts.is_dir():
            script_files.extend(sorted(root_scripts.rglob("*.py")))
        skills_root = self.root / ".github" / "skills"
        if skills_root.is_dir():
            script_files.extend(sorted(skills_root.glob("*/scripts/*.py")))

        compiled_count = 0
        for script in script_files:
            if script.is_symlink() and not script.exists():
                self.add("ERROR", "SCRIPT_BROKEN_SYMLINK", script, "Script is a broken symlink")
                continue
            source = script.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(script))
                compiled_count += 1
            except SyntaxError as exc:
                self.add("ERROR", "SCRIPT_SYNTAX_ERROR", script, f"SyntaxError at line {exc.lineno}: {exc.msg}")
                continue

            # Check for hardcoded /home/<user>/ workstation paths in executable AST nodes (excluding docstrings)
            if not script.name.startswith("test_"):
                docstring_ids = self.collect_docstring_node_ids(tree)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstring_ids:
                        if HARDCODED_HOME_RE.search(node.value):
                            self.add(
                                "ERROR",
                                "SCRIPT_HARDCODED_HOME_PATH",
                                script,
                                f"line {getattr(node, 'lineno', '?')}: hardcoded workstation path detected ({node.value.strip()})",
                            )

        self.metrics["compiled_scripts_count"] = compiled_count

        # Verify script references in AGENTS.md, CI workflows, and SKILL.md files
        docs_to_scan: list[Path] = []
        agents_md = self._resolve_agents_file()
        if agents_md.is_file():
            docs_to_scan.append(agents_md)
        gitlab_ci = self.root / ".gitlab-ci.yml"
        if gitlab_ci.is_file():
            docs_to_scan.append(gitlab_ci)
        workflows_dir = self.root / ".github" / "workflows"
        if workflows_dir.is_dir():
            docs_to_scan.extend(sorted(workflows_dir.glob("*.yml")))
        if skills_root.is_dir():
            docs_to_scan.extend(sorted(skills_root.glob("*/SKILL.md")))

        for doc in docs_to_scan:
            text = doc.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "docker run" in line:
                    continue
                for match in PYTHON_REF_RE.finditer(line):
                    rel_script = match.group(1)
                    if "<" in rel_script or ">" in rel_script or "*" in rel_script:
                        continue
                    target = self.root / rel_script
                    if not target.is_file():
                        self.add(
                            "ERROR",
                            "BROKEN_SCRIPT_REFERENCE",
                            doc,
                            f"Referenced Python script does not exist: {rel_script}",
                        )

            if doc.name == "SKILL.md" and JIRA_MUTATING_SCRIPT_RE.search(text):
                if "--confirm" not in text or ("ask_user" not in text and "user confirmation" not in text.lower()):
                    self.add(
                        "ERROR",
                        "UNCONFIRMED_JIRA_MUTATION_SKILL",
                        doc,
                        "Skill references a mutating Jira script without requiring human confirmation (ask_user) and --confirm",
                    )

    def audit_experience_ledger(self) -> None:
        exp_path = self.root / "docs" / "ai" / "experience.md"
        if not exp_path.is_file():
            self.add("ERROR", "EXPERIENCE_LEDGER_MISSING", exp_path, "docs/ai/experience.md does not exist")
            return

        text = exp_path.read_text(encoding="utf-8")
        exp_chars = len(text)
        self.metrics["experience_md_chars"] = exp_chars
        self.metrics["experience_md_budget"] = self.max_experience_chars

        if exp_chars > self.max_experience_chars:
            self.add(
                "ERROR",
                "EXPERIENCE_BUDGET_EXCEEDED",
                exp_path,
                f"docs/ai/experience.md is {exp_chars} chars (exceeds {self.max_experience_chars} chars); prune graduated entries",
            )

        rows = [
            line
            for line in text.splitlines()
            if line.strip().startswith("|") and "`EXP-" in line
        ]
        self.metrics["experience_entries_count"] = len(rows)

    def audit_wow_adr_index(self) -> None:
        for adr_rel, prefix in (
            ("docs/ai/wow-adr", "WOW_ADR"),
            ("docs/adr", "ADR"),
        ):
            adr_root = self.root / adr_rel
            if not adr_root.is_dir():
                continue
            index = adr_root / "README.md"
            if not index.is_file():
                self.add("ERROR", f"{prefix}_INDEX_MISSING", index, f"{adr_rel}/README.md does not exist")
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
                    self.add("ERROR", "WOW_ADR_UNINDEXED", adr, f"ADR is missing from {adr_rel}/README.md")
                elif count > 1:
                    self.add("WARNING", "WOW_ADR_DUPLICATE_INDEX", index, f"ADR appears {count} times in index: {adr.name}")

            for document in sorted(adr_root.glob("*.md")):
                for line_no, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
                    for raw_target in LINK_RE.findall(line):
                        target_text = self.clean_link_target(raw_target)
                        if not target_text or self.is_external_link(target_text):
                            continue
                        target = (document.parent / target_text).resolve()
                        if not target.exists():
                            self.add(
                                "ERROR",
                                "WOW_ADR_BROKEN_LINK",
                                document,
                                f"line {line_no}: local link does not resolve: {target_text}",
                            )

    def audit_zones_and_frozen_verifiers(self) -> None:
        touched_paths: set[str] = set()
        try:
            proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                for raw_line in proc.stdout.splitlines():
                    if len(raw_line) < 4:
                        continue
                    path_part = raw_line[3:].strip()
                    if " -> " in path_part:
                        path_part = path_part.split(" -> ", 1)[1].strip()
                    touched_paths.add(path_part)

            if self.base_ref and self.base_ref != "HEAD":
                diff_names = subprocess.run(
                    ["git", "diff", "--name-only", self.base_ref],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if diff_names.returncode == 0:
                    for line in diff_names.stdout.splitlines():
                        if line.strip():
                            touched_paths.add(line.strip())
        except OSError:
            return

        red_touched: list[str] = []
        green_touched: list[str] = []
        for path_part in sorted(touched_paths):
            zone = self.classify_zone(path_part)
            if zone == "RED":
                red_touched.append(path_part)
            elif zone == "GREEN":
                green_touched.append(path_part)

        self.metrics["red_zone_touched"] = red_touched
        self.metrics["green_zone_touched"] = green_touched

        # Check Frozen Verifier rule on CI workflow files if modified
        for ci_path in red_touched:
            if ci_path == ".gitlab-ci.yml" or fnmatch.fnmatch(ci_path, ".github/workflows/*.yml"):
                diff_proc = subprocess.run(
                    ["git", "diff", self.base_ref, "--", ci_path],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                removed_checks = [
                    line[1:].strip()
                    for line in diff_proc.stdout.splitlines()
                    if line.startswith("-")
                    and not line.startswith("---")
                    and (
                        "unittest" in line
                        or "pi_docs_audit.py" in line
                        or "planning_docs_audit.py" in line
                        or "validate_harness.py" in line
                    )
                ]
                added_checks = [
                    line[1:].strip()
                    for line in diff_proc.stdout.splitlines()
                    if line.startswith("+")
                    and not line.startswith("+++")
                    and (
                        "unittest" in line
                        or "pi_docs_audit.py" in line
                        or "planning_docs_audit.py" in line
                        or "validate_harness.py" in line
                    )
                ]
                if len(removed_checks) > len(added_checks):
                    self.add(
                        "ERROR",
                        "FROZEN_VERIFIER_VIOLATION",
                        self.root / ci_path,
                        f"Verification command removed from {ci_path} without replacement (Frozen Verifier violation)",
                    )

        # Check Frozen Verifier rule on validator/test scripts
        for rel_path in green_touched:
            if fnmatch.fnmatch(rel_path, ".github/skills/*/scripts/*.py"):
                diff_proc = subprocess.run(
                    ["git", "diff", self.base_ref, "--", rel_path],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                removed_tests = [
                    line
                    for line in diff_proc.stdout.splitlines()
                    if line.startswith("-")
                    and not line.startswith("---")
                    and ("def test_" in line or "self.assert" in line)
                ]
                added_tests = [
                    line
                    for line in diff_proc.stdout.splitlines()
                    if line.startswith("+")
                    and not line.startswith("+++")
                    and ("def test_" in line or "self.assert" in line)
                ]
                if len(removed_tests) > len(added_tests):
                    self.add(
                        "ERROR",
                        "FROZEN_VERIFIER_VIOLATION",
                        self.root / rel_path,
                        f"Test assertions removed from {rel_path} without replacement (Frozen Verifier violation)",
                    )

    def audit_closed_pi_compaction(self) -> None:
        for plan_rel in ("docs/pi", "docs/planning"):
            pi_root = self.root / plan_rel
            readme = pi_root / "README.md"
            if not readme.is_file():
                continue

            closed_pis: list[str] = []
            for line in readme.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^\|\s*([^|]+?)\s*\|[^|]*\|\s*([^|]+?)\s*\|", line)
                if match and match.group(2).strip().lower() == "done":
                    scope_val = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", match.group(1)).strip()
                    if scope_val and not scope_val.startswith("-"):
                        closed_pis.append(scope_val)

            self.metrics["closed_pis"] = closed_pis
            for pi_num in closed_pis:
                pi_dir = pi_root / pi_num
                if not pi_dir.is_dir():
                    continue
                for scratchpad in sorted(pi_dir.rglob("backlog-scratchpad.txt")):
                    self.add(
                        "WARNING",
                        "CLOSED_PI_SCRATCHPAD",
                        scratchpad,
                        f"Closed timebox {pi_num} still contains uncompacted scratchpad file",
                    )
                for story in sorted(pi_dir.rglob("stories/*.md")):
                    status = self.parse_story_status(story.read_text(encoding="utf-8"))
                    if status and status != "Done":
                        self.add(
                            "WARNING",
                            "CLOSED_PI_UNFINISHED_STORY",
                            story,
                            f"Closed timebox {pi_num} contains story with Status={status!r} (expected 'Done')",
                        )

    def audit_sibling_pointers(self) -> None:
        sibling_status: dict[str, str] = {}
        workspace_root = self.root.parent
        for repo_name in self.sibling_repos:
            repo_dir = workspace_root / repo_name
            if not repo_dir.is_dir():
                sibling_status[repo_name] = "checkout_missing"
                continue
            sibling_agents = repo_dir / "AGENTS.md"
            if not sibling_agents.is_file():
                sibling_status[repo_name] = "missing_agents_md"
                self.add(
                    "WARNING",
                    "SIBLING_AGENTS_MISSING",
                    sibling_agents,
                    f"Sibling repository {repo_name} has no local AGENTS.md pointer",
                )
                continue
            text = sibling_agents.read_text(encoding="utf-8")
            char_len = len(text)
            sibling_status[repo_name] = f"present ({char_len} chars)"
            if char_len > self.max_sibling_agents_chars:
                self.add(
                    "WARNING",
                    "SIBLING_AGENTS_BLOATED",
                    sibling_agents,
                    f"Sibling {repo_name}/AGENTS.md is {char_len} chars (recommended thin pointer <= {self.max_sibling_agents_chars} chars)",
                )
            if self.workspace_slug not in text and self.root.name not in text:
                self.add(
                    "WARNING",
                    "SIBLING_AGENTS_NO_POINTER",
                    sibling_agents,
                    f"Sibling {repo_name}/AGENTS.md does not point back to {self.workspace_slug}",
                )
        self.metrics["sibling_agents_status"] = sibling_status

    @staticmethod
    def collect_docstring_node_ids(tree: ast.AST) -> set[int]:
        ids: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.body and isinstance(node.body[0], ast.Expr):
                    val = node.body[0].value
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        ids.add(id(val))
        return ids

    @staticmethod
    def classify_zone(rel_path: str) -> str:
        for pattern in RED_ZONE_PATTERNS:
            if fnmatch.fnmatch(rel_path, pattern):
                return "RED"
        for pattern in GREEN_ZONE_PATTERNS:
            if fnmatch.fnmatch(rel_path, pattern):
                return "GREEN"
        return "WORKSPACE"

    @staticmethod
    def parse_frontmatter(text: str) -> dict[str, str] | None:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return None
        end_idx = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_idx = idx
                break
        if end_idx is None:
            return None

        result: dict[str, str] = {}
        current_key: str | None = None
        for line in lines[1:end_idx]:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith((" ", "\t")) and ":" in line:
                key, raw_val = line.split(":", 1)
                current_key = key.strip()
                val = raw_val.strip().strip("'\"")
                result[current_key] = val
            elif current_key is not None:
                extra = line.strip()
                result[current_key] = (result[current_key] + " " + extra).strip()
        return result

    @staticmethod
    def parse_story_status(text: str) -> str | None:
        for line in text.splitlines():
            match = re.match(r"^\|\s*Status\s*\|\s*(.*?)\s*\|$", line)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def clean_link_target(raw_target: str) -> str:
        target = raw_target.strip().split("#", 1)[0]
        return unquote(target.split(' "', 1)[0].strip("<>"))

    @staticmethod
    def is_external_link(target: str) -> bool:
        return target.startswith(("http://", "https://", "mailto:", "tel:", "#"))


def default_root() -> Path:
    cwd = Path.cwd()
    if ((cwd / "AGENTS.md").is_file() or (cwd / "AGENTS.md.template").is_file()) and (
        cwd / ".github" / "skills"
    ).is_dir():
        return cwd
    return Path(__file__).resolve().parents[4]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root(), help="repository root")
    parser.add_argument(
        "--max-agents-chars",
        type=int,
        default=DEFAULT_MAX_AGENTS_CHARS,
        help=f"maximum character budget for AGENTS.md (default: {DEFAULT_MAX_AGENTS_CHARS})",
    )
    parser.add_argument(
        "--max-core-chars",
        type=int,
        default=DEFAULT_MAX_CORE_CHARS,
        help=f"maximum character budget for AGENTS.md + workflow.md + architecture.md (default: {DEFAULT_MAX_CORE_CHARS})",
    )
    parser.add_argument(
        "--max-experience-chars",
        type=int,
        default=DEFAULT_MAX_EXPERIENCE_CHARS,
        help=f"maximum character budget for docs/ai/experience.md (default: {DEFAULT_MAX_EXPERIENCE_CHARS})",
    )
    parser.add_argument(
        "--check-siblings",
        action="store_true",
        help="check sibling repositories for thin local AGENTS.md pointer files",
    )
    parser.add_argument(
        "--check-pi-compaction",
        action="store_true",
        help="check closed PIs/timeboxes in docs/planning/README.md for unfinished stories or scratchpads",
    )
    parser.add_argument(
        "--check-zones",
        action="store_true",
        help="classify dirty files into Red/Green zones and verify Frozen Verifier constraints",
    )
    parser.add_argument(
        "--base-ref",
        help="Git base ref for --check-zones diff comparison (defaults to $CI_MERGE_REQUEST_DIFF_BASE_SHA or HEAD)",
    )
    parser.add_argument("--json", action="store_true", help="emit findings and metrics as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validator = HarnessValidator(
        args.root,
        max_agents_chars=args.max_agents_chars,
        max_core_chars=args.max_core_chars,
        max_experience_chars=args.max_experience_chars,
        check_siblings=args.check_siblings,
        check_pi_compaction=args.check_pi_compaction,
        check_zones=args.check_zones,
        base_ref=args.base_ref,
    )
    findings = validator.validate()
    errors = [item for item in findings if item.severity == "ERROR"]
    warnings = [item for item in findings if item.severity == "WARNING"]

    if args.json:
        payload = {
            "ok": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "metrics": validator.metrics,
            "findings": [asdict(item) for item in findings],
        }
        print(json.dumps(payload, indent=2))
    else:
        agents_chars = validator.metrics.get("agents_md_chars", "?")
        agents_budget = validator.metrics.get("agents_md_budget", args.max_agents_chars)
        skills_count = validator.metrics.get("skills_count", 0)
        scripts_count = validator.metrics.get("compiled_scripts_count", 0)
        exp_count = validator.metrics.get("experience_entries_count", 0)
        print(
            f"Harness² audit: AGENTS.md={agents_chars}/{agents_budget} chars | "
            f"skills={skills_count} | scripts={scripts_count} | experience_entries={exp_count}"
        )
        for item in findings:
            print(f"{item.severity}: [{item.code}] {item.path}: {item.message}")
        if not findings:
            print("OK: 0 errors, 0 warnings.")
        else:
            print(f"Summary: {len(errors)} error(s), {len(warnings)} warning(s).")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
