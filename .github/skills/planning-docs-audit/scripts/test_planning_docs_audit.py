#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from planning_docs_audit import PlanningAuditor


class TestPlanningDocsAudit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_workspace_warning(self):
        (self.root / "docs").mkdir()
        auditor = PlanningAuditor(self.root)
        findings = auditor.audit()
        self.assertTrue(any(f.severity == "WARNING" for f in findings))

    def test_valid_epic_and_story(self):
        planning_dir = self.root / "docs" / "planning" / "01" / "core" / "stories"
        planning_dir.mkdir(parents=True)
        
        progress = self.root / "docs" / "planning" / "01" / "core" / "progress.md"
        progress.write_text("# Progress\n- [ ] [Story 1](stories/story-1.md)\n")
        
        story = planning_dir / "story-1.md"
        story.write_text("""# Story 1
| Field | Value |
|---|---|
| Status | Not started |
| Effort | Small |
| Definition of Ready | Done |
""")
        
        auditor = PlanningAuditor(self.root)
        findings = auditor.audit()
        errors = [f for f in findings if f.severity == "ERROR"]
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")


if __name__ == "__main__":
    unittest.main()
