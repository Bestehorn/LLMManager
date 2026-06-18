---
paths:
  - "**/*.py"
---
# Dependency Management

Ported from `.kiro/steering/dependencies.md` (Kiro `inclusion: fileMatch`,
`fileMatchPattern: "**/*.py"`).

When adding, removing, or modifying imports:

1. **Review pyproject.toml** for needed dependency changes

2. **Dependency Locations**:
   - Production deps → `[project.dependencies]`
   - Dev tools → `[project.optional-dependencies.dev]`
   - Docs → `[project.optional-dependencies.docs]`

3. **Flag Changes**: Explicitly flag any dependency changes needed

4. **Install After Changes**:
```bash
venv\Scripts\activate & pip install -e ".[dev]"
```

5. **Project Dependencies**:
   - Core: boto3, botocore, beautifulsoup4, lxml, requests, tenacity
   - Dev: pytest, pytest-cov, pytest-mock, ruff, mypy, pre-commit, hypothesis
   - Docs: sphinx, sphinx-rtd-theme, sphinx-autodoc-typehints

6. **Version Constraints**: Preserve existing version pins unless explicitly updating
