# Story: Title

| Field | Value |
|---|---|
| Epic | [epic-slug](../plan.md) |
| Tracker Story | TBD — replace with link to remote ticket once created (and append `-KEY` to filename if configured) |
| Status | Not started |
| Effort | Small |
| Definition of Ready | Draft |

<!-- Stories are normally independent. Only when another story in this epic genuinely
     blocks starting this one, add a Depends on row linking the real story filename.
     Writing standard: Follow ASD-STE100 plain-language rules (active voice, short direct
     sentences, one main requirement per bullet, consistent GLOSSARY.md terms). -->

## Description

High-level functional objective and business context (synced to Issue Tracker description).

## Technical Context & Scope

- **Dependencies & Sibling Stories**: link real sibling story files here (keep technical cross-links in repo markdown)
- **Affected Repositories / Components**: `repo-name`, `path/to/module/`
- **Architecture / ADR References**: link applicable `docs/adr/NNNN-title.md`
- **Technical Details**: Specific architectural considerations, data formats, or constraints.

## Decisions / Assumptions

- Decisions already made and material assumptions the implementer may rely on.

## Readiness gaps

<!-- Leave empty once Definition of Ready is Done. While Draft or Pending Clarification,
     list concrete human decisions or missing inputs as `- <gap>` bullets. -->

## Non-Goals & Safety Rails

- Explicitly excluded behavior, repositories, environments, or follow-up work.
- State, secret, migration, destructive-operation, and rollback constraints.

## Acceptance Criteria

<!-- Keep Acceptance Criteria outcome-focused: describe observable functional behavior
     and verifiable contracts rather than internal variable names or line-by-line code edits. -->

### Functional (synced to Issue Tracker)
- [ ] User-facing or functional behavior delivered.

### Technical & Verification (local source of truth)
- [ ] Observable technical contract and expected verification outcome.

## Implementation Steps & Checkpoints

1. Step 1 — bounded change in target repository/module.
2. Step 2 — run deterministic verification command (`pytest`, `npm test`, `python3 ...`).

## Definition of Ready (DoR)

- [ ] Outcome, scope, and non-goals are explicit.
- [ ] Target repositories and bounded implementation surfaces are identified.
- [ ] The story can start independently, or its real blockers are recorded.
- [ ] Required decisions and material assumptions are recorded.
- [ ] Functional and technical acceptance criteria are separated.
- [ ] Verification commands, prerequisites, and expected outcomes are defined.
- [ ] Safety, state, secrets, migration, and rollback concerns are addressed.
- [ ] Effort is `Small` or `Medium` and the story is independently executable.
- [ ] No unresolved human clarification blocks implementation.
