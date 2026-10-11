# Contributing to saiga-cart

Contributions to extend the templates, planning frameworks, issue tracker adapters, or agent skills are welcome!

## Development & Testing

1. **Run Unit & Integration Tests**:
   ```bash
   # Run all unit and smoke tests
   python3 -m unittest discover -s tests -v

   # Run standalone unit tests
   python3 -m unittest tests/test_bootstrap_unit.py -v

   # Run end-to-end smoke matrix tests
   python3 -m unittest tests/test_bootstrap_matrix.py -v

   # Run skill unit tests
   python3 .github/skills/planning-docs-audit/scripts/test_planning_docs_audit.py
   python3 .github/skills/story-refiner/scripts/test_story_readiness.py
   ```
   *Note: On Windows systems, you can use `py -3 -m unittest discover -s tests -v`.*

   See [TESTING.md](TESTING.md) for full test strategy details and coverage matrix.

2. **Adding a New Planning Framework Adapter**:
   - Add template folder under `docs/planning/templates/<framework>-template/`.
   - Update `bootstrap.py` framework choices and mapping.

3. **Adding a New Issue Tracker Adapter**:
   - Add onboarding skill under `.github/skills/<tracker>-issue-onboard/`.
   - Add status sync skill under `.github/skills/<tracker>-status-sync/`.
   - Update `.github/skills/README.md`.
