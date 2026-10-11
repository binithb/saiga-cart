<!--
Copy this directory to ../<NN>/ to start a new program increment, then copy
goal-template/ to <goal-slug>/ for each goal. Epics nest under a goal; stories
are files under an epic.
-->

# PI NN

- **Window**: YYYY-MM-DD → YYYY-MM-DD ({{CADENCE_DURATION|default("2 months")}})
- **Status**: Planning | In progress | Done
- **Tracker Mapping**: _{{TRACKER_NAME|default("Jira")}} increment / release mapping — TBD_

One-line theme for the increment.

## Goals

Each goal is a directory (`<goal-slug>/`) with its own `plan.md` and
`progress.md`, delivered by one or more epics nested beneath it.

| Goal | Status | Epics |
|---|---|---|
| [Goal title](goal-template/plan.md) | Not started | epic-slug |

## Notes / risks

_Increment-level risks, dependencies, or context. None yet._
