---
name: planning-scaffold
description: 'Create or extend planning structures from committed templates. Use when asked to start a new cycle/sprint/PI, add a goal/epic, create story files, or update planning indexes.'
argument-hint: '<timebox, epic, or story details>'
---

# Planning Scaffold Skill

Create and structure planning artifacts under `docs/planning/` using committed templates:
- `docs/planning/templates/`

## Procedure

1. **Inspect Parent Context**: Read the immediate parent plan and progress files to prevent slug or numbering collisions.
2. **Copy & Populate Template**: Copy the matching template from `docs/planning/templates/` into the target directory.
3. **Clean Placeholders**: Replace template markers (e.g., `epic-slug`, `Title`, `NN`) with actual values.
4. **Update Parent Indexes**:
   - For new timebox/increment: add row to `docs/planning/README.md`.
   - For new epic: add to parent plan table and `progress.md`.
   - For new story: add link to epic `progress.md` in delivery order.
5. **Validate**:
   ```bash
   python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py
   ```
