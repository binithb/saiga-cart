---
name: pr-readiness-check
description: 'Assess whether a local branch or open PR/MR meets the Definition of Done prior to review or merge.'
argument-hint: '[--dir <repo-path>] [--target-branch <branch>]'
---

# PR / MR Readiness Check (Definition of Done)

Performs deterministic gates before submitting changes for human review.

## Gate Checklist
- [ ] **Clean Branch State**: No uncommitted changes, stashes, or merge conflict markers.
- [ ] **Tests Passing**: Smallest targeted test suite covering modified code passes completely.
- [ ] **No Leakage**: No secrets, temporary test fixtures, debug statements, or orphan files.
- [ ] **Architecture Reality**: If component contracts changed, `docs/architecture.md` is updated.
- [ ] **Clean Commit History**: Conventional commit messages referencing ticket identifiers.
