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


if __name__ == "__main__":
    unittest.main()

