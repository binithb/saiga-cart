# 🛷 saiga-cart: AI-Native Multi-Repository Workspace

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

An open-source template and interactive bootstrapper for **scaling AI development across multiple repositories**.

Named after the enduring steppe antelope (**saiga**) and the collaborative load pulling of a team (**cart**), `saiga-cart` gives AI agents (GitHub Copilot, Claude Code, Cursor, Windsurf) and software engineers durable, synchronized context across multiple related repositories and structured delivery planning.

---

## Platform Support

The generator, diagnostics, clone helper, and test suite use the Python standard
library and support **Windows, macOS, and Linux** with Python 3.8+ and Git.
Use `python` on macOS/Linux or `py -3` on Windows if `python` is unavailable.

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
│   - Multi-model consensus panels   │   - Bidirectional issue sync       │
└────────────────────────────────────┴────────────────────────────────────┘
```

1. **Cross-Repo AI Context**: Open multiple sibling repositories in one unified IDE session (`.code-workspace`). AI agents reason about contracts, shared models, infrastructure, and test suites simultaneously without switching windows.
2. **Durable Delivery Planning**: Keep planning context, ADRs, and story acceptance criteria versioned in markdown directly beside the codebase. This prevents settled decisions from being forgotten between AI chat sessions.

---

## 🚀 Quickstart: Bootstrapping a New Workspace

### Option A: Use as GitHub Template (Recommended)
1. Click **Use this template** on GitHub to create your own repository.
2. Clone your newly created repository:
   ```bash
   git clone git@github.com:your-org/your-ai-workspace.git
   cd your-ai-workspace
   ```
3. Run the interactive setup wizard:
   ```bash
   python bootstrap.py
   ```
4. Follow the prompts to configure your planning framework, issue tracker, and sibling repositories.
5. Clone your sibling repositories:
   ```bash
   python scripts/clone_siblings.py
   ```
6. Open in VS Code / Cursor:
   ```bash
   code your-workspace.code-workspace
   ```

### Option B: Non-Interactive / CI Preset
```bash
# Scrum + GitHub Issues
python bootstrap.py --preset github-scrum

# SAFe (PIs) + Jira Cloud
python bootstrap.py --preset jira-safe

# Scrum + Azure DevOps
python bootstrap.py --preset ado-scrum
```

---

## 📂 Repository Layout

```
saiga-cart/
├── bootstrap.py                    # Interactive setup wizard
├── AGENTS.md                       # Canonical agent directives & boundary rules
├── CLAUDE.md                       # Claude Code workspace guidelines
├── .cursorrules                    # Cursor IDE rules
├── .github/
│   ├── copilot-instructions.md     # GitHub Copilot CLI & Chat instructions
│   ├── agents/                     # Persistent custom agent definitions (/agent <name>)
│   │   ├── bootstrapper.agent.md
│   │   ├── ci-cd.agent.md
│   │   ├── test-engineer.agent.md
│   │   └── presentation-designer.agent.md
│   ├── workflows/                  # GitHub Actions multi-OS test matrix & Pages deploy
│   │   └── ci-cd.yml
│   └── skills/                     # Reusable autonomous agent procedures
│       ├── story-refiner/          # Batch story DoR audit and sizing
│       ├── planning-scaffold/      # Generates cycles/sprints/epics/stories
│       ├── planning-docs-audit/    # Validates link integrity and metadata
│       ├── consensus-check/        # Risk-scaled multi-agent deliberation
│       ├── pr-create/              # Functional PR/MR creation
│       └── pr-readiness-check/     # Definition of Done verification
├── scripts/
│   ├── clone_siblings.py           # Cross-platform sibling repository checkout
│   └── workspace_doctor.py         # Diagnostic verification utility
└── docs/
    ├── architecture.md             # Cross-repo system contracts & data flows
    ├── workflow.md                 # Working conventions, DoR/DoD, sizing rules
    ├── adr/                        # Architecture Decision Records (append-only)
    ├── planning/                   # Active cycles / increments / sprints
    └── presentation/               # Self-guided HTML presentation on AI WoW
```

---

## 🛠 Supported Tooling Integrations

| Dimension | Supported Integrations |
|---|---|
| **Planning Frameworks** | Scrum (Sprints), SAFe (Program Increments), Shape Up (Cycles), Kanban (Milestones) |
| **Issue Trackers** | GitHub Issues/Projects, Jira Cloud/Server, GitLab Issues, Azure DevOps Boards, Local Markdown |
| **Version Control** | GitHub (PRs), GitLab (MRs), Azure Repos, Bitbucket |
| **AI Assistants** | GitHub Copilot CLI/Chat, Claude Code, Cursor, Windsurf, generic MCP-compatible agents |

---

## 🤖 Persistent Custom Agents

The repository includes 4 persistent custom agent definitions under `.github/agents/` that can be loaded into GitHub Copilot CLI or compliant tools via `/agent <name>`:

- **/agent `bootstrapper`**: Scaffolding, customizing, and maintaining multi-repo topologies and generators.
- **/agent `ci-cd`**: GitHub Actions multi-OS test matrix automation and GitHub Pages deployment.
- **/agent `test-engineer`**: Cross-platform unit tests, smoke matrices, and test strategy maintenance.
- **/agent `presentation-designer`**: Static presentation deck design, HTML/CSS/JS, and UI/UX documentation.

---

## 🔍 Diagnostics & Health Check

Run the workspace doctor anytime to verify your environment, sibling checkouts, and planning integrity:

```bash
python scripts/workspace_doctor.py
```

---

## 📜 License

Distributed under the [MIT License](LICENSE).
