---
name: planning-docs-audit
description: 'Audit planning document hierarchy, story metadata, link integrity, and ADR indexes.'
argument-hint: '[--scope <scope>] [--fail-on-warning] [--json]'
---

# Planning Docs Audit Skill

Validate the integrity of all planning documents, story files, Definition of Ready metadata, dependency graphs, progress status labels, and ADR indexes.

## What It Checks

- **Progress & Story Linking**: Every `stories/*.md` (or `tasks/*.md`, `scopes/*.md`) file is linked once in its sibling `progress.md`, and every link resolves.
- **Status Vocabulary & Checkbox Parity**: Story `Status` is one of `Not started`, `In progress`, `In review`, `Blocked`, or `Done`; `Done` stories are checked (`[x]`), non-`Done` stories remain unchecked (`[ ]`), and optional trailing status labels (`— <Status>`) match ALLOWED_STATUSES and the story's `Status`.
- **Definition of Ready (DoR) & Effort Rules**: `Effort` (`Small`, `Medium`, `Large`) and `Definition of Ready` (`Draft`, `Pending Clarification`, `Done`) are paired; `Large` stories cannot have `Definition of Ready = Done`.
- **Dependency DAG & Tracker Keys**: `Depends on` links resolve within the same container without cycles; tracker keys are not duplicated across stories.
- **ADR Index Parity**: Every `docs/adr/[0-9][0-9][0-9][0-9]-*.md` (excluding `0000-template.md`) is linked in `docs/adr/README.md`.

## Usage

```bash
python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning
```

Options:
- `--scope <scope>`: Scopes check to a specific sprint or increment directory.
- `--fail-on-warning`: Returns non-zero exit code if any `WARNING` is present.
- `--json`: Outputs machine-readable JSON.

