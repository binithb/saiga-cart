# 🛷 saiga-cart: AI-Native Multi-Repository Workspace

<p align="center">
  <img src="docs/presentation/assets/saiga-cart-banner.svg" alt="saiga-cart Banner: A cart pulled by 3 rows of saigas across a multi-repository workspace" width="100%">
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Presentation](https://img.shields.io/badge/Presentation-GitHub%20Pages-brightgreen)](https://binithb.github.io/saiga-cart/)

An open-source template and interactive bootstrapper for **scaling AI development across multiple repositories**.

> 🌐 **Interactive Slide Deck & Overview**: Explore the live visual presentation and architecture walkthrough at **[https://binithb.github.io/saiga-cart/](https://binithb.github.io/saiga-cart/)**.

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

> **💡 Recommended Folder Layout**: Set up your workspace in its own **new folder** inside a shared parent directory (e.g., `~/work/my-ai-workspace`), rather than modifying your raw `saiga-cart` clone in-place. Because sibling repositories are checked out **beside** the workspace folder (`../service-a`, `../service-b`), this keeps your multi-repo parent directory clean and organized:
> ```text
> ~/work/
> ├── saiga-cart/                # Template / generator repo (stays clean)
> ├── my-ai-workspace/           # Your generated workspace (--output ../my-ai-workspace)
> ├── service-a/                 # Cloned sibling repo 1
> └── service-b/                 # Cloned sibling repo 2
> ```

### Option A: Interactive Setup into a New Folder (Recommended)
1. Clone `saiga-cart` inside your parent workspace directory:
   ```bash
   mkdir -p ~/work && cd ~/work
   git clone https://github.com/binithb/saiga-cart.git
   cd saiga-cart
   ```
2. Run the interactive setup wizard (it will prompt you for your new workspace folder path, defaulting to `../<workspace-slug>`, or you can pass `--output ../my-ai-workspace` explicitly):
   ```bash
   python bootstrap.py
   # Or specify the target folder directly:
   python bootstrap.py --output ../my-ai-workspace
   ```
3. Follow the prompts to configure your target workspace directory, planning framework, issue tracker, local credentials (`.env.azure`, `.env.jira`, `.env.github`, `.env.gitlab`, or `.env.local` / CLI keyring), and verified sibling repositories.
4. Switch into your newly created workspace folder and clone your sibling repositories (if not cloned automatically during setup):
   ```bash
   cd ../my-ai-workspace
   python scripts/clone_siblings.py
   ```
5. Add more sibling repositories anytime later from inside your generated workspace:
   ```bash
   python bootstrap.py --add-sibling
   ```
6. Open the unified multi-root workspace in VS Code / Cursor:
   ```bash
   code my-ai-workspace.code-workspace
   ```

### Option B: Non-Interactive / CI Preset into a New Folder
```bash
# Scrum + GitHub Issues
python bootstrap.py --preset github-scrum --output ../my-gh-workspace

# SAFe (PIs) + Jira Cloud
python bootstrap.py --preset jira-safe --output ../my-jira-workspace

# Scrum + Azure DevOps
python bootstrap.py --preset ado-scrum --output ../my-ado-workspace
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
│       ├── harness2/               # Context budget validator, experience ledger & task probes
│       ├── pr-create/              # Readiness + consensus check & functional PR/MR creation
│       └── pr-reviewer/            # Interactive PR/MR review walkthrough & thread replies
├── scripts/
│   ├── clone_siblings.py           # Cross-platform sibling repository checkout
│   └── workspace_doctor.py         # Diagnostic verification utility
└── docs/
    ├── architecture.md             # Cross-repo system contracts & data flows
    ├── workflow.md                 # Working conventions, DoR/DoD, sizing rules
    ├── adr/                        # Architecture Decision Records (append-only)
    ├── ai/                         # Cross-sprint Experience Ledger (experience.md)
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
