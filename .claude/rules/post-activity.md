# Post-Activity Checklist

Ported from `.kiro/steering/post-activity.md` (Kiro `inclusion: always`).

Before marking any activity as complete:

1. **Run All Tests**: `venv\Scripts\activate & pytest test/` — fix any failures before
   continuing. Implementation is never finished with failing tests
   (see `.claude/rules/tests-must-not-fail.md`).

2. **Run CI Checks Locally** (all inside the venv):
```bash
venv\Scripts\activate & black src/ test/ scripts/ --check --extend-exclude="src/bestehorn_llmmanager/_version.py"
venv\Scripts\activate & isort src/ test/ scripts/ --check-only --skip="src/bestehorn_llmmanager/_version.py"
venv\Scripts\activate & flake8 src/ test/ scripts/ --max-line-length=100 --extend-ignore=E203,W503 --exclude="src/bestehorn_llmmanager/_version.py"
venv\Scripts\activate & mypy --exclude="_version" src/
venv\Scripts\activate & bandit -r src/ scripts/ -x "src/bestehorn_llmmanager/_version.py"
```

Fix all issues before continuing.

3. **Update Documentation**:
   - Update `docs/` to reflect any changes
   - Update `docs/forLLMConsumption.md` with consolidated info

4. **Flag Deviations**: Report any documentation/implementation mismatches

5. **Clean tmp/**: Remove all temporary files

**Project-Specific Notes**:
- Line length is 100 characters (not 120)
- Always exclude `_version.py` from all checks
- Use Windows path separators and activation commands
- The `/run-ci` slash command automates this CI loop end to end.
