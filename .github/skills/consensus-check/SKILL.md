---
name: consensus-check
description: 'Escalate a high-blast-radius design, architecture decision, or PR/MR to a risk-scaled multi-model deliberation panel.'
argument-hint: '[--stage plan|mr|architecture] [--blast-radius low|medium|high] [--models <m1,m2,m3>] [--arbiter <model>] [path-or-pr-ref]'
---

# Multi-Model Consensus Check (`consensus-check`)

Run a structured, multi-perspective review across distinct model families before committing to high-blast-radius plans, opening/merging pull or merge requests, or accepting architectural decisions.

## Core Design Principles

1. **Dynamic Model Selection (No Hardcoded Vendor Lock-In)**:
   - Model availability evolves rapidly. Instead of relying on static model lists in `AGENTS.md` or `docs/workflow.md`, **select models dynamically at runtime** from the models supported by the active Copilot CLI `task` tool.
   - **Cross-Family Diversity Rule**: Whenever scaling requires $\ge 2$ models, pick models from **different model families** (for example: one Anthropic Claude model, one OpenAI GPT/Codex model, and one Google Gemini or xAI Grok model) so correlated blind spots do not reinforce each other.
   - **User Override**: If the user passes `--models` or `--arbiter`, honor their explicit choice.

2. **Blast-Radius Scaling (Proportional Cost & Latency)**:
   - Scale the number of subagents and reasoning depth to the actual blast radius of the change:

| Blast Radius | Typical Triggers | Reviewer Panel | Reasoning Depth |
|---|---|---|---|
| **Low** | Single-repo change, localized bugfix, standard story plan, docs-only update, non-breaking refactor | **1 independent reviewer subagent** (distinct from the authoring model if possible) | `low` / `medium` |
| **Medium** | Multi-file feature within one repo, new internal endpoint/schema, non-trivial planning breakdown, standard PR/MR readiness | **2 independent reviewer subagents** from **2 distinct model families** run in parallel | `medium` / `high` |
| **High** | Cross-repo API/contract change, auth/security boundary, database/state migration, infrastructure/Helm/CI cutover, new ADR | **2–3 independent reviewer subagents** from **distinct model families** + **1 high-reasoning synthesis pass** | `high` / `xhigh` |

3. **Three Supported Review Stages**:
   - **Stage 1 — Plan & Story Review (`--stage plan`)**: Stress-test epic/goal `plan.md` files, story breakdowns, acceptance criteria, and dependency ordering before implementation begins.
   - **Stage 2 — PR / MR & Code Review (`--stage mr`)**: Review branch diffs (`git diff <base>...HEAD`) or open PRs/MRs for correctness, regressions, security, test adequacy, and Definition of Done compliance. (Invoked automatically by `pr-create` or standalone.)
   - **Stage 3 — Architecture & ADR Review (`--stage architecture`)**: Challenge proposed ADRs (`docs/adr/NNNN-*.md`), cross-repo `architecture.md` changes, and irreversible system trade-offs.

---

## Mandatory Evidence-Gated Verification Rules (Anti-Hallucination Guardrails)

Every reviewer subagent prompt and the final synthesis pass **must** enforce these four verification rules to eliminate speculative false positives:

1. **Verify Before Flagging (Trace the Full Execution Path)**:
   - Never flag a finding based purely on an isolated diff hunk or surface pattern match.
   - Before raising any finding, read the surrounding file context, caller/callee sites, helper scripts, or parent documentation to confirm the issue is actually reachable and not already handled upstream or downstream.
2. **Concrete Trigger & Failure Mode Required**:
   - Every `BLOCKER`, `MAJOR`, or `MINOR` finding must state:
     - **File & Line / Section**: Exact location (`path/to/file:line` or document section).
     - **Trigger Condition**: The concrete input, state, or workflow step that triggers the problem.
     - **Failure Impact**: The specific broken behavior, regression, security exposure, or contract violation that results.
   - Drop any hypothetical concern ("might fail if...", "could potentially cause issues in the future...") that lacks a concrete trigger in the repository's actual architecture.
3. **Respect Repository Scope & Intentional Trade-Offs**:
   - Check `AGENTS.md`, `docs/architecture.md`, `docs/workflow.md`, and relevant ADRs/stories before flagging missing abstractions.
   - Do not penalize intentional design boundaries (e.g., stdlib-only Python scripts, thin markdown templates, or scoped single-story deliverables) as architectural defects.
4. **Strict Severity Calibration**:
   - **`BLOCKER`**: Proven bug, data loss, security vulnerability, broken build/test, or direct contract/AC violation that **must** be fixed before proceeding.
   - **`MAJOR`**: High-confidence edge-case defect, missing critical test coverage for new logic, or significant maintainability/cross-repo hazard.
   - **`MINOR`**: Non-blocking improvement, localized clarity gap, or minor edge case with a safe fallback.
   - **`NIT`**: Purely stylistic or optional polish (never blocks approval).

---

## Workflow

### Step 1: Assemble the Review Brief & Determine Blast Radius

1. Identify the review stage (`plan`, `mr`, or `architecture`) and inspect the target artifacts or git diff.
2. Classify the blast radius (`Low`, `Medium`, or `High`) using the scaling table above (unless explicitly specified by the user).
3. Build a self-contained **Review Brief** containing:
   - Goal / story / ADR context and acceptance criteria.
   - Exact file paths or `git diff` scope to inspect.
   - Key invariants to check for the active stage:
     - *Stage 1 (`plan`)*: scope completeness, dependency order, missing edge cases, testability of ACs.
     - *Stage 2 (`mr`)*: logic bugs, security/auth regressions, error handling, cross-repo compatibility, test coverage.
     - *Stage 3 (`architecture`)*: failure domains, operational complexity, migration safety, rejected alternatives.

### Step 2: Dispatch Independent Reviewer Subagents in Parallel

1. Select the panel of models from currently available `task` tool models (using `explore` or `code-review` agent types for read-only inspection) following the **Cross-Family Diversity Rule**.
2. Launch all reviewer subagents **in parallel in a single turn**, instructing each reviewer to:
   - Independently inspect the target files/diff using read-only tools.
   - Apply the **Mandatory Evidence-Gated Verification Rules** (verify full path before flagging; include file/line, concrete trigger, and impact).
   - Return structured findings categorized by severity (`BLOCKER`, `MAJOR`, `MINOR`, `NIT`) plus an overall verdict (`APPROVE`, `APPROVE_WITH_RECOMMENDATIONS`, or `REQUEST_CHANGES`).

### Step 3: Arbiter Synthesis & Deduplication

1. Collect all subagent responses and perform an **Evidence-Gated Synthesis**:
   - **Deduplicate** overlapping findings raised by multiple models, noting where multiple independent models converged (`[Consensus: 2/2]` or `[Consensus: 3/3]`).
   - **Verify & Filter Disagreements**: When only one model flags a `BLOCKER` or `MAJOR` issue, directly inspect the cited file and line to verify whether the claim holds against the actual codebase. Discard disproven hallucinations and retain verified single-model catches.
2. Present a concise **Consensus Report**:
   - **Panel & Blast Radius**: Stage, Blast Radius (`Low`/`Medium`/`High`), and Models used.
   - **Verdict**: `APPROVE`, `APPROVE WITH RECOMMENDATIONS`, or `CHANGES REQUIRED`.
   - **Verified Findings Table**: Severity, Consensus count, Location, Issue & Trigger, and Concrete Fix.
3. **Interactive Resolution**:
   - If `BLOCKER` or `MAJOR` findings remain, offer to apply surgical fixes immediately (following **ASD-STE100 plain-language rules** whenever documentation, plans, stories, or ADRs are updated) or ask the user via `ask_user` how they wish to proceed.

