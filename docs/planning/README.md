# Planning & Delivery Framework

This directory organizes software delivery into structured, repo-side planning trees.
Keeping plans, progress, and architectural decision records in markdown gives AI agents and human developers durable, structured context.

## Active Framework: {{PLANNING_FRAMEWORK_NAME|default("Program Increments (SAFe)")}}

- **Current Timebox**: [{{CURRENT_CADENCE_TITLE|default("Cycle / Increment")}}](./01/README.md)
- **Hierarchy**: `{{CADENCE_UNIT|default("Increment")}}` → `{{CONTAINER_UNIT|default("Goal/Epic")}}` → `{{LEAF_UNIT|default("Story/Task")}}`

## Document Altitudes

Within each epic or delivery unit, documents are partitioned by altitude:

| Document | Altitude | Content |
|---|---|---|
| `plan.md` | Strategic / 30-second view | Metadata, TL;DR, high-level approach steps, verification criteria. |
| `progress.md` | Real-time tracking | Checkbox list of child stories/tasks. |
| `architecture.md` | Current state | Component boundaries, data flows, cross-repo contracts. |
| `design-notes.md` | (Optional) Deep dive | Phase-by-phase implementation blueprints, schemas, migration sequencing. |
| `stories/*.md` | Leaf technical unit | Technical context, DoR checklist, exact verification commands, test criteria. |

## Creating New Planning Artifacts

Use the `planning-scaffold` agent skill:
```text
@copilot /planning-scaffold Start a new increment / sprint / epic ...
```
or manually copy from `templates/`.
