---
name: github-issue-onboard
description: 'Onboard a local planning story file into GitHub Issues with bidirectional linking.'
argument-hint: '<story-file-path>'
---

# GitHub Issue Onboard

Turn a local story markdown file into a tracked GitHub Issue.

## Procedure
1. Create GitHub Issue via `gh issue create --title "<title>" --body "<functional-desc>"`.
2. Add the repository permalink to the issue body or comment.
3. Update local story metadata: `| Tracker Story | [#123](https://github.com/org/repo/issues/123) |`.
4. (Optional) Rename file to append `-123.md` if configured.
5. Update parent `progress.md` and run `planning_docs_audit.py`.
