---
name: jira-status-sync
description: 'Batch-fetch Jira statuses for story tickets and reconcile them with repository progress.md files.'
argument-hint: '<PI/sprint scope number or list of Jira keys>'
---

# Jira Status Sync

Reconcile remote Jira issue statuses with local story files and `progress.md` checkboxes.

## Status Mapping Rules

| Jira Status Category / Name | Local Story `Status` | `progress.md` Checkbox |
|---|---|---|
| `To Do`, `Open`, `Backlog`, `New` | `Not started` | `- [ ]` |
| `In Progress`, `Active`, `Development` | `In progress` | `- [ ]` |
| `In Review`, `Code Review`, `Peer Review`, `PR Open` | `In review` | `- [ ]` |
| `Blocked`, `Impediment`, `On Hold` | `Blocked` | `- [ ]` |
| `Done`, `Closed`, `Resolved` | `Done` | `- [x]` |

## Procedure

1. **Batch-Fetch Statuses (Read-Only)**:
   ```bash
   python3 .github/skills/jira-status-sync/scripts/jira_bulk_status.py <JIRA_KEYS...>
   ```
2. **Reconcile Local Story & Progress Files**:
   - Update `| Status | <Mapped Status> |` in each drifted story file and synchronize its checkbox and trailing status label (`— <Mapped Status>`) in `progress.md`.
   - Note: Never mutate remote Jira statuses or log work without explicit interactive user confirmation (`ask_user` / `AskUserQuestion` or direct approval) and `--confirm`.
3. **Validate**:
   ```bash
   python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning
   ```

