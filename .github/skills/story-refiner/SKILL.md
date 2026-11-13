---
name: story-refiner
description: 'Batch-review and refine stories in a planning scope until they are ready for autonomous AI execution. Gathers human decisions, sizes stories, and produces an ordered implementation queue.'
argument-hint: '[scope number, epic path, or story path]'
---

# Story Refiner Skill

Refine a planning scope into bounded, unambiguous technical story specifications that AI agents can execute independently.

## Writing & Plain-Language Standards (ASD-STE100)

All story descriptions, Decisions / Assumptions, Acceptance Criteria, and Implementation Steps must follow **ASD-STE100 plain-language rules**:
- Use active voice, short direct sentences, and one main requirement per bullet.
- Use consistent domain terms from `GLOSSARY.md` (when present).
- **Acceptance Criteria must describe observable functional outcomes and verifiable contracts**—not line-by-line code edits, internal variable names, or private helper signatures.
- Put concrete verification commands and ordered implementation checkpoints in **`## Implementation Steps & Checkpoints`**.

## Definition of Ready (DoR) Checklist

A story is DoR `Done` only when:
1. **Outcome & Boundary**: Functional outcome and scope boundaries are explicit.
2. **Affected Surfaces**: Target repositories, modules, and directories are identified.
3. **Independence**: Can start independently or real blockers are recorded in `Depends on`.
4. **Decisions Recorded**: Architectural choices and assumptions are documented in the story file (`## Decisions / Assumptions`), and `## Readiness gaps` is empty.
5. **Acceptance Criteria & Checkpoints**: Functional outcome criteria and concrete technical verification commands (`## Implementation Steps & Checkpoints`) are defined.
6. **Effort Sizing**: Sized as `Small` or `Medium`. `Large` stories must be split (`Large` cannot have `Definition of Ready = Done`).

## Procedure

1. **Baseline Assessment**:
   ```bash
   python3 .github/skills/story-refiner/scripts/story_readiness.py --scope <scope>
   ```
2. **Derive Technical Facts from Code First**:
   - Inspect target sibling repositories, schemas, configs, and existing tests before asking the user. Never ask the user a question that the repository code already answers.
3. **Grouped Human Clarifications (`ask_user`)**:
   - Collect remaining product, scope, or trade-off decisions in structured `ask_user` rounds.
   - Record resolved answers in `## Decisions / Assumptions` and remove resolved items from `## Readiness gaps`.
4. **Decompose Large Stories**:
   - Split `Large` stories into `Small` or `Medium` child stories, update `progress.md` and `Depends on` links, and run `planning_docs_audit.py`.
5. **Final Queue Output**:
   - Re-run `story_readiness.py` and `planning_docs_audit.py --fail-on-warning` and present the final readiness dashboard and ordered implementation queue.

