# Architecture Overview

Cross-repository architecture and subsystem relationships across this workspace.

---

## 1. Multi-Repository Topology

```
┌─────────────────────────────────────────────────────────────┐
│                      Unified Workspace                      │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
     ┌──────────────────┐            ┌──────────────────┐
     │ {{REPO_A_NAME|default("core-service")}}       │            │ {{REPO_B_NAME|default("infra-platform")}}     │
     │ - Application    │            │ - Deployment     │
     │ - Domain Logic   │            │ - CI/CD & Infra  │
     └──────────────────┘            └──────────────────┘
```

### Sibling Repositories

| Repository | Purpose / Ownership | Language / Stack | Access Mode |
|---|---|---|---|
| `{{REPO_A_NAME|default("core-service")}}` | Core business logic and API services | Python / Go / TS | Active modification |
| `{{REPO_B_NAME|default("infra-platform")}}` | Infrastructure, container definitions, and CI pipelines | Terraform / Helm / YAML | Active modification |

---

## 2. Shared Contracts & Cross-Repo Workflows

Describe how repositories coordinate:
- Shared API contracts (Protobuf, OpenAPI, JSON Schema).
- CI/CD build artifact propagation (Docker images, packages).
- Environment deployments and configuration management.
