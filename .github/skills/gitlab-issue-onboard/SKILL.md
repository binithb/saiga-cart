---
name: gitlab-issue-onboard
description: 'Onboard a local planning story file into GitLab Issues with bidirectional linking.'
argument-hint: '<story-file-path>'
---

# GitLab Issue Onboard

Turn a local story markdown file into a tracked GitLab Issue with bidirectional linking and explicit user confirmation.

## Mandatory 3-Step Onboarding Procedure

1. **Confirm (`ask_user`) & Create GitLab Issue**:
   - Show the proposed issue title and functional description (including the repository story permalink) via `ask_user`.
   - After user confirmation, run:
     ```bash
     glab issue create --title "<title>" --description "<functional-desc-with-story-permalink>"
     ```
2. **Rename File (Strip Numeric Prefix + Append Key) & Update Metadata**:
   - Rename the story file via `git mv` to remove any leading numeric prefix (`01-`, `02-`) and append `-GL-<IID>.md` (e.g., `stories/01-auth-flow.md` $\rightarrow$ `stories/auth-flow-GL-123.md`).
   - Update local story metadata: `| Tracker Story | [#123](https://gitlab.com/group/repo/-/issues/123) |`.
3. **Update References & Validate**:
   - Update parent `progress.md`, `plan.md`, and any `Depends on` links to the new filename.
   - Run `python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning`.

