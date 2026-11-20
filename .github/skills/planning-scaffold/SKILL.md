---
name: planning-scaffold
description: 'Create or extend planning structures from committed templates. Use when asked to start a new cycle/sprint/PI, add a goal/epic, create story files, or update planning indexes.'
argument-hint: '<timebox, epic, or story details>'
---

# Planning Scaffold Skill

Create and structure planning artifacts under `docs/planning/` using committed templates in `docs/planning/templates/`.

## Conventions & Rules

1. **ASD-STE100 Plain-Language Writing**:
   - Write all plan summaries, scope boundaries, and story Acceptance Criteria in clear, active-voice sentences (one main requirement per bullet, consistent terms from `GLOSSARY.md`).
   - Keep Acceptance Criteria outcome-focused; place file-level steps and verification commands in `## Implementation Steps & Checkpoints`.
2. **Story Filenames & Ordering**:
   - Story execution order is defined by the checklist order in the parent `progress.md` and explicit `Depends on` links—not by filename prefixes.
   - Pre-onboarding stories may use `<story-slug>.md` (or temporary `<NN>-<story-slug>.md`); once onboarded to an issue tracker, the filename becomes `<story-slug>-<TICKET-KEY>.md` with any leading numeric prefix (`01-`, `02-`) removed.
3. **Recurring Epics (`Recurring | Yes`) & Backlog Scratchpads**:
   - Epics that carry over across timeboxes (such as tech-debt, security patching, operational maintenance, or Harness² evolution) set `| Recurring | Yes |` in their epic `plan.md` metadata table.
   - When scaffolding a new timebox/PI/sprint, inspect the immediately preceding timebox for epics with `| Recurring | Yes |` and offer via interactive user confirmation (`ask_user` / `AskUserQuestion` or direct prompt) to carry them forward into the new timebox, migrating any unfinished stories (`Status != Done`) and optional `stories/backlog-scratchpad.txt` notes.

## Procedure

1. **Inspect Parent & Prior Timebox Context**:
   - Read the immediate parent `plan.md` and `progress.md` to prevent slug collisions.
   - When starting a new timebox, check the previous timebox for recurring epics (`| Recurring | Yes |`) or unfinished stories to carry over.
2. **Copy & Populate Template**:
   - Copy the matching template from `docs/planning/templates/` into the target directory.
3. **Clean Placeholders**:
   - Replace template markers (`epic-slug`, `Title`, `NN`, `TBD`) with concrete values.
4. **Update Parent Indexes**:
   - For a new timebox/increment: add a row to `docs/planning/README.md`.
   - For a new epic: add to the parent plan table and `progress.md`.
   - For a new story: add its checklist link (`- [ ] [Title](stories/<slug>.md) — Not started`) to the epic `progress.md` in delivery order.
5. **Validate**:
   ```bash
   python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning
   ```

