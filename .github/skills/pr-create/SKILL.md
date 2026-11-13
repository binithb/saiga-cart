---
name: pr-create
description: 'Run branch readiness + multi-model consensus checks, generate a high-level functional summary, verify rebase/conflict status, and create a Pull Request (GitHub) or Merge Request (GitLab) after user confirmation.'
argument-hint: '[--title <title>] [--description <desc>] [--target-branch <branch>] [--dir <path>] [--draft] [--skip-consensus]'
---

# PR / MR Create Skill

Prepare, verify, and open a Pull Request (GitHub) or Merge Request (GitLab) in the workspace repository or any sibling repository after passing deterministic readiness checks, multi-model consensus review, and explicit user confirmation.

## Rules & Conventions

1. **Pre-Flight Readiness & Consensus Gate**: Before showing the PR/MR creation preview, run the deterministic readiness checks (Phase 1) and the Stage 2 `consensus-check` review (Phase 2, unless the user explicitly passed `--skip-consensus` or already completed `consensus-check` on the exact current commit SHA).
2. **High-Level & Functional Focus**: Keep the title and description concise and focused on the business or functional capability delivered.
   - Follow **ASD-STE100 plain-language rules** (active voice, clear verbs, short sentences, one main idea per bullet, consistent domain terms from `GLOSSARY.md` when available).
   - **Never** dump low-level code diffs, chat transcripts, or raw CLI output into the PR/MR description.
   - Structure the description around:
     - **Summary / Goal**: 1–3 sentences explaining *what* changed functionally and *why*.
     - **Key Changes**: High-level bullet points of functional changes.
     - **Tracker / Story Reference**: Ticket or issue key (e.g., `PROJ-1234` or `#42`) if applicable.
3. **Always Confirm Before Creating**: Always display a clear summary of the proposed PR/MR (repository, source branch, target branch, rebase/conflict status, readiness verdict, title, and description) and obtain explicit user approval via `ask_user` before executing the creation call.

---

## Workflow

### Phase 1: Deterministic Readiness & Rebase Gate

1. **Resolve Repository & Branches**:
   - Inspect `git status -sb`, current branch (`git branch --show-current`), and default target branch (`main` or `master`).
   - Refuse or warn if the current branch is the default branch (`main`/`master`).
   - Check for uncommitted or untracked files (`git status --porcelain`). If dirty, ask the user whether to commit, stash, or ignore before proceeding.
   - Verify the branch is pushed to `origin` (`git rev-parse --abbrev-ref --symbolic-full-name @{u}`).
2. **Rebase & Merge-Conflict Check**:
   - Run `git fetch origin <target-branch>`.
   - Check divergence: `git rev-list --left-right --count origin/<target-branch>...HEAD`.
   - Test mergeability against `origin/<target-branch>` (e.g., `git merge-tree $(git merge-base HEAD origin/<target-branch>) HEAD origin/<target-branch>`). If conflicts exist, report the conflicting files and stop until resolved.
3. **Definition of Done (DoD) Checks**:
   - Scan `git diff origin/<target-branch>...HEAD` for leftover debug markers, conflict markers (`<<<<<<<`), hardcoded secrets/tokens, or unintended temporary files.
   - Run the repository's fast deterministic verification commands:
     - In the workspace root:
       ```bash
       python3 .github/skills/planning-docs-audit/scripts/planning_docs_audit.py --fail-on-warning
       python3 .github/skills/harness2/scripts/validate_harness.py
       ```
     - In a sibling repository: run its fast lint/unit-test check (or verify the user has just run it).
   - If planning docs under `docs/planning/` were touched, confirm story metadata and `progress.md` status are consistent (`In review` once a PR/MR is opened).

### Phase 2: Multi-Model Consensus Check (`consensus-check`)

Unless `--skip-consensus` was explicitly requested or `consensus-check` has already passed for the current `HEAD` SHA in this session:

1. Invoke the **[`consensus-check`](../consensus-check/SKILL.md)** skill in **Stage 2 (PR / MR Review)** mode on `git diff origin/<target-branch>...HEAD`.
2. Classify the blast radius (`Low`, `Medium`, or `High`) per the `consensus-check` scaling matrix and run the independent subagent review.
3. Present the synthesized `consensus-check` findings (`BLOCKER`, `MAJOR`, `MINOR`, `NIT`):
   - If any `BLOCKER` or `MAJOR` issues are found, offer to fix them and re-verify before opening the PR/MR, or let the user explicitly override via `ask_user`.

### Phase 3: Functional Summary, Confirmation & Creation

1. **Draft Title & Description**:
   - Extract the tracker/issue key (`PROJ-XXXX` or `#XX`) from the branch name or commit history if present.
   - Draft a concise functional title and description (Summary, Key Changes, Tracker Reference).
2. **Ask User Confirmation (`ask_user`)**:
   - Present the preview card:
     - **Repository & Branches**: `<source_branch> -> <target_branch>`
     - **Rebase & Readiness Status**: Behind/ahead count, conflict check, DoD + `consensus-check` verdict
     - **Proposed Title & Description**
   - Wait for explicit approval (or edits to title/description/draft status).
3. **Create the PR / MR**:
   - Push the branch if needed (`git push -u origin <source-branch>`).
   - **GitHub**:
     ```bash
     gh pr create --repo <owner/repo> --title "<title>" --body "<description>" --base <target-branch>
     ```
   - **GitLab**:
     ```bash
     glab mr create --repo <group/project> --title "<title>" --description "<description>" --target-branch <target-branch>
     ```
     *(Or via the GitLab REST API skill if configured).*
   - Return the created PR/MR URL and remind the user to update the corresponding story status to `In review` if not already set.

