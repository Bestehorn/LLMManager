# Implementation Plan: Lambda Cache Fallback

## Overview

This implementation plan breaks down the lambda-cache-fallback feature into discrete coding tasks. Each task builds on previous steps and includes testing to validate core functionality early. The implementation modifies the cache management system to support multiple cache locations with automatic fallback, ensuring successfully retrieved data is always used regardless of cache write failures.

## Tasks

- [-] 1. Add fallback cache location constants and helper methods
  - Modify `src/bestehorn_llmmanager/bedrock/models/catalog_constants.py`
  - Add `get_fallback_cache_directory()` static method returning `/tmp/bestehorn-llmmanager-cache/`
  - Add `get_all_cache_locations()` static method returning list of [primary, fallback] directories
  - Add new log message constants for multi-location cache operations
  - _Requirements: 4.2_

- [~] 1.1 Write unit tests for cache location constants
  - Test `get_fallback_cache_directory()` returns correct path
  - Test `get_all_cache_locations()` returns correct priority order
  - _Requirements: 4.2_

- [ ] 2. Refactor CacheManager to support multiple cache locations
  - [~] 2.1 Modify CacheManager initialization to store list of cache locations
    - Update `__init__()` to create list of cache file paths (primary + fallback)
    - Store `_cache_locations: List[Path]` instead of single `_cache_file_path`
    - Maintain backward compatibility with existing `cache_file_path` property
    - _Requirements: 1.1, 4.1, 4.2_

  - [~] 2.2 Write property test for cache location initialization
    - **Property 1: Cache Write Location Priority**
    - **Validates: Requirements 1.1, 1.2**
    - Generate random cache configurations
    - Verify primary location is first in list
    - Verify fallback location is second in list

  - [~] 2.3 Extract cache file validation into helper method
    - Create `_is_cache_file_valid(cache_path: Path) -> bool` method
    - Move validation logic from `is_cache_valid()` to new helper
    - Update `is_cache_valid()` to delegate to helper for first location
    - _Requirements: 2.1, 2.2_

  - [~] 2.4 Write unit tests for cache file validation helper
    - Test validation with valid cache file
    - Test validation with expired cache file
    - Test validation with invalid JSON
    - Test validation with version mismatch
    - _Requirements: 2.1, 2.2_

- [~] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement multi-location cache read with fallback
  - [~] 4.1 Modify `load_cache()` to try multiple locations
    - Iterate through `_cache_locations` in priority order
    - Log DEBUG for each failed attempt with path
    - Log INFO for successful load with path
    - Return first valid cache found
    - Return None if all locations fail
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [~] 4.2 Write property test for multi-location cache read
    - **Property 2: Cache Read Location Priority**
    - **Validates: Requirements 2.1, 2.2**
    - Generate random cache configurations
    - Mock primary location to fail
    - Verify fallback location is attempted

  - [~] 4.3 Write property test for cache read failure
    - **Property 3: Cache Read Failure Returns None**
    - **Validates: Requirements 2.5, 7.2**
    - Generate random configurations
    - Mock all locations to fail
    - Verify None is returned

  - [~] 4.4 Write unit tests for cache read scenarios
    - Test cache exists in primary location only
    - Test cache exists in fallback location only
    - Test cache exists in both locations (primary wins)
    - Test no cache exists in any location
    - Test invalid cache in primary, valid in fallback
    - _Requirements: 2.1, 2.2, 2.5, 5.5_

- [ ] 5. Implement multi-location cache write with graceful degradation
  - [~] 5.1 Modify `save_cache()` to try multiple locations without raising exceptions
    - Iterate through `_cache_locations` in priority order
    - Catch all filesystem exceptions (OSError, IOError, PermissionError)
    - Catch all serialization exceptions (TypeError, ValueError)
    - Log WARNING for each failed attempt with path and error
    - Log INFO for successful write to primary location
    - Log WARNING for successful write to fallback location
    - Log WARNING if all writes fail
    - Never raise exceptions to caller
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 7.1, 7.4, 7.5_

  - [~] 5.2 Write property test for cache write never raises exceptions
    - **Property 11: Cache Write Never Raises Exceptions**
    - **Validates: Requirements 7.1**
    - Generate random catalog data
    - Mock filesystem to raise various exceptions
    - Verify no exceptions propagate to caller

  - [~] 5.3 Write property test for filesystem exception handling
    - **Property 12: Filesystem Exceptions Caught and Logged**
    - **Validates: Requirements 7.4**
    - Generate random filesystem exceptions
    - Verify exceptions are caught and logged
    - Verify fallback continues after exception

  - [~] 5.4 Write property test for fallback chain continuation
    - **Property 13: Fallback Chain Continues After Failures**
    - **Validates: Requirements 7.5**
    - Generate random failure patterns
    - Verify remaining locations are tried after failures

  - [~] 5.5 Write unit tests for cache write scenarios
    - Test primary location writable (fallback not attempted)
    - Test primary location read-only, fallback succeeds
    - Test both locations read-only (all writes fail)
    - Test directory creation succeeds
    - Test directory creation fails, fallback succeeds
    - Test serialization error handling
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.4, 4.5, 7.1, 7.4, 7.5_

- [~] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Update BedrockModelCatalog to use retrieved data regardless of cache write success
  - [~] 7.1 Remove try/except around `save_cache()` call
    - Remove exception handling since `save_cache()` no longer raises
    - Add informational logging after successful catalog load
    - Log model count and region count for all sources (cache, API, bundled)
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

  - [~] 7.2 Write property test for retrieved data always used
    - **Property 4: Retrieved Data Always Used**
    - **Validates: Requirements 3.1, 3.2, 7.3**
    - Generate random catalog data
    - Mock cache writes to fail
    - Verify retrieved data is used for operations

  - [~] 7.3 Write property test for no bundled fallback when retrieval succeeds
    - **Property 5: No Bundled Fallback When Retrieval Succeeds**
    - **Validates: Requirements 3.4**
    - Generate random catalog data
    - Mock cache writes to fail
    - Verify bundled data loader is not called

  - [~] 7.4 Write integration test for Lambda scenario
    - Mock read-only HOME directory
    - Mock writable /tmp directory
    - Verify API retrieval succeeds
    - Verify cache written to /tmp
    - Verify retrieved data is used
    - _Requirements: 3.1, 3.2, 4.3_

- [ ] 8. Add comprehensive logging for cache operations
  - [~] 8.1 Update log messages to include file paths
    - Ensure all cache-related log messages include the path being accessed
    - Use appropriate log levels (INFO for success, WARNING for fallback, DEBUG for expected failures)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [~] 8.2 Write property test for log messages include paths
    - **Property 10: Log Messages Include Paths**
    - **Validates: Requirements 6.4**
    - Generate random cache operations
    - Verify all log messages include file paths

  - [~] 8.3 Write unit tests for logging behavior
    - Test INFO logging for successful primary write
    - Test WARNING logging for fallback write
    - Test WARNING logging for all writes failed
    - Test DEBUG logging for cache miss
    - Test INFO logging for successful cache load
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 9. Verify backward compatibility
  - [~] 9.1 Write property test for backward compatible cache loading
    - **Property 8: Backward Compatible Cache Loading**
    - **Validates: Requirements 5.1, 5.2**
    - Generate random valid cache files
    - Place in primary location
    - Verify successful loading

  - [~] 9.2 Write property test for primary location priority
    - **Property 9: Primary Location Priority When Multiple Caches Exist**
    - **Validates: Requirements 5.5**
    - Generate cache files in multiple locations
    - Verify primary location data is used

  - [~] 9.3 Write unit tests for backward compatibility
    - Test existing cache files load successfully
    - Test cache file format unchanged
    - Test API compatibility (no signature changes)
    - Test default behavior unchanged when primary location is writable
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [~] 10. Final checkpoint - Ensure all tests pass and run code quality checks
  - Run all tests: `venv\Scripts\activate & pytest test/`
  - Run black: `venv\Scripts\activate & black src/ test/ --check --extend-exclude="src/bestehorn_llmmanager/_version.py"`
  - Run isort: `venv\Scripts\activate & isort src/ test/ --check-only --skip="src/bestehorn_llmmanager/_version.py"`
  - Run flake8: `venv\Scripts\activate & flake8 src/ test/ --exclude="src/bestehorn_llmmanager/_version.py"`
  - Run mypy: `venv\Scripts\activate & mypy --exclude="_version" src/`
  - Run bandit: `venv\Scripts\activate & bandit -r src/ scripts/ -x "src/bestehorn_llmmanager/_version.py"`
  - Fix any issues before continuing

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- All code must follow project coding standards (100 char line length, type hints, named parameters)
- All cache operations must use `pathlib.Path` objects, not string paths
- All logging must use the `logging` module with appropriate levels
- No breaking changes to public APIs
