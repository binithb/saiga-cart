---
name: jira-status-sync
description: 'Batch-fetch Jira statuses for story tickets and reconcile them with repository progress.md files.'
argument-hint: '<PI/sprint scope number or list of Jira keys>'
---

# Jira Status Sync

Reconcile remote Jira issue statuses with local story files and `progress.md` checkboxes.

## Command
```bash
python3 .github/skills/jira-status-sync/scripts/jira_bulk_status.py <JIRA_KEYS...>
```
