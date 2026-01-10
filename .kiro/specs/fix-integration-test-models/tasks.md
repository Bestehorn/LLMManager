# Implementation Plan: User-Friendly Model Name Resolution

## Overview

This plan implements a model name alias system for BedrockModelCatalog that provides user-friendly model names and robust name resolution. The implementation will be done incrementally, with each task building on previous work and including tests to validate functionality.

## Tasks

- [x] 1. Create core name resolution data structures
  - Create `ModelNameMatch` dataclass for resolution results
  - Create `MatchType` enum for match type classification
  - Create `AliasGenerationConfig` dataclass for configuration
  - Create `ModelResolutionError` dataclass for error details
  - _Requirements: 1.1, 2.1, 5.1_

- [x] 1.1 Write unit tests for data structures
  - Test dataclass initialization and validation
  - Test enum values and serialization
  - _Requirements: 1.1, 2.1, 5.1_

- [x] 2. Implement name normalization functions
  - [x] 2.1 Create `normalize_model_name()` function
    - Convert to lowercase
    - Remove special characters
    - Collapse whitespace
    - Normalize version numbers
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Write property test for normalization idempotence
    - **Property 2: Normalization Idempotence**
    - **Validates: Requirements 2.1**

  - [x] 2.3 Write unit tests for normalization edge cases
    - Test empty strings
    - Test special characters
    - Test version format variations
    - _Requirements: 2.1, 2.2_

- [x] 3. Implement alias generation strategies
  - [x] 3.1 Create `AliasGenerator` base class
    - Define interface for alias generation
    - Implement common utility methods
    - _Requirements: 1.1, 3.1, 3.2, 3.3_

  - [x] 3.2 Implement `ClaudeAliasGenerator`
    - Generate aliases for Claude models
    - Handle version number variations
    - _Requirements: 3.1_

  - [x] 3.3 Implement `VersionedModelAliasGenerator`
    - Generate aliases for versioned models
    - Handle spacing variations
    - _Requirements: 3.2_

  - [x] 3.4 Implement `PrefixedModelAliasGenerator`
    - Generate aliases for provider-prefixed models
    - Create both prefixed and unprefixed variants
    - _Requirements: 3.3_

  - [x] 3.5 Write property test for alias uniqueness
    - **Property 5: No Ambiguous Aliases**
    - **Validates: Requirements 2.4**

  - [x] 3.6 Write unit tests for alias generation
    - Test each generator with sample models
    - Test alias limit enforcement
    - Test edge cases
    - _Requirements: 1.1, 3.1, 3.2, 3.3_

- [x] 4. Create legacy name mapping
  - [x] 4.1 Define legacy name mapping dictionary
    - Map UnifiedModelManager names to catalog names
    - Include all known legacy names
    - _Requirements: 1.4, 3.4, 4.1, 4.2, 4.3_

  - [x] 4.2 Implement `LegacyNameMapper` class
    - Load legacy mappings
    - Resolve legacy names
    - Handle deprecated models
    - _Requirements: 1.4, 3.4, 4.4_

  - [x] 4.3 Write property test for legacy compatibility
    - **Property 3: Legacy Name Backward Compatibility**
    - **Validates: Requirements 1.4, 4.1, 4.2, 4.3**

  - [x] 4.4 Write unit tests for legacy mapping
    - Test all known legacy names
    - Test deprecated model handling
    - _Requirements: 1.4, 4.1, 4.2, 4.3, 4.4_

- [x] 5. Implement ModelNameResolver class
  - [x] 5.1 Create `ModelNameResolver` class structure
    - Initialize with UnifiedCatalog
    - Set up lazy index initialization
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

  - [x] 5.2 Implement index building methods
    - Build name index (alias → canonical)
    - Build normalized index (normalized → canonicals)
    - Build legacy mapping index
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 5.3 Implement `resolve_name()` method
    - Try exact match first
    - Try alias match
    - Try legacy match
    - Try normalized match
    - Try fuzzy match (if not strict)
    - _Requirements: 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_

  - [x] 5.4 Implement `get_suggestions()` method
    - Calculate edit distances
    - Find substring matches
    - Rank by relevance
    - _Requirements: 5.2, 5.3_

  - [x] 5.5 Implement `generate_aliases()` method
    - Apply all alias generation strategies
    - Enforce alias limit
    - Ensure uniqueness
    - _Requirements: 1.1, 3.1, 3.2, 3.3_

  - [x] 5.6 Write property test for alias resolution consistency
    - **Property 1: Alias Resolution Consistency**
    - **Validates: Requirements 1.2, 1.3**

  - [x] 5.7 Write property test for case insensitivity
    - **Property 6: Case Insensitivity**
    - **Validates: Requirements 2.1**

  - [x] 5.8 Write property test for version format flexibility
    - **Property 7: Version Format Flexibility**
    - **Validates: Requirements 2.2**

  - [x] 5.9 Write property test for suggestion relevance
    - **Property 4: Suggestion Relevance**
    - **Validates: Requirements 5.2**

  - [x] 5.10 Write unit tests for ModelNameResolver
    - Test exact name matching
    - Test alias matching
    - Test normalized matching
    - Test fuzzy matching
    - Test suggestion generation
    - Test error scenarios
    - _Requirements: 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 5.1, 5.2, 5.3, 5.4_

- [x] 6. Integrate ModelNameResolver into BedrockModelCatalog
  - [x] 6.1 Add ModelNameResolver to BedrockModelCatalog
    - Initialize resolver lazily
    - Update `get_model_info()` to use resolver
    - Update `is_model_available()` to use resolver
    - _Requirements: 1.2, 1.3, 4.1, 4.2, 4.3_

  - [x] 6.2 Update error messages with suggestions
    - Modify ConfigurationError messages
    - Include suggested model names
    - Include legacy name information
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 6.3 Write integration tests for catalog name resolution
    - Test catalog with friendly names
    - Test catalog with legacy names
    - Test catalog with API names
    - Test error messages include suggestions
    - _Requirements: 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 5.1, 5.2_

- [x] 7. Update LLMManager to use name resolution
  - [x] 7.1 Update `_validate_model_region_combinations()` method
    - Use catalog's name resolution
    - Improve error messages with suggestions
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

  - [x] 7.2 Write integration tests for LLMManager initialization
    - Test initialization with friendly names
    - Test initialization with legacy names
    - Test initialization with mixed name formats
    - Test error messages provide suggestions
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

- [-] 8. Verify existing integration tests pass
  - [-] 8.1 Run integration test suite
    - Verify all previously skipped tests now pass
    - Verify no regressions in passing tests
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 8.2 Fix any remaining test failures
    - Investigate root causes
    - Update name mappings if needed
    - Update test expectations if needed
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 9. Update documentation
  - Update `docs/forLLMConsumption.md` with name resolution info
  - Add migration guide for users
  - Document supported name formats
  - Document legacy name mappings
  - _Requirements: All_

- [x] 10. Final validation
  - Run full test suite (unit + integration)
  - Run code quality checks (black, isort, flake8, mypy, bandit)
  - Verify all integration tests pass
  - Clean up tmp/ directory

## Notes

- All tasks are required for comprehensive implementation with full test coverage
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end functionality
- The implementation follows an incremental approach where each component is tested before moving to the next
