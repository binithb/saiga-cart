---
name: jira-story-onboard
description: 'Onboard a local planning story file into Jira with complete bidirectional linking.'
argument-hint: '<story-file-path>'
---

# Jira Story Onboard

Convert an existing local story file into a fully linked Jira Story with explicit human confirmation before mutating Jira.

## Mandatory 3-Step Onboarding Procedure

1. **Pre-Flight Confirmation (`ask_user`) & Issue Creation**:
   - Present the proposed Jira project, issue type (`Story`), summary, parent Epic key, and high-level functional description to the user via `ask_user`.
   - Only after explicit approval, create the Jira ticket (passing `--confirm` if using `jira_create_issue.py`).
2. **Rename File (Strip Numeric Prefix + Append Key) & Update Metadata**:
   - Rename the story file with `git mv` so any leading numeric prefix (`01-`, `02-`, etc.) is removed and `-<JIRA-KEY>.md` is appended:
     - Example: `stories/01-token-rotation.md` $\rightarrow$ `stories/token-rotation-PROJ-123.md`
   - Update `| Tracker Story | [PROJ-123](https://<jira-host>/browse/PROJ-123) |` in the story file.
   - Update all relative links in sibling `progress.md`, `plan.md`, and `Depends on` fields to point to the renamed file.
3. **Link Back to Repository & Validate**:
   - Attach a remote Web Link on the Jira ticket pointing to the Git repository story markdown permalink (after `ask_user` confirmation and passing `--confirm` to `jira_remote_links.py --add`).
   - Run deterministic validation:
     ```bash
     python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning
     ```

