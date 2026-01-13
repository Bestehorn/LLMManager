# Contributing to bestehorn-llmmanager

First off, thank you for considering contributing to bestehorn-llmmanager! It's people like you that make this library a great tool for the community.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [markus.bestehorn@googlemail.com](mailto:markus.bestehorn@googlemail.com).

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, please include as many details as possible:

- **Use a clear and descriptive title** for the issue
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** to demonstrate the steps
- **Describe the behavior you observed** and what behavior you expected
- **Include Python version, OS, and AWS region** information
- **Include stack traces and error messages** if applicable

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful** to most users
- **List any alternatives you've considered**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the project's style guidelines
6. Issue that pull request!

## Development Setup

1. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/bestehorn-llmmanager.git
   cd bestehorn-llmmanager
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode with all dependencies**:
   ```bash
   pip install -e .[dev]
   ```
   
   This installs the package in editable mode along with all development dependencies including:
   - Testing tools (pytest, pytest-cov, etc.)
   - Code quality tools (black, isort, flake8, mypy)
   - Documentation tools (sphinx)
   - Build tools (build, twine)

4. **Install pre-commit hooks** (optional):
   ```bash
   pre-commit install
   ```

## Development Guidelines

### Code Style

- We use [Black](https://github.com/psf/black) for code formatting (line length: 100)
- We use [isort](https://pycqa.github.io/isort/) for import sorting
- We use [flake8](https://flake8.pycqa.org/) for linting
- We use [mypy](http://mypy-lang.org/) for type checking

Run all formatters and linters:
```bash
black src/ test/
isort src/ test/
flake8 src/ test/
mypy src/
```

### Testing

- Write tests for any new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage (>90%)

Run tests:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bestehorn_llmmanager

# Run only unit tests
pytest -m "not integration"

# Run specific test file
pytest test/bestehorn_llmmanager/test_llm_manager.py
```

### Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstrings
- Update README.md if adding new features
- Add examples to demonstrate new functionality

Example docstring:
```python
def converse(self, messages: List[Dict[str, Any]], **kwargs) -> BedrockResponse:
    """Send a conversation request to AWS Bedrock.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        **kwargs: Additional parameters for the Bedrock API
        
    Returns:
        BedrockResponse object containing the model's response
        
    Raises:
        ConfigurationError: If the manager is not properly configured
        RequestValidationError: If the request is invalid
    """
```

### Managing Deprecation Warnings

**Why This Matters**: Deprecation warnings accumulate over time and create noise that hides real issues. We maintain strict control over warnings to ensure code quality.

**Guidelines**:

1. **Zero Tolerance for Production Code**:
   - Production code (in `src/`) must generate ZERO deprecation warnings
   - Migrate to current APIs immediately when deprecating features
   - Never commit code that uses deprecated APIs

2. **Test Code Warning Threshold**:
   - Total deprecation warnings across all tests must be under 100
   - CI will fail if this threshold is exceeded
   - Regularly review and reduce warning counts

3. **When Deprecating APIs**:
   - Provide clear migration path in warning message
   - Update all production code in the same PR
   - Update test code within the same release cycle
   - Document migration in CHANGELOG.md
   - Set a removal deadline (typically 2-3 releases)

4. **Intentional Deprecation Tests**:
   - Clearly mark tests that intentionally use deprecated APIs
   - Use pytest warning filters for expected warnings
   - Document why the test uses deprecated APIs
   ```python
   @pytest.mark.filterwarnings("ignore::DeprecationWarning")
   def test_backward_compatibility_for_deprecated_api():
       """Test that deprecated API still works (intentional deprecation test)."""
       # Test code using deprecated API
   ```

5. **CI Warning Checks**:
   - CI automatically tracks deprecation warning counts
   - Warnings are reported in test output
   - PRs that increase warning counts will be flagged

### Test State Isolation

**Why This Matters**: Tests that share state can interfere with each other, causing flaky tests that pass or fail unpredictably. This wastes developer time and undermines confidence in CI.

**Guidelines**:

1. **Singleton Pattern Restrictions**:
   - Avoid singletons with mutable state when possible
   - If singletons are necessary, always provide a `reset_for_testing()` method
   - Document the reset method with clear warnings about production use
   - Make reset methods thread-safe

2. **Test Isolation Checklist**:
   Before submitting a PR with tests, verify:
   - [ ] Tests pass when run individually
   - [ ] Tests pass when run in any order
   - [ ] Tests pass when run in parallel (`pytest -n auto`)
   - [ ] Tests pass when run repeatedly (`pytest --count=10`)
   - [ ] No shared mutable state between tests

3. **Pytest Fixtures for Cleanup**:
   - Use `autouse=True` fixtures for automatic state cleanup
   - Reset state both before and after each test
   - Place shared fixtures in `conftest.py`
   ```python
   @pytest.fixture(autouse=True)
   def reset_singleton_state():
       """Reset singleton state before each test."""
       MySingleton.reset_for_testing()
       yield
       MySingleton.reset_for_testing()
   ```

4. **State Management Best Practices**:
   - Clear all caches before tests
   - Reset environment variables
   - Clean up temporary files and databases
   - Reset module-level variables
   - Close all open connections

5. **Detecting Flaky Tests**:
   - Run tests multiple times locally: `pytest --count=100 test_file.py::test_name`
   - Use Hypothesis with high iteration counts (100+)
   - Monitor CI for intermittent failures
   - Investigate any test that fails even once unexpectedly

### Singleton Patterns

**Why This Matters**: Singletons with mutable state are a common source of test flakiness and production bugs. Use them carefully and follow these guidelines.

**Guidelines**:

1. **When to Avoid Singletons**:
   - Prefer dependency injection over singletons
   - Use factory patterns for shared instances
   - Consider module-level instances instead of class-level singletons
   - Question whether you really need a singleton

2. **If Singletons Are Necessary**:
   - Always provide a `reset_for_testing()` class method
   - Make the reset method thread-safe (use locks)
   - Document that reset should ONLY be called from test code
   - Add clear warnings about production use
   ```python
   @classmethod
   def reset_for_testing(cls) -> None:
       """
       Reset singleton state for testing purposes.
       
       WARNING: This method should ONLY be called from test code.
       It clears all state and resets the singleton instance.
       Calling this in production will cause unexpected behavior.
       """
       with cls._lock:
           if cls._instance is not None:
               cls._instance._state.clear()
               cls._instance._initialized = False
           cls._instance = None
   ```

3. **Thread Safety**:
   - Protect all state access with locks
   - Use `threading.Lock()` for synchronization
   - Consider using `threading.RLock()` for reentrant locks
   - Test concurrent access patterns

4. **Alternative Patterns**:
   ```python
   # Instead of singleton:
   class MyService:
       _instance = None
       
       @classmethod
       def get_instance(cls):
           if cls._instance is None:
               cls._instance = cls()
           return cls._instance
   
   # Consider dependency injection:
   class MyClient:
       def __init__(self, service: MyService):
           self.service = service
   
   # Or factory pattern:
   def get_service(reset: bool = False) -> MyService:
       if reset or not hasattr(get_service, '_instance'):
           get_service._instance = MyService()
       return get_service._instance
   ```

5. **Documentation Requirements**:
   - Document singleton lifecycle clearly
   - Explain when state persists vs. resets
   - Provide examples of proper usage
   - Document thread-safety guarantees

### Property-Based Testing

**Why This Matters**: Property-based tests validate universal properties across many generated inputs, catching edge cases that example-based tests miss.

**Guidelines**:

1. **When to Use Property-Based Tests**:
   - Testing universal properties (e.g., "parsing then printing should be identity")
   - Validating invariants (e.g., "list length never decreases after filter")
   - Testing across wide input ranges
   - Verifying deterministic behavior

2. **Configuration**:
   - Use minimum 100 iterations for critical tests
   - Set appropriate deadlines for slow tests
   - Use deterministic seeds for reproducibility
   ```python
   from hypothesis import given, settings
   import hypothesis.strategies as st
   
   @given(st.integers(), st.text())
   @settings(max_examples=100, deadline=None)
   def test_property(x, y):
       # Property test
   ```

3. **Test Strategies**:
   - Create custom strategies for domain objects
   - Ensure generated data is valid
   - Use `assume()` to filter invalid inputs
   - Combine strategies for complex objects
   ```python
   @st.composite
   def model_access_info(draw):
       has_direct = draw(st.booleans())
       model_id = draw(st.text()) if has_direct else None
       return ModelAccessInfo(
           model_id=model_id,
           has_direct_access=has_direct,
           # ... other fields
       )
   ```

4. **Debugging Failed Properties**:
   - Use Hypothesis's `@reproduce_failure` decorator
   - Add `note()` calls to log intermediate values
   - Shrink failing examples to minimal cases
   - Investigate why the property failed

5. **Test Tagging**:
   - Tag each property test with its design property
   - Reference the feature and property number
   ```python
   # Feature: ci-failure-fixes, Property 1: Access Method Selection Determinism
   @given(model_access_info(), learned_preferences())
   def test_access_method_selection_determinism(access_info, preference):
       # Test implementation
   ```

### CI Configuration and Monitoring

**Why This Matters**: CI is our safety net. Proper configuration catches issues early and prevents regressions.

**Guidelines**:

1. **Warning Thresholds**:
   - CI fails if deprecation warnings exceed 100
   - Monitor warning trends over time
   - Gradually reduce threshold as warnings are fixed
   - Alert on sudden increases in warnings

2. **Pre-Commit Checks**:
   Run these checks before committing:
   ```bash
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

3. **CI Pipeline Stages**:
   - Code quality checks (black, isort, flake8, mypy, bandit)
   - Unit tests with coverage
   - Integration tests (if AWS credentials available)
   - Deprecation warning count check
   - Documentation build

4. **Monitoring Metrics**:
   - Test execution time trends
   - Test failure rates
   - Deprecation warning counts
   - Code coverage percentages
   - Flaky test occurrences

5. **Failure Response**:
   - Fix CI failures immediately
   - Don't merge PRs with failing CI
   - Investigate flaky tests promptly
   - Update thresholds as needed

### Code Review Checklist

**Why This Matters**: Code review is our first line of defense against bugs and technical debt.

**For Reviewers**:

1. **Singleton Usage**:
   - [ ] Is the singleton necessary?
   - [ ] Does it have a `reset_for_testing()` method?
   - [ ] Is the reset method thread-safe?
   - [ ] Is it documented clearly?

2. **Deprecation**:
   - [ ] Does new code use current APIs?
   - [ ] Are deprecated APIs migrated?
   - [ ] Are deprecation warnings clear?
   - [ ] Is migration documentation provided?

3. **Test Quality**:
   - [ ] Are tests deterministic?
   - [ ] Is state properly cleaned up?
   - [ ] Are tests isolated?
   - [ ] Do property-based tests have sufficient iterations?

4. **Code Quality**:
   - [ ] Does code follow style guidelines?
   - [ ] Are type hints comprehensive?
   - [ ] Is error handling appropriate?
   - [ ] Is documentation updated?

5. **Breaking Changes**:
   - [ ] Are breaking changes documented?
   - [ ] Is backward compatibility maintained?
   - [ ] Are migration paths provided?
   - [ ] Is the changelog updated?

**For Authors**:

Before requesting review:
- [ ] All CI checks pass
- [ ] Tests are added for new functionality
- [ ] Documentation is updated
- [ ] No new deprecation warnings
- [ ] Code follows style guidelines
- [ ] Commit messages are clear

### Commit Messages

- Use clear and meaningful commit messages
- Start with a verb in present tense: "Add", "Fix", "Update", etc.
- Keep the first line under 50 characters
- Add detailed description if needed

Examples:
```
Add support for Claude 3 Opus model
Fix retry logic for throttled requests
Update documentation for MessageBuilder
```

## Project Structure

```
bestehorn-llmmanager/
├── src/
│   └── bestehorn_llmmanager/      # Main package
│       ├── bedrock/               # AWS Bedrock specific modules
│       └── util/                  # Utility modules
├── test/                          # Test files
│   ├── bestehorn_llmmanager/      # Unit tests
│   └── integration/               # Integration tests
├── docs/                          # Documentation
├── examples/                      # Example scripts
└── notebooks/                     # Jupyter notebooks
```

## Release Process

1. Update version in `pyproject.toml` and `src/bestehorn_llmmanager/__init__.py`
2. Update CHANGELOG.md
3. Create a pull request with version bump
4. After merge, create a GitHub release
5. Package will be automatically published to PyPI

## Questions?

Feel free to open an issue for any questions about contributing. We're here to help!

## Recognition

Contributors will be recognized in the project's README and release notes. Thank you for your contributions!
