---
name: github-status-sync
description: 'Batch-fetch GitHub Issue statuses and reconcile them with repository progress.md files.'
argument-hint: '<scope number or issue numbers>'
---

# GitHub Status Sync

Reconcile GitHub Issue states (`OPEN`, `CLOSED`) with local story metadata and `progress.md` checkboxes.

## Command
```bash
gh issue list --state all --json number,title,state
```
