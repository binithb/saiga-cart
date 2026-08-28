# CI/CD & GitHub Pages Deployment

This repository uses GitHub Actions for continuous integration and automated GitHub Pages deployment of the static presentation site.

---

## Workflow Overview (`.github/workflows/ci-cd.yml`)

The pipeline comprises two sequential stages:

1. **Matrix Validation (`test`)**:
   - **Operating Systems**: `ubuntu-latest`, `macos-latest`, `windows-latest`
   - **Runtime**: Python 3.12 (standard library `unittest` framework)
   - **Test Scopes**:
     - Unit & smoke matrix suite (`tests/`)
     - Planning docs audit skill suite (`.github/skills/planning-docs-audit/scripts/test_planning_docs_audit.py`)
     - Story readiness skill suite (`.github/skills/story-refiner/scripts/test_story_readiness.py`)

2. **GitHub Pages Deployment (`deploy-pages`)**:
   - **Trigger Condition**: Executes only on successful completion of the `test` job for pushes to the `main` branch (or via manual `workflow_dispatch`).
   - **Source Directory**: `docs/presentation`
   - **Target**: GitHub Pages environment (`github-pages`)

---

## Triggers & Concurrency

- **Push**: Triggered on commits pushed to `main`.
- **Pull Request**: Triggered on pull requests targeting `main` (validation only; deployment is skipped).
- **Workflow Dispatch**: Allows manual runs from the GitHub Actions UI.
- **Concurrency Management**:
  - Workflow-level: In-progress PR validation runs are cancelled when new commits are pushed (`cancel-in-progress: true` on PRs).
  - Deploy-level: The `pages` deployment concurrency group enforces `cancel-in-progress: false` to prevent race conditions during artifact deployment.

---

## Security & Permissions

- **Least Privilege**: Default workflow permission is set to `contents: read`.
- **Deployment Job Permissions**: Elevated permissions (`pages: write`, `id-token: write`) are scoped strictly to the `deploy-pages` job for OpenID Connect (OIDC) token exchange with GitHub Pages.
- **No Hard-coded Credentials**: Uses native GitHub Actions OIDC and Pages authentication without long-lived personal access tokens or secrets.

---

## Required Repository Settings

To enable automatic GitHub Pages deployment:

1. Go to **Settings** > **Pages** in the repository.
2. Under **Build and deployment** > **Source**, select **GitHub Actions**.
3. (Optional) Under **Settings** > **Environments**, review the auto-created `github-pages` environment for deployment protection rules if needed.
