# CI Configuration Guide

This document describes the CI configuration for the bestehorn-llmmanager project and how to maintain it.

## Overview

The CI pipeline ensures code quality through automated checks. All checks must pass before code can be merged.

## CI Checks

### 1. Code Formatting

**Black** (line length: 100 characters):
```bash
black src/ test/ --check --extend-exclude="src/bestehorn_llmmanager/_version.py"
```

**isort** (import sorting):
```bash
isort src/ test/ --check-only --skip="src/bestehorn_llmmanager/_version.py"
```

### 2. Linting

**flake8**:
```bash
flake8 src/ test/ --exclude="src/bestehorn_llmmanager/_version.py"
```

### 3. Type Checking

**mypy**:
```bash
mypy --exclude="_version" src/
```

### 4. Security Scanning

**bandit**:
```bash
bandit -r src/ -x "src/bestehorn_llmmanager/_version.py"
```

### 5. Testing

**pytest** (with coverage):
```bash
pytest test/ -v --cov=bestehorn_llmmanager --cov-fail-under=80
```

## Deprecation Warning Management

### Current Status

- **Production Code**: Must generate ZERO deprecation warnings
- **Test Code**: Total warnings must be under 100
- **Monitoring**: `test/bestehorn_llmmanager/test_deprecation_warning_count.py` enforces the threshold

### Warning Threshold Configuration

The deprecation warning threshold is enforced by a dedicated test that:
1. Runs the full test suite
2. Counts deprecation warnings
3. Fails if count exceeds 100

**Location**: `test/bestehorn_llmmanager/test_deprecation_warning_count.py`

### Reducing the Threshold

As deprecated APIs are migrated, the threshold should be gradually reduced:

1. Update the threshold in `test_deprecation_warning_count.py`
2. Verify all tests pass with the new threshold
3. Document the change in the PR

**Goal**: Reduce threshold to 0 over time.

### Handling New Warnings

If CI fails due to deprecation warnings:

1. **Identify the source**:
   - Run tests locally with warnings enabled
   - Check if warnings are from production or test code

2. **Fix production code immediately**:
   - Production code must use current APIs
   - Migrate deprecated API usage in the same PR

3. **Fix test code within release cycle**:
   - Update test code to use current APIs
   - Mark intentional deprecation tests clearly

4. **For intentional deprecation tests**:
   ```python
   @pytest.mark.filterwarnings("ignore::DeprecationWarning")
   def test_backward_compatibility():
       """Test deprecated API (intentional deprecation test)."""
       # Test code
   ```

## Test State Isolation

### Singleton Reset Requirements

All singletons with mutable state must:
1. Provide a `reset_for_testing()` class method
2. Have pytest fixtures for automatic cleanup
3. Be documented clearly

### Fixture Configuration

Shared fixtures are placed in `conftest.py` files:
- `test/conftest.py`: Global fixtures
- `test/bestehorn_llmmanager/bedrock/retry/conftest.py`: Retry-specific fixtures

Example fixture:
```python
@pytest.fixture(autouse=True)
def reset_singleton_state():
    """Reset singleton state before each test."""
    MySingleton.reset_for_testing()
    yield
    MySingleton.reset_for_testing()
```

## Property-Based Testing

### Configuration

- **Library**: Hypothesis
- **Minimum Iterations**: 100 for critical tests
- **Deadline**: Set to `None` for slow tests

### Test Tagging

Each property-based test must reference its design property:
```python
# Feature: feature-name, Property N: Property description
@given(st.integers())
@settings(max_examples=100)
def test_property(x):
    # Test implementation
```

## Running CI Checks Locally

Before pushing code, run all CI checks locally:

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Code formatting
black src/ test/ --check --extend-exclude="src/bestehorn_llmmanager/_version.py"
isort src/ test/ --check-only --skip="src/bestehorn_llmmanager/_version.py"

# Linting
flake8 src/ test/ --exclude="src/bestehorn_llmmanager/_version.py"

# Type checking
mypy --exclude="_version" src/

# Security scanning
bandit -r src/ -x "src/bestehorn_llmmanager/_version.py"

# Tests
pytest test/ -v
```

## CI Failure Response

### Immediate Actions

1. **Don't merge failing PRs**: All checks must pass
2. **Fix failures promptly**: Don't let failures accumulate
3. **Investigate flaky tests**: Any intermittent failure needs investigation

### Common Failures

**Black/isort failures**:
- Run formatters to fix: `black src/ test/` and `isort src/ test/`

**Flake8 failures**:
- Fix linting issues manually
- Check for unused imports, long lines, etc.

**Mypy failures**:
- Add missing type hints
- Fix type errors

**Test failures**:
- Run tests locally to reproduce
- Fix the underlying issue
- Don't skip or ignore failing tests

**Deprecation warning threshold exceeded**:
- Identify new warnings
- Migrate to current APIs
- Update tests

## Monitoring and Alerts

### Metrics to Track

1. **Test execution time**: Should stay under 20 minutes
2. **Deprecation warning count**: Should trend downward
3. **Test failure rate**: Should be near zero
4. **Code coverage**: Should stay above 80%

### Setting Up Alerts

Configure GitHub Actions to:
- Notify on CI failures
- Track warning count trends
- Alert on coverage drops
- Monitor test execution time

## Updating CI Configuration

### When to Update

- Adding new code quality tools
- Changing thresholds (coverage, warnings)
- Adding new test markers
- Updating Python versions

### How to Update

1. Update `pyproject.toml` for tool configuration
2. Update `.github/workflows/` for GitHub Actions
3. Update this document with changes
4. Test changes locally before pushing
5. Document changes in PR

## Troubleshooting

### CI Passes Locally But Fails in GitHub Actions

- Check Python version differences
- Verify environment variables
- Check for platform-specific issues (Windows vs Linux)
- Review GitHub Actions logs

### Flaky Tests

- Run test multiple times: `pytest --count=100 test_file.py::test_name`
- Check for state isolation issues
- Review singleton usage
- Check for timing dependencies

### Slow CI

- Profile test execution: `pytest --durations=10`
- Identify slow tests
- Optimize or mark as slow
- Consider parallel execution: `pytest -n auto`

## References

- [CONTRIBUTING.md](../CONTRIBUTING.md): Development guidelines
- [pytest.ini](../pytest.ini): Pytest configuration
- [pyproject.toml](../pyproject.toml): Tool configuration
- [.github/workflows/](.github/workflows/): GitHub Actions workflows
