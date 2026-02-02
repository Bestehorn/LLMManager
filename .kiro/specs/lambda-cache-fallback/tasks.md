# Implementation Plan: Lambda Cache Fallback

## Overview

This implementation plan breaks down the lambda-cache-fallback feature into discrete coding tasks. Each task builds on previous steps and includes testing to validate core functionality early. The implementation modifies the cache management system to support multiple cache locations with automatic fallback, ensuring successfully retrieved data is always used regardless of cache write failures.

## Progress Summary

**Completed:**
- Task 1: Cache location constants and helper methods ✓
- Task 1.1: Unit tests for cache location constants ✓
- Task 2.1-2.4: CacheManager refactoring with multi-location support ✓
- Task 3: First checkpoint passed ✓
- Task 4.1: Multi-location cache read implementation ✓

**Current Status:**
- The CacheManager now supports multiple cache locations (primary + fallback)
- Cache reads iterate through locations in priority order
- Cache validation helper method extracted and tested
- Property tests verify cache location initialization
- Unit tests cover cache file validation scenarios

**Remaining Work:**
- Complete property and unit tests for multi-location cache read (Tasks 4.2-4.4)
- Implement multi-location cache write with graceful degradation (Task 5)
- Update BedrockModelCatalog to handle cache write failures gracefully (Task 7)
- Add comprehensive logging (Task 8)
- Verify backward compatibility (Task 9)
- Final validation and code quality checks (Task 10)

## Tasks

- [x] 1. Add fallback cache location constants and helper methods
  - Modify `src/bestehorn_llmmanager/bedrock/models/catalog_constants.py`
  - Add `get_fallback_cache_directory()` static method returning `/tmp/bestehorn-llmmanager-cache/`
  - Add `get_all_cache_locations()` static method returning list of [primary, fallback] directories
  - Add new log message constants for multi-location cache operations
  - _Requirements: 4.2_

- [x] 1.1 Write unit tests for cache location constants
  - Test `get_fallback_cache_directory()` returns correct path
  - Test `get_all_cache_locations()` returns correct priority order
  - _Requirements: 4.2_

- [x] 2. Refactor CacheManager to support multiple cache locations
  - [x] 2.1 Modify CacheManager initialization to store list of cache locations
    - Update `__init__()` to create list of cache file paths (primary + fallback)
    - Store `_cache_locations: List[Path]` instead of single `_cache_file_path`
    - Maintain backward compatibility with existing `cache_file_path` property
    - _Requirements: 1.1, 4.1, 4.2_

  - [x] 2.2 Write property test for cache location initialization
    - **Property 1: Cache Write Location Priority**
    - **Validates: Requirements 1.1, 1.2**
    - Generate random cache configurations
    - Verify primary location is first in list
    - Verify fallback location is second in list

  - [x] 2.3 Extract cache file validation into helper method
    - Create `_is_cache_file_valid(cache_path: Path) -> bool` method
    - Move validation logic from `is_cache_valid()` to new helper
    - Update `is_cache_valid()` to delegate to helper for first location
    - _Requirements: 2.1, 2.2_

  - [x] 2.4 Write unit tests for cache file validation helper
    - Test validation with valid cache file
    - Test validation with expired cache file
    - Test validation with invalid JSON
    - Test validation with version mismatch
    - _Requirements: 2.1, 2.2_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement multi-location cache read with fallback
  - [x] 4.1 Modify `load_cache()` to try multiple locations
    - Iterate through `_cache_locations` in priority order
    - Log DEBUG for each failed attempt with path
    - Log INFO for successful load with path
    - Return first valid cache found
    - Return None if all locations fail
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 4.2 Write property test for multi-location cache read
    - **Property 2: Cache Read Location Priority**
    - **Validates: Requirements 2.1, 2.2**
    - Create `test/bestehorn_llmmanager/bedrock/catalog/test_cache_read_properties.py`
    - Generate random cache configurations with valid data in fallback only
    - Mock primary location to fail (file doesn't exist or invalid)
    - Verify fallback location is attempted and data is loaded
    - Verify correct logging occurs for each attempt

  - [x] 4.3 Write property test for cache read failure
    - **Property 3: Cache Read Failure Returns None**
    - **Validates: Requirements 2.5, 7.2**
    - Add to `test_cache_read_properties.py`
    - Generate random configurations
    - Mock all locations to fail (files don't exist or are invalid)
    - Verify None is returned
    - Verify appropriate DEBUG logging occurs

  - [x] 4.4 Write unit tests for cache read scenarios
    - Add to `test/bestehorn_llmmanager/bedrock/catalog/test_cache_manager.py`
    - Test cache exists in primary location only (fallback not attempted)
    - Test cache exists in fallback location only (primary fails, fallback succeeds)
    - Test cache exists in both locations (primary wins, fallback not attempted)
    - Test no cache exists in any location (returns None)
    - Test invalid cache in primary, valid in fallback (fallback succeeds)
    - _Requirements: 2.1, 2.2, 2.5, 5.5_

- [ ] 5. Implement multi-location cache write with graceful degradation
  - [x] 5.1 Modify `save_cache()` to try multiple locations without raising exceptions
    - Modify `src/bestehorn_llmmanager/bedrock/catalog/cache_manager.py`
    - Iterate through `_cache_locations` in priority order
    - Catch all filesystem exceptions (OSError, IOError, PermissionError)
    - Catch all serialization exceptions (TypeError, ValueError)
    - Log WARNING for each failed attempt with path and error
    - Log INFO for successful write to primary location
    - Log WARNING for successful write to fallback location
    - Log WARNING if all writes fail (use `CACHE_ALL_WRITES_FAILED` message)
    - Never raise exceptions to caller (remove all `raise CacheError`)
    - Break loop after first successful write
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 7.1, 7.4, 7.5_

  - [x] 5.2 Write property test for cache write never raises exceptions
    - **Property 11: Cache Write Never Raises Exceptions**
    - **Validates: Requirements 7.1**
    - Create `test/bestehorn_llmmanager/bedrock/catalog/test_cache_write_properties.py`
    - Generate random catalog data
    - Mock filesystem to raise various exceptions (PermissionError, OSError, IOError)
    - Verify no exceptions propagate to caller
    - Verify appropriate WARNING logging occurs

  - [x] 5.3 Write property test for filesystem exception handling
    - **Property 12: Filesystem Exceptions Caught and Logged**
    - **Validates: Requirements 7.4**
    - Add to `test_cache_write_properties.py`
    - Generate random filesystem exceptions
    - Verify exceptions are caught and logged at WARNING level
    - Verify fallback location is attempted after primary fails

  - [x] 5.4 Write property test for fallback chain continuation
    - **Property 13: Fallback Chain Continues After Failures**
    - **Validates: Requirements 7.5**
    - Add to `test_cache_write_properties.py`
    - Generate random failure patterns (primary fails, fallback succeeds)
    - Verify remaining locations are tried after failures
    - Verify loop breaks after first success

  - [x] 5.5 Write unit tests for cache write scenarios
    - Add to `test/bestehorn_llmmanager/bedrock/catalog/test_cache_manager.py`
    - Test primary location writable (fallback not attempted, INFO log)
    - Test primary location read-only, fallback succeeds (WARNING log for fallback)
    - Test both locations read-only (all writes fail, WARNING log)
    - Test directory creation succeeds at primary
    - Test directory creation fails at primary, succeeds at fallback
    - Test serialization error handling (TypeError, ValueError)
    - Verify no CacheError exceptions are raised in any scenario
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.4, 4.5, 7.1, 7.4, 7.5_

- [x] 6. Checkpoint - Ensure all tests pass
  - Run: `venv\Scripts\activate & pytest test/bestehorn_llmmanager/bedrock/catalog/ -v`
  - Verify all cache manager tests pass
  - Ask user if questions arise

- [ ] 7. Update BedrockModelCatalog to use retrieved data regardless of cache write success
  - [x] 7.1 Remove try/except around `save_cache()` call
    - Modify `src/bestehorn_llmmanager/bedrock/catalog/bedrock_catalog.py`
    - In `ensure_catalog_available()` method, remove try/except around `save_cache()` call
    - Since `save_cache()` no longer raises exceptions, direct call is safe
    - Add informational logging after successful catalog load from any source
    - Use `CATALOG_LOADED_INFO` message with model count and region count
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

  - [x] 7.2 Write property test for retrieved data always used
    - **Property 4: Retrieved Data Always Used**
    - **Validates: Requirements 3.1, 3.2, 7.3**
    - Create `test/bestehorn_llmmanager/bedrock/catalog/test_catalog_retrieval_properties.py`
    - Generate random catalog data
    - Mock API fetch to succeed
    - Mock cache writes to fail (all locations)
    - Verify retrieved data is stored in `_catalog` attribute
    - Verify retrieved data is returned to caller
    - Verify bundled data loader is NOT called

  - [x] 7.3 Write property test for no bundled fallback when retrieval succeeds
    - **Property 5: No Bundled Fallback When Retrieval Succeeds**
    - **Validates: Requirements 3.4**
    - Add to `test_catalog_retrieval_properties.py`
    - Generate random catalog data
    - Mock API fetch to succeed
    - Mock cache writes to fail
    - Mock bundled data loader
    - Verify bundled data loader is never called
    - Verify retrieved data is used

  - [x] 7.4 Write integration test for Lambda scenario
    - Create `test/integration/bedrock/catalog/test_lambda_cache_fallback.py`
    - Mock read-only HOME directory (PermissionError on primary location)
    - Mock writable /tmp directory (fallback succeeds)
    - Mock successful API retrieval
    - Verify cache written to /tmp (fallback location)
    - Verify retrieved data is used and returned
    - Verify appropriate WARNING logging for fallback usage
    - _Requirements: 3.1, 3.2, 4.3_

- [ ] 8. Add comprehensive logging for cache operations
  - [x] 8.1 Update log messages to include file paths
    - Review all logging calls in `cache_manager.py`
    - Ensure all cache-related log messages include the path being accessed
    - Use f-strings with path variables: `f"Loading cache from: {cache_path}"`
    - Use appropriate log levels:
      - INFO: Successful operations (cache loaded, cache saved to primary)
      - WARNING: Fallback behavior (saved to alternative location, all writes failed)
      - DEBUG: Expected failures (cache miss, cache invalid)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 8.2 Write property test for log messages include paths
    - **Property 10: Log Messages Include Paths**
    - **Validates: Requirements 6.4**
    - Create `test/bestehorn_llmmanager/bedrock/catalog/test_cache_logging_properties.py`
    - Generate random cache operations (read and write)
    - Capture log output using caplog fixture
    - Verify all cache-related log messages include file paths
    - Use regex to verify path patterns in log messages

  - [x] 8.3 Write unit tests for logging behavior
    - Add to `test/bestehorn_llmmanager/bedrock/catalog/test_cache_manager.py`
    - Test INFO logging for successful primary write (includes path)
    - Test WARNING logging for fallback write (includes both paths)
    - Test WARNING logging for all writes failed
    - Test DEBUG logging for cache miss (includes path)
    - Test INFO logging for successful cache load (includes path)
    - Use caplog fixture to capture and verify log messages
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 9. Verify backward compatibility
  - [x] 9.1 Write property test for backward compatible cache loading
    - **Property 8: Backward Compatible Cache Loading**
    - **Validates: Requirements 5.1, 5.2**
    - Create `test/bestehorn_llmmanager/bedrock/catalog/test_cache_compatibility_properties.py`
    - Generate random valid cache files (existing format)
    - Place in primary location only
    - Verify successful loading
    - Verify cache file format unchanged (same JSON structure)

  - [x] 9.2 Write property test for primary location priority
    - **Property 9: Primary Location Priority When Multiple Caches Exist**
    - **Validates: Requirements 5.5**
    - Add to `test_cache_compatibility_properties.py`
    - Generate different cache files in multiple locations
    - Place newer data in fallback, older data in primary
    - Verify primary location data is used (not fallback)
    - Verify fallback is not attempted when primary is valid

  - [x] 9.3 Write unit tests for backward compatibility
    - Add to `test/bestehorn_llmmanager/bedrock/catalog/test_cache_manager.py`
    - Test existing cache files load successfully from primary location
    - Test cache file format unchanged (JSON structure matches)
    - Test API compatibility (no signature changes to public methods)
    - Test default behavior unchanged when primary location is writable
    - Test `cache_file_path` property returns primary location (backward compat)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Final checkpoint - Ensure all tests pass and run code quality checks
  - Run all tests: `venv\Scripts\activate & pytest test/ -v`
  - Verify all tests pass (unit, property, and integration)
  - Run code quality checks:
    - Black: `venv\Scripts\activate & black src/ test/ --check --extend-exclude="src/bestehorn_llmmanager/_version.py"`
    - isort: `venv\Scripts\activate & isort src/ test/ --check-only --skip="src/bestehorn_llmmanager/_version.py"`
    - flake8: `venv\Scripts\activate & flake8 src/ test/ --exclude="src/bestehorn_llmmanager/_version.py"`
    - mypy: `venv\Scripts\activate & mypy --exclude="_version" src/`
    - bandit: `venv\Scripts\activate & bandit -r src/ scripts/ -x "src/bestehorn_llmmanager/_version.py"`
  - Fix any issues before marking complete
  - Update documentation if needed

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
- The current `save_cache()` implementation still raises `CacheError` - this must be changed in Task 5.1
