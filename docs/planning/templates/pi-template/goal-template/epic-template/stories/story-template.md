# Story: Title

| Field | Value |
|---|---|
| Epic | [epic-slug](../plan.md) |
| Tracker Story | TBD — replace with link to remote ticket once created (and append `-KEY` to filename if configured) |
| Status | Not started |
| Effort | Small |
| Definition of Ready | Draft |

<!-- Stories are normally independent. Only when another story in this epic genuinely
     blocks starting this one, add a Depends on row linking the real story filename. -->

## Description

High-level functional objective and business context (synced to Issue Tracker description).

## Technical Context & Scope

- **Dependencies & Sibling Stories**: link real sibling story files here (keep technical cross-links in repo markdown)
- **Affected Repositories / Components**: `repo-name`, `path/to/module/`
- **Architecture / ADR References**: link applicable `docs/adr/NNNN-title.md`
- **Technical Details**: Specific architectural considerations, data formats, or constraints.
- **Decisions / Assumptions**: Decisions already made and material assumptions the implementer may rely on.

## Non-Goals & Safety Rails

- Explicitly excluded behavior, repositories, environments, or follow-up work.
- State, secret, migration, destructive-operation, and rollback constraints.

## Acceptance Criteria

### Functional (synced to Issue Tracker)
- [ ] User-facing or functional behavior delivered.

### Technical & Verification (local source of truth)
- [ ] Exact command, required environment/credentials, and expected outcome.
- [ ] CI, test, build, or manual evidence required when local validation is insufficient.

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
