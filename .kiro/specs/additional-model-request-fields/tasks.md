# Implementation Plan: Additional Model Request Fields Support

## Overview

This implementation plan breaks down the feature into discrete, testable tasks. Each task builds on previous work and includes references to specific requirements from the design document.

## Tasks

- [x] 1. Create ModelSpecificConfig data structure
  - Create new file `src/bestehorn_llmmanager/bedrock/models/model_specific_structures.py`
  - Implement ModelSpecificConfig dataclass with enable_extended_context and custom_fields
  - Implement to_dict() and from_dict() methods for serialization
  - Add validation in __post_init__ for field types
  - _Requirements: 3.1, 3.5, 9.1, 9.2_

- [x] 1.1 Write property test for ModelSpecificConfig serialization
  - **Property 5: Configuration Serialization Round-Trip**
  - **Validates: Requirements 3.5**
  - Generate random ModelSpecificConfig instances
  - Verify to_dict() → from_dict() produces equivalent object
  - Test with various combinations of enable_extended_context and custom_fields
  - _Requirements: 3.5_

- [x] 2. Implement ParameterBuilder class
  - Create new file `src/bestehorn_llmmanager/bedrock/builders/parameter_builder.py`
  - Implement build_additional_fields() method with priority merging logic
  - Implement _merge_anthropic_beta() for array merging without duplicates
  - Implement _is_extended_context_compatible() for model checking
  - Add constants for extended context models and beta headers
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 2.4_

- [x] 2.1 Write property test for parameter pass-through
  - **Property 1: Parameter Pass-Through Preservation**
  - **Validates: Requirements 1.1, 1.2, 1.5**
  - Generate random nested dictionaries
  - Verify complete structure preservation through ParameterBuilder
  - Test with various nesting levels and data types
  - _Requirements: 1.1, 1.2, 1.5_

- [x] 2.2 Write property test for parameter coexistence
  - **Property 2: Parameter Coexistence**
  - **Validates: Requirements 1.4**
  - Generate random inferenceConfig and additionalModelRequestFields
  - Verify both are preserved when passed together
  - _Requirements: 1.4_

- [x] 2.3 Write property test for beta array merging
  - **Property 3: Extended Context Beta Merging**
  - **Validates: Requirements 2.4**
  - Generate various anthropic_beta arrays
  - Verify merging with enable_extended_context produces no duplicates
  - Test edge cases (empty arrays, already contains context-1m header)
  - _Requirements: 2.4_

- [x] 2.4 Write unit tests for ParameterBuilder edge cases
  - Test None and empty additionalModelRequestFields (Requirement 1.3)
  - Test enable_extended_context with Claude Sonnet 4 (Requirement 2.1)
  - Test enable_extended_context with incompatible models (Requirement 2.2)
  - Test enable_extended_context=False default (Requirement 2.3)
  - _Requirements: 1.3, 2.1, 2.2, 2.3_

- [x] 3. Create ParameterCompatibilityTracker
  - Create new file `src/bestehorn_llmmanager/bedrock/tracking/parameter_compatibility_tracker.py`
  - Implement singleton pattern with thread-safe get_instance()
  - Implement record_success() and record_failure() methods
  - Implement is_known_incompatible() query method
  - Implement _hash_parameters() for stable parameter hashing
  - Implement get_statistics() for observability
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 3.1 Write property test for compatibility tracking
  - **Property 9: Compatibility Tracking**
  - **Validates: Requirements 5.1, 5.2**
  - Generate random model/region/parameter combinations
  - Record successes and failures
  - Verify correct tracking of both success and failure states
  - _Requirements: 5.1, 5.2_

- [x] 3.2 Write property test for compatibility-based optimization
  - **Property 10: Compatibility-Based Retry Optimization**
  - **Validates: Requirements 5.4**
  - Record known incompatible combinations
  - Verify is_known_incompatible() returns correct results
  - Test that optimization skips known-bad combinations
  - _Requirements: 5.4_

- [x] 3.3 Write unit test for cross-instance persistence
  - Create multiple ParameterCompatibilityTracker instances
  - Verify they share the same underlying data
  - Test thread safety with concurrent access
  - _Requirements: 5.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Enhance RetryManager for parameter compatibility
  - Modify `src/bestehorn_llmmanager/bedrock/retry/retry_manager.py`
  - Add is_parameter_compatibility_error() method
  - Add PARAMETER_INCOMPATIBILITY_PATTERNS constant
  - Modify execute_with_retry() to handle parameter errors
  - Add _retry_without_parameters() helper method
  - Integrate with ParameterCompatibilityTracker
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 5.1 Write property test for error classification
  - **Property 6: Parameter Compatibility Error Classification**
  - **Validates: Requirements 4.1**
  - Generate various error messages
  - Verify correct classification of parameter compatibility errors
  - Test with different error patterns
  - _Requirements: 4.1_

- [x] 5.2 Write property test for retry warning logging
  - **Property 7: Retry Warning Logging**
  - **Validates: Requirements 4.3**
  - Simulate parameter removal scenarios
  - Verify warning logs include parameter names
  - Test log level is WARNING
  - _Requirements: 4.3_

- [x] 5.3 Write property test for response warnings
  - **Property 8: Response Warning Inclusion**
  - **Validates: Requirements 4.5**
  - Generate scenarios with parameter removal
  - Verify BedrockResponse includes warnings
  - _Requirements: 4.5_

- [x] 5.4 Write unit tests for retry behavior
  - Test retry without parameters after compatibility error (Requirement 4.2)
  - Test multiple model/region retry order (Requirement 4.4)
  - Test extended context with unsupported region (Requirement 2.5)
  - _Requirements: 4.2, 4.4, 2.5_

- [x] 6. Extend BedrockResponse with parameter metadata
  - Modify `src/bestehorn_llmmanager/bedrock/models/bedrock_response.py`
  - Add parameters_removed field
  - Add original_additional_fields field
  - Add final_additional_fields field
  - Implement had_parameters_removed() method
  - Implement get_parameter_warnings() method
  - _Requirements: 4.5, 10.4_

- [x] 6.1 Write property test for response metadata
  - **Property 19: Response Metadata Completeness**
  - **Validates: Requirements 10.4, 10.5**
  - Generate responses with parameter removal
  - Verify metadata is complete and accurate
  - Verify retry statistics include compatibility info
  - _Requirements: 10.4, 10.5_

- [x] 7. Update LLMManager with new API
  - Modify `src/bestehorn_llmmanager/llm_manager.py`
  - Add model_specific_config parameter to __init__
  - Add model_specific_config and enable_extended_context to converse()
  - Add model_specific_config and enable_extended_context to converse_stream()
  - Integrate ParameterBuilder for parameter construction
  - Update _execute_converse_request() to handle new parameters
  - _Requirements: 1.1-1.5, 2.1-2.5, 3.2, 3.3, 3.4, 8.1-8.5_

- [x] 7.1 Write property test for ModelSpecificConfig extraction
  - **Property 4: ModelSpecificConfig Extraction**
  - **Validates: Requirements 3.2, 3.4**
  - Generate random ModelSpecificConfig instances
  - Verify correct extraction and application of fields
  - Test merging of enable_extended_context and custom_fields
  - _Requirements: 3.2, 3.4_

- [x] 7.2 Write property test for backward compatibility
  - **Property 14: Backward Compatibility Preservation**
  - **Validates: Requirements 8.1, 8.2, 8.3, 8.5**
  - Test requests without new parameters
  - Verify behavior matches pre-feature implementation
  - Test existing additionalModelRequestFields usage
  - _Requirements: 8.1, 8.2, 8.3, 8.5_

- [x] 7.3 Write unit tests for LLMManager integration
  - Test enable_extended_context flag (Requirement 2.1)
  - Test default enable_extended_context=False (Requirement 8.4)
  - Test existing additionalModelRequestFields (Requirement 8.2)
  - Test plain dictionary without ModelSpecificConfig (Requirement 8.3)
  - _Requirements: 2.1, 8.2, 8.3, 8.4_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update ParallelLLMManager and structures
  - Modify `src/bestehorn_llmmanager/parallel_llm_manager.py`
  - Add model_specific_config support to converse_parallel()
  - Ensure per-request parameter independence
  - Modify `src/bestehorn_llmmanager/bedrock/models/parallel_structures.py`
  - Add model_specific_config field to BedrockConverseRequest
  - Extend ParallelResponse with get_requests_with_removed_parameters()
  - Extend ParallelResponse with get_parameter_compatibility_summary()
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 9.1 Write property test for parallel field independence
  - **Property 11: Parallel Request Field Independence**
  - **Validates: Requirements 6.1, 6.2**
  - Generate parallel requests with different parameters
  - Verify no cross-contamination between requests
  - _Requirements: 6.1, 6.2_

- [x] 9.2 Write property test for parallel model-specific filtering
  - **Property 12: Parallel Request Model-Specific Filtering**
  - **Validates: Requirements 6.4**
  - Generate parallel requests for different models
  - Verify independent filtering per model
  - _Requirements: 6.4_

- [x] 9.3 Write property test for parallel response metadata
  - **Property 13: Parallel Response Parameter Metadata**
  - **Validates: Requirements 6.5**
  - Generate parallel execution with parameter removal
  - Verify ParallelResponse includes complete metadata
  - _Requirements: 6.5_

- [x] 9.4 Write unit test for parallel parameter incompatibility
  - Test parallel request with parameter error and retry
  - Verify only affected request is retried without parameters
  - _Requirements: 6.3_

- [x] 10. Add input validation
  - Modify `src/bestehorn_llmmanager/bedrock/validators/request_validator.py`
  - Add validation for additionalModelRequestFields type
  - Add validation for enable_extended_context type
  - Add validation for ModelSpecificConfig structure
  - Ensure descriptive error messages
  - _Requirements: 9.1, 9.2_

- [x] 10.1 Write property test for input validation
  - **Property 15: Input Validation**
  - **Validates: Requirements 9.1, 9.2**
  - Generate invalid inputs (non-dict, non-bool)
  - Verify RequestValidationError is raised
  - Verify error messages are descriptive
  - _Requirements: 9.1, 9.2_

- [x] 11. Implement comprehensive logging
  - Add DEBUG logging for parameter names in ParameterBuilder
  - Add WARNING logging for parameter removal in RetryManager
  - Add INFO logging for extended context enablement
  - Ensure log messages distinguish error types
  - _Requirements: 10.1, 10.2, 10.3, 9.3, 9.5_

- [x] 11.1 Write property test for logging levels
  - **Property 18: Logging Level Compliance**
  - **Validates: Requirements 10.1, 10.2, 10.3**
  - Verify DEBUG level for parameter names
  - Verify WARNING level for parameter removal
  - Verify INFO level for extended context
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 11.2 Write property test for error type distinction
  - **Property 17: Error Type Distinction in Logs**
  - **Validates: Requirements 9.5**
  - Generate different error types
  - Verify distinct log patterns for each type
  - _Requirements: 9.5_

- [x] 11.3 Write property test for error message content
  - **Property 16: Error Message Parameter Inclusion**
  - **Validates: Requirements 9.4**
  - Simulate all retries failing due to parameters
  - Verify final error includes parameter names
  - _Requirements: 9.4_

- [x] 12. Update package exports
  - Modify `src/bestehorn_llmmanager/__init__.py`
  - Export ModelSpecificConfig
  - Export ParameterCompatibilityTracker (for advanced users)
  - Update __all__ list
  - _Requirements: 3.1, 5.3_

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Fix test performance issues
  - Fix Hypothesis health check issue in test_parallel_request_field_independence
  - Add @settings(suppress_health_check=[HealthCheck.too_slow]) or optimize strategy
  - Ensure all property tests run efficiently
  - _Requirements: 6.1, 6.2_

- [ ] 15. Create demonstration notebook
  - Create `notebooks/ExtendedContext_Demo.ipynb`
  - Add introduction explaining extended context feature
  - Add example with enable_extended_context=True
  - Add example with manual additionalModelRequestFields
  - Add example showing token usage reporting
  - Add example handling parameter incompatibility
  - Include explanatory markdown cells
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 16. Write integration tests
  - Create `test/integration/test_integration_additional_model_fields.py`
  - Test supported parameters with compatible models (Requirement 12.1)
  - Test unsupported parameters with graceful failure (Requirement 12.2)
  - Test errors without retry configuration (Requirement 12.3)
  - Test extended context with Claude Sonnet 4 (Requirement 12.4)
  - Test extended context with incompatible models (Requirement 12.5)
  - Mark tests with @pytest.mark.integration
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 17. Update documentation
  - Update `docs/forLLMConsumption.md` with new API
  - Add section on ModelSpecificConfig
  - Add section on enable_extended_context
  - Add section on parameter compatibility tracking
  - Add examples for all new features
  - Document known beta features and compatibility
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 18. Update README with extended context example
  - Add section on model-specific parameters
  - Add quick example of enable_extended_context
  - Link to full documentation and notebook
  - _Requirements: 7.1, 7.2_

- [ ] 19. Final checkpoint - Run all tests and checks
  - Run full test suite: `pytest test/`
  - Run integration tests: `pytest test/integration/ -m integration`
  - Run code quality checks (black, isort, flake8, mypy, bandit)
  - Verify all property tests pass with 100+ iterations
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- Integration tests require actual AWS Bedrock access
