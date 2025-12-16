---
inclusion: always
---

# Post-Activity Checklist

Before marking any activity as complete:

1. **Run All Tests**: `pytest test/` - fix any failures before continuing

2. **Run CI Checks Locally**:
```bash
venv\Scripts\activate & black src/ test/ --check --extend-exclude="src/bestehorn_llmmanager/_version.py"
venv\Scripts\activate & isort src/ test/ --check-only --skip="src/bestehorn_llmmanager/_version.py"
venv\Scripts\activate & flake8 src/ test/ --exclude="src/bestehorn_llmmanager/_version.py"
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
