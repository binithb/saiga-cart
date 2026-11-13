---
name: ado-work-item-onboard
description: 'Onboard a local planning story file into Azure DevOps as a User Story or Task.'
argument-hint: '<story-file-path>'
---

# Azure DevOps Work Item Onboard

Turn a local story markdown file into a tracked Azure DevOps Work Item with bidirectional linking and explicit user confirmation.

## Mandatory 3-Step Onboarding Procedure

1. **Confirm (`ask_user`) & Create Work Item**:
   - Present the proposed title, work item type (`User Story` or `Task`), and functional description via `ask_user`.
   - After user confirmation, create the work item via `az boards work-item create --title "<title>" --type "User Story" --description "<functional-desc>"` and attach the repository story permalink.
2. **Rename File (Strip Numeric Prefix + Append Key) & Update Metadata**:
   - Rename the story file via `git mv` to remove any leading numeric prefix (`01-`, `02-`) and append `-AB-<ID>.md` (e.g., `stories/01-auth-flow.md` $\rightarrow$ `stories/auth-flow-AB-123.md`).
   - Update local story metadata: `| Tracker Story | [AB#123](https://dev.azure.com/org/proj/_workitems/edit/123) |`.
3. **Update References & Validate**:
   - Update parent `progress.md`, `plan.md`, and any `Depends on` links to the new filename.
   - Run `python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning`.

