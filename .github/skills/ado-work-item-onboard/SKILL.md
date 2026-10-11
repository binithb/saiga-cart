---
name: ado-work-item-onboard
description: 'Onboard a local planning story file into Azure DevOps as a User Story or Task.'
argument-hint: '<story-file-path>'
---

# Azure DevOps Work Item Onboard

Turn a local story markdown file into a tracked Azure DevOps Work Item.

## Procedure
1. Create Work Item via `az boards work-item create --title "<title>" --type "User Story" --description "<functional-desc>"`.
2. Add the repository permalink as a hyperlink on the work item.
3. Update local story metadata: `| Tracker Story | [AB#123](https://dev.azure.com/org/proj/_workitems/edit/123) |`.
4. Update parent `progress.md` and run `planning_docs_audit.py`.
