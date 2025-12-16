---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Dependency Management

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
   - Core: boto3, botocore, beautifulsoup4, lxml, requests
   - Dev: pytest, pytest-cov, black, isort, flake8, mypy, pre-commit
   - Docs: sphinx, sphinx-rtd-theme

6. **Version Constraints**: Preserve existing version pins unless explicitly updating
