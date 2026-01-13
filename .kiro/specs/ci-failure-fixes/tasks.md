# Implementation Plan: CI Failure Fixes

## Overview

This plan addresses the flaky property-based test and massive deprecation warnings in the CI pipeline. The implementation follows a phased approach: first fix the critical flaky test, then reduce deprecation warnings, and finally clean up and add monitoring.

## Tasks

- [x] 1. Fix Flaky Property-Based Test (Critical)
  - Add reset method to AccessMethodTracker singleton
  - Create pytest fixture for automatic state reset
  - Verify test passes consistently
  - _Requirements: 1.1, 1.2, 1.3, 4.1_

- [x] 1.1 Add reset_for_testing() method to AccessMethodTracker
  - Implement class method that clears singleton state
  - Add thread-safe reset using existing lock
  - Document that method should ONLY be called from tests
  - Add warning comment about production use
  - _Requirements: 1.1, 4.1_

- [x] 1.2 Write property test for AccessMethodTracker reset
  - **Property 5: Test State Isolation**
  - **Validates: Requirements 1.1**

- [x] 1.3 Create pytest fixture for automatic state reset
  - Create test/bestehorn_llmmanager/bedrock/retry/conftest.py
  - Implement autouse fixture that resets AccessMethodTracker
  - Reset before and after each test
  - Document fixture purpose and usage
  - _Requirements: 1.1_

- [x] 1.4 Verify flaky test now passes consistently
  - Run test_direct_access_preferred_by_default 100 times
  - Verify all runs pass
  - Check that test produces consistent results
  - _Requirements: 1.1, 1.4_

- [x] 1.5 Write property test for access method selection determinism
  - **Property 1: Access Method Selection Determinism**
  - **Validates: Requirements 1.2, 4.1**

- [x] 1.6 Write property test for direct access preference
  - **Property 2: Direct Access Preference Without Learned State**
  - **Validates: Requirements 1.2, 1.3**

- [x] 2. Checkpoint - Verify flaky test is fixed
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Migrate Production Code to Current APIs
  - Update all production code to use current APIs
  - Remove use of deprecated properties and enum values
  - Maintain backward compatibility
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3.1 Identify all uses of deprecated APIs in production code
  - Search for access_method property usage
  - Search for inference_profile_id property usage
  - Search for ModelAccessMethod.BOTH usage
  - Search for ModelAccessMethod.CRIS_ONLY usage
  - Create list of files to update
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3.2 Update RetryManager to use current APIs
  - Replace access_method checks with orthogonal flag checks
  - Replace inference_profile_id with specific profile IDs
  - Add comments explaining the migration
  - _Requirements: 2.1, 2.2_

- [x] 3.3 Update AccessMethodSelector to use current APIs
  - Replace access_method comparisons with flag checks
  - Update model ID selection logic
  - Add comments explaining the changes
  - _Requirements: 2.1, 2.2_

- [x] 3.4 Update other production modules using deprecated APIs
  - Update any remaining production code
  - Ensure consistent API usage across codebase
  - Add migration comments where helpful
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3.5 Write property test for backward compatibility
  - **Property 6: Deprecated API Backward Compatibility**
  - **Validates: Requirements 2.5**

- [x] 3.6 Write unit test for zero production deprecation warnings
  - Test that production code generates no warnings
  - Import all production modules and check warnings
  - _Requirements: 2.4_

- [x] 4. Checkpoint - Verify production code is clean
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Migrate Test Code to Current APIs
  - Update test code to use current APIs
  - Mark intentional deprecation tests clearly
  - Reduce warning count below threshold
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5.1 Update test_retry_manager_profile_properties.py
  - Update model_access_info_strategy to use current constructor
  - Update assertions to check orthogonal flags
  - Remove use of deprecated properties
  - _Requirements: 3.1, 3.2_

- [x] 5.2 Update test_retry_manager_profile_integration.py
  - Update ModelAccessInfo creation to use current APIs
  - Update access method validation
  - Add comments for any intentional deprecation tests
  - _Requirements: 3.1, 3.2_

- [x] 5.3 Update other retry-related tests
  - Update test_retry_manager.py
  - Update test_retry_manager_validation.py
  - Update test_retry_manager_parameter_compatibility.py
  - Update test_retry_manager_content_compatibility.py
  - _Requirements: 3.1, 3.2_

- [x] 5.4 Mark intentional deprecation tests
  - Add clear comments to tests that intentionally use deprecated APIs
  - Add pytest warning filters for expected warnings
  - Document why these tests use deprecated APIs
  - _Requirements: 3.5_

- [x] 5.5 Write unit test for deprecation warning count
  - Test that total warnings are under 100
  - Run full test suite and count warnings
  - _Requirements: 3.4_

- [x] 6. Checkpoint - Verify warning count is reduced
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Add Property Tests for Deterministic Behavior
  - Add comprehensive property tests
  - Verify consistent behavior across all inputs
  - Test learned preference application
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 7.1 Write property test for consistent preference order
  - **Property 3: Consistent Preference Order**
  - **Validates: Requirements 4.2**

- [x] 7.2 Write property test for learned preference application
  - **Property 4: Learned Preference Application**
  - **Validates: Requirements 4.3**

- [x] 7.3 Write property test for valid test data generation
  - **Property 7: Valid Test Data Generation**
  - **Validates: Requirements 4.4**

- [x] 8. Verify CI Pipeline Health
  - Run all CI checks locally
  - Verify all checks pass
  - Confirm ready for release
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8.1 Write integration test for CI pipeline
  - Test that all CI checks pass
  - Run black, isort, flake8, mypy, bandit, pytest
  - Verify zero failures
  - _Requirements: 5.1, 5.2, 5.4, 5.5_

- [x] 8.2 Run full test suite locally
  - Execute pytest with all tests
  - Verify zero test failures
  - Check test execution time
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 8.3 Run all code quality checks locally
  - Run black --check
  - Run isort --check-only
  - Run flake8
  - Run mypy
  - Run bandit
  - Verify all pass
  - _Requirements: 5.4_

- [x] 8.4 Verify deprecation warning count
  - Run test suite and count warnings
  - Verify count is under 100
  - Document remaining warnings
  - _Requirements: 3.4_

- [x] 9. Final Checkpoint - Ready for Release
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Document Root Cause and Prevention
  - Add documentation explaining the issues
  - Provide recommendations for prevention
  - Update development guidelines
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 10.1 Document root cause in design document
  - Explain why test was flaky (singleton state)
  - Explain why warnings accumulated (API evolution)
  - Add to Root Cause Analysis section
  - _Requirements: 6.1, 6.2_

- [x] 10.2 Add code comments explaining fixes
  - Comment reset_for_testing() method
  - Comment pytest fixture
  - Comment API migration in production code
  - _Requirements: 6.3_

- [x] 10.3 Create prevention recommendations document
  - Document singleton patterns to avoid
  - Recommend deprecation management practices
  - Suggest test quality improvements
  - Add to design document
  - _Requirements: 6.4_

- [x] 10.4 Update development guidelines
  - Add section on managing deprecation warnings
  - Add section on test state isolation
  - Add section on singleton patterns
  - Update CI configuration to fail on warning threshold
  - _Requirements: 6.5_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation is phased: critical fix first, then cleanup, then monitoring
- All tests are required for comprehensive coverage
