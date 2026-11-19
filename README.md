# 🛷 saiga-cart: AI-Native Multi-Repository Workspace

<p align="center">
  <img src="docs/presentation/assets/saiga-cart-banner.svg" alt="saiga-cart Banner: A cart pulled by 3 rows of saigas across a multi-repository workspace" width="100%">
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Presentation](https://img.shields.io/badge/Presentation-GitHub%20Pages-brightgreen)](https://binithb.github.io/saiga-cart/)

An open-source template and interactive bootstrapper for **scaling AI development across multiple repositories**.

> 🌐 **Interactive Slide Deck & Overview**: Explore the live visual presentation and architecture walkthrough at **[https://binithb.github.io/saiga-cart/](https://binithb.github.io/saiga-cart/)**.

Named after the enduring steppe antelope (**saiga**) and the collaborative load pulling of a team (**cart**), `saiga-cart` gives AI coding assistants—generating dedicated instruction files for **GitHub Copilot**, **Claude Code**, and **Cursor**, plus canonical `AGENTS.md` and `.code-workspace` files used by **Windsurf** and MCP-compatible agents—durable, synchronized context across multiple related repositories and structured delivery planning.

---

## Platform Support

The generator, diagnostics, clone helper, skill scripts, and test suite use the Python standard library and support **Windows, macOS, and Linux** with **Python 3.8+** and **Git** (zero external `pip` packages required; `PyYAML` is optional).
Use `python` or `python3` on macOS/Linux, or `python` / `py -3` on Windows (when executing bundled skill commands on Windows where `python3` is not aliased, substitute `python` or `py -3`).

---

## 🌟 The Two Core Capabilities

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             saiga-cart Pattern                          │
├────────────────────────────────────┬────────────────────────────────────┤
│   1. Cross-Repo AI Context         │   2. Durable Delivery Planning     │
│                                    │                                    │
│   - Multi-root IDE workspace       │   - Markdown planning hierarchy    │
│   - Unified AGENTS.md directives   │   - SAFe, Scrum, Shape Up, Kanban  │
│   - Sibling repo orchestration     │   - Definition of Ready (DoR) gates│
│   - Bounded Harness² context budget│   - Bidirectional issue sync       │
└────────────────────────────────────┴────────────────────────────────────┘
```

1. **Cross-Repo AI Context**: Open multiple sibling repositories in one unified IDE session (`.code-workspace`) with synchronized `AGENTS.md` routing, cross-repo architecture contracts (`docs/architecture.md`), and **Harness²** context-budget enforcement (`AGENTS.md <= 14,000` chars).
2. **Durable Delivery Planning**: Version ADRs, epics, story specifications, and cross-sprint lessons (`docs/ai/experience.md`) in markdown beside the code—keeping remote tickets concise for stakeholders while giving AI agents bounded, decision-complete specs.

---

## 🤔 Why saiga-cart (and When You Don't Need It)

### ✅ When you need it
- **Multi-repository architectures**: Your system spans multiple repositories (e.g., frontend, microservices, shared libraries, infrastructure) and AI agents must inspect contracts, schemas, and tests across repo boundaries simultaneously.
- **Preventing context rot & cross-session amnesia**: Instead of re-explaining architecture rules in every chat or bloating root prompt files, `saiga-cart` enforces a strict context budget (`validate_harness.py`), records durable ADRs, and distills recurring review lessons into `docs/ai/experience.md` and deterministic scripts.
- **AI-assisted delivery lifecycle**: You want AI agents to participate across the full delivery loop—auditing stories against Definition of Ready (DoR), sizing work (`Small`/`Medium`), onboarding stories to issue trackers (Jira, GitHub, GitLab, Azure DevOps), and running risk-scaled multi-model `consensus-check` panels before opening PRs/MRs.
- **Team-wide AI cockpit**: You want one reproducible bootstrapper that generates synchronized multi-root `.code-workspace` configs, tool-specific agent instructions, pruned tracker skills, and workspace health diagnostics.

### ❌ When you don't need it
- **Single-repository projects without structured AI delivery planning**: If all code lives in one repository and you don't need local DoR story gates or tracker sync, standard single-repo instruction files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`) are usually sufficient.
- **Standalone scripts or simple hobby apps**: Self-contained projects without cross-repo contracts, ADRs, or iterative planning cadences don't need a workspace orchestration layer.
- **File- or function-level AI assistance only**: If you primarily use AI as a typing assistant at the file or function level (inline autocomplete, small local refactors, or quick single-file Q&A) rather than delegating multi-file or cross-repo agentic tasks, your IDE's built-in context is already enough—shared planning harnesses, skills, and consensus panels would add unnecessary overhead.

---

## 🚀 Quickstart: Bootstrapping a New Workspace

> **💡 Recommended Folder Layout**: Set up your workspace in its own **new folder** inside a shared parent directory (e.g., `~/work/my-ai-workspace`), rather than modifying your raw `saiga-cart` clone in-place. Because sibling repositories are checked out **beside** the workspace folder (`../service-a`, `../service-b`), this keeps your multi-repo parent directory clean and organized:
> ```text
> ~/work/
> ├── saiga-cart/                # Template / generator repo (stays clean)
> ├── my-ai-workspace/           # Your generated workspace (--output ../my-ai-workspace)
> ├── service-a/                 # Cloned sibling repo 1
> └── service-b/                 # Cloned sibling repo 2
> ```

Clone `saiga-cart` inside your parent workspace directory first:
```bash
mkdir -p ~/work && cd ~/work
git clone https://github.com/binithb/saiga-cart.git
cd saiga-cart
```

### Option A: Fast Preset + `add-sibling` (Fastest & Easiest)
Generate your workspace in one command using a preset, then let your AI assistant inspect your repositories and configure everything automatically:

```bash
# Pick the preset matching your team's stack:
python bootstrap.py --preset github-scrum --output ../my-ai-workspace   # GitHub Issues + PRs + Scrum
python bootstrap.py --preset jira-safe    --output ../my-ai-workspace   # Jira Cloud + GitLab MRs + SAFe PIs
python bootstrap.py --preset ado-scrum    --output ../my-ai-workspace   # Azure DevOps Boards + Repos + Scrum

# Switch into your newly generated workspace:
cd ../my-ai-workspace
```

Open the multi-root workspace in your IDE (`code my-ai-workspace.code-workspace` for VS Code / Cursor / Windsurf), or start your terminal agent inside `../my-ai-workspace` with parent/sibling directory access enabled (e.g., `copilot --add-dir ..` or `/add-dir ../<repo-name>`), then onboard each sibling repository:

```text
# In GitHub Copilot CLI (slash skill):
/add-sibling <your-git-repo-url>

# In Claude Code, Cursor, or Windsurf chat (natural language):
Use add-sibling to onboard <your-git-repo-url>
```
```bash
# Or directly from the terminal without an AI chat session:
python bootstrap.py --add-sibling --sibling-url <your-git-repo-url> --clone
```
The `add-sibling` workflow verifies and clones the repository into `../<repo-name>`, inspects its tech stack and API contracts, asks you to confirm its architectural role (`active` or `read-only`), and remaps `AGENTS.md`, `docs/architecture.md`, `.code-workspace`, and your active tracker skills.

### Option B: Interactive Guided Wizard (Token Verification & Custom Topologies)
Prefer a guided terminal walkthrough that tests your API tokens and verifies sibling repository URLs immediately?

```bash
python bootstrap.py
# Or specify the target folder upfront:
python bootstrap.py --output ../my-ai-workspace
```

1. **Preset or Custom Mode**: Pick a Quick Preset (`github-scrum`, `jira-safe`, `ado-scrum`) or **Custom Setup**.
2. **Workspace Identity & Target Location**: Set workspace name, organization, and target folder (defaults to a clean `../<slug>` sibling directory, or in-place).
3. **Planning, Tracker & VCS**: Choose Scrum, SAFe, Shape Up, or Kanban; Jira, GitHub, GitLab, Azure DevOps, or local markdown; and your VCS host.
4. **Authentication & Live Check**: Save tokens to `.env.jira`, `.env.azure`, `.env.github`, `.env.gitlab`, or `.env.local` (gitignored) and test connectivity against the remote API, or skip for later.
5. **Sibling Repositories**: Add sibling Git URLs (verified via `git ls-remote`) and optionally clone them immediately into `../<repo-name>`, or skip and run `add-sibling` later.

### Option C: Declarative Config (`workspace.yaml`) & Headless CLI Reference
Commit or share a `workspace.yaml` manifest (see `workspace.yaml.template`) for repeatable team or CI bootstrapping:

```bash
# Generate a workspace deterministically from a YAML/JSON manifest
python bootstrap.py --config workspace.yaml --output ../my-ai-workspace

# Headless default generation (uses github-scrum unless --preset is specified)
python bootstrap.py --non-interactive --output ../my-ai-workspace

# Clone all configured siblings in an existing workspace (injects PATs from .env* files)
cd ../my-ai-workspace && python scripts/clone_siblings.py
```

---

## ⏱️ Your First 5 Minutes (Day-1 AI Workflow)

Once your workspace is created (`cd ../my-ai-workspace`), follow this progression in your AI coding assistant:

| Step | What You Type in AI Chat (or Terminal) | What Happens |
|---|---|---|
| **1. Add Repos** | `/add-sibling <git-repo-url>` *(or `"Use add-sibling to onboard <git-repo-url>"`)* | Clones `../<repo>`, inspects stack/contracts, and remaps `AGENTS.md` & `docs/architecture.md`. |
| **2. Plan Epic & Stories** | `"Use planning-scaffold to create our first epic and stories in docs/planning/01/"` | Extends pre-seeded `docs/planning/01/` (Sprint / PI Goal / Cycle Pitch / Milestone) with `plan.md`, `progress.md`, and story specs. |
| **3. Refine & Size** | `"Run story-refiner on scope 01 (docs/planning/01/)"` | Audits Definition of Ready (DoR), resolves open decisions via `ask_user`, and sizes stories (`Small`/`Medium`). |
| **4. Sync to Tracker** | `"Use github-issue-onboard (or jira-story-onboard / ado-work-item-onboard / gitlab-issue-onboard) on our ready story"` | Creates the remote issue after your confirmation, renames `<story>-<KEY>.md`, and links bidirectionally (`bootstrap.py` keeps only your active tracker's skill). |
| **5. Ship & Review** | `"Use pr-create to run readiness + consensus checks and open our PR/MR"` | Runs `consensus-check` + DoD gates and opens a GitHub PR (`gh`) or GitLab MR (`glab`) *(for Azure Repos/Bitbucket, run `consensus-check` directly before opening your PR)*. |

---

## 📂 Repository Layout

```text
saiga-cart/                              # Template & generator repository
├── bootstrap.py                         # Interactive wizard, preset & config generator
├── AGENTS.md.template                   # -> Renders AGENTS.md (canonical directives, <= 14k chars)
├── CLAUDE.md.template                   # -> Renders CLAUDE.md (Claude Code rules)
├── .cursorrules.template                # -> Renders .cursorrules (Cursor IDE rules)
├── GLOSSARY.md.template                 # -> Renders GLOSSARY.md (ubiquitous domain terms)
├── workspace.yaml.template              # -> Renders workspace.yaml (declarative workspace manifest)
├── workspace.code-workspace.template    # -> Renders <slug>.code-workspace (multi-root IDE config)
├── .env.example                         # Template for gitignored .env.local / .env.<provider> tokens
├── .github/
│   ├── copilot-instructions.md.template # -> Renders .github/copilot-instructions.md
│   ├── agents/                          # Reference custom agents (/agent <name> in Copilot CLI)
│   │   ├── bootstrapper.agent.md
│   │   ├── ci-cd.agent.md
│   │   ├── test-engineer.agent.md
│   │   └── presentation-designer.agent.md
│   ├── workflows/
│   │   └── ci-cd.yml                    # Multi-OS test matrix (Linux/macOS/Windows) & Pages deploy
│   └── skills/                          # 14 autonomous skills (unused tracker skills pruned on bootstrap)
│       ├── add-sibling/                 # Onboard sibling repo, inspect stack & remap workspace docs
│       ├── planning-scaffold/           # Scaffold cycles, sprints, PIs, goals, epics & stories
│       ├── planning-docs-audit/         # Validate planning hierarchy, metadata & link integrity
│       ├── story-refiner/               # Batch DoR readiness check, sizing & implementation queue
│       ├── consensus-check/             # Risk-scaled multi-model deliberation panel
│       ├── harness2/                    # Context budget validator, experience ledger & worktree probes
│       ├── pr-create/                   # Readiness + consensus check & GitHub PR / GitLab MR creation
│       ├── pr-reviewer/                 # Interactive GitHub PR / GitLab MR review & thread replies
│       ├── github-issue-onboard/        # Onboard local story -> GitHub Issue (bidirectional)
│       ├── github-status-sync/          # Batch reconcile GitHub Issue statuses -> progress.md
│       ├── jira-story-onboard/          # Onboard local story -> Jira Story (bidirectional)
│       ├── jira-status-sync/            # Batch reconcile Jira statuses -> progress.md
│       ├── ado-work-item-onboard/       # Onboard local story -> Azure DevOps Work Item
│       └── gitlab-issue-onboard/        # Onboard local story -> GitLab Issue (bidirectional)
├── scripts/
│   └── workspace_doctor.py              # Workspace health check (bootstrap also generates clone_siblings.py & siblings.json)
├── docs/
│   ├── architecture.md                  # Cross-repo system contracts & ownership boundaries
│   ├── workflow.md                      # Working conventions, DoR/DoD & ASD-STE100 writing rules
│   ├── adr/                             # Architecture Decision Records (append-only)
│   ├── ai/                              # Experience Ledger (experience.md) & WoW ADRs (wow-adr/)
│   ├── planning/                        # Framework templates (bootstrap seeds docs/planning/01/)
│   └── presentation/                    # Self-guided HTML slide deck deployed to GitHub Pages
└── tests/                               # Cross-platform unit, matrix & E2E onboarding test suites
    └── mocks/tracker_sandbox.py         # Offline mock Jira, Azure DevOps & GitLab REST + Git sandbox
```

---

## 🛠 Supported Tooling Integrations

| Dimension | Supported Integrations |
|---|---|
| **Planning Frameworks** | Scrum (Sprints), SAFe (Program Increments), Shape Up (Cycles), Kanban (Milestones) |
| **Issue Trackers** | **Story onboarding**: GitHub Issues, Jira Cloud, GitLab Issues, Azure DevOps Boards, or Local Markdown (`none`)<br>**Batch status sync (`*-status-sync`)**: GitHub Issues & Jira Cloud |
| **Version Control** | **Full `pr-create` / `pr-reviewer` automation**: GitHub PRs (`gh`), GitLab MRs (`glab` / REST)<br>**Workspace topology, authenticated `clone_siblings.py` & `consensus-check`**: GitHub, GitLab, Azure Repos, Bitbucket |
| **AI Assistants** | **Dedicated rule files generated**: GitHub Copilot (`.github/copilot-instructions.md`), Claude Code (`CLAUDE.md`), Cursor (`.cursorrules`)<br>**Via `AGENTS.md` + `.code-workspace`**: Windsurf & MCP-compatible coding agents |

---

## 🤖 Persistent Custom Agents

The repository includes 4 reference custom agent definitions under `.github/agents/` used to maintain `saiga-cart` itself (selectable in GitHub Copilot CLI via `/agent` or `copilot --agent <name>`, and customizable in generated workspaces for your own domain roles):

- **`bootstrapper`**: Scaffolding, customizing, and maintaining multi-repo topologies and generators.
- **`ci-cd`**: GitHub Actions multi-OS test matrix automation and GitHub Pages deployment.
- **`test-engineer`**: Cross-platform unit tests, smoke matrices, and skill test suites.
- **`presentation-designer`**: Static presentation deck design, HTML/CSS/JS, and GitHub Pages assets.

---

## 🔍 Diagnostics, E2E Tests & Local Mock Onboarding Sandbox

### Inside a Generated Workspace (`cd ../my-ai-workspace`)
Run the workspace doctor and Harness² surface validator anytime to verify `AGENTS.md` context budgets, sibling checkouts, and planning link integrity:

```bash
cd ../my-ai-workspace
python scripts/workspace_doctor.py
python .github/skills/harness2/scripts/validate_harness.py
```

### Inside the `saiga-cart` Template Repository (`cd ~/work/saiga-cart`)
Run the full unit, matrix, skill, and offline E2E onboarding test suites (spinning up local mock Jira Cloud v3, Azure DevOps v7.1, and GitLab v4 REST servers, `az`/`gh`/`glab` CLI shims, and bare sibling Git repositories):

```bash
cd ~/work/saiga-cart
python -m unittest discover -s tests -v

# Launch the interactive local mock sandbox (--demo all runs Jira + ADO, or pick one):
python tests/mocks/tracker_sandbox.py --demo all
python tests/mocks/tracker_sandbox.py --demo jira
python tests/mocks/tracker_sandbox.py --demo ado
```

---

## 📜 License

Distributed under the [MIT License](LICENSE).
