# Implementation Plan: Token Usage Key Inconsistency Fix

## Overview

This implementation plan addresses the token usage display bug in the ExtendedContext_Demo.ipynb notebook and adds individual accessor methods to BedrockResponse and StreamingResponse for better encapsulation. The implementation is divided into three main phases: adding accessor methods, fixing the notebook, and comprehensive testing.

## Tasks

- [x] 1. Add token accessor methods to BedrockResponse
  - Add five new methods: get_input_tokens(), get_output_tokens(), get_total_tokens(), get_cache_read_tokens(), get_cache_write_tokens()
  - Each method should delegate to get_usage() and return 0 for missing data
  - Include comprehensive docstrings with type hints
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 5.2, 5.4_

- [x] 1.1 Write property test for accessor methods returning correct values
  - **Property 1: Accessor Methods Return Values Matching get_usage()**
  - **Validates: Requirements 2.1, 2.2, 2.3**
  - Generate random BedrockResponse objects with valid usage data
  - Verify accessor methods return same values as get_usage() dictionary keys
  - Test all five accessor methods

- [x] 1.2 Write property test for accessor methods with missing data
  - **Property 2: Accessor Methods Return Zero for Missing Data**
  - **Validates: Requirements 2.4, 2.5, 3.3, 5.2**
  - Generate random BedrockResponse objects with various missing data scenarios
  - Verify all accessor methods return 0 for unsuccessful responses, missing response_data, and missing usage fields

- [x] 1.3 Write property test for cache accessor methods
  - **Property 3: Cache Accessor Methods Return Correct Values**
  - **Validates: Requirements 3.1, 3.2**
  - Generate random BedrockResponse objects with cache usage data
  - Verify cache accessor methods return correct values matching get_usage() dictionary

- [x] 1.4 Write property test for backward compatibility
  - **Property 4: get_usage() Maintains Backward Compatible Structure**
  - **Validates: Requirements 4.1, 4.2, 4.4**
  - Generate random BedrockResponse objects
  - Verify get_usage() returns None or dictionary with snake_case keys
  - Verify existing access patterns still work

- [x] 1.5 Write property test for accessor delegation
  - **Property 5: Accessor Methods Delegate to get_usage()**
  - **Validates: Requirements 5.4**
  - Generate random BedrockResponse objects
  - Verify accessor values are derivable from get_usage() dictionary
  - Ensure no independent data sources

- [x] 1.6 Write property test for token arithmetic invariant
  - **Property 6: Total Tokens Equals Input Plus Output**
  - **Validates: Requirements 2.3**
  - Generate random BedrockResponse objects with valid usage data
  - Verify get_total_tokens() == get_input_tokens() + get_output_tokens()

- [x] 2. Add token accessor methods to StreamingResponse
  - Add the same five accessor methods to StreamingResponse class
  - Ensure consistency with BedrockResponse implementation
  - Reuse the same delegation pattern to get_usage()
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3_

- [x] 2.1 Write unit tests for StreamingResponse accessor methods
  - Test all five accessor methods with valid data
  - Test accessor methods with missing data
  - Test accessor methods with unsuccessful streaming
  - Verify consistency with BedrockResponse behavior
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Fix notebook display_response() function
  - Update display_response() to use new accessor methods instead of dictionary access
  - Replace usage.get('inputTokens') with response.get_input_tokens()
  - Replace usage.get('outputTokens') with response.get_output_tokens()
  - Replace usage.get('totalTokens') with response.get_total_tokens()
  - Update conditional to check if total_tokens > 0 instead of if usage
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [x] 5. Fix notebook Example 3 token usage tracking
  - Update Example 3 to use accessor methods in results dictionary
  - Replace usage.get('inputTokens') with response.get_input_tokens()
  - Replace usage.get('outputTokens') with response.get_output_tokens()
  - Replace usage.get('totalTokens') with response.get_total_tokens()
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 5.1 Write integration test for notebook token display

  - Test that notebook displays non-zero token counts for successful requests
  - Test Example 1 with large text input shows token usage > 0
  - Verify displayed values match actual API response
  - _Requirements: 1.4, 1.5_

- [x] 6. Update documentation and examples
  - Update docs/forLLMConsumption.md with new accessor methods
  - Add examples showing recommended usage pattern (accessor methods vs dictionary access)
  - Update any other examples that access token usage
  - Document that accessor methods are the recommended approach
  - _Requirements: 5.1, 5.3_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation maintains full backward compatibility with existing code
