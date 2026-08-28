---
name: jira-story-onboard
description: 'Onboard a local planning story file into Jira with complete bidirectional linking.'
argument-hint: '<story-file-path>'
---

# Jira Story Onboard

Convert an existing local story file into a fully linked Jira Story.

## Completion Contract
1. Story file's `Tracker Story` metadata links to the created Jira ticket.
2. Story filename is renamed via `git mv` to append `-<JIRA-KEY>.md`.
3. Jira issue includes a remote link back to the repository story markdown permalink.
4. All repository references (`progress.md`, `plan.md`) are updated to the new path.
5. `planning_docs_audit.py` passes cleanly.
