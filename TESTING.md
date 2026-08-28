# Testing Strategy

The test suite uses only Python's standard-library `unittest` framework, so
the same commands run on Windows, macOS, and Linux.

## Running Tests

```text
python -m unittest discover -v
```

If Windows does not provide `python`, use `py -3 -m unittest discover -v`.

## Unit Tests

`tests/test_bootstrap_unit.py` verifies:

- YAML-safe serialization of workspace names, URLs, roles, descriptions, and empty sibling lists.
- Template string rendering, variable substitution, and fallback defaults (`{{KEY|default("val")}}`).
- Output directory validation and seeding logic (`prepare_output_directory`).
- Platform-neutral sibling cloning: generated code invokes Git through
  `subprocess.run([...], shell=False)` rather than a shell.
- Preservation of sibling metadata in `scripts/siblings.json`.

The planning-audit and story-readiness scripts keep their focused unit tests
beside their respective skill implementations.

## Minimal System Smoke Tests

`tests/test_bootstrap_matrix.py` copies the template into a temporary
directory, bootstraps it, then runs the generated workspace doctor and
planning audit. It covers the three representative happy paths:

1. **`test_e2e_smoke_github_scrum_preset`**: **GitHub + Scrum + GitHub Issues** — a two-week Scrum workspace with
   GitHub issue skills retained and non-GitHub tracker skills pruned.
2. **`test_e2e_smoke_jira_safe_preset`**: **GitLab + SAFe + Jira** — an eight-week PI workspace with Jira onboarding
   and status-sync skills retained and GitHub tracker skills pruned.
3. **`test_e2e_smoke_ado_scrum_preset`**: **Azure DevOps + Scrum + Azure Repos** — a two-week Scrum workspace with
   Azure DevOps onboarding skills retained and Jira/GitHub tracker skills pruned.

The combinations are deliberately representative of the public/open-source
and enterprise/multi-team audiences: GitHub describes itself as home to more
than 150 million developers in its [Octoverse report](https://github.blog/news-insights/octoverse/),
while Jira is Atlassian's issue tracker designed to coordinate cross-team
software delivery; Scrum's timeboxed sprint model and SAFe's PI planning fit
those respective workflows.

The same module also verifies standalone generation into an empty directory via
`test_e2e_standalone_generation_to_empty_directory`.
