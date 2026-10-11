---
name: pr-create
description: 'Create a pull request (GitHub) or merge request (GitLab) across workspace repositories with pre-flight rebase/conflict checks and user confirmation.'
argument-hint: '[--title <title>] [--description <desc>] [--target-branch <branch>] [--dir <path>] [--draft]'
---

# PR / MR Create Skill

Automate pull request and merge request creation across this workspace or sibling repositories.

## Rules & Conventions
1. **High-Level & Functional Focus**: Title and description must focus on business/functional capability delivered.
2. **No Transcript Dumps**: Do not paste terminal output, raw logs, or chat transcripts into the PR description.
3. **Pre-flight Checks**: Verify branch is up-to-date with target branch and has no merge conflicts.
4. **Mandatory Confirmation**: Always display the full PR summary card and get explicit user approval before submitting.

## Commands

### GitHub
```bash
gh pr create --repo <owner/repo> --title "<title>" --body "<description>" --base main
```

### GitLab
```bash
glab mr create --repo <group/project> --title "<title>" --description "<description>" --target-branch main
```
