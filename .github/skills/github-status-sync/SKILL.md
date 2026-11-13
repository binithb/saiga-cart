---
name: github-status-sync
description: 'Batch-fetch GitHub Issue statuses and reconcile them with repository progress.md files.'
argument-hint: '<scope number or issue numbers>'
---

# GitHub Status Sync

Reconcile GitHub Issue states (`OPEN`, `CLOSED`, linked PR in review) with local story metadata (`Not started`, `In progress`, `In review`, `Blocked`, `Done`) and `progress.md` checkboxes.

## Command
```bash
gh issue list --state all --json number,title,state,labels
```

After updating local story `Status` fields and `progress.md` entries, run:
```bash
python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning
```

