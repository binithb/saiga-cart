#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from story_readiness import collect_stories, build_report


class TestStoryReadiness(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_story_readiness_queue(self):
        stories_dir = self.root / "docs" / "planning" / "01" / "epic1" / "stories"
        stories_dir.mkdir(parents=True)

        progress = self.root / "docs" / "planning" / "01" / "epic1" / "progress.md"
        progress.write_text("# Progress\n- [ ] [Story A](stories/01-story-a.md)\n- [ ] [Story B](stories/02-story-b-PROJ-101.md)\n")

        story_a = stories_dir / "01-story-a.md"
        story_a.write_text("""# Story A
| Field | Value |
|---|---|
| Status | Not started |
| Effort | Small |
| Definition of Ready | Done |
""")

        story_b = stories_dir / "02-story-b-PROJ-101.md"
        story_b.write_text("""# Story B
| Field | Value |
|---|---|
| Tracker Story | [PROJ-101](https://tracker/PROJ-101) |
| Status | Not started |
| Effort | Small |
| Definition of Ready | Done |
""")

        stories = collect_stories([self.root / "docs" / "planning" / "01"])
        report = build_report(stories, self.root)

        self.assertEqual(len(report["readiness"]), 2)
        self.assertEqual(len(report["queue"]), 2)
        self.assertEqual(report["queue"][0]["availability"], "Needs tracker onboarding")
        self.assertEqual(report["queue"][1]["availability"], "Available now")


if __name__ == "__main__":
    unittest.main()
