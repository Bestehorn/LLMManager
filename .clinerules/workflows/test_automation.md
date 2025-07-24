# Test Automation Workflow

This Cline Workflow ensures comprehensive test coverage and quality for the LLMManager project by systematically improving test coverage, running all tests, fixing failures, maintaining code quality, and updating documentation.

## Overview

This workflow automates the process of achieving and maintaining high test coverage while ensuring code quality and documentation alignment. It follows a systematic approach to test automation that mirrors production-ready development practices.
Any coding assistant that is asked to perform this workflow, must execute the entire process outlines in the "Workflow Steps" section below.

## Prerequisites

Before starting this workflow, the coding assistant must review the project documentation to ensure all changes align with the design and coding principles:

### Pre-Workflow Documentation Review
```bash
# Review core documentation files
cat docs/forLLMConsumption.md
cat docs/ProjectStructure.md
cat README.md
cat pyproject.toml
```

**Required Understanding:**
- Project architecture and design principles
- Coding standards and conventions
- API design patterns
- Testing strategies and markers
- Coverage requirements and configuration

## Workflow Steps

### Step 1: Test Coverage Analysis and Improvement

#### 1.1: Generate Current Coverage Report
```bash
# Install development dependencies
pip install -e .[dev]

# Generate comprehensive coverage report
pytest test/bestehorn_llmmanager/ --cov=bestehorn_llmmanager --cov-report=html:htmlcov --cov-report=term-missing --cov-report=json:coverage.json --cov-fail-under=80 -v
```

#### 1.2: Analyze Coverage Gaps
```bash
# Display coverage report with missing lines
coverage report --show-missing

# Generate detailed HTML coverage report for analysis
coverage html
```

**Coverage Analysis Criteria:**
- **Target Threshold**: 80% minimum (configured in pyproject.toml)
- **Critical Path Priority**: Focus on core functionality in:
  - `src/bestehorn_llmmanager/llm_manager.py`
  - `src/bestehorn_llmmanager/parallel_llm_manager.py`
  - `src/bestehorn_llmmanager/message_builder.py`
  - `src/bestehorn_llmmanager/bedrock/` core modules
- **Low Coverage Priority**: Files with <60% coverage
- **Functionality Priority**: Public APIs, error handling, retry logic, validation

#### 1.3: Identify Test Gaps
```bash
# List all source files for coverage analysis
find src/bestehorn_llmmanager -name "*.py" -not -path "*/__pycache__/*" -not -name "_version.py" | sort

# Check existing test structure
find test -name "*.py" -not -path "*/__pycache__/*" | sort
```

#### 1.4: Implement Missing Tests

**Test Categories to Implement:**

1. **Unit Tests** (test/bestehorn_llmmanager/):
   - Core functionality tests
   - Edge case handling
   - Error condition testing
   - Input validation testing
   - Configuration testing

2. **Integration Tests** (test/integration/):
   - API interaction tests
   - Multi-component workflow tests
   - End-to-end functionality tests

3. **Property-Based Tests**:
   - MessageBuilder input validation
   - Retry logic verification
   - Parallel processing behavior

**Test Implementation Guidelines:**
- Use pytest fixtures from `test/conftest.py`
- Follow existing test patterns and naming conventions
- Include comprehensive docstrings
- Use appropriate test markers (unit, integration, aws, etc.)
- Mock external dependencies appropriately
- Test both success and failure scenarios

#### 1.5: Coverage Validation
```bash
# Verify improved coverage meets threshold
pytest test/bestehorn_llmmanager/ --cov=bestehorn_llmmanager --cov-report=term-missing --cov-fail-under=80 -v

# Generate updated coverage report
coverage report --show-missing
```

**Step 1 Completion Criteria:**
- Overall test coverage ≥80%
- Critical path components have ≥90% coverage
- All public APIs have test coverage
- Error handling paths are tested
- No major functionality gaps remain

### Step 2: Complete Test Suite Execution

#### 2.1: Run Unit Tests
```bash
# Execute all unit tests with coverage
pytest test/bestehorn_llmmanager/ -v --cov=bestehorn_llmmanager --cov-report=term-missing --tb=short --durations=10
```

#### 2.2: Run Integration Tests
```bash
# Execute integration tests (may require AWS credentials)
pytest test/integration/ -v --tb=short --durations=10

# Run with specific markers for controlled execution
pytest test/integration/ -m "aws_fast" -v --tb=short
```

#### 2.3: Run Complete Test Suite
```bash
# Execute all tests with comprehensive reporting
pytest test/ -v --cov=bestehorn_llmmanager --cov-report=html:htmlcov --cov-report=term-missing --cov-report=json:coverage.json --html=test_results.html --self-contained-html --tb=short --durations=10
```

#### 2.4: Coverage Gap Analysis
```bash
# Check if coverage threshold is still met after full test run
coverage report --fail-under=80

# Identify any remaining gaps
coverage report --show-missing | grep -E "^(TOTAL|.*\.py)" | sort -k4 -n
```

**Step 2 Completion Criteria:**
- All unit tests pass
- All integration tests pass (or are properly skipped with markers)
- Overall coverage ≥80%
- No critical functionality remains untested

**If Coverage Gaps Remain**: Return to Step 1 and implement additional tests for uncovered areas.

### Step 3: Test Failure Resolution

#### 3.1: Identify Failing Tests
```bash
# Run tests with detailed failure information
pytest test/ -v --tb=long --failed-first --no-header -q

# Generate failure report
pytest test/ --tb=short -q | tee test_failures.txt
```

#### 3.2: Analyze Test Failures

**Failure Categories:**
1. **Logic Errors**: Incorrect implementation in application code
2. **Test Errors**: Incorrect test implementation or assumptions
3. **Configuration Issues**: Environment or dependency problems
4. **Integration Issues**: External service dependency problems
5. **Timing Issues**: Race conditions or timeout problems

#### 3.3: Implement Fixes

**Fix Implementation Process:**
1. **Root Cause Analysis**: Identify the underlying cause of each failure
2. **Application Code Fixes**: Correct logic errors, edge cases, or implementation bugs
3. **Test Code Fixes**: Update test expectations, mocks, or test data
4. **Documentation Updates**: Update docstrings and comments if behavior changes

**Fix Categories:**
- **Application Code**: Fix bugs in `src/bestehorn_llmmanager/`
- **Test Code**: Fix test logic in `test/`
- **Configuration**: Update `pyproject.toml`, `pytest.ini`, or `.coveragerc`
- **Dependencies**: Update requirements or version constraints

#### 3.4: Verify Fixes
```bash
# Re-run previously failing tests
pytest test/ -v --tb=short --failed-first

# Run full test suite to ensure no regressions
pytest test/ -v --cov=bestehorn_llmmanager --cov-report=term-missing --cov-fail-under=80
```

**Step 3 Completion Criteria:**
- All tests pass
- No new test failures introduced
- Coverage threshold maintained
- All fixes are properly tested

**If Tests Still Fail**: Repeat Steps 3.1-3.4 until all tests pass.

### Step 4: Code Quality Validation

#### 4.1: Execute Code Quality Checks
```bash
# Run the complete code quality workflow
# This references the existing pre-commit-checks workflow
```

**Code Quality Workflow Reference**: `.clinerules/workflows/pre-commit-checks.md`

#### 4.2: Code Quality Check Steps

**Step 4.2.1: Install Dependencies**
```bash
python -m pip install --upgrade pip
pip install black flake8 isort mypy
pip install -e .
```

**Step 4.2.2: Code Formatting Check**
```bash
black --check --extend-exclude="src/bestehorn_llmmanager/_version.py" src/ test/
```

**Step 4.2.3: Import Sorting Check**
```bash
isort --check-only --skip="src/bestehorn_llmmanager/_version.py" src/ test/
```

**Step 4.2.4: Linting Check**
```bash
flake8 --exclude="src/bestehorn_llmmanager/_version.py" src/ test/
```

**Step 4.2.5: Type Checking**
```bash
mypy --exclude="_version" src/
```

#### 4.3: Fix Code Quality Issues

**If Code Quality Issues Are Found:**

1. **Formatting Issues**:
   ```bash
   black --extend-exclude="src/bestehorn_llmmanager/_version.py" src/ test/
   ```

2. **Import Sorting Issues**:
   ```bash
   isort --skip="src/bestehorn_llmmanager/_version.py" src/ test/
   ```

3. **Linting Issues**:
   - Fix style violations, unused imports, undefined variables
   - Ensure line length compliance
   - Address code complexity issues

4. **Type Checking Issues**:
   - Add missing type annotations
   - Fix type mismatches
   - Update type hints for clarity

#### 4.4: Verify Code Quality
```bash
# Run all quality checks in sequence
black --check --extend-exclude="src/bestehorn_llmmanager/_version.py" src/ test/ && \
isort --check-only --skip="src/bestehorn_llmmanager/_version.py" src/ test/ && \
flake8 --exclude="src/bestehorn_llmmanager/_version.py" src/ test/ && \
mypy --exclude="_version" src/
```

**Step 4 Completion Criteria:**
- All code formatting checks pass
- All import sorting checks pass
- All linting checks pass
- All type checking passes
- Code follows project conventions

**If Code Quality Issues Remain**: Repeat Steps 4.2-4.4 until all quality standards are met.

### Step 5: Documentation Review and Updates

#### 5.1: Review All Documentation
```bash
# List all documentation files
find docs/ -name "*.md" -o -name "*.rst" -o -name "*.txt" | sort

# Review core documentation
cat docs/forLLMConsumption.md
cat docs/ProjectStructure.md  
cat README.md
cat CHANGELOG.md
```

#### 5.2: Identify Documentation Updates

**Documentation Categories to Review:**

1. **API Documentation** (`docs/forLLMConsumption.md`):
   - Method signatures and parameter changes
   - New functionality additions
   - Behavior modifications
   - Error handling changes

2. **Project Structure** (`docs/ProjectStructure.md`):
   - New modules or components
   - Architecture changes
   - Test structure updates

3. **README** (`README.md`):
   - Installation instructions
   - Usage examples
   - Feature descriptions
   - Requirements updates

4. **Changelog** (`CHANGELOG.md`):
   - New features added
   - Bug fixes implemented
   - Breaking changes
   - Test improvements

5. **Code Comments and Docstrings**:
   - Function and class documentation
   - Parameter descriptions
   - Return value documentation
   - Example usage

#### 5.3: Update Documentation

**Update Process:**
1. **Code Documentation**: Update docstrings for modified functions/classes
2. **API Documentation**: Update API reference for changed interfaces
3. **Usage Examples**: Update examples to reflect new functionality
4. **Configuration**: Update configuration documentation for new options
5. **Testing**: Document new test categories or markers

**Documentation Standards:**
- Follow existing documentation style and format
- Include code examples for new features
- Update version information where applicable
- Ensure consistency across all documentation files

#### 5.4: Validate Documentation
```bash
# Check for broken links in documentation
find docs/ -name "*.md" -exec grep -l "http" {} \;

# Verify code examples in documentation work
# (Extract and test code examples if applicable)

# Check documentation formatting
# (Use documentation linting tools if available)
```

**Step 5 Completion Criteria:**
- All documentation reflects current functionality
- API documentation is complete and accurate
- Code examples are working and current
- Installation and usage instructions are up to date
- Changelog reflects all changes made

## Workflow Completion

### Final Verification
```bash
# Run complete test suite one final time
pytest test/ -v --cov=bestehorn_llmmanager --cov-report=html:htmlcov --cov-report=term-missing --cov-report=json:coverage.json --html=test_results.html --self-contained-html --cov-fail-under=80

# Run final code quality check
black --check --extend-exclude="src/bestehorn_llmmanager/_version.py" src/ test/ && \
isort --check-only --skip="src/bestehorn_llmmanager/_version.py" src/ test/ && \
flake8 --exclude="src/bestehorn_llmmanager/_version.py" src/ test/ && \
mypy --exclude="_version" src/

# Generate final coverage report
coverage report --show-missing
```

### Success Criteria

The test automation workflow is complete when:

1. **Test Coverage**: ≥80% overall coverage with critical paths at ≥90%
2. **Test Execution**: All unit and integration tests pass
3. **Code Quality**: All formatting, linting, and type checking passes
4. **Documentation**: All documentation is current and accurate
5. **Reproducibility**: All changes are properly tested and documented

### Deliverables

- **Updated Test Suite**: Comprehensive test coverage for all functionality
- **Test Reports**: HTML coverage report and test results
- **Quality Assurance**: Code that passes all quality checks
- **Documentation**: Updated and accurate documentation
- **Configuration**: Updated test configuration if needed

## Error Handling and Troubleshooting

### Common Issues

1. **Coverage Below Threshold**:
   - Return to Step 1 and implement additional tests
   - Focus on critical path functionality
   - Add edge case testing

2. **Integration Test Failures**:
   - Check AWS credentials and permissions
   - Verify network connectivity
   - Use appropriate test markers to skip if needed

3. **Code Quality Failures**:
   - Run automatic fixes where possible
   - Manual review and correction for complex issues
   - Update configuration if standards change

4. **Documentation Inconsistencies**:
   - Review all changed functionality
   - Update examples and usage instructions
   - Verify consistency across all documentation

### Recovery Procedures

- **Backup**: Ensure all changes are committed before major modifications
- **Rollback**: Ability to revert to previous state if needed
- **Validation**: Continuous validation at each step
- **Incremental**: Make changes incrementally to isolate issues

## Notes

- This workflow is designed for comprehensive test automation
- All steps should be executed from the project root directory
- AWS credentials may be required for integration tests
- Some integration tests may be skipped in environments without AWS access
- The workflow aligns with CI/CD pipeline requirements
- Documentation updates are essential for maintaining project quality

## Related Workflows

- **Pre-commit Checks**: `.clinerules/workflows/pre-commit-checks.md`
- **GitHub CI**: `.github/workflows/ci.yml`
- **Test Configuration**: `pyproject.toml`, `pytest.ini`, `.coveragerc`
