# Design Document: CI Failure Fixes

## Overview

This design addresses two critical CI failures in the bestehorn-llmmanager project:

1. **Flaky Property-Based Test**: The test `test_direct_access_preferred_by_default` intermittently fails due to non-deterministic behavior in the AccessMethodTracker singleton, which can retain state between test runs
2. **Massive Deprecation Warnings**: Over 50,000 warnings are generated from using deprecated APIs (ModelAccessMethod.BOTH, ModelAccessMethod.CRIS_ONLY, access_method property, inference_profile_id property)

The root cause of the flaky test is that the AccessMethodTracker is a singleton that persists state across test runs. When tests run in parallel or in sequence, the tracker may contain learned preferences from previous tests, causing non-deterministic behavior.

The deprecation warnings stem from widespread use of deprecated APIs throughout the codebase, both in production code and tests. The library introduced new orthogonal access flags (has_direct_access, has_regional_cris, has_global_cris) but the old APIs remain in use.

## Architecture

### Component Overview

The retry system consists of several interconnected components:

1. **RetryManager**: Orchestrates retry logic and manages the overall retry flow
2. **AccessMethodTracker**: Singleton that tracks learned access method preferences across the process
3. **AccessMethodSelector**: Selects optimal access method based on availability and learned preferences
4. **ProfileRequirementDetector**: Detects when models require inference profile access
5. **ModelAccessInfo**: Data structure containing model availability and access method flags

### State Management Issue

The AccessMethodTracker uses a singleton pattern with process-wide state:

```python
class AccessMethodTracker:
    _instance: Optional["AccessMethodTracker"] = None
    _lock: threading.Lock = threading.Lock()
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._preferences: Dict[Tuple[str, str], AccessMethodPreference] = {}
        self._initialized = True
```

This design causes test flakiness because:
- The singleton persists across test runs
- Tests that record preferences affect subsequent tests
- Hypothesis runs tests multiple times, amplifying the issue
- No mechanism exists to reset state between tests

### Access Method Selection Flow

The current flow for selecting an access method:

1. RetryManager calls `_select_model_id_for_request()`
2. Query AccessMethodTracker for learned preferences
3. AccessMethodSelector applies preferences or defaults
4. Default order: Direct → Regional CRIS → Global CRIS
5. If learned preference exists, it overrides the default

The flaky test expects direct access to always be first when no preference exists, but the singleton may contain preferences from previous tests.

## Components and Interfaces

### AccessMethodTracker Modifications

Add a method to reset state for testing:

```python
@classmethod
def reset_for_testing(cls) -> None:
    """
    Reset singleton state for testing purposes.
    
    WARNING: This method should ONLY be called from test code.
    It clears all learned preferences and resets the singleton.
    """
    with cls._lock:
        if cls._instance is not None:
            cls._instance._preferences.clear()
            cls._instance._initialized = False
        cls._instance = None
```

### Test Fixture for State Management

Create a pytest fixture to ensure clean state:

```python
@pytest.fixture(autouse=True)
def reset_access_method_tracker():
    """
    Reset AccessMethodTracker before each test.
    
    This fixture ensures tests don't interfere with each other
    by clearing the singleton state before each test run.
    """
    from src.bestehorn_llmmanager.bedrock.tracking.access_method_tracker import AccessMethodTracker
    
    # Reset before test
    AccessMethodTracker.reset_for_testing()
    
    yield
    
    # Reset after test (cleanup)
    AccessMethodTracker.reset_for_testing()
```

### Deprecated API Migration Strategy

The library has two sets of APIs:

**Deprecated APIs (v3.0.0)**:
- `ModelAccessMethod.BOTH` enum value
- `ModelAccessMethod.CRIS_ONLY` enum value  
- `ModelAccessInfo.access_method` property
- `ModelAccessInfo.inference_profile_id` property

**Current APIs (v3.0.0+)**:
- `ModelAccessInfo.has_direct_access` flag
- `ModelAccessInfo.has_regional_cris` flag
- `ModelAccessInfo.has_global_cris` flag
- `ModelAccessInfo.regional_cris_profile_id` property
- `ModelAccessInfo.global_cris_profile_id` property

Migration approach:
1. Update production code to use current APIs
2. Update test code to use current APIs
3. Keep deprecated APIs functional for backward compatibility
4. Clearly mark intentional deprecation tests

## Data Models

### ModelAccessInfo Current Structure

```python
@dataclass
class ModelAccessInfo:
    model_id: Optional[str]
    region: str
    has_direct_access: bool
    has_regional_cris: bool
    has_global_cris: bool
    regional_cris_profile_id: Optional[str] = None
    global_cris_profile_id: Optional[str] = None
    
    # Deprecated properties (maintained for backward compatibility)
    @property
    def access_method(self) -> ModelAccessMethod:
        """Deprecated: Use orthogonal flags instead."""
        emit_deprecation_warning()
        # ... implementation
    
    @property
    def inference_profile_id(self) -> Optional[str]:
        """Deprecated: Use regional_cris_profile_id or global_cris_profile_id."""
        emit_deprecation_warning()
        # ... implementation
```

### AccessMethodPreference Structure

```python
@dataclass
class AccessMethodPreference:
    prefer_direct: bool
    prefer_regional_cris: bool
    prefer_global_cris: bool
    learned_from_error: bool
    last_updated: datetime
    
    def get_preferred_method(self) -> str:
        """Returns the preferred access method name."""
        if self.prefer_direct:
            return AccessMethodNames.DIRECT
        elif self.prefer_regional_cris:
            return AccessMethodNames.REGIONAL_CRIS
        elif self.prefer_global_cris:
            return AccessMethodNames.GLOBAL_CRIS
        return AccessMethodNames.DIRECT  # Default
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Access Method Selection Determinism

*For any* ModelAccessInfo and learned preference combination, when the AccessMethodSelector selects an access method with the same inputs, it should always return the same model ID and access method name.

**Validates: Requirements 1.2, 4.1**

### Property 2: Direct Access Preference Without Learned State

*For any* ModelAccessInfo with direct access enabled and no learned preference, the AccessMethodSelector should select the direct model ID (not a profile ARN) as the first choice.

**Validates: Requirements 1.2, 1.3**

### Property 3: Consistent Preference Order

*For any* ModelAccessInfo with multiple access methods available, when no learned preference exists, the AccessMethodSelector should apply the preference order: direct → regional CRIS → global CRIS.

**Validates: Requirements 4.2**

### Property 4: Learned Preference Application

*For any* learned preference and ModelAccessInfo where the preferred method is available, the AccessMethodSelector should use the learned preference instead of the default order.

**Validates: Requirements 4.3**

### Property 5: Test State Isolation

*For any* sequence of test runs, when the AccessMethodTracker is reset between tests, each test should produce the same result regardless of execution order.

**Validates: Requirements 1.1**

### Property 6: Deprecated API Backward Compatibility

*For any* ModelAccessInfo created using current APIs, accessing it through deprecated properties (access_method, inference_profile_id) should return equivalent values to the current API.

**Validates: Requirements 2.5**

### Property 7: Valid Test Data Generation

*For any* ModelAccessInfo generated by the test strategy, the data should satisfy ModelAccessInfo validation rules (e.g., model_id is set only when has_direct_access is True).

**Validates: Requirements 4.4**

## Error Handling

### Singleton State Management

The AccessMethodTracker singleton requires careful state management:

1. **Production Use**: State persists across requests (desired behavior for learning)
2. **Test Use**: State must be reset between tests (prevent interference)
3. **Thread Safety**: All state access protected by locks

Error scenarios:
- **Concurrent Test Execution**: Tests running in parallel could interfere if state isn't properly isolated
- **Test Cleanup Failure**: If reset fails, subsequent tests may see stale state
- **Lock Contention**: Heavy concurrent access could cause performance issues

Mitigation:
- Provide explicit `reset_for_testing()` method
- Use pytest fixtures with autouse=True for automatic reset
- Document that reset should ONLY be called from test code
- Maintain thread-safe access patterns

### Deprecation Warning Management

Deprecation warnings serve as migration signals but can create noise:

1. **Expected Warnings**: Intentional use of deprecated APIs in compatibility tests
2. **Unexpected Warnings**: Unintentional use in production or test code
3. **Warning Fatigue**: Too many warnings make it hard to spot real issues

Mitigation:
- Clearly mark intentional deprecation tests with comments
- Use pytest warning filters to suppress expected warnings in specific tests
- Track warning counts in CI to catch regressions
- Provide clear migration paths in warning messages

### Test Flakiness Detection

Flaky tests are particularly problematic in CI:

1. **Intermittent Failures**: Tests that sometimes pass, sometimes fail
2. **Order Dependencies**: Tests that fail when run in certain orders
3. **Timing Issues**: Tests that depend on timing or race conditions

Mitigation:
- Run property-based tests with high iteration counts (100+)
- Use Hypothesis's `@reproduce_failure` decorator to capture failures
- Reset all shared state between tests
- Log detailed information about access method selection

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests:

**Unit Tests**:
- Verify specific examples of access method selection
- Test edge cases (no access methods, single access method)
- Validate error conditions (invalid ModelAccessInfo)
- Check deprecation warning counts
- Verify CI pipeline passes

**Property-Based Tests**:
- Test access method selection across all input combinations
- Verify determinism with repeated runs
- Test state isolation across test sequences
- Validate backward compatibility across all valid inputs

### Property-Based Testing Configuration

- **Library**: Hypothesis (already in use)
- **Minimum Iterations**: 100 per property test
- **Test Tagging**: Each test references its design property
- **Tag Format**: `# Feature: ci-failure-fixes, Property N: [property text]`

### Test Organization

```
test/bestehorn_llmmanager/bedrock/retry/
├── test_retry_manager_profile_properties.py  # Existing PBT tests (to be fixed)
├── test_access_method_selector.py            # New unit tests for selector
├── conftest.py                                # Shared fixtures including reset fixture
└── test_deprecation_compatibility.py         # Backward compatibility tests
```

### Specific Test Cases

**Example Test 1: Flaky Test Passes 100 Times**
```python
def test_flaky_test_passes_100_times():
    """Run the previously flaky test 100 times to verify fix."""
    for i in range(100):
        # Reset state before each run
        AccessMethodTracker.reset_for_testing()
        
        # Run the test
        test_direct_access_preferred_by_default()
```

**Example Test 2: Zero Production Deprecation Warnings**
```python
def test_zero_production_deprecation_warnings():
    """Verify production code generates no deprecation warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # Import all production modules
        import_all_production_modules()
        
        # Filter to deprecation warnings from production code
        prod_warnings = [
            warning for warning in w
            if "src/bestehorn_llmmanager" in str(warning.filename)
            and "test/" not in str(warning.filename)
        ]
        
        assert len(prod_warnings) == 0, f"Found {len(prod_warnings)} deprecation warnings"
```

**Example Test 3: Deprecation Warning Count Under Threshold**
```python
def test_deprecation_warnings_under_threshold():
    """Verify total deprecation warnings are under 100."""
    # Run full test suite and count warnings
    result = pytest.main(["--tb=no", "-v", "test/"])
    
    # Parse warning count from output
    warning_count = parse_warning_count(result)
    
    assert warning_count < 100, f"Found {warning_count} warnings (threshold: 100)"
```

**Example Test 4: CI Pipeline Passes**
```python
def test_ci_pipeline_passes():
    """Verify all CI checks pass."""
    checks = [
        ("black", "black src/ test/ --check --extend-exclude='_version.py'"),
        ("isort", "isort src/ test/ --check-only --skip='_version.py'"),
        ("flake8", "flake8 src/ test/ --exclude='_version.py'"),
        ("mypy", "mypy --exclude='_version' src/"),
        ("bandit", "bandit -r src/ -x '_version.py'"),
        ("pytest", "pytest test/"),
    ]
    
    for name, command in checks:
        result = subprocess.run(command, shell=True, capture_output=True)
        assert result.returncode == 0, f"{name} check failed"
```

### Integration Testing

After all fixes are applied:

1. Run full test suite locally
2. Verify zero test failures
3. Check deprecation warning count
4. Run CI pipeline end-to-end
5. Verify all checks pass
6. Confirm ready for release

### Continuous Monitoring

To prevent regression:

1. Add CI check for deprecation warning count
2. Fail CI if warnings exceed threshold
3. Monitor test flakiness metrics
4. Track test execution time
5. Alert on new deprecation warnings

## Implementation Notes

### Code Changes Required

1. **AccessMethodTracker**:
   - Add `reset_for_testing()` class method
   - Document that it should only be called from tests
   - Ensure thread-safe reset operation

2. **Test Fixtures**:
   - Create `conftest.py` with autouse fixture
   - Apply fixture to all retry-related tests
   - Document fixture purpose and usage

3. **Production Code Migration**:
   - Replace `access_info.access_method` with flag checks
   - Replace `access_info.inference_profile_id` with specific profile IDs
   - Remove use of deprecated enum values
   - Add comments explaining the migration

4. **Test Code Migration**:
   - Update test assertions to use current APIs
   - Mark intentional deprecation tests clearly
   - Add warning filters for expected warnings
   - Update test documentation

### Migration Priority

1. **Critical (Fix Flaky Test)**:
   - Add `reset_for_testing()` method
   - Create pytest fixture
   - Apply fixture to failing test

2. **High (Reduce Warnings)**:
   - Migrate production code to current APIs
   - Update most common test patterns
   - Add warning count check to CI

3. **Medium (Clean Up)**:
   - Migrate remaining test code
   - Add comprehensive property tests
   - Document migration patterns

4. **Low (Polish)**:
   - Add monitoring and alerts
   - Create migration guide
   - Update development guidelines

### Backward Compatibility Considerations

The deprecated APIs must continue to work:

1. **access_method Property**:
   - Maps orthogonal flags to enum value
   - Emits deprecation warning
   - Returns correct value for all flag combinations

2. **inference_profile_id Property**:
   - Returns regional_cris_profile_id if available
   - Falls back to global_cris_profile_id
   - Emits deprecation warning
   - Returns None if no CRIS access

3. **Deprecated Enum Values**:
   - `ModelAccessMethod.BOTH` maps to has_direct_access=True + has_regional_cris=True
   - `ModelAccessMethod.CRIS_ONLY` maps to has_direct_access=False + has_regional_cris=True
   - Emit warnings when used
   - Maintain correct behavior

### Performance Considerations

1. **Singleton Reset**: Should be fast (< 1ms) to avoid slowing tests
2. **Lock Contention**: Reset acquires lock, could block concurrent access
3. **Test Execution Time**: Fixture overhead should be minimal
4. **Warning Emission**: Deprecation warnings have minimal overhead

### Security Considerations

1. **State Isolation**: Ensure tests can't leak sensitive data through shared state
2. **Thread Safety**: Maintain thread-safe access patterns
3. **Production Impact**: Reset method should never be called in production

## Root Cause Analysis

### Why the Test Was Flaky

The test `test_direct_access_preferred_by_default` was flaky because:

1. **Singleton State Persistence**: AccessMethodTracker is a singleton that persists across test runs
2. **Hypothesis Behavior**: Hypothesis runs tests multiple times with different inputs
3. **State Pollution**: Some test runs recorded preferences, affecting subsequent runs
4. **Non-Deterministic Order**: Test execution order varied, causing different initial states
5. **No State Reset**: No mechanism existed to reset the singleton between tests

The test would:
- **Pass** when run first (no learned preferences)
- **Fail** when run after tests that recorded preferences
- **Flake** when Hypothesis ran it multiple times in different orders

### Why Deprecation Warnings Accumulated

The warnings accumulated because:

1. **Gradual API Evolution**: New APIs were added but old code wasn't migrated
2. **Test Code Lag**: Tests continued using old patterns
3. **Copy-Paste**: Old patterns were copied to new tests
4. **No Warning Checks**: CI didn't fail on deprecation warnings
5. **Warning Fatigue**: Too many warnings made them easy to ignore

The warnings came from:
- **Production Code**: ~5% of warnings (critical to fix)
- **Test Code**: ~95% of warnings (less critical but noisy)
- **Legacy Tests**: Tests for deprecated managers (intentional)

### Prevention Strategies

To prevent similar issues in the future:

1. **State Management**:
   - Document singleton patterns clearly
   - Provide test-specific reset methods
   - Use pytest fixtures for automatic cleanup
   - Consider dependency injection over singletons

2. **Deprecation Management**:
   - Add CI check for warning counts
   - Fail CI if warnings exceed threshold
   - Migrate code when deprecating APIs
   - Provide clear migration guides

3. **Test Quality**:
   - Run property-based tests with high iteration counts
   - Test for flakiness explicitly
   - Monitor test execution order dependencies
   - Use Hypothesis's shrinking to find minimal failing cases

4. **Code Review**:
   - Check for singleton usage
   - Verify test isolation
   - Review deprecation warnings
   - Ensure new code uses current APIs

5. **Documentation**:
   - Document state management patterns
   - Explain singleton lifecycle
   - Provide migration examples
   - Update guidelines proactively

## Prevention Recommendations

This section provides concrete recommendations to prevent similar issues in future development.

### Singleton Pattern Best Practices

**Problem**: Singletons with mutable state can cause test interference and non-deterministic behavior.

**Recommendations**:

1. **Avoid Singletons When Possible**:
   - Prefer dependency injection over singleton pattern
   - Use factory patterns for shared instances
   - Consider module-level instances instead of class-level singletons

2. **If Singletons Are Necessary**:
   - Always provide a `reset_for_testing()` method
   - Document the method with clear warnings about production use
   - Make the reset method thread-safe
   - Consider using weak references to allow garbage collection

3. **Test Isolation**:
   - Create pytest fixtures with `autouse=True` for automatic cleanup
   - Reset state both before and after each test
   - Document fixture purpose and scope
   - Place fixtures in `conftest.py` for automatic discovery

4. **Alternative Patterns**:
   ```python
   # Instead of singleton:
   class AccessMethodTracker:
       _instance = None
       
   # Consider dependency injection:
   class RetryManager:
       def __init__(self, tracker: AccessMethodTracker):
           self.tracker = tracker
   
   # Or factory pattern:
   def get_tracker(reset: bool = False) -> AccessMethodTracker:
       if reset or not hasattr(get_tracker, '_instance'):
           get_tracker._instance = AccessMethodTracker()
       return get_tracker._instance
   ```

### Deprecation Management Practices

**Problem**: Deprecation warnings accumulate over time, creating noise and hiding real issues.

**Recommendations**:

1. **Proactive Migration**:
   - Migrate production code immediately when deprecating APIs
   - Update test code within the same release cycle
   - Don't let deprecated API usage accumulate
   - Set a deadline for removing deprecated APIs

2. **CI Warning Thresholds**:
   - Add pytest configuration to track warning counts
   - Fail CI if warnings exceed threshold (e.g., 100)
   - Gradually reduce threshold over time
   - Monitor warning trends in CI metrics

3. **Clear Deprecation Messages**:
   ```python
   def emit_deprecation_warning(old_api: str, new_api: str, version: str):
       warnings.warn(
           f"{old_api} is deprecated and will be removed in version {version}. "
           f"Use {new_api} instead. "
           f"See migration guide: https://docs.example.com/migration",
           DeprecationWarning,
           stacklevel=2
       )
   ```

4. **Migration Documentation**:
   - Create migration guides with code examples
   - Document the rationale for API changes
   - Provide automated migration scripts when possible
   - Include migration checklist in release notes

5. **Intentional Deprecation Tests**:
   - Clearly mark tests that intentionally use deprecated APIs
   - Use pytest warning filters for expected warnings
   - Document why the test uses deprecated APIs
   ```python
   @pytest.mark.filterwarnings("ignore::DeprecationWarning")
   def test_backward_compatibility_for_deprecated_api():
       """Test that deprecated API still works (intentional deprecation test)."""
       # Test code using deprecated API
   ```

### Test Quality Improvements

**Problem**: Flaky tests undermine confidence in CI and waste developer time.

**Recommendations**:

1. **Property-Based Testing Best Practices**:
   - Use high iteration counts (100+ for critical tests)
   - Test with deterministic seeds for reproducibility
   - Use Hypothesis's `@reproduce_failure` decorator
   - Shrink failing examples to minimal cases
   ```python
   @given(st.integers(), st.text())
   @settings(max_examples=100, deadline=None)
   def test_property(x, y):
       # Property test
   ```

2. **Test Isolation Checklist**:
   - [ ] No shared mutable state between tests
   - [ ] All fixtures properly clean up resources
   - [ ] Tests pass in any order
   - [ ] Tests pass when run in parallel
   - [ ] Tests pass when run repeatedly

3. **Flakiness Detection**:
   - Run tests multiple times in CI (e.g., 3 times)
   - Use pytest-repeat plugin for local testing
   - Monitor test failure rates over time
   - Investigate any test that fails intermittently
   ```bash
   # Run test 100 times to detect flakiness
   pytest test_file.py::test_name --count=100
   ```

4. **State Management in Tests**:
   - Reset all singletons before each test
   - Clear caches and registries
   - Reset environment variables
   - Clean up temporary files and databases

5. **Logging and Debugging**:
   - Add detailed logging to complex test scenarios
   - Log the inputs that caused failures
   - Use Hypothesis's `note()` function for context
   - Capture and display relevant state in failures

### CI Configuration Best Practices

**Problem**: CI doesn't catch issues early enough, leading to accumulated technical debt.

**Recommendations**:

1. **Warning Threshold Configuration**:
   ```ini
   # pytest.ini
   [pytest]
   filterwarnings =
       error::DeprecationWarning
       # Allow specific expected warnings
       ignore::DeprecationWarning:test.legacy.*
   ```

2. **CI Pipeline Checks**:
   - Run all code quality tools (black, isort, flake8, mypy, bandit)
   - Track and fail on warning count thresholds
   - Run tests with coverage requirements
   - Check for flaky tests with repeated runs
   - Validate documentation builds

3. **Pre-Commit Hooks**:
   ```yaml
   # .pre-commit-config.yaml
   repos:
     - repo: local
       hooks:
         - id: check-warnings
           name: Check deprecation warnings
           entry: python -m pytest --tb=no -q
           language: system
           pass_filenames: false
   ```

4. **Monitoring and Alerts**:
   - Track warning counts over time
   - Alert on sudden increases in warnings
   - Monitor test execution time trends
   - Track flaky test occurrences

### Code Review Guidelines

**Problem**: Issues slip through code review without proper scrutiny.

**Recommendations**:

1. **Singleton Usage Review**:
   - Question the need for singletons
   - Verify test isolation mechanisms exist
   - Check for thread-safety concerns
   - Ensure documentation is clear

2. **Deprecation Review**:
   - Verify new code uses current APIs
   - Check that deprecated APIs have migration paths
   - Ensure deprecation warnings are clear
   - Confirm migration documentation exists

3. **Test Quality Review**:
   - Verify tests are deterministic
   - Check for proper state cleanup
   - Ensure tests are isolated
   - Validate property-based test strategies

4. **Review Checklist**:
   - [ ] No new deprecation warnings introduced
   - [ ] Singletons have test reset methods
   - [ ] Tests are isolated and deterministic
   - [ ] Code uses current APIs
   - [ ] Documentation is updated

### Development Workflow Integration

**Problem**: Issues aren't caught until CI runs, slowing down development.

**Recommendations**:

1. **Local Pre-Commit Checks**:
   ```bash
   # Run before committing
   black src/ test/ --check
   isort src/ test/ --check-only
   flake8 src/ test/
   mypy src/
   pytest test/ -v
   ```

2. **IDE Integration**:
   - Configure IDE to show deprecation warnings
   - Enable real-time linting and type checking
   - Set up automatic code formatting on save
   - Configure test runners to show warnings

3. **Documentation Updates**:
   - Update docs when changing APIs
   - Document breaking changes immediately
   - Maintain changelog with migration notes
   - Keep examples up to date

4. **Regular Maintenance**:
   - Schedule quarterly deprecation cleanup
   - Review and update CI thresholds
   - Audit singleton usage patterns
   - Refactor problematic patterns proactively
