---
name: pr-reviewer
description: 'Interactive PR/MR review workflow that fetches open review threads (GitHub PR or GitLab MR), performs a structured code review, walks through each item interactively with the developer, applies local code fixes, and posts confirmed replies or inline review comments.'
argument-hint: '[<pr-or-mr-url-or-number>] [--repo <path-or-slug>] [--mode address|review|both]'
---

# Interactive PR / MR Reviewer (`pr-reviewer`)

Conduct an end-to-end, developer-in-the-loop Pull Request (GitHub) or Merge Request (GitLab) review session. This skill supports addressing existing reviewer comments on your own PR/MR, reviewing a teammate's PR/MR with inline comments, or doing both in one guided workflow.

## Core Rules

1. **Always Interactive (Per Item or Batch Confirmation)**:
   - Never auto-post comments, auto-resolve threads, or push fixes without walking through the items interactively with the developer (`ask_user` / `AskUserQuestion` or structured chat confirmation).
2. **Evidence-Gated Review Findings**:
   - Apply the same **Mandatory Evidence-Gated Verification Rules** used in [`consensus-check`](../consensus-check/SKILL.md): trace the full execution path before flagging, cite exact `file:line`, specify the concrete trigger and failure mode, and calibrate severity (`BLOCKER`, `MAJOR`, `MINOR`, `NIT`).
3. **Batch Remote Publishing Confirmation**:
   - Local code fixes are applied during the interactive walkthrough, while remote PR/MR actions (posting thread replies, resolving discussions, or creating new inline diff comments) are queued and executed only after a final summary confirmation (`ask_user` / `AskUserQuestion` or explicit user approval, plus `--confirm` for mutating scripts).
4. **Harness² Post-Publish Distillation Hook**:
   - At the end of a review session where $\ge 2$ `Fix` actions or recurring defect patterns were addressed, prompt `💡 [Harness²]` offering to distill the recurring pattern into a deterministic check, skill step, or `docs/ai/experience.md` entry (`h2 distill`).

---

## Supported Modes

- **`address` (Address Existing Review Threads)**:
  Fetch all unresolved review discussions/threads on an open PR/MR, analyze each comment against the local branch code, and ask the developer interactively (`ask_user` / `AskUserQuestion` or structured prompt) per thread whether to:
  1. **Fix & Reply**: Apply the local code/doc fix and queue a concise reply explaining the fix.
  2. **Reply Only (Explain / Push Back)**: Draft a clear technical explanation without changing code.
  3. **Skip**: Leave untouched for now.
- **`review` (Perform Code Review on a PR/MR)**:
  Inspect the PR/MR diff (`gh pr diff` or GitLab MR changes), optionally run `consensus-check` for medium/high blast radius changes, and walk through each verified finding interactively (`ask_user` / `AskUserQuestion` or structured prompt) to decide whether to queue an inline diff comment, fix locally, or drop.
- **`both` (Default when unresolved threads exist)**:
  Walk through unresolved reviewer discussions first (`address`), then present any new verified code-review findings (`review`).

---

## Tooling by Git Host

### GitHub Pull Requests (`gh` CLI)
- **Inspect PR metadata & diff**:
  ```bash
  gh pr view <number> --json number,title,body,headRefName,baseRefName,url
  gh pr diff <number>
  ```
- **Fetch review comments**:
  ```bash
  gh api repos/{owner}/{repo}/pulls/<number>/comments
  ```
- **Reply to a review comment thread (after final confirmation)**:
  ```bash
  gh api repos/{owner}/{repo}/pulls/<number>/comments/<comment_id>/replies -f body="<reply>"
  ```

### GitLab Merge Requests (`gitlab_mr_discussions.py`)
Use the bundled deterministic helper script `.github/skills/pr-reviewer/scripts/gitlab_mr_discussions.py` (reads `GITLAB_TOKEN` / `GITLAB_PAT` from environment, `.env.local`, `.env`, or `~/.copilot/skills/gitlab/.env`):

- **List unresolved discussions (read-only)**:
  ```bash
  python3 .github/skills/pr-reviewer/scripts/gitlab_mr_discussions.py list \
    --mr <mr-url-or-iid> [--project <group/project>] --unresolved-only
  ```
- **Reply to a discussion thread (requires interactive user confirmation + `--confirm`)**:
  ```bash
  python3 .github/skills/pr-reviewer/scripts/gitlab_mr_discussions.py reply \
    --mr <mr-url-or-iid> --discussion-id <id> --body "<reply>" [--resolve] --confirm
  ```
- **Resolve/unresolve a discussion thread (requires interactive user confirmation + `--confirm`)**:
  ```bash
  python3 .github/skills/pr-reviewer/scripts/gitlab_mr_discussions.py resolve \
    --mr <mr-url-or-iid> --discussion-id <id> --confirm
  ```
- **Post a new inline diff comment or general note (requires interactive user confirmation + `--confirm`)**:
  ```bash
  python3 .github/skills/pr-reviewer/scripts/gitlab_mr_discussions.py comment \
    --mr <mr-url-or-iid> --body "<comment>" \
    [--new-path <file> --new-line <line>] --confirm
  ```

---

## Step-by-Step Workflow

### Step 1: Discover PR/MR Context & Unresolved Threads
1. Resolve the target repository and open PR/MR from the user's argument or current git branch.
2. Fetch PR/MR metadata, diff, and unresolved review threads (`gh api` for GitHub or `gitlab_mr_discussions.py list --unresolved-only` for GitLab).
3. Summarize the PR/MR status (branch, files changed, unresolved thread count) for the user.

### Step 2: Interactive Walkthrough
1. For each unresolved discussion thread (in `address` / `both` mode):
   - Read the referenced file and surrounding lines in the local checkout.
   - Evaluate the reviewer's point and formulate a concrete recommendation + proposed code change or reply text.
   - Present the thread context, code snippet, and recommendation for interactive confirmation (`ask_user` / `AskUserQuestion` or structured prompt) with choices (`Fix + Reply`, `Reply Only`, `Skip`).
   - If `Fix + Reply` is chosen, apply the edit immediately using `edit` and verify tests/linting pass.
2. For each verified code-review finding (in `review` / `both` mode):
   - Present the exact `file:line`, severity, trigger/impact, and suggested inline comment or local fix for interactive confirmation (`ask_user` / `AskUserQuestion` or structured prompt).

### Step 3: Batch Confirm & Publish
1. If local files were modified, show `git status -sb` / `git diff --stat` and run the repo's verification command.
2. Present a complete summary table of all queued remote actions (thread replies, thread resolutions, new inline comments, and whether to commit/push local fixes) for final interactive confirmation (`ask_user` / `AskUserQuestion` or explicit approval).
3. Upon confirmation, execute the queued `gh` or `gitlab_mr_discussions.py ... --confirm` commands and report the updated PR/MR status.
4. **Harness² Hook**: If $\ge 2$ fixes addressed a recurring pattern, ask if the user would like to run `h2 distill` to capture the lesson in a validator script, skill, or `docs/ai/experience.md`.
