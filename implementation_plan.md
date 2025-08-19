# Implementation Plan

## [Overview]
Fix the arbitrary default value issue in ParallelLLMManager where target_regions_per_request defaults to 5, causing errors when fewer regions are available.

The current implementation uses a hardcoded default value of 5 for `target_regions_per_request` in the `converse_parallel()` method, which causes `RegionDistributionError` when users have fewer than 5 regions available. This implementation will replace the arbitrary default with intelligent auto-calculation based on the user's actual configuration (using the smaller of `max_concurrent_requests` and available regions count) and provide transparent feedback through warning messages when auto-adjustment occurs.

## [Types]
No new type definitions required for this implementation.

The existing types in `parallel_structures.py` and `parallel_constants.py` will be modified to support the new default calculation logic. The method signature of `converse_parallel()` will change to make `target_regions_per_request` optional with `None` as the default value to trigger auto-calculation.

## [Files]
Modifications to existing files to implement intelligent default calculation.

Detailed breakdown:
- **Modified files:**
  - `src/bestehorn_llmmanager/parallel_llm_manager.py` - Update `converse_parallel()` method signature and add auto-calculation logic
  - `src/bestehorn_llmmanager/bedrock/models/parallel_constants.py` - Remove or deprecate `DEFAULT_TARGET_REGIONS_PER_REQUEST` and add new warning messages
  - `test/bestehorn_llmmanager/test_ParallelLLMManager.py` - Add tests for the new auto-calculation behavior
  - `notebooks/ParallelLLMManager_Demo.ipynb` - Update examples to demonstrate the new default behavior

## [Functions]
Modifications to method signatures and logic to support intelligent defaults.

Detailed breakdown:
- **Modified functions:**
  - `ParallelLLMManager.converse_parallel()` in `parallel_llm_manager.py` - Change signature to make `target_regions_per_request` optional (default `None`), add auto-calculation logic with warning
  - `ParallelLLMManager._calculate_optimal_target_regions()` in `parallel_llm_manager.py` - New private method to calculate optimal target regions based on config and available regions
  - `ParallelLLMManager._log_target_regions_adjustment()` in `parallel_llm_manager.py` - New private method to log warning when auto-adjustment occurs

## [Classes]
Minor modifications to existing classes for improved default behavior.

Detailed breakdown:
- **Modified classes:**
  - `ParallelLLMManager` in `parallel_llm_manager.py` - Add new private methods for auto-calculation and logging, modify `converse_parallel()` method signature and implementation
  - `ParallelConfig` in `parallel_constants.py` - Deprecate `DEFAULT_TARGET_REGIONS_PER_REQUEST` constant, add new warning message constants for auto-adjustment notifications

## [Dependencies]
No new external dependencies required.

This implementation uses existing Python standard library features and current project dependencies. The changes are internal to the existing codebase structure and maintain backward compatibility with existing code that explicitly provides `target_regions_per_request` values.

## [Testing]
Comprehensive testing of the new auto-calculation behavior and backward compatibility.

Test file requirements:
- Add test cases in `test_ParallelLLMManager.py` for auto-calculation with various scenarios:
  - When `target_regions_per_request` is `None` (default)
  - When `max_concurrent_requests` < available regions
  - When `max_concurrent_requests` > available regions  
  - When `max_concurrent_requests` == available regions
  - Backward compatibility when `target_regions_per_request` is explicitly provided
- Add test for warning message generation when auto-adjustment occurs
- Ensure existing tests continue to pass without modification

## [Implementation Order]
Logical sequence of changes to minimize conflicts and ensure successful integration.

1. **Update constants** - Modify `parallel_constants.py` to add new warning messages and mark old default as deprecated
2. **Add auto-calculation methods** - Implement `_calculate_optimal_target_regions()` and `_log_target_regions_adjustment()` in `ParallelLLMManager`
3. **Modify method signature** - Update `converse_parallel()` method signature to make `target_regions_per_request` optional
4. **Implement auto-calculation logic** - Add the intelligent default calculation in `converse_parallel()` method
5. **Update tests** - Add comprehensive test cases for the new behavior and ensure backward compatibility
6. **Update documentation** - Modify notebook examples to demonstrate the improved default behavior
7. **Validation testing** - Run full test suite to ensure no regressions
