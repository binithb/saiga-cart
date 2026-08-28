---
name: story-refiner
description: 'Batch-review and refine stories in a planning scope until they are ready for autonomous AI execution. Gathers human decisions, sizes stories, and produces an ordered implementation queue.'
argument-hint: '[scope number, epic path, or story path]'
---

# Story Refiner Skill

Refine a planning scope into bounded, unambiguous technical story specifications that AI agents can execute independently.

## Definition of Ready (DoR) Checklist

A story is DoR `Done` only when:
1. **Outcome & Boundary**: Functional outcome and scope boundaries are explicit.
2. **Affected Surfaces**: Target repositories, modules, and directories are identified.
3. **Independence**: Can start independently or real blockers are recorded in `Depends on`.
4. **Decisions Recorded**: Architectural choices and assumptions are documented in the story file.
5. **Acceptance Criteria**: Functional criteria and technical verification commands are defined.
6. **Effort Sizing**: Sized as `Small` or `Medium`. `Large` stories must be split.

## Procedure

1. **Baseline Assessment**:
   ```bash
   python3 .github/skills/story-refiner/scripts/story_readiness.py --scope <scope>
   ```
2. **Derive Facts from Code**: Inspect repository code before asking human questions.
3. **Grouped Clarifications**: Collect missing human/product decisions in structured rounds. Record answers in the story's **Decisions / Assumptions** section.
4. **Decompose Large Stories**: Split `Large` stories into `Small`/`Medium` children.
5. **Final Queue Output**: Render the final readiness dashboard and execution queue.
