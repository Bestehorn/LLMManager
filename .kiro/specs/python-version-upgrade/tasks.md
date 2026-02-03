# Implementation Plan: Python Version Upgrade

## Overview

This implementation plan outlines the steps to upgrade Python version support from 3.9-3.12 to 3.10-3.14. The approach involves systematically updating configuration files, CI pipelines, and documentation to ensure consistency across the project. Each task builds incrementally, with validation steps to ensure correctness.

## Tasks

- [x] 1. Update pyproject.toml configuration
  - Update the `requires-python` field to ">=3.10,<4.0"
  - Remove "Programming Language :: Python :: 3.9" from classifiers
  - Add "Programming Language :: Python :: 3.13" to classifiers
  - Add "Programming Language :: Python :: 3.14" to classifiers
  - Update `tool.black.target-version` to ['py310', 'py311', 'py312', 'py313', 'py314']
  - Update `tool.mypy.python_version` to "3.10"
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 1.1 Write unit tests for pyproject.toml validation
  - Test that requires-python is exactly ">=3.10,<4.0"
  - Test that Python 3.9 classifier is not present
  - Test that Python 3.13 and 3.14 classifiers are present
  - Test that all five versions (3.10-3.14) are in classifiers
  - Test that black target-version includes all five py versions
  - Test that mypy python_version is "3.10"
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 2. Update GitHub Actions CI workflow
  - Open .github/workflows/ci.yml
  - Update the test job matrix to include Python versions ['3.10', '3.11', '3.12', '3.13', '3.14']
  - Ensure Python 3.9 is removed from the matrix
  - Verify the matrix is used in all relevant jobs (test, lint, build)
  - _Requirements: 1.3, 2.3, 3.3, 4.6, 8.4_

- [x] 2.1 Write unit tests for CI workflow validation
  - Test that CI matrix includes exactly ['3.10', '3.11', '3.12', '3.13', '3.14']
  - Test that '3.9' is not in the matrix
  - Test that all test jobs use the correct matrix
  - _Requirements: 1.3, 2.3, 3.3, 4.6, 8.4_

- [x] 3. Update tox.ini configuration
  - Update the envlist to include py310, py311, py312, py313, py314
  - Remove py38 and py39 from the envlist
  - Verify all tox environments (lint, type, docs) are compatible
  - _Requirements: 4.7, 4.8_

- [x] 3.1 Write unit tests for tox.ini validation
  - Test that envlist includes py310, py311, py312, py313, py314
  - Test that py38 and py39 are not in envlist
  - Test that other environments (lint, type, docs) are present
  - _Requirements: 4.7, 4.8_

- [x] 4. Update README.md documentation
  - Update the "Prerequisites" section to state "Python 3.10+"
  - Update the "Requirements" section to state "Python 3.10+"
  - Search for any other references to "3.9" and update to "3.10+"
  - Verify all code examples are compatible with Python 3.10+
  - _Requirements: 1.5, 5.1, 5.2_

- [x] 5. Update examples documentation
  - Open examples/README.md
  - Find Lambda runtime specification (currently python3.9)
  - Update to python3.10 or later
  - Verify all example code is Python 3.10+ compatible
  - _Requirements: 5.3_

- [x] 6. Update steering rules documentation
  - Open .kiro/steering/tech-stack.md
  - Update "Core Technologies" section to state "Python 3.10+"
  - Verify consistency with other documentation
  - _Requirements: 5.4_

- [x] 6.1 Write unit tests for documentation validation
  - Test that README.md contains "Python 3.10+" in prerequisites
  - Test that README.md does not reference "3.9" as supported
  - Test that examples/README.md does not use python3.9 runtime
  - Test that tech-stack.md specifies "Python 3.10+"
  - _Requirements: 1.4, 1.5, 2.5, 2.6, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4_

- [x] 7. Write cross-file consistency tests
  - Test that all configuration files specify the same Python versions
  - Test that pyproject.toml, ci.yml, and tox.ini are synchronized
  - Test that documentation matches configuration files
  - _Requirements: 1.4, 2.5, 3.5, 4.1-4.8_

- [x] 8. Checkpoint - Verify all configuration changes
  - Run all unit tests to verify configuration file updates
  - Manually review each changed file for correctness
  - Ensure no references to Python 3.9 remain
  - Ensure all references to Python 3.13 and 3.14 are present
  - Ask the user if questions arise

- [x] 9. Verify dependency compatibility
  - Check that all dependencies in pyproject.toml support Python 3.10-3.14
  - Review dependency version constraints for compatibility
  - Test package installation on Python 3.10, 3.11, 3.12 (if available locally)
  - Document any dependencies that need version updates
  - _Requirements: 7.1-7.6_

- [x] 10. Run local validation tests
  - Run pytest to ensure all tests pass
  - Run black, isort, flake8, mypy to ensure code quality checks pass
  - Run tox locally (if multiple Python versions available) to test across versions
  - Fix any issues that arise
  - _Requirements: 6.1-6.5_

- [x] 11. Final checkpoint - Prepare for CI validation
  - Ensure all local tests pass
  - Ensure all code quality checks pass
  - Review all changes one final time
  - Prepare commit message describing the Python version upgrade
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster implementation
- The unit tests validate configuration file correctness but do not test runtime behavior
- Runtime validation (tests passing on all Python versions) will be verified by the CI pipeline
- Dependency compatibility should be verified by attempting installation on available Python versions
- The CI pipeline will provide the final validation that all changes work correctly
- After merging, monitor the CI pipeline to ensure tests pass on all Python versions
