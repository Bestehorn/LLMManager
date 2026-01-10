# Implementation Plan: Inference Profile Support

## Overview

This plan implements automatic inference profile support for AWS Bedrock models. The implementation will detect when models require profile-based access, automatically select and use appropriate profiles, and learn access method preferences over time to optimize future requests.

## Tasks

- [x] 1. Create profile requirement detection module
  - [x] 1.1 Create `ProfileRequirementDetector` class
    - Implement error pattern matching for profile requirements
    - Implement model ID extraction from error messages
    - Add logging for detection events
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.2 Write property test for detection accuracy
    - **Property 1: Profile Requirement Detection Accuracy**
    - **Validates: Requirements 1.1, 1.2**

  - [x] 1.3 Write unit tests for ProfileRequirementDetector
    - Test various error message patterns
    - Test model ID extraction
    - Test non-profile errors return False
    - Test edge cases (empty messages, malformed errors)
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Create access method preference data structures
  - [x] 2.1 Create `AccessMethodPreference` dataclass
    - Define preference flags (prefer_direct, prefer_regional_cris, prefer_global_cris)
    - Add learned_from_error flag
    - Add last_updated timestamp
    - Implement get_preferred_method() helper
    - _Requirements: 5.1, 5.2_

  - [x] 2.2 Create `ProfileRequirementError` exception class
    - Define exception with model_id, region, original_error attributes
    - Implement clear error message formatting
    - _Requirements: 1.4, 4.1_

  - [x] 2.3 Write unit tests for data structures
    - Test AccessMethodPreference initialization and methods
    - Test ProfileRequirementError creation and attributes
    - _Requirements: 5.1, 5.2_

- [x] 3. Implement access method tracker
  - [x] 3.1 Create `AccessMethodTracker` class structure
    - Implement singleton pattern with thread-safe initialization
    - Initialize preference cache dictionary
    - Add threading lock for concurrent access
    - _Requirements: 5.3, 5.4_

  - [x] 3.2 Implement preference recording methods
    - Implement record_success() method
    - Implement record_profile_requirement() method
    - Add thread-safe cache updates
    - _Requirements: 5.1, 5.2, 5.5_

  - [x] 3.3 Implement preference query methods
    - Implement get_preference() method
    - Implement requires_profile() method
    - Implement get_statistics() method
    - _Requirements: 5.4, 7.4_

  - [x] 3.4 Write property test for preference learning persistence
    - **Property 3: Preference Learning Persistence**
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [x] 3.5 Write property test for thread safety
    - **Property 7: Tracker Thread Safety**
    - **Validates: Requirements 5.3**

  - [x] 3.6 Write unit tests for AccessMethodTracker
    - Test singleton pattern
    - Test preference recording
    - Test preference retrieval
    - Test statistics generation
    - Test thread safety with concurrent access
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4. Implement access method selector
  - [x] 4.1 Create `AccessMethodSelector` class
    - Initialize with AccessMethodTracker reference
    - Define preference order constants (direct → regional CRIS → global CRIS)
    - _Requirements: 2.1, 2.2, 6.2_

  - [x] 4.2 Implement access method selection logic
    - Implement select_access_method() method
    - Apply learned preferences when available
    - Fall back to default preference order
    - Return (model_id_to_use, access_method_name) tuple
    - _Requirements: 2.1, 2.2, 2.3, 6.1, 6.2_

  - [x] 4.3 Implement fallback method generation
    - Implement get_fallback_access_methods() method
    - Generate ordered list of fallback methods
    - Exclude failed method from fallbacks
    - _Requirements: 2.4, 4.4_

  - [x] 4.4 Write property test for selection consistency
    - **Property 2: Access Method Selection Consistency**
    - **Validates: Requirements 2.1, 2.2**

  - [x] 4.5 Write property test for fallback ordering
    - **Property 4: Fallback Access Method Ordering**
    - **Validates: Requirements 2.3, 4.4**

  - [x] 4.6 Write unit tests for AccessMethodSelector
    - Test selection with direct access available
    - Test selection with only CRIS access
    - Test selection with multiple CRIS options
    - Test selection with learned preferences
    - Test fallback generation
    - Test edge cases (no access methods, all failed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.1, 6.2_

- [x] 5. Integrate profile support into RetryManager
  - [x] 5.1 Add profile support components to RetryManager initialization
    - Initialize AccessMethodTracker instance
    - Initialize AccessMethodSelector instance
    - _Requirements: 4.1, 4.2_

  - [x] 5.2 Implement profile requirement detection in retry logic
    - Add profile requirement check in execute_with_retry()
    - Call ProfileRequirementDetector.is_profile_requirement_error()
    - Extract model ID from error when detected
    - _Requirements: 1.1, 1.2, 1.3, 4.1_

  - [x] 5.3 Implement immediate profile retry logic
    - Create _retry_with_profile() method
    - Select profile using AccessMethodSelector
    - Retry with profile without incrementing attempt counter
    - Record success/failure with AccessMethodTracker
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 5.1_

  - [x] 5.4 Implement intelligent model ID selection
    - Create _select_model_id_for_request() method
    - Query AccessMethodTracker for learned preferences
    - Use AccessMethodSelector to choose optimal ID
    - Apply selection at start of each retry attempt
    - _Requirements: 2.1, 2.2, 5.4, 6.1, 6.2_

  - [x] 5.5 Add profile usage logging
    - Log profile requirement detection at WARNING level
    - Log profile selection at INFO level
    - Log profile retry success at INFO level
    - Log access method learning at DEBUG level
    - _Requirements: 1.4, 2.5, 7.1, 7.2, 7.3, 7.4_

  - [x] 5.6 Write property test for profile retry idempotence
    - **Property 5: Profile Retry Idempotence**
    - **Validates: Requirements 4.2**

  - [x] 5.7 Write property test for backward compatibility
    - **Property 6: Backward Compatibility Preservation**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [x] 5.8 Write unit tests for RetryManager profile integration
    - Test profile requirement detection in retry flow
    - Test immediate profile retry
    - Test access method selection
    - Test preference learning
    - Test backward compatibility with direct access
    - Test error handling when no profile available
    - _Requirements: 1.1, 1.2, 2.1, 4.1, 4.2, 4.3, 5.1, 6.1, 6.2_

- [x] 6. Add profile metadata to response objects
  - [x] 6.1 Add access method fields to BedrockResponse
    - Add access_method_used field
    - Add inference_profile_used boolean field
    - Add inference_profile_id field
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 6.2 Update BedrockResponse to capture access method
    - Capture access method from retry manager
    - Set inference_profile_used flag
    - Store profile ID when used
    - _Requirements: 8.1, 8.2, 8.5_

  - [x] 6.3 Add access method statistics to ParallelResponse
    - Aggregate access method usage across requests
    - Count direct vs profile-based requests
    - Include in parallel execution statistics
    - _Requirements: 8.4, 10.4_

  - [x] 6.4 Write unit tests for response metadata
    - Test access method capture in BedrockResponse
    - Test profile ID storage
    - Test parallel response aggregation
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 7. Implement graceful degradation for missing profiles
  - [x] 7.1 Add profile availability check in retry logic
    - Check if profile information is available in catalog
    - Log warning when profile required but unavailable
    - Continue to next model/region combination
    - _Requirements: 2.4, 9.1, 9.2_

  - [x] 7.2 Implement clear error messages for profile unavailability
    - Create specific error message for missing profiles
    - Include suggestion to refresh catalog data
    - List models that require profiles
    - _Requirements: 9.3, 9.4, 9.5_

  - [x] 7.3 Write unit tests for graceful degradation
    - Test behavior when profile required but unavailable
    - Test error message content
    - Test fallback to other models
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 8. Add parallel processing support
  - [x] 8.1 Verify profile support works with ParallelLLMManager
    - Test that profile detection works in parallel requests
    - Test that access method selection is independent per request
    - Test that profile retry works for individual parallel requests
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 8.2 Write integration tests for parallel profile support
    - Test parallel requests with mixed access methods
    - Test parallel requests all requiring profiles
    - Test access method statistics aggregation
    - Test performance impact of profile detection
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 9. Update documentation
  - [x] 9.1 Update forLLMConsumption.md with profile support
    - Document automatic profile detection
    - Document access method selection
    - Document response metadata for access methods
    - Provide examples of checking access method used
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 9.2 Create profile support troubleshooting guide
    - Document common profile-related errors
    - Explain how to check which access method was used
    - Provide guidance for missing profile information
    - Include examples of access method statistics
    - _Requirements: 11.5_

  - [x] 9.3 Add profile support examples to notebooks
    - Create example showing automatic profile handling
    - Show how to monitor access method usage
    - Demonstrate access method statistics
    - _Requirements: 11.3, 11.4_

- [x] 10. Integration testing and validation
  - [x] 10.1 Write end-to-end integration tests
    - Test complete flow from error detection to profile retry
    - Test access method learning across multiple requests
    - Test backward compatibility with existing code
    - Test parallel processing with profiles
    - _Requirements: 1.1, 2.1, 4.1, 5.1, 6.1, 10.1_

  - [x] 10.2 Test with real AWS Bedrock models (if available)
    - Test with Claude Sonnet 4.5 (requires profile)
    - Test with Claude 3 Haiku (supports direct)
    - Verify automatic profile selection
    - Verify access method learning
    - _Requirements: All_

  - [x] 10.3 Verify no regressions in existing tests
    - Run full test suite
    - Verify all existing tests pass
    - Verify no performance degradation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 11. Final validation and cleanup
  - [x] 11.1 Run full test suite (unit + integration + property tests)
    - Ensure all tests pass
    - Verify property tests run successfully
    - Check test coverage
    - _Requirements: All_

  - [x] 11.2 Run code quality checks
    - Run black, isort, flake8, mypy, bandit
    - Fix any issues found
    - Ensure no _version.py in checks
    - _Requirements: All_

  - [x] 11.3 Update CHANGELOG.md
    - Document new profile support feature
    - Note automatic detection and retry
    - Mention backward compatibility
    - _Requirements: All_

  - [x] 11.4 Clean up tmp/ directory
    - Remove any temporary test files
    - Verify no leftover artifacts
    - _Requirements: All_

## Notes

- All tasks are required for comprehensive implementation with full test coverage
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end functionality
- The implementation follows an incremental approach where each component is tested before moving to the next
- Profile support is designed to be completely transparent to existing users
- No breaking changes to existing APIs
