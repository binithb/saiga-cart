---
name: add-sibling
description: 'Onboard or update a sibling repository, inspect its codebase to discover stack and contracts, ask the user for architectural intent, and remap workspace agent and architecture files.'
argument-hint: '<git-repo-url or sibling-repo-name>'
---

# Add Sibling Repository Skill

Use this skill when the user invokes `/add-sibling` or asks to add, onboard, or remap a sibling repository in the workspace.

Every time this skill runs, it verifies and clones the repository, inspects the repository to discover its stack and entry points first, asks the user via `ask_user` to confirm its architectural intent and role, and rewrites all workspace agent instruction and architecture files.

---

## Procedure

### Step 1: Collect Target Repository & Verify / Clone

1. If the user has not yet provided a Git repository URL (or an existing sibling folder name under `../<repo-name>`), ask for the Git repository URL via `ask_user`.
2. Register the repository, verify remote reachability (`git ls-remote`), auto-infer Azure DevOps org/project/base URL (when applicable), and clone it beside the workspace (`../<repo-name>`) by running:
   ```bash
   python3 bootstrap.py --add-sibling --sibling-url "<GIT_URL>" --clone
   ```
   *(If `../<repo-name>` is already cloned locally and only needs inspection/remapping, you may proceed directly to Step 2.)*

### Step 2: Inspect the Repository Basics (Before Asking the User)

Before asking the developer to describe the repository, inspect `../<repo-name>/` directly (read-only) to gather concrete facts:

1. **Manifests & Tech Stack**: Check `README.md`, `package.json`, `pyproject.toml`, `*.csproj`, `*.sln`, `pom.xml`, `build.gradle`, `go.mod`, `Cargo.toml`, `Dockerfile`, or `docker-compose.yml`.
2. **Build & Verification Commands**: Identify the primary build, test, and lint commands used by the repository or its CI workflows (`.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`).
3. **Contracts & Interfaces**: Look for exposed or consumed APIs, OpenAPI/Swagger specs, Protobuf/gRPC definitions, GraphQL schemas, database migrations, or message queue consumers/producers.
4. **Domain Concepts**: Note key domain nouns or bounded-context terms that may belong in `GLOSSARY.md`.

### Step 3: Ask the User for Intent, Description & Story Management Tool (`ask_user`)

Present a brief summary of what you discovered in Step 2 (stack, APIs, test commands), and call `ask_user` to confirm or refine:

1. **`role` (Intent & Responsibility Summary)**: Pre-fill the default with a concise 1–2 sentence description synthesized from Step 2 (for example: *"Pricing calculation REST API (.NET 8) owning tier rules, discount evaluation, and quote endpoints"*). Ask the user to confirm or edit what this repo owns and what kinds of changes belong in it.
2. **`relationships` (Cross-Repo Interactions)**: How this repository interacts with other sibling repositories in the workspace (upstream callers, downstream dependencies, shared schemas, or release coordination).
3. **`access` (Agent Access Mode)**:
   - `active`: Agents can read and modify code in `../<repo-name>/`.
   - `read-only`: Reference only; agents inspect contracts/schemas in `../<repo-name>/` without modifying files.
4. **`tracker_type` (Story Management Tool & Skill Pruning)**:
   - Infer the default story/issue tracker from the repository URL (`azure-devops` for `dev.azure.com` / `ssh.dev.azure.com` / `visualstudio.com`; `github` for `github.com`; `gitlab` for `gitlab.*`; or `jira` / `none`).
   - Ask the user to confirm their story management tool (`azure-devops`, `jira`, `github`, `gitlab`, or `none`) — especially if a GitHub/GitLab/Azure Repos repository actually tracks stories in Jira, or if `workspace.yaml` still has placeholder tracker settings (`acme-corp` / `acme-org`).
   - Only the skills matching the selected `tracker_type` are deployed in `.github/skills/` and routed in `AGENTS.md` (unused tracker skills are pruned automatically).

### Step 4: Remap & Rewrite Workspace Agent and Architecture Files

Once the user confirms the repository's intent, access mode, and story tracker:

1. **Rewrite Workspace Manifests, Agent Instruction Files & Prune Unused Tracker Skills**:
   Run `bootstrap.py --add-sibling` with the confirmed metadata so `workspace.yaml`, `AGENTS.md`, `<workspace>.code-workspace`, `scripts/siblings.json`, `scripts/clone_siblings.py`, `.github/skills/harness2/profiles.json`, and enabled assistant instruction files (`.github/copilot-instructions.md`, `CLAUDE.md`, `.cursorrules`) are deterministically updated, and unused issue-tracker skills are pruned so only the required tracker skill remains:
   ```bash
   python3 bootstrap.py --add-sibling \
     --sibling-name "<REPO_NAME>" \
     --sibling-url "<GIT_URL>" \
     --sibling-role "<CONFIRMED_ROLE_AND_INTENT>" \
     --sibling-access "<active|read-only>" \
     --tracker-type "<azure-devops|jira|github|gitlab|none>"
   ```
   *(Include `--tracker-base-url "<URL>"` and `--tracker-project-key "<KEY>"` if the user specified a Jira or custom tracker URL/project key.)*
2. **Update `.github/skills/harness2/profiles.json` Verifier**:
   If Step 2 identified a concrete unit test or build command for an `active` sibling repository, update its entry under `repositories.<REPO_NAME>.default_verifier` and `verifier_paths` in `.github/skills/harness2/profiles.json`.
3. **Remap `docs/architecture.md`**:
   - Update the **Multi-Repository Topology** ASCII diagram and **Sibling Repositories** table (`Repository | Purpose / Ownership | Language / Stack | Access Mode`), removing any leftover `{{REPO_A_NAME...}}` template placeholders.
   - Update **Shared Contracts & Cross-Repo Workflows** with the repository's exposed/consumed contracts, cross-repo dependencies, and local verification commands.
4. **Update `GLOSSARY.md` (When Applicable)**:
   - Add any newly discovered canonical domain terms or service names to `GLOSSARY.md`.
5. **Preserve Sibling Repository Cleanliness**:
   - Do not create or modify files inside `../<repo-name>/` during sibling onboarding.

### Step 5: Validate Workspace Health

Run the workspace diagnostics and Harness² surface validator to confirm all generated files, skill indexes, and context budgets are valid:

```bash
python3 scripts/workspace_doctor.py
python3 .github/skills/harness2/scripts/validate_harness.py
```
