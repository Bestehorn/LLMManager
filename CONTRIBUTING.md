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
