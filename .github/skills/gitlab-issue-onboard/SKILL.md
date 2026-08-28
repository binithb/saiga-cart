---
name: gitlab-issue-onboard
description: 'Onboard a local planning story file into GitLab Issues with bidirectional linking.'
argument-hint: '<story-file-path>'
---

# GitLab Issue Onboard

Turn a local story markdown file into a tracked GitLab Issue.

## Procedure
1. Create GitLab Issue via `glab issue create --title "<title>" --description "<functional-desc>"`.
2. Add the repository permalink to the issue description.
3. Update local story metadata: `| Tracker Story | [#123](https://gitlab.com/group/repo/-/issues/123) |`.
4. Update parent `progress.md` and run `planning_docs_audit.py`.
