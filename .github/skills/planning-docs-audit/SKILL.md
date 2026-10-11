---
name: planning-docs-audit
description: 'Audit planning document hierarchy, story metadata, link integrity, and ADR indexes.'
argument-hint: '[--scope <scope>] [--json]'
---

# Planning Docs Audit Skill

Validate the integrity of all planning documents, story files, Definition of Ready metadata, dependency graphs, and ADR indexes.

## Usage

```bash
python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py
```

Options:
- `--scope <scope>`: Scopes check to a specific sprint or increment directory.
- `--json`: Outputs machine-readable JSON.
