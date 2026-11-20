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
            self.assertTrue((target / ".env.example").is_file())
            self.assertIn("GITHUB_TOKEN", (target / ".env.example").read_text(encoding="utf-8"))
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
            self.assertTrue((target / ".env.example").is_file())
            env_text = (target / ".env.example").read_text(encoding="utf-8")
            self.assertIn("JIRA_API_TOKEN", env_text)
            self.assertIn("read:jira-work, write:jira-work", env_text)
            self.assertIn("GITLAB_TOKEN", env_text)
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

    def test_e2e_smoke_ado_scrum_preset(self):
        """Documented Smoke Path 3: Azure DevOps + Scrum Sprints + Azure Repos."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ado-scrum-ws"
            shutil.copytree(self.template_dir, target, ignore=shutil.ignore_patterns("tests", ".git"))

            res = subprocess.run(
                [
                    sys.executable,
                    str(target / "bootstrap.py"),
                    "--non-interactive",
                    "--preset",
                    "ado-scrum",
                    "--output",
                    str(target),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"Bootstrap failed:\n{res.stdout}\n{res.stderr}")

            # Verify created files
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "docs" / "planning" / "01" / "README.md").is_file())
            self.assertTrue((target / ".env.example").is_file())
            env_text = (target / ".env.example").read_text(encoding="utf-8")
            self.assertIn("AZURE_DEVOPS_EXT_PAT", env_text)
            self.assertIn("Work Items: `Read & write`", env_text)
            self.assertTrue((target / ".github" / "skills" / "ado-work-item-onboard").is_dir())
            self.assertFalse((target / ".github" / "skills" / "jira-story-onboard").exists())
            self.assertFalse((target / ".github" / "skills" / "github-issue-onboard").exists())
            self.assertIn(
                'tracker:\n  type: "azure-devops"',
                (target / "workspace.yaml").read_text(encoding="utf-8"),
            )

            # Run workspace doctor
            doc_res = subprocess.run(
                [sys.executable, str(target / "scripts" / "workspace_doctor.py")],
                capture_output=True,
                text=True,
                cwd=target,
            )
            self.assertEqual(doc_res.returncode, 0, f"Doctor failed:\n{doc_res.stdout}\n{doc_res.stderr}")

            # Run planning docs audit
            audit_script = target / ".github" / "skills" / "planning-docs-audit" / "scripts" / "planning_docs_audit.py"
            if audit_script.is_file():
                audit_res = subprocess.run(
                    [sys.executable, str(audit_script), "--root", str(target)],
                    capture_output=True,
                    text=True,
                    cwd=target,
                )
                self.assertEqual(audit_res.returncode, 0, f"Planning docs audit failed:\n{audit_res.stdout}\n{audit_res.stderr}")

    def test_agents_flag_single_subset_and_all_modes_pass_validators(self):
        """Verify --agents copilot, claude, codex, copilot,claude, and all install native clutter-free layouts without symlinks."""
        cases = [
            (
                "copilot",
                {".github/skills"},
                True,
                False,
                False,
                ".github/skills",
            ),
            (
                "claude",
                {".claude/skills"},
                False,
                True,
                False,
                ".claude/skills",
            ),
            (
                "codex",
                {".agents/skills"},
                False,
                False,
                False,
                ".agents/skills",
            ),
            (
                "copilot,claude",
                {".github/skills", ".claude/skills"},
                True,
                True,
                False,
                ".github/skills",
            ),
            (
                "all",
                {".github/skills", ".claude/skills", ".agents/skills"},
                True,
                True,
                True,
                ".github/skills",
            ),
        ]

        all_skill_rels = {".github/skills", ".claude/skills", ".agents/skills"}

        for agents_arg, expected_skill_rels, exp_copilot_md, exp_claude_md, exp_cursor, primary_rel in cases:
            with self.subTest(agents=agents_arg), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / f"ws-{agents_arg.replace(',', '-')}"
                res = subprocess.run(
                    [
                        sys.executable,
                        str(self.template_dir / "bootstrap.py"),
                        "--non-interactive",
                        "--preset",
                        "github-scrum",
                        "--agents",
                        agents_arg,
                        "--output",
                        str(target),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(res.returncode, 0, f"Bootstrap failed ({agents_arg}):\n{res.stdout}\n{res.stderr}")

                # Canonical AGENTS.md is always generated and points to primary active skills path
                self.assertTrue((target / "AGENTS.md").is_file())
                agents_md_text = (target / "AGENTS.md").read_text(encoding="utf-8")
                self.assertIn(f"{primary_rel}/README.md", agents_md_text)

                # Tool-specific instruction files exist ONLY when enabled
                self.assertEqual((target / ".github" / "copilot-instructions.md").exists(), exp_copilot_md)
                self.assertEqual((target / "CLAUDE.md").exists(), exp_claude_md)
                self.assertEqual((target / ".cursorrules").exists(), exp_cursor)
                if exp_claude_md:
                    self.assertIn(".claude/skills/README.md", (target / "CLAUDE.md").read_text(encoding="utf-8"))

                # Native skill directories exist ONLY for selected tools and use real copies (no symlinks)
                for rel in all_skill_rels:
                    skill_dir = target / rel
                    if rel in expected_skill_rels:
                        self.assertTrue(skill_dir.is_dir(), f"Expected {rel} in {agents_arg}")
                        self.assertFalse(skill_dir.is_symlink(), f"{rel} must not be a symlink")
                        self.assertTrue((skill_dir / "github-issue-onboard" / "SKILL.md").is_file())
                        self.assertFalse((skill_dir / "jira-story-onboard").exists())
                        for p in skill_dir.rglob("*"):
                            self.assertFalse(p.is_symlink(), f"Found symlink {p} in {rel}")
                        # Verify path rewriting inside SKILL.md and profiles.json
                        onboard_text = (skill_dir / "github-issue-onboard" / "SKILL.md").read_text(encoding="utf-8")
                        self.assertIn(f"{rel}/planning-docs-audit/scripts/planning_docs_audit.py", onboard_text)
                        profiles_text = (skill_dir / "harness2" / "profiles.json").read_text(encoding="utf-8")
                        self.assertIn(f"{rel}/harness2/scripts/validate_harness.py", profiles_text)
                        # Multi-root overview row in harness2/SKILL.md must preserve all 3 distinct directories
                        h2_skill_text = (skill_dir / "harness2" / "SKILL.md").read_text(encoding="utf-8")
                        self.assertIn(
                            "`.github/skills/**`, `.claude/skills/**`, `.agents/skills/**`",
                            h2_skill_text,
                        )
                    else:
                        self.assertFalse(skill_dir.exists(), f"Unexpected unused {rel} in {agents_arg}")

                # Verify GLOSSARY.md, README.md, and CONTRIBUTING.md align single-root commands to primary_rel
                self.assertIn(f"`{primary_rel}/`", (target / "GLOSSARY.md").read_text(encoding="utf-8"))
                self.assertIn(
                    f"python {primary_rel}/harness2/scripts/validate_harness.py",
                    (target / "README.md").read_text(encoding="utf-8"),
                )
                self.assertIn(
                    f"python3 {primary_rel}/story-refiner/scripts/test_story_readiness.py",
                    (target / "CONTRIBUTING.md").read_text(encoding="utf-8"),
                )

                # Verify the generated workspace's own presentation test passes even when .github/skills is absent
                pres_res = subprocess.run(
                    [sys.executable, "-m", "unittest", "tests/test_presentation.py"],
                    capture_output=True,
                    text=True,
                    cwd=target,
                )
                self.assertEqual(pres_res.returncode, 0, f"test_presentation failed ({agents_arg}):\n{pres_res.stderr}")

                # Run workspace_doctor.py and validate_harness.py inside the generated workspace
                doc_res = subprocess.run(
                    [sys.executable, str(target / "scripts" / "workspace_doctor.py")],
                    capture_output=True,
                    text=True,
                    cwd=target,
                )
                self.assertEqual(doc_res.returncode, 0, f"Doctor failed ({agents_arg}):\n{doc_res.stdout}\n{doc_res.stderr}")

                harness_script = target / primary_rel / "harness2" / "scripts" / "validate_harness.py"
                h_res = subprocess.run(
                    [sys.executable, str(harness_script), "--root", str(target)],
                    capture_output=True,
                    text=True,
                    cwd=target,
                )
                self.assertEqual(h_res.returncode, 0, f"validate_harness failed ({agents_arg}):\n{h_res.stdout}\n{h_res.stderr}")

    def test_add_sibling_preserves_single_tool_agents_and_switches_tracker_cleanly(self):
        """Verify bootstrap.py --add-sibling preserves --agents codex / claude without resurrecting .github/skills."""
        for agent_mode, skill_rel in (("claude", ".claude/skills"), ("codex", ".agents/skills")):
            with self.subTest(agent_mode=agent_mode), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / f"{agent_mode}-ws"
                init_res = subprocess.run(
                    [
                        sys.executable,
                        str(self.template_dir / "bootstrap.py"),
                        "--non-interactive",
                        "--preset",
                        "github-scrum",
                        "--agents",
                        agent_mode,
                        "--output",
                        str(target),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(init_res.returncode, 0, init_res.stderr)

                # Add a sibling repo AND switch tracker to jira without passing --agents
                add_res = subprocess.run(
                    [
                        sys.executable,
                        str(target / "bootstrap.py"),
                        "--add-sibling",
                        "--sibling-url",
                        "https://gitlab.com/acme-corp/billing-service.git",
                        "--sibling-name",
                        "billing-service",
                        "--sibling-role",
                        "Billing & invoicing microservice",
                        "--sibling-access",
                        "active",
                        "--tracker-type",
                        "jira",
                        "--tracker-base-url",
                        "https://acme-corp.atlassian.net",
                        "--tracker-project-key",
                        "BILL",
                        "--skip-verify",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=target,
                )
                self.assertEqual(add_res.returncode, 0, f"add-sibling failed:\n{add_res.stdout}\n{add_res.stderr}")

                # Agent selection must stay preserved (no .github/skills or copilot-instructions.md created)
                self.assertFalse((target / ".github" / "skills").exists())
                self.assertFalse((target / ".github" / "copilot-instructions.md").exists())
                self.assertEqual((target / "CLAUDE.md").exists(), agent_mode == "claude")
                self.assertTrue((target / skill_rel / "jira-story-onboard" / "SKILL.md").is_file())
                self.assertFalse((target / skill_rel / "github-issue-onboard").exists())

                # Both workspace_doctor.py and validate_harness.py must pass cleanly
                doc_res = subprocess.run(
                    [sys.executable, str(target / "scripts" / "workspace_doctor.py")],
                    capture_output=True,
                    text=True,
                    cwd=target,
                )
                self.assertEqual(doc_res.returncode, 0, f"Doctor failed:\n{doc_res.stdout}\n{doc_res.stderr}")

                h_res = subprocess.run(
                    [
                        sys.executable,
                        str(target / skill_rel / "harness2" / "scripts" / "validate_harness.py"),
                        "--root",
                        str(target),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=target,
                )
                self.assertEqual(h_res.returncode, 0, f"validate_harness failed:\n{h_res.stdout}\n{h_res.stderr}")

    def test_config_run_supports_agents_override_and_rejects_invalid_agents(self):
        """Verify --config honors --agents override and invalid --agents exits with code 2."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bad_res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--non-interactive",
                    "--agents",
                    "unknown_ai",
                    "--output",
                    str(tmp_path / "bad-ws"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(bad_res.returncode, 2)

            cfg_manifest = tmp_path / "custom-workspace.yaml"
            cfg_manifest.write_text(
                'version: 1\nworkspace:\n  name: "Config WS"\n  slug: "config-ws"\n'
                'planning:\n  framework: "scrum"\ntracker:\n  type: "github"\nvcs:\n  platform: "github"\n'
                "agents:\n  copilot: true\n  claude: true\n  codex: true\n  cursor: true\n",
                encoding="utf-8",
            )
            cfg_out = tmp_path / "cfg-claude-ws"
            cfg_res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--config",
                    str(cfg_manifest),
                    "--agents",
                    "claude",
                    "--output",
                    str(cfg_out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(cfg_res.returncode, 0, cfg_res.stderr)
            self.assertTrue((cfg_out / "CLAUDE.md").is_file())
            self.assertTrue((cfg_out / ".claude" / "skills").is_dir())
            self.assertFalse((cfg_out / ".github" / "skills").exists())
            self.assertFalse((cfg_out / ".agents" / "skills").exists())

    def test_add_sibling_preserves_custom_skills_and_distill_edits_in_secondary_skill_dirs(self):
        """Regression: h2 distill edits and custom skills in .claude/skills or .agents/skills survive --add-sibling."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "multi-agent-ws"
            init_res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--non-interactive",
                    "--preset",
                    "github-scrum",
                    "--agents",
                    "all",
                    "--output",
                    str(target),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(init_res.returncode, 0, init_res.stderr)

            # 1. Simulate h2 distill edits made during Claude Code and OpenAI Codex sessions
            claude_refiner = target / ".claude" / "skills" / "story-refiner" / "SKILL.md"
            claude_refiner.write_text(
                claude_refiner.read_text(encoding="utf-8") + "\n<!-- CLAUDE_DISTILL_MARKER -->\n",
                encoding="utf-8",
            )
            codex_consensus = target / ".agents" / "skills" / "consensus-check" / "SKILL.md"
            codex_consensus.write_text(
                codex_consensus.read_text(encoding="utf-8") + "\n<!-- CODEX_DISTILL_MARKER -->\n",
                encoding="utf-8",
            )

            # 2. Simulate adding a brand-new custom skill in .claude/skills/team-custom/
            custom_dir = target / ".claude" / "skills" / "team-custom"
            (custom_dir / "scripts").mkdir(parents=True)
            (custom_dir / "SKILL.md").write_text(
                "---\nname: team-custom\ndescription: Verify team API conventions.\n---\n\n"
                "# Team Custom Skill\n\nRun `python3 .claude/skills/team-custom/scripts/check_api.py`.\n",
                encoding="utf-8",
            )
            (custom_dir / "scripts" / "check_api.py").write_text(
                "#!/usr/bin/env python3\nprint('ok')\n",
                encoding="utf-8",
            )

            # 3. Re-run bootstrap.py --add-sibling
            add_res = subprocess.run(
                [
                    sys.executable,
                    str(target / "bootstrap.py"),
                    "--add-sibling",
                    "--sibling-url",
                    "https://github.com/acme-corp/orders-api.git",
                    "--sibling-name",
                    "orders-api",
                    "--sibling-role",
                    "Order management REST service",
                    "--sibling-access",
                    "active",
                    "--skip-verify",
                ],
                capture_output=True,
                text=True,
                cwd=target,
            )
            self.assertEqual(add_res.returncode, 0, f"add-sibling failed:\n{add_res.stdout}\n{add_res.stderr}")

            # 4. Assert edits and custom skills survived and synchronized across all three active skill roots
            for rel in (".github/skills", ".claude/skills", ".agents/skills"):
                sdir = target / rel
                self.assertIn(
                    "CLAUDE_DISTILL_MARKER",
                    (sdir / "story-refiner" / "SKILL.md").read_text(encoding="utf-8"),
                )
                self.assertIn(
                    "CODEX_DISTILL_MARKER",
                    (sdir / "consensus-check" / "SKILL.md").read_text(encoding="utf-8"),
                )
                custom_md = sdir / "team-custom" / "SKILL.md"
                self.assertTrue(custom_md.is_file(), f"Missing team-custom/SKILL.md in {rel}")
                self.assertIn(f"{rel}/team-custom/scripts/check_api.py", custom_md.read_text(encoding="utf-8"))
                self.assertTrue((sdir / "team-custom" / "scripts" / "check_api.py").is_file())
                self.assertIn(
                    "[team-custom](team-custom/SKILL.md)",
                    (sdir / "README.md").read_text(encoding="utf-8"),
                )

            # 5. Harness² validator passes cleanly with 0 errors
            h_res = subprocess.run(
                [
                    sys.executable,
                    str(target / ".github" / "skills" / "harness2" / "scripts" / "validate_harness.py"),
                    "--root",
                    str(target),
                ],
                capture_output=True,
                text=True,
                cwd=target,
            )
            self.assertEqual(h_res.returncode, 0, f"validate_harness failed:\n{h_res.stdout}\n{h_res.stderr}")


if __name__ == "__main__":
    unittest.main()
