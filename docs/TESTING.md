# Testing Framework Documentation

This document describes the comprehensive testing framework implemented for the LLMManager project, including both unit testing and AWS integration testing capabilities.

## Overview

The testing framework follows best practices for Python testing using pytest and provides:

- **Mirror Structure**: The `test/` directory mirrors the `src/` directory structure exactly
- **Comprehensive Coverage**: Unit tests for all functions, classes, and code assets
- **AWS Integration Testing**: Real AWS Bedrock API integration tests for production validation
- **Automated Testing**: Easy-to-use test runners for different scenarios including hybrid test execution
- **Coverage Reporting**: Detailed coverage reports in multiple formats
- **Cost-Aware Testing**: AWS integration tests designed to minimize costs while maximizing coverage
- **CI/CD Ready**: Configured for continuous integration workflows

## Framework Structure

```
├── test/                           # Test directory (mirrors src/)
│   ├── __init__.py                # Test package initialization
│   ├── conftest.py                # Shared fixtures and configuration
│   ├── integration/               # Integration tests (real API calls)
│   │   ├── __init__.py
│   │   ├── test_integration_auth.py      # AWS authentication tests
│   │   └── test_integration_bedrock_api.py # Bedrock API tests
│   └── bedrock/                   # Unit tests for src/bedrock/
│       ├── __init__.py
│       ├── test_CRISManager.py    # Tests for CRISManager.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── test_constants.py  # Tests for constants.py
│       ├── parsers/
│       ├── downloaders/
│       ├── serializers/
│       ├── correlators/
│       └── testing/               # Tests for testing utilities
│           ├── __init__.py
│           └── test_integration_config.py
├── pytest.ini                     # Pytest configuration
├── requirements-test.txt           # Testing dependencies
├── run_tests.py                   # Python test runner
├── run_tests.bat                  # Windows batch test runner
├── docs/TESTING.md                # This documentation
└── docs/INTEGRATION_TESTING.md    # AWS integration testing guide
```

## Key Features

### 1. Test Organization

- **Mirror Structure**: Every file in `src/` has a corresponding test file in `test/`
- **Naming Convention**: Test files are prefixed with `test_` (e.g., `test_constants.py`)
- **Class Organization**: Test classes group related tests (e.g., `TestJSONFields`, `TestCRISManager`)

### 2. Test Categories

Tests are organized using pytest markers:

**Standard Test Types:**
- `@pytest.mark.unit` - Unit tests (default for all tests)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.network` - Tests requiring network access
- `@pytest.mark.aws` - Tests requiring AWS access

**AWS Integration Test Types:**
- `@pytest.mark.aws_integration` - Tests requiring real AWS Bedrock API access
- `@pytest.mark.aws_fast` - Fast integration tests (< 30 seconds)
- `@pytest.mark.aws_slow` - Slow integration tests (> 30 seconds)
- `@pytest.mark.aws_low_cost` - Low-cost tests (< $0.01 estimated)
- `@pytest.mark.aws_medium_cost` - Medium-cost tests ($0.01 - $0.10 estimated)
- `@pytest.mark.aws_high_cost` - High-cost tests (> $0.10 estimated)
- `@pytest.mark.aws_bedrock_runtime` - Tests using Bedrock Runtime API
- `@pytest.mark.aws_streaming` - Tests using streaming responses

For detailed information about AWS integration testing, see [`docs/INTEGRATION_TESTING.md`](INTEGRATION_TESTING.md).

### 3. Coverage Requirements

- **Minimum Coverage**: 80% code coverage required
- **Multiple Reports**: Terminal, HTML, and JSON coverage reports
- **Coverage Enforcement**: Tests fail if coverage drops below threshold

### 4. Fixtures and Utilities

Common fixtures in `conftest.py`:

- `temp_dir` - Temporary directory for test files
- `sample_html_content` - Mock HTML content for parser tests
- `sample_json_data` - Mock JSON data for serializer tests
- `mock_datetime` - Fixed datetime for consistent timestamps
- `mock_requests` - Mock HTTP requests for network tests

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
python run_tests.py

# Or use pytest directly
pytest
```

### Test Runner Options

The `run_tests.py` script provides many options:

```bash
# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Comprehensive Testing (Enhanced Feature)
python run_tests.py --all                          # Run both unit AND integration tests
python run_tests.py --all --aws-profile=my-dev     # Run all tests with specific AWS profile

# AWS Integration Testing (requires AWS credentials)
python run_tests.py --aws-integration              # Run all AWS integration tests
python run_tests.py --aws-fast                     # Run fast AWS tests only
python run_tests.py --aws-low-cost                 # Run low-cost AWS tests only
python run_tests.py --aws-profile=profile-name     # Use specific AWS profile

# Speed and performance options
python run_tests.py --fast                         # Skip slow tests (for quick feedback)
python run_tests.py --parallel                     # Run tests in parallel

# Reporting options
python run_tests.py --html                         # Generate HTML reports
python run_tests.py --verbose                      # Verbose output

# Control options
python run_tests.py --fail-fast                    # Stop on first failure
python run_tests.py --install-deps                 # Install dependencies automatically
```

#### Enhanced `--all` Switch

The `--all` switch provides comprehensive testing by combining both unit and integration tests:

- **Intelligent AWS Detection**: Automatically detects AWS credential availability
- **Graceful Fallback**: Runs unit tests only when AWS credentials aren't available
- **Clear User Feedback**: Provides informative messages about AWS credential status
- **Backward Compatibility**: Maintains compatibility with existing test runner options

**AWS Credential Detection:**
- **Environment Variables**: Checks for `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- **AWS CLI Configuration**: Validates credentials using `aws sts get-caller-identity`
- **Graceful Fallback**: When `--all` is used without AWS credentials, runs unit tests only
- **Clear Messaging**: Informs users about AWS credential status and provides guidance

### Windows Users

Use the batch script:

```cmd
run_tests.bat --unit
run_tests.bat --html
```

### Direct Pytest Usage

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run specific test files
pytest test/bedrock/models/test_constants.py
pytest test/bedrock/test_CRISManager.py -v

# Run tests matching a pattern
pytest -k "test_initialization"

# Run with parallel execution
pytest -n auto
```

## Test Writing Guidelines

### 1. Test Structure

Each test file should follow this structure:

```python
"""
Unit tests for src.module.file module.

Brief description of what this module tests.
"""

import pytest
from unittest.mock import Mock, patch

from src.module.file import ClassToTest


class TestClassToTest:
    """Test the main class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.instance = ClassToTest()
    
    def test_method_success(self):
        """Test successful operation of method."""
        result = self.instance.method()
        assert result == expected_value
    
    def test_method_error_handling(self):
        """Test error handling in method."""
        with pytest.raises(ExpectedException):
            self.instance.method(invalid_input)
```

### 2. Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<what_is_being_tested>`

### 3. Comprehensive Testing

Each test file should test:

- ✅ **Happy Path**: Normal operation with valid inputs
- ✅ **Edge Cases**: Boundary conditions and edge cases
- ✅ **Error Handling**: Exception handling and error conditions
- ✅ **State Changes**: Object state changes and side effects
- ✅ **Integration Points**: Interactions with other components
- ✅ **Configuration**: Different configuration options
- ✅ **Immutability**: Constants and final values (where applicable)

### 4. Mock Usage

Use mocks for:

- External dependencies (network, file system, databases)
- Time-dependent operations
- Random or non-deterministic behavior
- Expensive operations

```python
@patch('src.module.requests.get')
def test_network_operation(self, mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "test response"
    
    result = function_that_makes_request()
    assert result == expected_result
```

### 5. Fixture Usage

Use fixtures for:

- Common test data
- Temporary resources
- Setup and teardown operations

```python
@pytest.fixture
def sample_data():
    return {"key": "value", "number": 42}

def test_with_fixture(sample_data):
    result = process_data(sample_data)
    assert result is not None
```

## AWS Integration Testing

### Overview

AWS Integration Testing validates the LLMManager project with real AWS Bedrock API calls, providing comprehensive coverage of areas that cannot be effectively tested with mocks alone.

### New AWS Integration Test Files

#### `test/integration/test_integration_llm_manager.py`
Comprehensive integration tests for the main `LLMManager` class covering:

**Basic Functionality:**
- Real model initialization with AWS Bedrock
- Actual converse API calls with real models
- System message handling
- Multi-region failover testing
- Custom retry configuration testing

**Error Handling:**
- Invalid model name handling with proper exception validation
- Request validation with real AWS constraints
- Invalid region error handling
- Retry exhaustion scenarios

**Advanced Features:**
- Streaming converse functionality
- Model access information retrieval
- Model data refresh operations
- Response parsing and content extraction

#### `test/integration/test_integration_unified_model_manager.py`
Comprehensive integration tests for the `UnifiedModelManager` class covering:

**Basic Functionality:**
- Manager initialization with real network calls
- Data refresh with actual AWS documentation
- Model catalog queries with real data
- Cached data loading and management

**Model Access Testing:**
- Real model access information retrieval
- Regional availability queries
- Access method determination (direct vs CRIS)
- Recommendation system testing

**Configuration Testing:**
- Fuzzy matching configuration
- Error handling with no data scenarios
- String representation testing

### Integration Test Organization

**Test Structure:**
Tests are organized into logical classes:
- **Basic Functionality**: Core operations that should work in normal conditions
- **Error Handling**: Tests for failure scenarios and error recovery
- **Advanced Features**: Tests for complex features and edge cases
- **Configuration**: Tests for various configuration options and settings

**Pytest Markers Used:**
- `@pytest.mark.aws_integration`: Marks tests requiring real AWS access
- `@pytest.mark.aws_low_cost`: Tests estimated to cost < $0.01
- `@pytest.mark.aws_fast`: Tests completing in < 30 seconds
- `@pytest.mark.integration`: General integration test marker

### Coverage Improvements

The AWS integration tests target high-miss areas from the coverage report:

**Areas Previously Uncovered (Now Tested):**

1. **Authentication Flows**: Real AWS credential handling and region-specific authentication
2. **API Response Parsing**: Actual Bedrock API response structures and parsing logic
3. **Retry Logic**: Real failure scenarios and exponential backoff behavior
4. **Network Error Handling**: Actual network timeouts and connectivity issues
5. **Model Data Processing**: Real AWS documentation parsing and correlation
6. **Multi-Region Operations**: Actual cross-region failover and availability checking

**Expected Coverage Improvements:**

- **LLMManager.py**: 13% → 40-50% (targets lines 89-121, 130-144, 148-163, 204-289, 325-378, etc.)
- **UnifiedModelManager.py**: 26% → 50-60% (targets lines 99-112, 135-170, 179-191, etc.)
- **Authentication components**: 45% → 70-80%
- **Retry mechanisms**: 8% → 30-40%

**Overall Project Coverage:**
- **Before Integration Tests**: 38% overall coverage with `--aws-integration`
- **After Integration Tests**: 55-65% overall coverage with `--all`

### AWS Integration Usage Examples

#### Run All Tests (Unit + Integration)
```bash
python run_tests.py --all --aws-profile my-profile
```

#### Run Only AWS Integration Tests
```bash
python run_tests.py --aws-integration --aws-profile my-profile
```

#### Run Fast, Low-Cost Integration Tests
```bash
python run_tests.py --aws-integration --aws-fast --aws-low-cost --aws-profile my-profile
```

#### Run with Coverage and HTML Report
```bash
python run_tests.py --all --html --aws-profile my-profile
```

### AWS Integration Best Practices

#### Test Design Principles
1. **Use Real AWS Calls**: Tests make actual API calls to validate real-world behavior
2. **Cost Awareness**: Tests are designed to minimize AWS costs while maximizing coverage
3. **Graceful Degradation**: Tests skip rather than fail when AWS resources are unavailable
4. **Comprehensive Assertions**: Tests verify not just success but also response structure and content

#### Configuration Requirements
- AWS credentials must be configured (via profile or environment variables)
- Test regions must be enabled for Bedrock access
- Models must be available in the test regions

#### Error Handling in Integration Tests
- Tests use `pytest.skip()` for infrastructure issues (network, AWS availability)
- Tests use `pytest.raises()` for expected error conditions
- All tests include appropriate error messages for debugging

**Important for Integration Tests:** When writing integration tests that validate exception handling, import exceptions directly from `bedrock.exceptions.llm_manager_exceptions` rather than `src.bedrock.exceptions.llm_manager_exceptions` to ensure proper exception type matching with pytest.raises().

```python
# ✅ Correct import for integration tests
from bedrock.exceptions.llm_manager_exceptions import ConfigurationError, RequestValidationError

# ❌ Incorrect import (will cause pytest.raises to fail)
from src.bedrock.exceptions.llm_manager_exceptions import ConfigurationError, RequestValidationError
```

#### Maintenance Considerations

**Updating Tests:**
- Add new integration tests when adding AWS-dependent functionality
- Update test configurations when adding new regions or models
- Maintain cost-awareness as AWS pricing changes

**Monitoring:**
- Monitor test execution costs through AWS billing
- Track test execution times to ensure they remain in "fast" category
- Update test data when AWS adds new models or regions

## Coverage Reporting

### Coverage Thresholds

- **Project Minimum**: 80% overall coverage
- **File Minimum**: 70% per file (recommended)
- **Critical Modules**: 90% coverage for core functionality

### Coverage Reports

1. **Terminal Report**: Shows coverage summary with missing lines
2. **HTML Report**: Detailed interactive report in `htmlcov/index.html`
3. **JSON Report**: Machine-readable report in `coverage.json`

### Viewing Coverage

```bash
# Generate and view HTML coverage report
python run_tests.py --html
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html # Windows
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: python run_tests.py --html
    
    - name: Upload coverage reports
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/
```

## Best Practices

### 1. Test Independence

- Each test should be independent
- Tests should not depend on execution order
- Use fixtures for shared setup, not global state

### 2. Test Data

- Use realistic but minimal test data
- Create dedicated test data factories
- Avoid hardcoded values where possible

### 3. Assertions

- Use specific assertions (`assert x == 5` not `assert x`)
- Test one thing per test method
- Include descriptive failure messages when helpful

### 4. Performance

- Mark slow tests with `@pytest.mark.slow`
- Use mocks to avoid expensive operations
- Consider parallel test execution for large test suites

### 5. Maintenance

- Keep tests up to date with code changes
- Refactor tests when code is refactored
- Remove obsolete tests for removed functionality

## Common Patterns

### Testing Constants

```python
def test_constant_values(self):
    """Test that constants have expected values."""
    assert MyConstants.VALUE == "expected_value"
    assert isinstance(MyConstants.VALUE, str)

def test_constants_immutable(self):
    """Test that constants cannot be changed."""
    with pytest.raises(AttributeError):
        MyConstants.VALUE = "new_value"
```

### Testing Error Handling

```python
def test_error_handling(self):
    """Test proper error handling."""
    with pytest.raises(CustomException) as exc_info:
        function_that_should_fail()
    
    assert "expected error message" in str(exc_info.value)
```

### Testing File Operations

```python
def test_file_operations(self, temp_dir):
    """Test file operations using temporary directory."""
    test_file = temp_dir / "test.txt"
    
    write_file(test_file, "test content")
    
    assert test_file.exists()
    assert test_file.read_text() == "test content"
```

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test asynchronous function."""
    result = await async_function()
    assert result == expected_value
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `src/` is in Python path
2. **Missing Dependencies**: Run `pip install -r requirements-test.txt`
3. **Coverage Too Low**: Add more tests or exclude non-testable code
4. **Slow Tests**: Use `--fast` flag or mark tests with `@pytest.mark.slow`

### Debug Tips

```bash
# Run single test with verbose output
pytest test/bedrock/test_CRISManager.py::TestCRISManager::test_method -v -s

# Run with debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Show full traceback
pytest --tb=long
```

## Adding New Tests

When adding a new module to `src/`, follow these steps:

1. **Create Test File**: Create corresponding test file in `test/`
2. **Mirror Structure**: Match the directory structure exactly
3. **Import Module**: Import the module being tested
4. **Write Test Classes**: Create test classes for each main class
5. **Test All Functions**: Write tests for all public functions/methods
6. **Test Error Cases**: Include error handling tests
7. **Run Tests**: Verify tests pass and coverage is adequate
8. **Update Documentation**: Update this document if needed

This comprehensive testing framework ensures code quality, prevents regressions, and provides confidence in the reliability of the LLMManager project.
