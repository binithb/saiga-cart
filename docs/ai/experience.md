# Cross-Sprint AI Experience Ledger (`Harness²`)

This file is the **Tier 3 Experience Ledger** managed by the [`harness2`](../../.github/skills/harness2/SKILL.md) skill (`h2 distill`, see [ADR 0003](../adr/0003-developer-gated-harness2-and-context-budget.md)).

It stores compact, high-signal engineering lessons (`Cue → Lesson → Evidence → Status / Target`) discovered during story implementation, `pr-reviewer` triage, or cross-repo debugging that are not yet ready for—or are awaiting graduation into—a deterministic script (Tier 1) or on-demand skill (Tier 2).

## Rules for this ledger

1. **Human-gated writes only:** Entries are added or updated only after developer confirmation via `h2 distill` (`ask_user` 3-Line Evidence Audit Card).
2. **Prose-to-script graduation:** When an entry (`provisional` or `active`) is automated in a validator script or codified in a `SKILL.md`, update its `Status & Graduation Target` to `graduated (<path>)` and keep the row to preserve provenance.
3. **Hard size budget:** Keep this file $\le 12,000$ characters (enforced by `.github/skills/harness2/scripts/validate_harness.py`). Prune superseded `graduated` rows when approaching the cap.

## Experience Entries

| ID | Date | Cue (When / Where) | Distilled Lesson (Do / Do Not) | Evidence | Status & Graduation Target |
|---|---|---|---|---|---|
| `EXP-0001` | 2026-04-19 | Modifying `AGENTS.md`, `docs/workflow.md`, or `.github/skills/*` | Keep `AGENTS.md` $\le 14,000$ chars as a routing charter; place detailed procedures in `.github/skills/<skill>/SKILL.md` and deterministic checks in `.github/skills/<skill>/scripts/*.py` so always-on context never drifts or bloats. | Initial `AGENTS.md` audit found 26,573 chars (~60% duplicated with `docs/workflow.md` and skills, plus `consensus-check` model-name drift). | `graduated (.github/skills/harness2/scripts/validate_harness.py)` |
| `EXP-0002` | 2026-04-19 | Writing or updating validator scripts under `.github/skills/*/scripts/` | Never hardcode absolute workstation paths (`/home/<user>/...`) or use naive line-skipping YAML parsers for multi-line lists; resolve repository root dynamically from `Path(__file__).resolve()` and test against `unittest`. | Empirical audit of `hq` Harness² prototype prior to porting to `sputnik-ai-workspace` and `saiga-cart`. | `graduated (.github/skills/harness2/scripts/validate_harness.py)` |
| `EXP-0003` | 2026-11-12 | Authoring or invoking external mutating scripts/skills (e.g. Jira/tracker write scripts) or prompting via `h2 distill` | Pair `ask_user` confirmation rules in `SKILL.md` with a hard `--confirm` CLI flag on mutating scripts (defaulting to dry-run/exit 2), and explain `h2 distill` adaptations in plain language before calling `ask_user`. | Confirmation gate audit across `jira-story-onboard` and tracker mutation scripts (effect: helped, confidence: high) | `graduated (.github/skills/harness2/scripts/validate_harness.py)` |
