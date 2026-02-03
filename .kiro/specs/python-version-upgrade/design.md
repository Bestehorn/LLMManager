# Design Document: Python Version Upgrade

## Overview

This design document outlines the approach for upgrading Python version support in the bestehorn-llmmanager project. The upgrade involves:

1. Dropping Python 3.9 support (EOL October 2025)
2. Adding Python 3.13 support (stable, released October 2024)
3. Adding Python 3.14 support (new, released October 2025)
4. Updating the supported version range from 3.9-3.12 to 3.10-3.14

The design focuses on systematic updates to configuration files, CI pipelines, and documentation to ensure consistency and maintain backward compatibility for all supported versions.

## Architecture

### High-Level Approach

The upgrade follows a configuration-driven approach where Python version specifications are updated across multiple configuration files in a coordinated manner. The architecture consists of three main layers:

1. **Package Configuration Layer**: Core package metadata and build configuration (pyproject.toml)
2. **Testing Configuration Layer**: Test environment specifications and CI pipeline definitions (tox.ini, .github/workflows/ci.yml)
3. **Documentation Layer**: User-facing documentation and development guidelines (README.md, steering rules)

### Design Principles

1. **Consistency**: All version specifications must be synchronized across configuration files
2. **Backward Compatibility**: No breaking changes to the public API
3. **Comprehensive Testing**: All supported versions must be tested in CI
4. **Clear Documentation**: Users must have clear guidance on supported versions

### Configuration File Dependencies

```
pyproject.toml (source of truth)
    ├── requires-python: >=3.10,<4.0
    ├── classifiers: Python 3.10-3.14
    ├── tool.black.target-version: py310-py314
    └── tool.mypy.python_version: 3.10

.github/workflows/ci.yml
    └── matrix.python-version: ['3.10', '3.11', '3.12', '3.13', '3.14']

tox.ini
    └── envlist: py310,py311,py312,py313,py314,...

README.md
    └── Prerequisites: Python 3.10+

.kiro/steering/tech-stack.md
    └── Core Technologies: Python 3.10+
```

## Components and Interfaces

### Component 1: Package Configuration Updater

**Purpose**: Update pyproject.toml with new Python version specifications

**Responsibilities**:
- Update `requires-python` field to ">=3.10,<4.0"
- Remove Python 3.9 classifier
- Add Python 3.13 and 3.14 classifiers
- Update `tool.black.target-version` to include py310, py311, py312, py313, py314
- Update `tool.mypy.python_version` to "3.10"

**Key Sections to Modify**:
```toml
[project]
requires-python = ">=3.10,<4.0"
classifiers = [
    # Remove: "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",  # Add
    "Programming Language :: Python :: 3.14",  # Add
]

[tool.black]
target-version = ['py310', 'py311', 'py312', 'py313', 'py314']

[tool.mypy]
python_version = "3.10"
```

### Component 2: CI Pipeline Updater

**Purpose**: Update GitHub Actions workflow to test new Python versions

**Responsibilities**:
- Update test matrix to include Python 3.10, 3.11, 3.12, 3.13, 3.14
- Remove Python 3.9 from test matrix
- Ensure all CI jobs use the updated matrix

**Key Sections to Modify**:
```yaml
jobs:
  test:
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12', '3.13', '3.14']
```

### Component 3: Tox Configuration Updater

**Purpose**: Update tox.ini to support new Python versions

**Responsibilities**:
- Update envlist to include py310, py311, py312, py313, py314
- Remove py38 and py39 from envlist
- Ensure all tox environments work with new versions

**Key Sections to Modify**:
```ini
[tox]
envlist = py310,py311,py312,py313,py314,lint,type,docs
```

### Component 4: Documentation Updater

**Purpose**: Update all documentation to reflect new Python version support

**Responsibilities**:
- Update README.md prerequisites to "Python 3.10+"
- Update README.md requirements section to "Python 3.10+"
- Update examples/README.md Lambda runtime references
- Update .kiro/steering/tech-stack.md to "Python 3.10+"

**Files to Modify**:
- README.md (2 locations: Quick Start and Requirements sections)
- examples/README.md (Lambda runtime specification)
- .kiro/steering/tech-stack.md (Core Technologies section)

## Data Models

### Version Specification Model

The version specifications follow a consistent pattern across all configuration files:

```
Minimum Version: 3.10
Maximum Version: 3.14 (exclusive 4.0)
Supported Versions: [3.10, 3.11, 3.12, 3.13, 3.14]
Removed Versions: [3.9]
Added Versions: [3.13, 3.14]
```

### Configuration File Mapping

| File | Field/Section | Current Value | New Value |
|------|--------------|---------------|-----------|
| pyproject.toml | requires-python | >=3.9,<4.0 | >=3.10,<4.0 |
| pyproject.toml | classifiers | 3.9, 3.10, 3.11, 3.12 | 3.10, 3.11, 3.12, 3.13, 3.14 |
| pyproject.toml | tool.black.target-version | py39, py310, py311, py312 | py310, py311, py312, py313, py314 |
| pyproject.toml | tool.mypy.python_version | 3.9 | 3.10 |
| ci.yml | matrix.python-version | 3.9, 3.10, 3.11, 3.12 | 3.10, 3.11, 3.12, 3.13, 3.14 |
| tox.ini | envlist | py38, py39, py310, py311, py312 | py310, py311, py312, py313, py314 |
| README.md | Prerequisites | Python 3.9+ | Python 3.10+ |
| tech-stack.md | Core Technologies | Python 3.9+ | Python 3.10+ |


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, most of the testable requirements are specific examples rather than universal properties. The requirements focus on verifying that specific configuration files contain (or don't contain) specific values. These are best validated through example-based tests that check exact file contents.

The key insight is that this feature is primarily a configuration change rather than a behavioral change. We're not implementing new algorithms or data transformations that would benefit from property-based testing across many inputs. Instead, we're making precise, deterministic changes to configuration files that can be validated with targeted example tests.

### Testable Properties

Since this feature involves configuration file updates rather than algorithmic behavior, we have no universal properties that would benefit from property-based testing. All testable requirements are specific examples that verify exact file contents.

### Example-Based Tests

The following examples should be validated through unit tests:

**Example 1: pyproject.toml version specifications**
- Verify requires-python is exactly ">=3.10,<4.0"
- Verify classifiers include 3.10, 3.11, 3.12, 3.13, 3.14
- Verify classifiers do not include 3.9
- Verify tool.black.target-version includes py310, py311, py312, py313, py314
- Verify tool.mypy.python_version is "3.10"
- **Validates: Requirements 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5**

**Example 2: CI workflow matrix**
- Verify .github/workflows/ci.yml matrix includes ['3.10', '3.11', '3.12', '3.13', '3.14']
- Verify matrix does not include '3.9'
- **Validates: Requirements 1.3, 2.3, 3.3, 4.6, 8.4**

**Example 3: tox.ini environment list**
- Verify envlist includes py310, py311, py312, py313, py314
- Verify envlist does not include py38 or py39
- **Validates: Requirements 4.7, 4.8**

**Example 4: Documentation updates**
- Verify README.md states "Python 3.10+" in prerequisites
- Verify README.md does not reference "3.9" as supported
- Verify examples/README.md does not use python3.9 runtime
- Verify .kiro/steering/tech-stack.md specifies "Python 3.10+"
- **Validates: Requirements 1.4, 1.5, 2.5, 2.6, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4**

### Non-Testable Requirements

The following requirements are verified through actual execution rather than static testing:

- **Runtime test execution** (Requirements 2.4, 3.4, 6.1-6.5): Tests must actually run on each Python version
- **Dependency installation** (Requirements 7.1-7.6): Dependencies must actually install on each Python version
- **CI pipeline behavior** (Requirements 8.1-8.3, 8.5): CI must actually execute and report results

These are validated by running the CI pipeline after the configuration changes are made.

## Error Handling

### Configuration File Parsing Errors

**Error Type**: File parsing failures (TOML, YAML, INI)

**Handling Strategy**:
- Use robust parsing libraries (tomli/tomllib for TOML, PyYAML for YAML, configparser for INI)
- Validate file structure before making changes
- Provide clear error messages indicating which file and line failed to parse

**Example**:
```python
try:
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
except tomllib.TOMLDecodeError as e:
    raise ConfigurationError(f"Failed to parse pyproject.toml: {e}")
```

### File Not Found Errors

**Error Type**: Missing configuration files

**Handling Strategy**:
- Check for file existence before attempting to read
- Provide clear error messages indicating which required file is missing
- Fail fast if critical files are missing

**Example**:
```python
if not Path("pyproject.toml").exists():
    raise ConfigurationError("Required file pyproject.toml not found")
```

### Invalid Version Format Errors

**Error Type**: Malformed version strings in configuration

**Handling Strategy**:
- Validate version strings match expected patterns (e.g., "3.10", "py310")
- Provide clear error messages about expected format
- Use regex patterns to validate version strings

**Example**:
```python
VERSION_PATTERN = r"^3\.(1[0-4])$"
if not re.match(VERSION_PATTERN, version):
    raise ValueError(f"Invalid version format: {version}")
```

### File Write Permission Errors

**Error Type**: Insufficient permissions to modify configuration files

**Handling Strategy**:
- Check write permissions before attempting modifications
- Provide clear error messages about permission issues
- Suggest running with appropriate permissions

**Example**:
```python
if not os.access("pyproject.toml", os.W_OK):
    raise PermissionError("No write permission for pyproject.toml")
```

## Testing Strategy

### Dual Testing Approach

This feature uses a **unit testing only** approach since there are no universal properties to test. All requirements are specific configuration changes that are best validated through example-based tests.

### Unit Testing Focus

Unit tests will verify:
1. **Configuration file parsing**: Ensure files can be read and parsed correctly
2. **Version specification validation**: Verify exact values in configuration files
3. **Absence validation**: Verify removed versions are not present
4. **Presence validation**: Verify added versions are present
5. **Consistency validation**: Verify all files are updated consistently

### Test Organization

Tests will be organized by configuration file:

```
test/
  test_python_version_upgrade/
    test_pyproject_toml.py       # Tests for pyproject.toml updates
    test_ci_workflow.py          # Tests for .github/workflows/ci.yml updates
    test_tox_ini.py              # Tests for tox.ini updates
    test_documentation.py        # Tests for README.md and other docs
    test_consistency.py          # Cross-file consistency tests
```

### Test Implementation Examples

**Test 1: Verify pyproject.toml requires-python**
```python
def test_pyproject_requires_python():
    """Verify requires-python is set to >=3.10,<4.0"""
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    
    assert config["project"]["requires-python"] == ">=3.10,<4.0"
```

**Test 2: Verify Python 3.9 is removed from classifiers**
```python
def test_pyproject_no_python_39_classifier():
    """Verify Python 3.9 classifier is not present"""
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    
    classifiers = config["project"]["classifiers"]
    assert "Programming Language :: Python :: 3.9" not in classifiers
```

**Test 3: Verify Python 3.13 and 3.14 are added to classifiers**
```python
def test_pyproject_new_version_classifiers():
    """Verify Python 3.13 and 3.14 classifiers are present"""
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    
    classifiers = config["project"]["classifiers"]
    assert "Programming Language :: Python :: 3.13" in classifiers
    assert "Programming Language :: Python :: 3.14" in classifiers
```

**Test 4: Verify CI workflow matrix**
```python
def test_ci_workflow_python_versions():
    """Verify CI workflow tests correct Python versions"""
    with open(".github/workflows/ci.yml") as f:
        workflow = yaml.safe_load(f)
    
    matrix = workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    expected = ["3.10", "3.11", "3.12", "3.13", "3.14"]
    
    assert matrix == expected
    assert "3.9" not in matrix
```

**Test 5: Verify cross-file consistency**
```python
def test_version_consistency_across_files():
    """Verify all configuration files specify consistent Python versions"""
    # Parse all configuration files
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    
    with open(".github/workflows/ci.yml") as f:
        ci_workflow = yaml.safe_load(f)
    
    with open("tox.ini") as f:
        tox_config = configparser.ConfigParser()
        tox_config.read_file(f)
    
    # Extract versions from each file
    pyproject_versions = extract_versions_from_classifiers(pyproject)
    ci_versions = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    tox_versions = extract_versions_from_envlist(tox_config)
    
    # Verify consistency
    expected_versions = ["3.10", "3.11", "3.12", "3.13", "3.14"]
    assert set(pyproject_versions) == set(expected_versions)
    assert set(ci_versions) == set(expected_versions)
    assert set(tox_versions) == set(expected_versions)
```

### Integration Testing

After configuration changes are made, integration testing will verify:

1. **Package installation**: Install package on Python 3.10, 3.11, 3.12, 3.13, 3.14
2. **Test execution**: Run full test suite on all supported versions
3. **CI pipeline execution**: Verify CI pipeline runs successfully
4. **Dependency resolution**: Verify all dependencies install correctly

These integration tests are performed by the CI pipeline itself and are not part of the unit test suite.

### Manual Verification Steps

After implementation, manually verify:

1. **Local testing**: Run tests locally on multiple Python versions using tox
2. **CI pipeline**: Create a pull request and verify CI runs on all versions
3. **Package build**: Verify package builds successfully with new configuration
4. **Documentation review**: Manually review all documentation for accuracy

### Test Coverage Goals

- **Unit test coverage**: 100% of configuration file parsing and validation logic
- **Integration test coverage**: All supported Python versions tested in CI
- **Documentation coverage**: All documentation files verified for correct version references
