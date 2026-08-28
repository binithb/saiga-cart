# Workflow & Conventions

How we work across repositories in this workspace.

---

## 1. Issue Tracking & Project Management

- **External Tracker as Task Tracker**: Unchecked boxes in `progress.md` map to issues/stories in the configured tracker (Jira, GitHub Issues, GitLab Issues, or Azure DevOps).
- **`progress.md` vs. Remote Tracker**:
  - `progress.md` is the repo-side dashboard answering *"Where are we across the whole initiative?"*
  - Remote issues answer *"Who owns this and what is the stakeholder requirement?"*
- **Bidirectional Linking**:
  - Remote issues link directly to their corresponding repo Markdown file permalinks.
  - Repo story files link to the remote issue URL in their metadata table.
  - Commit messages, branches, and PR/MR titles reference the ticket identifier (e.g. `PROJ-123` or `#123`).

### Content Boundary: Story File vs. Remote Ticket

| Content Dimension | Remote Issue Tracker | Local Story File (`docs/planning/.../stories/*.md`) |
|---|---|---|
| **Audience** | Product Owner, QA, Stakeholders | AI Agent, Software Engineer |
| **Summary & Scope** | High-level user story / functional requirement | Deep technical context, affected directories & repos |
| **Acceptance Criteria** | Observable user/business acceptance criteria | Concrete verification commands (`pytest`, `npm test`, `terraform plan`) |
| **Dependencies** | Cross-team blockers only | Markdown links to prerequisite local stories & ADRs |
| **Architecture / ADRs** | High-level summary | Direct relative links to `docs/adr/` and architecture notes |

---

## 2. Autonomous AI Definition of Ready (DoR) & Sizing

To enable AI agents to execute tasks independently without getting stuck or hallucinating requirements:

### Upfront Story Refinement (`story-refiner` skill)
Run the `story-refiner` skill across planned work before starting implementation. It:
1. Inspects repository code to extract facts automatically.
2. Identifies genuinely human/product decisions and asks structured, grouped questions.
3. Records all decisions into the story's **Decisions / Assumptions** section so they are permanent.

### Sizing Rules & Decomposition
- **`Small`**: Single localized concern with straightforward verification (1 MR/PR).
- **`Medium`**: Bounded multi-file or single-component change with clear verification.
- **`Large`**: **Split Required Threshold**. High-risk, multi-stage, or uncertain scope. Must be split into `Small` or `Medium` children before being marked DoR `Done`.

### Independence by Default
Stories are independent by default and can be picked up in parallel. Add `| Depends on | [prereq](prereq.md) |` only when work literally cannot start until the prerequisite is completed.

---

## 3. Implementation Disciplines

### Micro-Surgical Changes
- Touch only files required to satisfy the story's acceptance criteria.
- Do not refactor adjacent, unrelated code.
- Clean up any temporary files or orphans introduced by your own changes.

### Simplicity First
- Deliver the simplest complete solution.
- Avoid speculative parameterization or abstractions not needed by the current story.

### Verification Evidence
- Always run targeted verification tests before creating a PR/MR.
- Do not paste full command transcripts, prompts, or test outputs into PR descriptions — summarize the functional outcome cleanly.

---

## 4. Quality Gates & Deliberation

### Definition of Done (DoD) Gate (`pr-readiness-check`)
Before opening or merging a PR/MR, ensure:
1. All technical acceptance criteria pass.
2. Documentation and architecture notes are updated if reality changed.
3. Tests covering the new/changed code are passing.
4. No secrets, debug logs, or temporary code are committed.

### Risk-Scaled Consensus Review (`consensus-check`)
For high-stakes decisions (database schema migrations, security-sensitive auth flows, major infrastructure changes), invoke the multi-model consensus skill to deliberate across diverse perspectives before execution.
