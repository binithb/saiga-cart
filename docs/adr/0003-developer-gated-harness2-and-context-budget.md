# 0003. Developer-Gated Harness² Evolution and Always-On Context Budget

Date: 2026-04-19
Status: Accepted

## Context

`saiga-cart` workspaces serve as cross-repository AI context and delivery
planning meta-repositories coordinating multiple sibling engineering
repositories alongside a structured planning tree (`docs/planning/`).

As a multi-repository workspace matures across sprints or Program Increments,
`AGENTS.md` tends to accumulate tactical rules, duplicating `docs/workflow.md`,
`docs/architecture.md`, and `.github/skills/*/SKILL.md` while introducing
drift between always-loaded instructions and specialized skills.

Google Research's **Harness² (`arXiv:2610.14224`)** formalizes a dual-loop
architecture (*Task Loop* for multi-hypothesis execution probes and *Meta-Harness
Loop* for distilling execution trajectories into harness improvements). However,
an unguarded port of autonomous harness self-mutation introduces failure modes:

1. **Always-on prose inflation:** Distilled proposals mutate `AGENTS.md`
   directly instead of graduating rules into scripts or skills.
2. **State/log bloat:** Full-file proposal copies and dirty-tree hash logs
   pollute Git history without preventing direct edits.
3. **Overlap with existing multi-agent review:** The workspace already provides
   `consensus-check` and `pr-reviewer` for multi-model review.

## Decision

Adopt a **Developer-Gated Harness²** architecture via the
[`.github/skills/harness2/`](../../.github/skills/harness2/SKILL.md) skill,
deterministic validator
([`validate_harness.py`](../../.github/skills/harness2/scripts/validate_harness.py)),
and cross-sprint experience ledger ([`../ai/experience.md`](../ai/experience.md)):

1. **Hard Always-On Context Budget (`AGENTS.md <= 14,000` chars):**
   - `AGENTS.md` is strictly a routing charter, cross-repo ownership table, and
     safety-boundary index. Detailed procedures live in
     `.github/skills/<skill>/SKILL.md` and `docs/workflow.md`; mutable system
     state lives in `docs/architecture.md`.
   - `validate_harness.py` enforces `--max-agents-chars 14000` in CI and local
     audits (`h2 audit`).

2. **Red Zone vs. Green Zone Governance (No Hash-Log Ceremony):**
   - **Red Zone** (`AGENTS.md`, `AGENTS.md.template`, `docs/workflow.md`,
     `docs/architecture.md`, `docs/adr/**`, `.github/workflows/**`,
     `.gitlab-ci.yml`) holds governance and architecture contracts.
   - **Green Zone** (`.github/skills/**`, `scripts/**`, `docs/ai/experience.md`)
     holds operational skills, deterministic validators, and distilled lessons.
   - Mutations to either zone during `h2 distill` are gated interactively via
     `ask_user` using a **3-Line Evidence Audit Card** (`Target & Zone`,
     `Evidence`, `Proposed Change`) and verified in CI (`Frozen Verifier` rule).

3. **Prose-to-Script Cost Hierarchy (`h2 distill`):**
   - Recurring failures and review clusters must graduate to the lowest-cost
     artifact that can enforce them:
     1. **Tier 1:** Deterministic Python script (`.github/skills/*/scripts/*.py`
        or `scripts/*.py`) + `unittest`
     2. **Tier 2:** On-demand skill procedure (`.github/skills/*/SKILL.md`)
     3. **Tier 3:** Cross-sprint experience ledger (`docs/ai/experience.md`)
     4. **Tier 4:** Architecture / WoW ADR (`docs/adr/`)
     5. **Tier 5:** `AGENTS.md` (last resort only)
   - `pr-reviewer` includes a post-publish distillation hook so recurring review
     `Fix` clusters prompt `💡 [Harness²]` graduation into scripts or skills.

4. **Exception-Triggered Task Probes (`h2 probe`):**
   - `consensus-check` remains the sole multi-model review skill.
   - `h2 probe` is reserved strictly for exception recovery when a deterministic
     story verification command fails repeatedly ($\ge 2$ times), running two
     orthogonal lenses (`INV` contract/verifier vs. `DOM` target-repo idiom) in
     isolated `git worktree` checkouts.

## Consequences

- **Positive:**
  - Keeps `AGENTS.md` compact (`<= 14,000` chars) with zero information loss and
    prevents future context bloat via CI enforcement.
  - Eliminates model-roster drift between `AGENTS.md`, `docs/workflow.md`, and
    `consensus-check/SKILL.md`.
  - Enforces prose-to-script graduation and provides `--check-siblings` and
    `--check-pi-compaction` auditing.
- **Negative / Trade-offs:**
  - Adding a new skill or script requires indexing it in
    `.github/skills/README.md` and keeping `validate_harness.py` + its unit
    tests green in CI.
