"""Unit tests for bootstrapper rendering and cross-platform helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("bootstrap", MODULE_PATH)
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap
SPEC.loader.exec_module(bootstrap)


class TestBootstrapUnit(unittest.TestCase):
    def test_workspace_yaml_quotes_special_characters(self) -> None:
        config = bootstrap.WorkspaceConfig(
            name='Widget: "Alpha"',
            description="A workspace: AI & delivery",
            siblings=[
                bootstrap.SiblingRepo(
                    name="api",
                    url="https://github.com/example/api.git",
                    role='API: "public"',
                )
            ],
        )

        rendered = bootstrap.render_workspace_config(config)

        self.assertIn('name: "Widget: \\"Alpha\\""', rendered)
        self.assertIn('role: "API: \\"public\\""', rendered)
        self.assertIn('url: "https://github.com/example/api.git"', rendered)

    def test_render_workspace_config_empty_siblings(self) -> None:
        config = bootstrap.WorkspaceConfig(siblings=[])
        rendered = bootstrap.render_workspace_config(config)
        self.assertIn("siblings:\n  []", rendered)

    def test_render_template_str_substitutions_and_defaults(self) -> None:
        tmpl = "Name: {{WORKSPACE_NAME}}, Sprintf: {{MISSING|default(\"fallback\")}}, Empty: {{OTHER}}"
        res = bootstrap.render_template_str(tmpl, {"WORKSPACE_NAME": "Alpha"})
        self.assertEqual(res, 'Name: Alpha, Sprintf: fallback, Empty: ')

    def test_render_template_str_preserves_backslashes_in_values(self) -> None:
        tmpl = "Desc: {{WORKSPACE_DESC}}"
        res = bootstrap.render_template_str(tmpl, {"WORKSPACE_DESC": r"Path C:\Users\name\test \U \1"})
        self.assertEqual(res, r"Desc: Path C:\Users\name\test \U \1")

    def test_sibling_clone_utility_is_platform_neutral(self) -> None:
        script = bootstrap.clone_siblings_script()

        self.assertIn('subprocess.run(', script)
        self.assertIn('["git", "clone"', script)
        self.assertNotIn("BASH_SOURCE", script)
        self.assertNotIn("chmod", script)

    def test_prepare_output_directory_same_source(self) -> None:
        src = Path(tempfile.gettempdir())
        out = bootstrap.prepare_output_directory(src, src)
        self.assertEqual(out, src.resolve())

    def test_prepare_output_directory_empty_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "sample.txt").write_text("hello", encoding="utf-8")
            (src / "__pycache__").mkdir()
            (src / "__pycache__" / "cached.pyc").write_text("bin", encoding="utf-8")

            dest = Path(tmp) / "dest"
            dest.mkdir()
            out = bootstrap.prepare_output_directory(src, dest)
            self.assertEqual(out, dest.resolve())
            self.assertTrue((dest / "sample.txt").is_file())
            self.assertFalse((dest / "__pycache__").exists())

    def test_prepare_output_directory_rejects_non_empty_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "sample.txt").write_text("hello", encoding="utf-8")

            dest = Path(tmp) / "dest"
            dest.mkdir()
            (dest / "existing.txt").write_text("occupied", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                bootstrap.prepare_output_directory(src, dest)
            self.assertIn("Output directory must be empty", str(ctx.exception))

    def test_generated_manifest_preserves_sibling_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / ".github" / "skills").mkdir(parents=True)
            (root / "docs" / "planning" / "templates" / "sprint-template").mkdir(
                parents=True
            )
            (root / "AGENTS.md.template").write_text("{{WORKSPACE_NAME}}", encoding="utf-8")
            (root / "workspace.code-workspace.template").write_text(
                '{"folders": []}', encoding="utf-8"
            )
            (root / "docs" / "planning" / "templates" / "sprint-template" / "README.md").write_text(
                "# Sprint", encoding="utf-8"
            )

            config = bootstrap.WorkspaceConfig(
                siblings=[
                    bootstrap.SiblingRepo(
                        name="api",
                        url="https://github.com/example/api.git",
                        role="Backend API",
                        access="read-only",
                    )
                ]
            )
            bootstrap.generate_workspace(config, root)

            manifest = json.loads(
                (root / "scripts" / "siblings.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest, [config.siblings[0].__dict__])
            self.assertTrue((root / "scripts" / "clone_siblings.py").is_file())
            self.assertTrue((root / ".env.example").is_file())

    def test_render_env_example_jira(self) -> None:
        cfg = bootstrap.WorkspaceConfig(
            tracker_type="jira",
            tracker_base_url="https://acme.atlassian.net",
            vcs_platform="gitlab",
        )
        content = bootstrap.render_env_example(cfg)
        self.assertIn("JIRA_API_TOKEN", content)
        self.assertIn("read:jira-work, write:jira-work", content)
        self.assertIn("https://id.atlassian.com/manage-profile/security/api-tokens", content)
        self.assertIn("GITLAB_TOKEN", content)
        self.assertIn("api", content)

    def test_render_env_example_ado(self) -> None:
        cfg = bootstrap.WorkspaceConfig(
            tracker_type="azure-devops",
            tracker_base_url="https://dev.azure.com/acme",
            vcs_platform="azure-repos",
        )
        content = bootstrap.render_env_example(cfg)
        self.assertIn("AZURE_DEVOPS_EXT_PAT", content)
        self.assertIn("Work Items: `Read & write`", content)
        self.assertIn("Code: `Read & write`", content)
        self.assertIn("az devops login", content)

    def test_render_env_example_github(self) -> None:
        cfg = bootstrap.WorkspaceConfig(
            tracker_type="github",
            vcs_platform="github",
        )
        content = bootstrap.render_env_example(cfg)
        self.assertIn("GITHUB_TOKEN", content)
        self.assertIn("repo", content)
        self.assertIn("gh auth login", content)

    def test_normalize_ado_base_and_project_handles_browser_urls_and_spaces(self) -> None:
        base, proj = bootstrap.normalize_ado_base_and_project(
            "https://dev.azure.com/my-org/My%20Project/_git/my-repo",
            "fallback-org",
            "fallback-proj",
        )
        self.assertEqual(proj, "My Project")
        self.assertEqual(base, "https://dev.azure.com/my-org/My%20Project")

        vs_base, vs_proj = bootstrap.normalize_ado_base_and_project(
            "https://contoso.visualstudio.com/Platform/_boards",
            "contoso",
            "Default",
        )
        self.assertEqual(vs_proj, "Platform")
        self.assertEqual(vs_base, "https://contoso.visualstudio.com/Platform")

    def test_normalize_git_repo_url_strips_browser_suffixes_and_clone_prefix(self) -> None:
        raw = "git clone https://dev.azure.com/acme/My%20Proj/_git/core-api/pullrequest/42"
        self.assertEqual(
            bootstrap.normalize_git_repo_url(raw),
            "https://dev.azure.com/acme/My%20Proj/_git/core-api",
        )
        raw_spaces = "https://dev.azure.com/acme/My Proj/_git/core api"
        self.assertEqual(
            bootstrap.normalize_git_repo_url(raw_spaces),
            "https://dev.azure.com/acme/My%20Proj/_git/core%20api",
        )

    def test_derive_and_validate_sibling_name_unhappy_paths(self) -> None:
        self.assertEqual(
            bootstrap.derive_repo_name_from_url(
                "https://dev.azure.com/acme/Proj/_git/billing%20service.git"
            ),
            "billing-service",
        )
        self.assertEqual(
            bootstrap.derive_repo_name_from_url(
                r"C:\Users\RUNNER~1\AppData\Local\Temp\tmpw4n1zclv\valid-service.git"
            ),
            "valid-service",
        )
        existing = [
            bootstrap.SiblingRepo(
                name="billing-service",
                url="https://dev.azure.com/acme/Proj/_git/billing-service",
                role="Billing",
            )
        ]
        ok, err = bootstrap.validate_sibling_name("../escape", existing, "ws-slug")
        self.assertFalse(ok)
        self.assertIn("without slashes", err)

        ok, err = bootstrap.validate_sibling_name("ws-slug", existing, "ws-slug")
        self.assertFalse(ok)
        self.assertIn("conflicts with the workspace", err)

        ok, err = bootstrap.validate_sibling_name("Billing-Service", existing, "ws-slug")
        self.assertFalse(ok)
        self.assertIn("already in the list", err)

        ok, clean = bootstrap.validate_sibling_name("orders-api", existing, "ws-slug")
        self.assertTrue(ok)
        self.assertEqual(clean, "orders-api")

    def test_write_and_load_provider_specific_env_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = bootstrap.WorkspaceConfig(
                tracker_type="azure-devops",
                vcs_platform="azure-repos",
            )
            env_name = bootstrap.default_env_filename(cfg)
            self.assertEqual(env_name, ".env.azure")
            env_path = root / env_name
            bootstrap.write_env_vars(
                env_path,
                {
                    "AZURE_DEVOPS_ORG_URL": "https://dev.azure.com/acme/proj",
                    "AZURE_DEVOPS_EXT_PAT": "secret-pat-123",
                },
            )
            loaded = bootstrap.load_env_files(root)
            self.assertEqual(loaded["AZURE_DEVOPS_EXT_PAT"], "secret-pat-123")

    def test_verify_git_repo_url_valid_and_invalid_local_repo(self) -> None:
        import subprocess as sp

        with tempfile.TemporaryDirectory() as tmp:
            bare_repo = Path(tmp) / "remote.git"
            sp.run(["git", "init", "--bare", str(bare_repo)], check=True, capture_output=True)

            ok, msg = bootstrap.verify_git_repo_url(str(bare_repo))
            self.assertTrue(ok, msg)

            bad_ok, bad_msg = bootstrap.verify_git_repo_url(str(Path(tmp) / "nonexistent-repo.git"))
            self.assertFalse(bad_ok)
            self.assertTrue(bad_msg)

    def test_prompt_and_verify_siblings_rejects_bad_url_until_valid_or_skipped(self) -> None:
        import subprocess as sp
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            bare_repo = Path(tmp) / "valid-service.git"
            sp.run(["git", "init", "--bare", str(bare_repo)], check=True, capture_output=True)
            invalid_repo = str(Path(tmp) / "does-not-exist.git")

            cfg = bootstrap.WorkspaceConfig(
                slug="my-ws",
                tracker_type="azure-devops",
                vcs_platform="azure-repos",
            )
            # Flow:
            # 1. Add a sibling? -> y
            # 2. Enter invalid URL -> rejected by git ls-remote
            # 3. Enter valid bare_repo URL -> accepted
            # 4. Enter invalid folder name '../bad' -> rejected
            # 5. Accept default folder name '' -> 'valid-service'
            # 6. Enter role 'Core service'
            # 7. Select access mode '' (default 'active')
            # 8. Add another sibling? -> y
            # 9. Enter invalid URL -> rejected
            # 10. Enter '' (blank to skip)
            # 11. Add another sibling? -> n
            inputs = iter([
                "y",
                invalid_repo,
                str(bare_repo),
                "../bad",
                "",
                "Core service",
                "",
                "y",
                invalid_repo,
                "",
                "n",
            ])
            with mock.patch("builtins.input", side_effect=lambda _prompt="": next(inputs)):
                siblings = bootstrap.prompt_and_verify_siblings(cfg)

            self.assertEqual(len(siblings), 1)
            self.assertEqual(siblings[0].name, "valid-service")
            self.assertEqual(siblings[0].url, str(bare_repo))
            self.assertEqual(siblings[0].role, "Core service")
            self.assertEqual(siblings[0].access, "active")

    def test_render_onboarding_primer_tailored_to_framework_and_tracker(self) -> None:
        cfg = bootstrap.WorkspaceConfig(
            name="Contoso ADO Workspace",
            slug="contoso-ado",
            planning_framework="safe",
            tracker_type="azure-devops",
            vcs_platform="azure-repos",
            siblings=[
                bootstrap.SiblingRepo(
                    name="payments-api",
                    url="https://dev.azure.com/contoso/Proj/_git/payments-api",
                    role="Payments API",
                )
            ],
        )
        primer = bootstrap.render_onboarding_primer(cfg, "python3")
        self.assertIn("Program Increment (PI 01)", primer)
        self.assertIn("ado-work-item-onboard", primer)
        self.assertIn("payments-api", primer)
        self.assertIn("bootstrap.py --add-sibling", primer)
        self.assertIn("planning-scaffold", primer)
        self.assertIn("story-refiner", primer)
        self.assertIn("consensus-check", primer)

    def test_prompt_target_directory_defaults_to_new_folder_and_rejects_non_empty(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            source = parent / "saiga-cart"
            source.mkdir()

            occupied = parent / "occupied-ws"
            occupied.mkdir()
            (occupied / "file.txt").write_text("busy", encoding="utf-8")

            # 1. Select default "new-folder" ("")
            # 2. Enter non-empty occupied directory -> rejected
            # 3. Accept default new directory ("") -> parent / "my-new-ws"
            inputs = iter(["", str(occupied), ""])
            with mock.patch("builtins.input", side_effect=lambda _prompt="": next(inputs)):
                chosen = bootstrap.prompt_target_directory(source, "my-new-ws")

            self.assertEqual(chosen, (parent / "my-new-ws").resolve())


if __name__ == "__main__":
    unittest.main()

