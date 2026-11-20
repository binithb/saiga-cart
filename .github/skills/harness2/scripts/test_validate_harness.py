#!/usr/bin/env python3
"""Unit tests for the Harness² surface validator (validate_harness.py)."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manage_experience as me  # noqa: E402
import validate_harness as vh  # noqa: E402


class ValidateHarnessTests(unittest.TestCase):
    def _create_minimal_workspace(self, root: Path) -> None:
        (root / "docs" / "ai" / "wow-adr").mkdir(parents=True)
        (root / "docs" / "pi" / "78" / "goal" / "epic" / "stories").mkdir(parents=True)
        (root / ".github" / "skills" / "sample-skill" / "scripts").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)

        (root / "AGENTS.md").write_text(
            "# AGENTS\nUse `sample-skill` (`python3 .github/skills/sample-skill/scripts/check.py`).\n",
            encoding="utf-8",
        )
        (root / "docs" / "workflow.md").write_text("# Workflow\n", encoding="utf-8")
        (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
        (root / "docs" / "ai" / "experience.md").write_text(
            "# Experience\n\n| ID | Date | Cue | Lesson | Evidence | Status |\n|---|---|---|---|---|---|\n"
            "| `EXP-0001` | 2026-04-19 | cue | lesson | evidence | `active` |\n",
            encoding="utf-8",
        )
        (root / "docs" / "ai" / "wow-adr" / "README.md").write_text(
            "# WoW ADRs\n\n| # | Title | Status | Date |\n|---|---|---|---|\n"
            "| [0001](0001-initial.md) | Initial | Accepted | 2026-04-19 |\n",
            encoding="utf-8",
        )
        (root / "docs" / "ai" / "wow-adr" / "0001-initial.md").write_text(
            "# 0001. Initial\n",
            encoding="utf-8",
        )
        (root / ".github" / "skills" / "README.md").write_text(
            "# Skills\n\n- [sample-skill](sample-skill/SKILL.md)\n",
            encoding="utf-8",
        )
        (root / ".github" / "skills" / "sample-skill" / "SKILL.md").write_text(
            "---\nname: sample-skill\ndescription: A sample skill for testing.\n---\n\n"
            "Run `python3 .github/skills/sample-skill/scripts/check.py`.\n",
            encoding="utf-8",
        )
        (root / ".github" / "skills" / "sample-skill" / "scripts" / "check.py").write_text(
            "#!/usr/bin/env python3\nprint('ok')\n",
            encoding="utf-8",
        )

    def test_clean_minimal_workspace_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            validator = vh.HarnessValidator(root, check_pi_compaction=True)
            findings = validator.validate()
            self.assertEqual(findings, [])
            self.assertEqual(validator.metrics["skills_count"], 1)
            self.assertEqual(validator.metrics["compiled_scripts_count"], 1)
            self.assertEqual(validator.metrics["experience_entries_count"], 1)

    def test_agents_budget_exceeded_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            validator = vh.HarnessValidator(root, max_agents_chars=10)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("AGENTS_BUDGET_EXCEEDED", codes)

    def test_unindexed_skill_and_frontmatter_mismatch_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            rogue_dir = root / ".github" / "skills" / "rogue-skill"
            rogue_dir.mkdir(parents=True)
            (rogue_dir / "SKILL.md").write_text(
                "---\nname: wrong-name\ndescription: \n---\n",
                encoding="utf-8",
            )
            validator = vh.HarnessValidator(root)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("SKILL_NAME_MISMATCH", codes)
            self.assertIn("SKILL_DESCRIPTION_EMPTY", codes)
            self.assertIn("SKILL_UNINDEXED", codes)
            self.assertIn("SKILL_UNROUTED_IN_AGENTS", codes)

    def test_broken_symlink_and_missing_script_reference_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            os.symlink(
                root / "nonexistent-target",
                root / ".github" / "skills" / "broken-skill",
            )
            (root / "AGENTS.md").write_text(
                "# AGENTS\nUse `sample-skill` and `python3 scripts/missing_tool.py`.\n",
                encoding="utf-8",
            )
            validator = vh.HarnessValidator(root)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("SKILL_BROKEN_SYMLINK", codes)
            self.assertIn("BROKEN_SCRIPT_REFERENCE", codes)

    def test_hardcoded_home_path_in_script_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            bad_script = root / ".github" / "skills" / "sample-skill" / "scripts" / "check.py"
            bad_script.write_text(
                "from pathlib import Path\nROOT = Path('/home/" + "alice/repo')\n",
                encoding="utf-8",
            )
            validator = vh.HarnessValidator(root)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("SCRIPT_HARDCODED_HOME_PATH", codes)

    def test_wow_adr_unindexed_and_closed_pi_compaction_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            (root / "docs" / "ai" / "wow-adr" / "0002-unlisted.md").write_text(
                "# 0002. Unlisted\n",
                encoding="utf-8",
            )
            (root / "docs" / "pi" / "README.md").write_text(
                "# PIs\n\n| PI | Goal | Status |\n|---|---|---|\n| 78 | Goal | Done |\n",
                encoding="utf-8",
            )
            story_dir = root / "docs" / "pi" / "78" / "goal" / "epic" / "stories"
            (story_dir / "unfinished-PROJ-1.md").write_text(
                "# Story\n\n| Field | Value |\n|---|---|\n| Status | In progress |\n",
                encoding="utf-8",
            )
            (story_dir / "backlog-scratchpad.txt").write_text("todo\n", encoding="utf-8")

            validator = vh.HarnessValidator(root, check_pi_compaction=True)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("WOW_ADR_UNINDEXED", codes)
            self.assertIn("CLOSED_PI_UNFINISHED_STORY", codes)
            self.assertIn("CLOSED_PI_SCRATCHPAD", codes)

    def test_sibling_pointer_check_flags_missing_backlink_and_bloat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            root = workspace / "saiga-cart"
            self._create_minimal_workspace(root)
            (root / "scripts" / "siblings.json").write_text(
                json.dumps(
                    [
                        {"name": "core-service", "url": "git@github.com:org/core.git", "role": "Core", "access": "active"},
                        {"name": "infra-platform", "url": "git@github.com:org/infra.git", "role": "Infra", "access": "active"},
                    ]
                ),
                encoding="utf-8",
            )
            core_dir = workspace / "core-service"
            core_dir.mkdir(parents=True)
            (core_dir / "AGENTS.md").write_text("# Local rules without workspace pointer\n", encoding="utf-8")
            (workspace / "infra-platform").mkdir(parents=True)

            validator = vh.HarnessValidator(root, check_siblings=True)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("SIBLING_AGENTS_NO_POINTER", codes)
            self.assertIn("SIBLING_AGENTS_MISSING", codes)

    def test_profiles_validation_and_unrouted_skill_suggestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            extra_skill = root / ".github" / "skills" / "new-helper"
            extra_skill.mkdir(parents=True)
            (extra_skill / "SKILL.md").write_text(
                "---\nname: new-helper\ndescription: Helper skill.\n---\n",
                encoding="utf-8",
            )
            h2_dir = root / ".github" / "skills" / "harness2"
            h2_dir.mkdir(parents=True)
            (h2_dir / "SKILL.md").write_text(
                "---\nname: harness2\ndescription: H2 skill.\n---\n",
                encoding="utf-8",
            )
            (root / ".github" / "skills" / "README.md").write_text(
                "# Skills\n\n- [sample-skill](sample-skill/SKILL.md)\n"
                "- [new-helper](new-helper/SKILL.md)\n- [harness2](harness2/SKILL.md)\n",
                encoding="utf-8",
            )
            (h2_dir / "profiles.json").write_text('{"repositories": {}}', encoding="utf-8")

            before_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            validator = vh.HarnessValidator(root)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("SKILL_UNROUTED_IN_AGENTS", codes)
            self.assertIn("PROFILE_REPO_MISSING", codes)
            # Red Zone AGENTS.md must never be auto-mutated by validator
            self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), before_agents)

    def test_manage_experience_record_confounder_gate_escaped_pipes_and_graduate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)

            # Confounded effect must be blocked with exit code 2
            rc_confounded = me.main(
                [
                    "--root",
                    str(root),
                    "record",
                    "--repo",
                    "infra-platform",
                    "--cue",
                    "Modifying Helm values",
                    "--lesson",
                    "Check parent template first",
                    "--evidence",
                    "Multiple simultaneous edits",
                    "--effect",
                    "confounded",
                ]
            )
            self.assertEqual(rc_confounded, 2)

            # Valid record with pipe character '|' in lesson appends EXP-0002 cleanly
            rc_ok = me.main(
                [
                    "--root",
                    str(root),
                    "record",
                    "--repo",
                    "infra-platform",
                    "--cue",
                    "Modifying Helm | JCasC values",
                    "--lesson",
                    "Verify shared defaults | sibling values first",
                    "--evidence",
                    "PROJ-101 review",
                    "--confidence",
                    "high",
                    "--effect",
                    "helped",
                ]
            )
            self.assertEqual(rc_ok, 0)

            # Subsequent record must still parse EXP-0002 (despite escaped pipes) and assign EXP-0003
            rc_ok2 = me.main(
                [
                    "--root",
                    str(root),
                    "record",
                    "--repo",
                    "core-service",
                    "--cue",
                    "Editing skill prompts",
                    "--lesson",
                    "Keep prompts Jinja-safe",
                    "--evidence",
                    "CI run",
                    "--confidence",
                    "medium",
                    "--effect",
                    "helped",
                ]
            )
            self.assertEqual(rc_ok2, 0)

            # Path outside workspace root must be rejected
            rc_outside = me.main(
                [
                    "--root",
                    str(root),
                    "graduate",
                    "--id",
                    "EXP-0002",
                    "--target",
                    "../outside.py",
                ]
            )
            self.assertEqual(rc_outside, 1)

            # Graduate EXP-0002 to an existing script inside workspace
            rc_grad = me.main(
                [
                    "--root",
                    str(root),
                    "graduate",
                    "--id",
                    "EXP-0002",
                    "--target",
                    ".github/skills/sample-skill/scripts/check.py",
                ]
            )
            self.assertEqual(rc_grad, 0)
            exp_text = (root / "docs" / "ai" / "experience.md").read_text(encoding="utf-8")
            self.assertIn("`EXP-0002`", exp_text)
            self.assertIn("`EXP-0003`", exp_text)
            self.assertIn("`graduated (.github/skills/sample-skill/scripts/check.py)`", exp_text)

    def test_unconfirmed_jira_mutation_in_skill_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "saiga-cart"
            self._create_minimal_workspace(root)
            skill_md = root / ".github" / "skills" / "sample-skill" / "SKILL.md"
            skill_md.write_text(
                "---\nname: sample-skill\ndescription: A sample skill.\n---\n\n"
                "Run `python3 jira_create_issue.py --project PROJ --type Story --summary test`.\n",
                encoding="utf-8",
            )
            validator = vh.HarnessValidator(root)
            findings = validator.validate()
            codes = {f.code for f in findings}
            self.assertIn("UNCONFIRMED_JIRA_MUTATION_SKILL", codes)

    def test_claude_and_codex_native_skill_layouts_validate_cleanly(self) -> None:
        for skills_rel in (".claude/skills", ".agents/skills"):
            with self.subTest(skills_rel=skills_rel), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "saiga-cart"
                self._create_minimal_workspace(root)
                (root / skills_rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(root / ".github" / "skills"), str(root / skills_rel))
                (root / ".github").rmdir()
                (root / "AGENTS.md").write_text(
                    f"# AGENTS\nUse `sample-skill` (`python3 {skills_rel}/sample-skill/scripts/check.py`).\n",
                    encoding="utf-8",
                )
                (root / skills_rel / "sample-skill" / "SKILL.md").write_text(
                    "---\nname: sample-skill\ndescription: A sample skill.\n---\n\n"
                    f"Run `python3 {skills_rel}/sample-skill/scripts/check.py`.\n",
                    encoding="utf-8",
                )
                validator = vh.HarnessValidator(root)
                findings = validator.validate()
                self.assertEqual(findings, [])
                self.assertEqual(validator.metrics.get("skills_count"), 1)

    def test_real_repository_passes_with_zero_errors(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        validator = vh.HarnessValidator(
            repo_root,
            check_pi_compaction=True,
            check_zones=True,
        )
        findings = validator.validate()
        errors = [item for item in findings if item.severity == "ERROR"]
        self.assertEqual(errors, [], f"Unexpected errors on real repository: {errors}")


if __name__ == "__main__":
    unittest.main()
