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
| **Acceptance Criteria** | Observable user/business acceptance criteria | Observable technical contracts; concrete commands live in `## Implementation Steps & Checkpoints` |
| **Dependencies** | Cross-team blockers only | Markdown links to prerequisite local stories & ADRs |
| **Architecture / ADRs** | High-level summary | Direct relative links to `docs/adr/` and architecture notes |

### Story Status Lifecycle & 3-Step Onboarding

- **Allowed Status Vocabulary**: `Not started` | `In progress` | `In review` | `Blocked` | `Done`
  - Set `Status` to `In review` once a PR/MR is opened (`pr-create`), and `Done` (with `[x]` in `progress.md`) once merged.
- **Mandatory Human Confirmation Gate (`ask_user` + `--confirm`)**:
  - Never create or mutate remote issues, remote links, worklogs, or PR/MR comments without presenting a preview card via `ask_user` and receiving explicit approval.
- **3-Step Tracker Onboarding**:
  1. Confirm ticket details via `ask_user` and create the remote issue.
  2. Rename the local story file via `git mv` to strip any leading numeric prefix (`01-`, `02-`) and append `-<TICKET-KEY>.md` (e.g., `stories/01-auth-flow.md` $\rightarrow$ `stories/auth-flow-PROJ-123.md`), updating `Tracker Story` metadata and all `progress.md` / `plan.md` / `Depends on` links.
  3. Attach the repository story markdown permalink to the remote ticket and run `planning_docs_audit.py --fail-on-warning`.
- **Recurring Epics (`Recurring | Yes`)**:
  - Operational or continuous-improvement epics that carry across timeboxes set `| Recurring | Yes |` in their `plan.md` metadata table so `planning-scaffold` can carry them and any unfinished stories forward into the next timebox.

### Plain-Language Writing Standards (ASD-STE100)

All plans, stories, ADRs, and PR/MR descriptions follow **ASD-STE100 simplified technical English**:
- Use active voice, specific verbs, short sentences, and one main requirement per bullet.
- Use canonical domain terms from `GLOSSARY.md` consistently.
- Write **outcome-focused Acceptance Criteria** that specify observable functional behavior and verifiable contracts—not internal variable names or line-by-line code edits. Place implementation steps and exact verification commands in `## Implementation Steps & Checkpoints`.

### Local Authentication & API Tokens (Skills & Autonomous Agents)

Skills (e.g. `jira-status-sync`, `gitlab-issue-onboard`, `ado-work-item-onboard`, `pr-create`) require API tokens to read and write remote resources. Never commit credentials to git.

1. **Local Credentials File**: Copy the template `.env.example` to `.env.local` in the workspace root (`.env.local` is git-ignored).
2. **Platform Permissions & Scopes**:

| Platform | Variable | Scope / Permissions | Token Creation URL |
|---|---|---|---|
| **Jira Cloud** | `JIRA_API_TOKEN`<br>`JIRA_USER_EMAIL` | Scopes: `read:jira-work`, `write:jira-work` | [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens) |
| **GitLab** | `GITLAB_TOKEN` (or `glab auth login`) | `api` (or `read_api` + `write_repository`) | [GitLab Access Tokens](https://gitlab.com/-/user_settings/personal_access_tokens) |
| **Azure DevOps** | `AZURE_DEVOPS_EXT_PAT` (or `az devops login`) | `Work Items (Read & write)`<br>`Code (Read & write)` | [Azure DevOps PATs](https://dev.azure.com/) (User Settings &rarr; Personal Access Tokens) |
| **GitHub** | `GITHUB_TOKEN` (or `gh auth login`) | `repo` (or fine-grained: Issues, PRs, Contents) | [GitHub Token Settings](https://github.com/settings/tokens) |

Run `python scripts/workspace_doctor.py` to verify whether credentials are correctly loaded for your configured tracker.

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

## 3. Implementation Disciplines (Zen of Python Inspired)

### Explicit, Simple, and Flat
- Explicit is better than implicit; simple is better than complex; flat is better than nested.
- If an implementation is hard to explain, simplify the design before writing more code.
- Deliver the simplest complete solution without speculative parameterization or premature abstractions.

### Micro-Surgical Changes
- Touch only files required to satisfy the story's acceptance criteria.
- Do not refactor adjacent, unrelated code.
- Clean up any temporary files or orphans introduced by your own changes.

### Confused-State Gating
- In the face of ambiguity, refuse the temptation to guess. Stop and ask the developer via `ask_user` and record the decision in the story's `## Decisions / Assumptions` section.

### Verification Evidence
- Always run targeted verification tests before creating a PR/MR.
- Do not paste full command transcripts, prompts, or test outputs into PR descriptions — summarize the functional outcome cleanly.

---

## 4. Quality Gates, Deliberation & Harness² Evolution

### Pre-Flight Readiness & PR/MR Creation (`pr-create`)
`pr-create` folds Definition of Done (DoD) verification, rebase/conflict checks, and Stage 2 `consensus-check` into a single pre-flight workflow before opening a PR or MR:
1. All functional and technical acceptance criteria pass (`planning_docs_audit.py --fail-on-warning` and `validate_harness.py` in the workspace root, or the target repo's test suite).
2. Branch is rebased/mergeable against the target branch with no secrets, debug markers, or conflict markers.
3. Multi-model `consensus-check` review passes (unless `--skip-consensus` is explicitly passed).
4. Developer confirms the functional summary card via `ask_user`.

### Interactive PR/MR Review (`pr-reviewer`)
Use `pr-reviewer` to fetch unresolved review threads on a GitHub PR or GitLab MR (`gitlab_mr_discussions.py`), walk through each thread or new review finding interactively via `ask_user` (`Fix + Reply`, `Reply Only`, `Skip`), apply local fixes, and batch-publish confirmed replies.

### Risk-Scaled Consensus Review (`consensus-check`)
Invoke `consensus-check` across three supported stages (**Stage 1: `plan`**, **Stage 2: `mr`**, **Stage 3: `architecture`**). Models are selected dynamically at runtime across distinct model families according to blast radius (`Low` = 1 reviewer, `Medium` = 2 reviewers from distinct families, `High` = 2–3 reviewers + arbiter synthesis), governed by the four **Mandatory Evidence-Gated Verification Rules** in [`.github/skills/consensus-check/SKILL.md`](../.github/skills/consensus-check/SKILL.md).

### Developer-Gated Harness² (`harness2`)
Use [`.github/skills/harness2/SKILL.md`](../.github/skills/harness2/SKILL.md) to keep the workspace's AI harness fast, accurate, and within context budgets (see [ADR 0003](adr/0003-developer-gated-harness2-and-context-budget.md)):
- **`h2 audit` (`validate_harness.py`)**: Enforces `AGENTS.md <= 14,000` chars, skill/script parity, `profiles.json` coverage, and Red/Green zone Frozen Verifier rules.
- **`h2 distill` (`manage_experience.py`)**: Graduates recurring failure patterns or review findings into deterministic scripts (Tier 1), skills (Tier 2), or the cross-sprint experience ledger (`docs/ai/experience.md`, Tier 3) via a plain-language explanation and `ask_user` 3-Line Evidence Audit Card.
- **`h2 probe`**: Exception-only dual-hypothesis recovery (`INV` vs. `DOM` in isolated `git worktree` checkouts) when a story verification command fails repeatedly ($\ge 2$ times).

