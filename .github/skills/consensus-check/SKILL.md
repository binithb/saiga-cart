---
name: consensus-check
description: 'Escalate a high-blast-radius design, architecture decision, or PR/MR to risk-scaled multi-model deliberation panel.'
argument-hint: '[--stage plan|mr|architecture] [--blast-radius low|medium|high]'
---

# Multi-Model Consensus Review Skill

Provides rigorous, multi-perspective evaluation for high-stakes or irreversible changes across workspace repositories.

## Scaling Levels

- **Low Blast Radius**: Fast single-model pass (low reasoning effort). Focuses on standard syntax, DoD checks, and contract adherence.
- **Medium Blast Radius**: Dual-perspective review with 2 distinct models (medium reasoning effort). Evaluates edge cases, failure modes, and security implications.
- **High Blast Radius**: 3-agent deliberation panel (2 reviewers + 1 arbiter, high reasoning effort). Used for core database migrations, auth changes, breaking cross-repo APIs, or state cutovers.

## Procedure

1. **Synthesize Change Artifact**: Summarize the proposal, affected files, risks, and verification evidence.
2. **Execute Reviews**: Dispatch prompt to designated review personas.
3. **Resolve Consensus**: Arbiter resolves trade-offs and issues a verdict: `Approve`, `Approve with Modifications`, or `Reject`.
