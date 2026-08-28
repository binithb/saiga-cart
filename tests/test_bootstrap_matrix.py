#!/usr/bin/env python3
"""Integration tests for workspace bootstrapper across framework/tooling matrices."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestBootstrapMatrix(unittest.TestCase):
    def setUp(self):
        self.template_dir = Path(__file__).resolve().parents[1]

    def test_e2e_smoke_github_scrum_preset(self):
        """Documented Smoke Path 1: GitHub + Scrum Sprints + GitHub Issues."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gh-scrum-ws"
            shutil.copytree(self.template_dir, target, ignore=shutil.ignore_patterns("tests", ".git"))
            
            res = subprocess.run(
                [sys.executable, str(target / "bootstrap.py"), "--non-interactive", "--preset", "github-scrum", "--output", str(target)],
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 0, f"Bootstrap failed:\n{res.stdout}\n{res.stderr}")
            
            # Verify created files
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "CLAUDE.md").is_file())
            self.assertTrue((target / ".cursorrules").is_file())
            self.assertTrue((target / "workspace.yaml").is_file())
            self.assertTrue((target / "scripts" / "clone_siblings.py").is_file())
            self.assertTrue((target / "scripts" / "siblings.json").is_file())
            self.assertTrue((target / "docs" / "planning" / "01" / "README.md").is_file())
            self.assertTrue((target / ".github" / "skills" / "github-issue-onboard").is_dir())
            self.assertFalse((target / ".github" / "skills" / "jira-story-onboard").exists())
            self.assertIn(
                'framework: "scrum"',
                (target / "workspace.yaml").read_text(encoding="utf-8"),
            )
            
            # Run workspace doctor on generated workspace
            doc_res = subprocess.run(
                [sys.executable, str(target / "scripts" / "workspace_doctor.py")],
                capture_output=True,
                text=True,
                cwd=target
            )
            self.assertEqual(doc_res.returncode, 0, f"Doctor failed:\n{doc_res.stdout}\n{doc_res.stderr}")

            # Run planning docs audit on generated workspace
            audit_script = target / ".github" / "skills" / "planning-docs-audit" / "scripts" / "planning_docs_audit.py"
            if audit_script.is_file():
                audit_res = subprocess.run(
                    [sys.executable, str(audit_script), "--root", str(target)],
                    capture_output=True,
                    text=True,
                    cwd=target
                )
                self.assertEqual(audit_res.returncode, 0, f"Planning docs audit failed:\n{audit_res.stdout}\n{audit_res.stderr}")

    def test_preset_github_scrum(self):
        """Alias for test_e2e_smoke_github_scrum_preset."""
        return self.test_e2e_smoke_github_scrum_preset()

    def test_e2e_standalone_generation_to_empty_directory(self):
        """Smoke path: Seeding an empty standalone directory."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "standalone-ws"
            res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--non-interactive",
                    "--preset",
                    "github-scrum",
                    "--output",
                    str(target),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(res.returncode, 0, f"Bootstrap failed:\n{res.stdout}\n{res.stderr}")
            self.assertTrue((target / "bootstrap.py").is_file())
            self.assertTrue((target / "scripts" / "clone_siblings.py").is_file())

    def test_standalone_generation_to_empty_directory(self):
        """Alias for test_e2e_standalone_generation_to_empty_directory."""
        return self.test_e2e_standalone_generation_to_empty_directory()

    def test_e2e_smoke_jira_safe_preset(self):
        """Documented Smoke Path 2: Jira + SAFe Program Increments."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "jira-safe-ws"
            shutil.copytree(self.template_dir, target, ignore=shutil.ignore_patterns("tests", ".git"))
            
            res = subprocess.run(
                [sys.executable, str(target / "bootstrap.py"), "--non-interactive", "--preset", "jira-safe", "--output", str(target)],
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 0, f"Bootstrap failed:\n{res.stdout}\n{res.stderr}")
            
            # Verify created files
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "docs" / "planning" / "01" / "README.md").is_file())
            self.assertTrue((target / ".github" / "skills" / "jira-story-onboard").is_dir())
            self.assertTrue((target / ".github" / "skills" / "jira-status-sync").is_dir())
            self.assertFalse((target / ".github" / "skills" / "github-issue-onboard").exists())
            self.assertIn(
                'framework: "safe"',
                (target / "workspace.yaml").read_text(encoding="utf-8"),
            )
            
            # Run workspace doctor
            doc_res = subprocess.run(
                [sys.executable, str(target / "scripts" / "workspace_doctor.py")],
                capture_output=True,
                text=True,
                cwd=target
            )
            self.assertEqual(doc_res.returncode, 0, f"Doctor failed:\n{doc_res.stdout}\n{doc_res.stderr}")

            # Run planning docs audit on generated workspace
            audit_script = target / ".github" / "skills" / "planning-docs-audit" / "scripts" / "planning_docs_audit.py"
            if audit_script.is_file():
                audit_res = subprocess.run(
                    [sys.executable, str(audit_script), "--root", str(target)],
                    capture_output=True,
                    text=True,
                    cwd=target
                )
                self.assertEqual(audit_res.returncode, 0, f"Planning docs audit failed:\n{audit_res.stdout}\n{audit_res.stderr}")

    def test_preset_jira_safe(self):
        """Alias for test_e2e_smoke_jira_safe_preset."""
        return self.test_e2e_smoke_jira_safe_preset()


if __name__ == "__main__":
    unittest.main()
