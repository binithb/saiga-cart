#!/usr/bin/env python3
"""High-level E2E user interaction and onboarding workflow tests for Jira and Azure DevOps.

Covers the full matrix of user journeys using the local mock sandbox (`tests/mocks/tracker_sandbox.py`):
1. Jira (SAFe):
   - Interactive wizard (without preset) + entering sibling repo URL at start + Jira story onboarding + bulk status sync.
   - Interactive wizard (without preset) WITHOUT sibling repo at start -> deferred sibling onboarding via `add-sibling` skill workflow.
   - Preset onboarding (`--preset jira-safe`) WITHOUT sibling repo at start -> deferred sibling onboarding via `add-sibling` skill workflow.
2. Azure DevOps (Scrum):
   - Interactive wizard (without preset) + entering sibling repo URL at start + ADO work item onboarding (`az boards work-item create`).
   - Interactive wizard (without preset) WITHOUT sibling repo at start -> deferred sibling onboarding via `add-sibling` skill workflow.
   - Preset onboarding (`--preset ado-scrum`) WITHOUT sibling repo at start -> deferred sibling onboarding via `add-sibling` skill workflow.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.mocks.tracker_sandbox import TrackerSandbox, create_jira_ticket_via_api


def inspect_and_remap_sibling(
    workspace_dir: Path,
    sibling_dir: Path,
    sibling_name: str,
    sibling_url: str,
    access: str,
    tracker_type: str,
    tracker_base_url: str,
    tracker_project_key: str,
    env: dict[str, str],
) -> dict[str, str]:
    """Execute Steps 2–4 of the `add-sibling` skill deterministically against a cloned sibling repo."""
    # Step 2: Inspect the cloned sibling repository manifests, contracts, and test commands
    pyproject = (sibling_dir / "pyproject.toml").read_text(encoding="utf-8")
    readme = (sibling_dir / "README.md").read_text(encoding="utf-8")
    openapi = (sibling_dir / "openapi.yaml").read_text(encoding="utf-8")

    desc_match = re.search(r'description\s*=\s*"([^"]+)"', pyproject)
    discovered_desc = desc_match.group(1) if desc_match else f"Service {sibling_name}"

    title_match = re.search(r"title:\s*(.+)", openapi)
    discovered_api = title_match.group(1).strip() if title_match else "REST API"

    cmd_match = re.search(r"`(python3 -m unittest[^`]+)`", readme)
    discovered_verifier = cmd_match.group(1) if cmd_match else "python3 -m unittest"

    synthesized_role = f"{discovered_desc} exposing {discovered_api}"

    # Step 4.1: Rewrite workspace manifests, agent files, and prune/restore tracker skills
    remap_res = subprocess.run(
        [
            sys.executable,
            str(workspace_dir / "bootstrap.py"),
            "--add-sibling",
            "--sibling-name",
            sibling_name,
            "--sibling-url",
            sibling_url,
            "--sibling-role",
            synthesized_role,
            "--sibling-access",
            access,
            "--tracker-type",
            tracker_type,
            "--tracker-base-url",
            tracker_base_url,
            "--tracker-project-key",
            tracker_project_key,
        ],
        cwd=workspace_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    if remap_res.returncode != 0:
        raise AssertionError(
            f"bootstrap.py --add-sibling remap failed:\n{remap_res.stdout}\n{remap_res.stderr}"
        )

    # Step 4.2: Update `.github/skills/harness2/profiles.json` with discovered verifier
    profiles_path = workspace_dir / ".github" / "skills" / "harness2" / "profiles.json"
    profiles_data = json.loads(profiles_path.read_text(encoding="utf-8"))
    if sibling_name in profiles_data.get("repositories", {}):
        profiles_data["repositories"][sibling_name]["default_verifier"] = discovered_verifier
        profiles_data["repositories"][sibling_name]["verifier_paths"] = [
            "pyproject.toml",
            "openapi.yaml",
            "tests/test_smoke.py",
        ]
        profiles_path.write_text(json.dumps(profiles_data, indent=2) + "\n", encoding="utf-8")

    # Step 4.3: Remap `docs/architecture.md` with discovered topology & contracts
    arch_path = workspace_dir / "docs" / "architecture.md"
    if arch_path.is_file():
        arch_text = arch_path.read_text(encoding="utf-8")
        updated_arch = (
            arch_text
            + f"\n## Onboarded Sibling: `{sibling_name}`\n"
            + f"- **Role**: {synthesized_role}\n"
            + f"- **Contract**: `{discovered_api}` (`openapi.yaml`)\n"
            + f"- **Verification**: `{discovered_verifier}`\n"
        )
        arch_path.write_text(updated_arch, encoding="utf-8")

    # Step 4.4: Update `GLOSSARY.md` with canonical service term
    glossary_path = workspace_dir / "GLOSSARY.md"
    if glossary_path.is_file():
        glossary_text = glossary_path.read_text(encoding="utf-8")
        if sibling_name not in glossary_text:
            glossary_path.write_text(
                glossary_text + f"\n| `{sibling_name}` | {synthesized_role} |\n",
                encoding="utf-8",
            )

    return {
        "role": synthesized_role,
        "api": discovered_api,
        "verifier": discovered_verifier,
    }


class TestUserOnboardingFlows(unittest.TestCase):
    """High-level user onboarding tests across Jira and Azure DevOps with and without presets/initial siblings."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.template_dir = Path(__file__).resolve().parents[1]
        cls.sandbox = TrackerSandbox().start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.stop()

    def _run_workspace_validators(self, ws_dir: Path, env: dict[str, str]) -> None:
        """Run workspace_doctor.py, validate_harness.py, and planning_docs_audit.py --fail-on-warning."""
        doctor_res = subprocess.run(
            [sys.executable, str(ws_dir / "scripts" / "workspace_doctor.py")],
            cwd=ws_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            doctor_res.returncode,
            0,
            f"workspace_doctor.py failed:\n{doctor_res.stdout}\n{doctor_res.stderr}",
        )

        harness_script = ws_dir / ".github" / "skills" / "harness2" / "scripts" / "validate_harness.py"
        harness_res = subprocess.run(
            [sys.executable, str(harness_script), "--root", str(ws_dir)],
            cwd=ws_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            harness_res.returncode,
            0,
            f"validate_harness.py failed:\n{harness_res.stdout}\n{harness_res.stderr}",
        )

        audit_script = (
            ws_dir
            / ".github"
            / "skills"
            / "planning-docs-audit"
            / "scripts"
            / "planning_docs_audit.py"
        )
        audit_res = subprocess.run(
            [sys.executable, str(audit_script), "--root", str(ws_dir), "--fail-on-warning"],
            cwd=ws_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            audit_res.returncode,
            0,
            f"planning_docs_audit.py failed:\n{audit_res.stdout}\n{audit_res.stderr}",
        )

    # =========================================================================
    # JIRA WORKFLOWS
    # =========================================================================

    def test_jira_interactive_no_preset_with_sibling_at_start_and_story_onboard(self) -> None:
        """Jira Flow 1: Full interactive wizard (no preset) + sibling entered at start + story onboard + status sync."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "acme-jira-ws"
            payments_repo_url = str(self.sandbox.sibling_repos["payments-api"])

            env = self.sandbox.env_with_mocks()
            env["GITLAB_BASE_URL"] = self.sandbox.gitlab_base_url

            wizard_answers = [
                # Section 1: Quick Preset or Custom Setup -> choose "custom"
                "custom",
                # Section 2: Workspace Identity & Location (including target directory prompt!)
                "Acme Jira SAFe Workspace",
                "acme-corp",
                "new-folder",
                str(ws_dir),
                # Section 3: Planning, Tracker & Version Control
                "safe",
                "jira",
                self.sandbox.jira_base_url,
                "SAIGA",
                "gitlab",
                # Section 4b: Authentication & Live Connection Check (Jira, then GitLab)
                "env-file",
                ".env.jira",
                self.sandbox.state.jira_email,
                self.sandbox.state.jira_token,
                "env-file",
                ".env.jira",
                self.sandbox.state.gitlab_token,
                # Section 5: Multi-Repo Sibling Repositories (entered at the start!)
                "y",
                payments_repo_url,
                "payments-api",
                "Payment authorization and settlement REST service",
                "active",
                "n",
            ]

            res = subprocess.run(
                [sys.executable, str(self.template_dir / "bootstrap.py")],
                input="\n".join(wizard_answers) + "\n",
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Interactive Jira wizard failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
            )
            self.assertIn("Verified Jira credentials against", res.stdout)
            self.assertIn("Verified GITLAB_TOKEN against", res.stdout)
            self.assertIn("Repository reachable", res.stdout)

            # Verify .env.jira and workspace.yaml
            self.assertTrue((ws_dir / ".env.jira").is_file())
            ws_yaml = (ws_dir / "workspace.yaml").read_text(encoding="utf-8")
            self.assertIn('type: "jira"', ws_yaml)
            self.assertIn('project_key: "SAIGA"', ws_yaml)
            self.assertIn('name: "payments-api"', ws_yaml)

            # Clone sibling repo configured during initial wizard
            clone_res = subprocess.run(
                [sys.executable, str(ws_dir / "scripts" / "clone_siblings.py")],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(clone_res.returncode, 0, clone_res.stderr)
            self.assertTrue((parent_dir / "payments-api" / "pyproject.toml").is_file())

            # Prepare a ready local story with a numeric prefix (`01-settlement-batch.md`)
            epic_dir = ws_dir / "docs" / "planning" / "01" / "goal-template" / "epic-template"
            stories_dir = epic_dir / "stories"
            old_template = stories_dir / "story-template.md"
            numbered_story = stories_dir / "01-settlement-batch.md"
            story_content = old_template.read_text(encoding="utf-8")
            story_content = story_content.replace(
                "| Definition of Ready | Draft |",
                "| Definition of Ready | Done |",
            )
            numbered_story.write_text(story_content, encoding="utf-8")
            old_template.unlink()

            progress_path = epic_dir / "progress.md"
            progress_path.write_text(
                progress_path.read_text(encoding="utf-8").replace(
                    "stories/story-template.md",
                    "stories/01-settlement-batch.md",
                ),
                encoding="utf-8",
            )

            # Execute `jira-story-onboard` 3-Step Procedure against the mock Jira server
            created_issue = create_jira_ticket_via_api(
                base_url=self.sandbox.jira_base_url,
                email=self.sandbox.state.jira_email,
                token=self.sandbox.state.jira_token,
                project_key="SAIGA",
                summary="Settlement Batch Endpoint",
                description="Create /v1/settlements endpoint in payments-api",
                repo_story_permalink="https://gitlab.example/acme-corp/acme-jira-ws/-/blob/main/docs/planning/01/goal-template/epic-template/stories/settlement-batch-SAIGA-101.md",
            )
            jira_key = created_issue["key"]
            self.assertTrue(jira_key.startswith("SAIGA-"))
            self.assertIn(jira_key, self.sandbox.state.jira_remote_links)

            # Step 2: Strip numeric prefix `01-` and append `-<JIRA-KEY>.md`
            onboarded_story = stories_dir / f"settlement-batch-{jira_key}.md"
            numbered_story.rename(onboarded_story)
            updated_story = re.sub(
                r"\|\s*Tracker Story\s*\|.*\|",
                f"| Tracker Story | [{jira_key}]({self.sandbox.jira_base_url}/browse/{jira_key}) |",
                onboarded_story.read_text(encoding="utf-8"),
            )
            onboarded_story.write_text(updated_story, encoding="utf-8")
            progress_path.write_text(
                progress_path.read_text(encoding="utf-8").replace(
                    "stories/01-settlement-batch.md",
                    f"stories/settlement-batch-{jira_key}.md",
                ),
                encoding="utf-8",
            )

            # Execute `jira-status-sync` script (`jira_bulk_status.py`) against mock Jira server
            bulk_script = (
                ws_dir / ".github" / "skills" / "jira-status-sync" / "scripts" / "jira_bulk_status.py"
            )
            sync_res = subprocess.run(
                [sys.executable, str(bulk_script), jira_key],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(sync_res.returncode, 0, sync_res.stderr)
            statuses = json.loads(sync_res.stdout)
            self.assertEqual(statuses.get(jira_key), "In progress")

            # Reconcile local story and progress.md with synced status
            onboarded_story.write_text(
                onboarded_story.read_text(encoding="utf-8").replace(
                    "| Status | Not started |",
                    f"| Status | {statuses[jira_key]} |",
                ),
                encoding="utf-8",
            )
            progress_path.write_text(
                progress_path.read_text(encoding="utf-8").replace(
                    f"[Story title](stories/settlement-batch-{jira_key}.md)",
                    f"[Story title](stories/settlement-batch-{jira_key}.md) — {statuses[jira_key]}",
                ),
                encoding="utf-8",
            )

            # Step 3: Validate workspace health & planning docs audit
            self._run_workspace_validators(ws_dir, env)

    def test_jira_interactive_no_preset_without_sibling_then_add_sibling_skill(self) -> None:
        """Jira Flow 2: Interactive wizard WITHOUT sibling at start -> deferred onboarding via `add-sibling` skill."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "jira-deferred-sib-ws"
            payments_repo_url = str(self.sandbox.sibling_repos["payments-api"])
            env = self.sandbox.env_with_mocks()

            wizard_answers = [
                # Section 1: Select Quick Preset "jira-safe" right from the interactive wizard!
                "jira-safe",
                # Section 2: Identity
                "Acme Jira Deferred Sibling WS",
                "acme-corp",
                # Section 3: Tracker Connection Details (preset skipped framework/tracker/VCS questions)
                self.sandbox.jira_base_url,
                "SAIGA",
                # Section 4b: Configure Jira auth, skip GitLab auth initially
                "env-file",
                ".env.jira",
                self.sandbox.state.jira_email,
                self.sandbox.state.jira_token,
                "skip",
                # Section 5: Do NOT enter any sibling URLs at the start
                "n",
            ]

            res = subprocess.run(
                [sys.executable, str(self.template_dir / "bootstrap.py"), "--output", str(ws_dir)],
                input="\n".join(wizard_answers) + "\n",
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"{res.stdout}\n{res.stderr}")
            self.assertIn("*(No sibling repositories configured yet)*", (ws_dir / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertEqual(json.loads((ws_dir / "scripts" / "siblings.json").read_text(encoding="utf-8")), [])

            # Now user invokes the `add-sibling` workflow (Step 1: interactive `--add-sibling --clone`)
            add_sibling_answers = [
                "y",
                payments_repo_url,
                "payments-api",
                "Service repository (payments-api)",
                "active",
                "n",
                "n",  # Do not reconfigure Jira credentials (already verified)
                "skip",  # Skip GitLab token prompt
            ]
            add_res = subprocess.run(
                [sys.executable, str(ws_dir / "bootstrap.py"), "--add-sibling", "--clone"],
                input="\n".join(add_sibling_answers) + "\n",
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(add_res.returncode, 0, f"{add_res.stdout}\n{add_res.stderr}")
            sibling_checkout = parent_dir / "payments-api"
            self.assertTrue((sibling_checkout / "openapi.yaml").is_file())

            # Steps 2–4 of `add-sibling` skill: inspect cloned repo and remap workspace files
            discovered = inspect_and_remap_sibling(
                workspace_dir=ws_dir,
                sibling_dir=sibling_checkout,
                sibling_name="payments-api",
                sibling_url=payments_repo_url,
                access="active",
                tracker_type="jira",
                tracker_base_url=self.sandbox.jira_base_url,
                tracker_project_key="SAIGA",
                env=env,
            )
            self.assertIn("Payments Ledger API", discovered["role"])
            self.assertIn(discovered["role"], (ws_dir / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("payments-api", (ws_dir / "docs" / "architecture.md").read_text(encoding="utf-8"))
            self.assertIn("payments-api", (ws_dir / "GLOSSARY.md").read_text(encoding="utf-8"))

            # Step 5 of `add-sibling` skill: validate workspace health
            self._run_workspace_validators(ws_dir, env)

    def test_jira_with_preset_without_sibling_then_add_sibling_skill(self) -> None:
        """Jira Flow 3: Preset (`--preset jira-safe`, no sibling at start) -> `add-sibling` skill onboarding."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "jira-preset-ws"
            payments_repo_url = str(self.sandbox.sibling_repos["payments-api"])
            env = self.sandbox.env_with_mocks()

            # 1. Initial onboarding WITH preset and WITHOUT sibling URLs
            preset_res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--non-interactive",
                    "--preset",
                    "jira-safe",
                    "--output",
                    str(ws_dir),
                ],
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(preset_res.returncode, 0, f"{preset_res.stdout}\n{preset_res.stderr}")
            self.assertEqual(json.loads((ws_dir / "scripts" / "siblings.json").read_text(encoding="utf-8")), [])

            # 2. User runs `add-sibling` Step 1: verify & clone sibling repository
            step1_res = subprocess.run(
                [
                    sys.executable,
                    str(ws_dir / "bootstrap.py"),
                    "--add-sibling",
                    "--sibling-url",
                    payments_repo_url,
                    "--clone",
                ],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(step1_res.returncode, 0, f"{step1_res.stdout}\n{step1_res.stderr}")
            sibling_checkout = parent_dir / "payments-api"
            self.assertTrue((sibling_checkout / "pyproject.toml").is_file())

            # 3. User runs `add-sibling` Steps 2–4: inspect repo, confirm intent, remap workspace
            inspect_and_remap_sibling(
                workspace_dir=ws_dir,
                sibling_dir=sibling_checkout,
                sibling_name="payments-api",
                sibling_url=payments_repo_url,
                access="active",
                tracker_type="jira",
                tracker_base_url=self.sandbox.jira_base_url,
                tracker_project_key="SAIGA",
                env=env,
            )

            profiles = json.loads(
                (ws_dir / ".github" / "skills" / "harness2" / "profiles.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                profiles["repositories"]["payments-api"]["default_verifier"],
                "python3 -m unittest discover -s tests",
            )

            # 4. Step 5: Validate workspace health
            self._run_workspace_validators(ws_dir, env)

    def test_jira_with_config_and_sibling_at_start_then_second_sibling_via_skill(self) -> None:
        """Jira Flow 4: Config/preset WITH sibling at start (`payments-api`) -> add second sibling (`inventory-service`) via `add-sibling` skill."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "jira-multi-sib-ws"
            payments_url = str(self.sandbox.sibling_repos["payments-api"])
            inventory_url = str(self.sandbox.sibling_repos["inventory-service"])
            env = self.sandbox.env_with_mocks()

            cfg_file = parent_dir / "initial-jira-config.yaml"
            cfg_file.write_text(
                "\n".join(
                    [
                        "version: 1",
                        "workspace:",
                        '  name: "Acme Jira Multi-Sibling Workspace"',
                        '  slug: "jira-multi-sib-ws"',
                        '  description: "Preconfigured Jira workspace with initial sibling"',
                        '  organization: "acme-corp"',
                        "planning:",
                        '  framework: "safe"',
                        '  cadence_duration: "8 weeks"',
                        "tracker:",
                        '  type: "jira"',
                        f'  base_url: "{self.sandbox.jira_base_url}"',
                        '  project_key: "SAIGA"',
                        "vcs:",
                        '  platform: "gitlab"',
                        "siblings:",
                        '  - name: "payments-api"',
                        f'    url: "{payments_url}"',
                        '    role: "Payment authorization and settlement REST service"',
                        '    access: "active"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            init_res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--config",
                    str(cfg_file),
                    "--output",
                    str(ws_dir),
                ],
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(init_res.returncode, 0, f"{init_res.stdout}\n{init_res.stderr}")

            # Clone the initial sibling declared at start
            clone_res = subprocess.run(
                [sys.executable, str(ws_dir / "scripts" / "clone_siblings.py")],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(clone_res.returncode, 0, clone_res.stderr)
            self.assertTrue((parent_dir / "payments-api" / "pyproject.toml").is_file())

            # Add a 2nd sibling repository (`inventory-service`) using `add-sibling` skill
            add_res = subprocess.run(
                [
                    sys.executable,
                    str(ws_dir / "bootstrap.py"),
                    "--add-sibling",
                    "--sibling-url",
                    inventory_url,
                    "--clone",
                ],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(add_res.returncode, 0, f"{add_res.stdout}\n{add_res.stderr}")
            self.assertTrue((parent_dir / "inventory-service" / "openapi.yaml").is_file())

            inspect_and_remap_sibling(
                workspace_dir=ws_dir,
                sibling_dir=parent_dir / "inventory-service",
                sibling_name="inventory-service",
                sibling_url=inventory_url,
                access="read-only",
                tracker_type="jira",
                tracker_base_url=self.sandbox.jira_base_url,
                tracker_project_key="SAIGA",
                env=env,
            )

            siblings_manifest = json.loads(
                (ws_dir / "scripts" / "siblings.json").read_text(encoding="utf-8")
            )
            self.assertEqual([s["name"] for s in siblings_manifest], ["payments-api", "inventory-service"])
            self.assertEqual(siblings_manifest[1]["access"], "read-only")
            self._run_workspace_validators(ws_dir, env)

    # =========================================================================
    # AZURE DEVOPS (ADO) WORKFLOWS
    # =========================================================================

    def test_ado_interactive_no_preset_with_sibling_at_start_and_work_item_onboard(self) -> None:
        """ADO Flow 1: Full interactive wizard (no preset) + sibling entered at start + ADO work item onboarding."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "acme-ado-ws"
            inventory_repo_url = str(self.sandbox.sibling_repos["inventory-service"])
            env = self.sandbox.env_with_mocks()

            wizard_answers = [
                # Section 1: Quick Preset or Custom Setup -> choose "custom"
                "custom",
                # Section 2: Workspace Identity & Location
                "Acme Azure DevOps Workspace",
                "acme-org",
                # Section 3: Planning, Tracker & Version Control
                "scrum",
                "azure-devops",
                self.sandbox.ado_org_url,
                "CorePlatform",
                "azure-repos",
                # Section 4b: Authentication & Live Connection Check (ADO PAT verified against mock server)
                "env-file",
                ".env.azure",
                self.sandbox.state.ado_pat,
                # Section 5: Multi-Repo Sibling Repositories (entered at the start!)
                "y",
                inventory_repo_url,
                "inventory-service",
                "Warehouse stock reservation and SKU allocation service",
                "active",
                "n",
            ]

            res = subprocess.run(
                [sys.executable, str(self.template_dir / "bootstrap.py"), "--output", str(ws_dir)],
                input="\n".join(wizard_answers) + "\n",
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Interactive ADO wizard failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
            )
            self.assertIn("Verified Azure DevOps PAT against", res.stdout)
            self.assertIn("Repository reachable", res.stdout)
            self.assertTrue((ws_dir / ".env.azure").is_file())
            self.assertTrue((ws_dir / ".github" / "skills" / "ado-work-item-onboard").is_dir())
            self.assertFalse((ws_dir / ".github" / "skills" / "jira-story-onboard").exists())

            # Clone configured sibling repository
            clone_res = subprocess.run(
                [sys.executable, str(ws_dir / "scripts" / "clone_siblings.py")],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(clone_res.returncode, 0, clone_res.stderr)
            self.assertTrue((parent_dir / "inventory-service" / "openapi.yaml").is_file())

            # Prepare a numbered story file `01-sku-reservation.md`
            epic_dir = ws_dir / "docs" / "planning" / "01" / "epic-template"
            stories_dir = epic_dir / "stories"
            old_template = stories_dir / "story-template.md"
            numbered_story = stories_dir / "01-sku-reservation.md"
            story_content = old_template.read_text(encoding="utf-8").replace(
                "| Definition of Ready | Draft |",
                "| Definition of Ready | Done |",
            )
            numbered_story.write_text(story_content, encoding="utf-8")
            old_template.unlink()

            progress_path = epic_dir / "progress.md"
            progress_path.write_text(
                progress_path.read_text(encoding="utf-8").replace(
                    "stories/story-template.md",
                    "stories/01-sku-reservation.md",
                ),
                encoding="utf-8",
            )

            # Execute `ado-work-item-onboard` 3-Step Procedure using `az boards work-item create`
            az_exe = shutil.which("az", path=env.get("PATH")) or "az"
            az_res = subprocess.run(
                [
                    az_exe,
                    "boards",
                    "work-item",
                    "create",
                    "--title",
                    "Reserve SKU Stock Endpoint",
                    "--type",
                    "User Story",
                    "--project",
                    "CorePlatform",
                    "--organization",
                    self.sandbox.ado_org_url,
                    "--description",
                    "Implement POST /v1/reservations in inventory-service",
                ],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(az_res.returncode, 0, f"az CLI shim failed:\n{az_res.stdout}\n{az_res.stderr}")
            wi_data = json.loads(az_res.stdout)
            wi_id = wi_data["id"]
            self.assertIn(wi_id, self.sandbox.state.ado_work_items)
            self.assertIn("/acme-org/CorePlatform/_workitems/edit/", wi_data["url"])

            # Step 2: Strip leading numeric prefix `01-` and append `-AB-<ID>.md`
            onboarded_story = stories_dir / f"sku-reservation-AB-{wi_id}.md"
            numbered_story.rename(onboarded_story)
            updated_story = onboarded_story.read_text(encoding="utf-8").replace(
                "| Tracker Story | TBD |",
                f"| Tracker Story | [AB#{wi_id}]({wi_data['url']}) |",
            )
            onboarded_story.write_text(updated_story, encoding="utf-8")

            progress_path.write_text(
                progress_path.read_text(encoding="utf-8").replace(
                    "stories/01-sku-reservation.md",
                    f"stories/sku-reservation-AB-{wi_id}.md",
                ),
                encoding="utf-8",
            )

            # Step 3: Validate workspace health & planning docs audit
            self._run_workspace_validators(ws_dir, env)

    def test_ado_interactive_no_preset_without_sibling_then_add_sibling_skill(self) -> None:
        """ADO Flow 2: Interactive wizard WITHOUT sibling at start -> deferred onboarding via `add-sibling` skill."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "ado-deferred-sib-ws"
            inventory_repo_url = str(self.sandbox.sibling_repos["inventory-service"])
            env = self.sandbox.env_with_mocks()

            wizard_answers = [
                # Section 1: Select Quick Preset "ado-scrum" interactively in the wizard!
                "ado-scrum",
                # Section 2: Identity
                "Acme ADO Deferred Sibling WS",
                "acme-org",
                # Section 3: ADO Connection Details (preset skipped framework/tracker/VCS questions)
                self.sandbox.ado_org_url,
                "CorePlatform",
                # Section 4b: Configure ADO PAT in .env.azure
                "env-file",
                ".env.azure",
                self.sandbox.state.ado_pat,
                # Section 5: Do NOT add sibling repositories during initial wizard
                "n",
            ]

            res = subprocess.run(
                [sys.executable, str(self.template_dir / "bootstrap.py"), "--output", str(ws_dir)],
                input="\n".join(wizard_answers) + "\n",
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"{res.stdout}\n{res.stderr}")
            self.assertEqual(json.loads((ws_dir / "scripts" / "siblings.json").read_text(encoding="utf-8")), [])

            # Deferred `add-sibling` skill execution (Step 1: interactive `--add-sibling --clone`)
            add_sibling_answers = [
                "y",
                inventory_repo_url,
                "inventory-service",
                "Service repository (inventory-service)",
                "active",
                "n",
                "n",  # Do not reconfigure ADO credentials (already verified via .env.azure)
            ]
            add_res = subprocess.run(
                [sys.executable, str(ws_dir / "bootstrap.py"), "--add-sibling", "--clone"],
                input="\n".join(add_sibling_answers) + "\n",
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(add_res.returncode, 0, f"{add_res.stdout}\n{add_res.stderr}")
            sibling_checkout = parent_dir / "inventory-service"
            self.assertTrue((sibling_checkout / "openapi.yaml").is_file())

            # Steps 2–4: Inspect cloned repo and remap workspace files
            discovered = inspect_and_remap_sibling(
                workspace_dir=ws_dir,
                sibling_dir=sibling_checkout,
                sibling_name="inventory-service",
                sibling_url=inventory_repo_url,
                access="active",
                tracker_type="azure-devops",
                tracker_base_url=self.sandbox.ado_org_url,
                tracker_project_key="CorePlatform",
                env=env,
            )
            self.assertIn("Inventory Reservation API", discovered["role"])
            self.assertIn(discovered["role"], (ws_dir / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("inventory-service", (ws_dir / "docs" / "architecture.md").read_text(encoding="utf-8"))

            # Step 5: Validate workspace health
            self._run_workspace_validators(ws_dir, env)

    def test_ado_with_preset_without_sibling_then_add_sibling_skill(self) -> None:
        """ADO Flow 3: Preset (`--preset ado-scrum`, no sibling at start) -> `add-sibling` skill onboarding."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "ado-preset-ws"
            inventory_repo_url = str(self.sandbox.sibling_repos["inventory-service"])
            env = self.sandbox.env_with_mocks()

            # 1. Initial onboarding WITH preset and WITHOUT sibling URLs
            preset_res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--non-interactive",
                    "--preset",
                    "ado-scrum",
                    "--output",
                    str(ws_dir),
                ],
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(preset_res.returncode, 0, f"{preset_res.stdout}\n{preset_res.stderr}")
            self.assertEqual(json.loads((ws_dir / "scripts" / "siblings.json").read_text(encoding="utf-8")), [])

            # 2. User runs `add-sibling` Step 1: verify & clone sibling repository
            step1_res = subprocess.run(
                [
                    sys.executable,
                    str(ws_dir / "bootstrap.py"),
                    "--add-sibling",
                    "--sibling-url",
                    inventory_repo_url,
                    "--clone",
                ],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(step1_res.returncode, 0, f"{step1_res.stdout}\n{step1_res.stderr}")
            sibling_checkout = parent_dir / "inventory-service"
            self.assertTrue((sibling_checkout / "pyproject.toml").is_file())

            # 3. User runs `add-sibling` Steps 2–4: inspect repo, confirm intent, remap workspace
            inspect_and_remap_sibling(
                workspace_dir=ws_dir,
                sibling_dir=sibling_checkout,
                sibling_name="inventory-service",
                sibling_url=inventory_repo_url,
                access="active",
                tracker_type="azure-devops",
                tracker_base_url=self.sandbox.ado_org_url,
                tracker_project_key="CorePlatform",
                env=env,
            )

            profiles = json.loads(
                (ws_dir / ".github" / "skills" / "harness2" / "profiles.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                profiles["repositories"]["inventory-service"]["default_verifier"],
                "python3 -m unittest discover -s tests",
            )

            # 4. Step 5: Validate workspace health
            self._run_workspace_validators(ws_dir, env)

    def test_preset_tracker_switch_to_ado_via_add_sibling_skill_prunes_and_restores_skills(self) -> None:
        """ADO Flow 4: Start with default `github-scrum` preset (no siblings) -> switch to `azure-devops` during `add-sibling` skill."""
        with tempfile.TemporaryDirectory() as tmp:
            parent_dir = Path(tmp)
            ws_dir = parent_dir / "switched-ado-ws"
            inventory_repo_url = str(self.sandbox.sibling_repos["inventory-service"])
            env = self.sandbox.env_with_mocks()

            # Start with github-scrum preset
            preset_res = subprocess.run(
                [
                    sys.executable,
                    str(self.template_dir / "bootstrap.py"),
                    "--non-interactive",
                    "--preset",
                    "github-scrum",
                    "--output",
                    str(ws_dir),
                ],
                cwd=parent_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(preset_res.returncode, 0, f"{preset_res.stdout}\n{preset_res.stderr}")
            self.assertTrue((ws_dir / ".github" / "skills" / "github-issue-onboard").is_dir())
            self.assertFalse((ws_dir / ".github" / "skills" / "ado-work-item-onboard").exists())

            # Run `add-sibling` Step 1 (clone) + Steps 2–4 switching tracker to `azure-devops`
            step1_res = subprocess.run(
                [
                    sys.executable,
                    str(ws_dir / "bootstrap.py"),
                    "--add-sibling",
                    "--sibling-url",
                    inventory_repo_url,
                    "--clone",
                ],
                cwd=ws_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(step1_res.returncode, 0, f"{step1_res.stdout}\n{step1_res.stderr}")

            inspect_and_remap_sibling(
                workspace_dir=ws_dir,
                sibling_dir=parent_dir / "inventory-service",
                sibling_name="inventory-service",
                sibling_url=inventory_repo_url,
                access="active",
                tracker_type="azure-devops",
                tracker_base_url=self.sandbox.ado_org_url,
                tracker_project_key="CorePlatform",
                env=env,
            )

            # Verify unused GitHub skills were pruned and ADO skill was restored
            self.assertFalse((ws_dir / ".github" / "skills" / "github-issue-onboard").exists())
            self.assertFalse((ws_dir / ".github" / "skills" / "github-status-sync").exists())
            self.assertTrue((ws_dir / ".github" / "skills" / "ado-work-item-onboard").is_dir())
            self._run_workspace_validators(ws_dir, env)


if __name__ == "__main__":
    unittest.main()
