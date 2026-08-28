#!/usr/bin/env python3
"""Workspace Doctor: Diagnostic & Environment Verification Utility."""

import json
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


def run_diagnostics(root: Path) -> int:
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
