# Design Document: Inference Profile Support

## Overview

This design implements automatic inference profile support for AWS Bedrock models that require profile-based access. The system will detect when models require inference profiles (based on ValidationException errors), automatically select and use appropriate profiles, and learn access method preferences over time to optimize future requests.

The design integrates seamlessly with the existing `ModelAccessInfo` structure which already supports orthogonal access flags (`has_direct_access`, `has_regional_cris`, `has_global_cris`), requiring minimal changes to the existing architecture.

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      RetryManager                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │         ProfileRequirementDetector                        │ │
│  │  - Detect profile requirement errors                      │ │
│  │  - Extract model ID from error messages                   │ │
│  │  - Trigger profile-based retry                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │         AccessMethodSelector                              │ │
│  │  - Select optimal access method                           │ │
│  │  - Prefer direct → regional CRIS → global CRIS            │ │
│  │  - Use learned preferences when available                 │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                  AccessMethodTracker                            │
│  - Track successful access methods                              │
│  - Learn model/region access requirements                       │
│  - Persist preferences across instances                         │
│  - Provide access method recommendations                        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                BedrockModelCatalog                              │
│  - Already provides ModelAccessInfo with orthogonal flags       │
│  - No changes needed to core catalog structure                  │
│  - Catalog already includes profile IDs in ModelAccessInfo      │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Minimal Changes**: Leverage existing `ModelAccessInfo` structure with orthogonal access flags
2. **Error-Driven Detection**: Detect profile requirements from AWS ValidationException errors
3. **Intelligent Retry**: Retry with profile immediately upon detection, don't count as separate attempt
4. **Learning System**: Track successful access methods to optimize future requests
5. **Backward Compatible**: Maintain all existing direct access behavior
6. **Profile Preference Order**: Direct → Regional CRIS → Global CRIS (when multiple options available)

## Components and Interfaces

### 1. ProfileRequirementDetector

**Purpose**: Detect when AWS errors indicate a model requires inference profile access.

**Location**: `src/bestehorn_llmmanager/bedrock/retry/profile_requirement_detector.py`

**Interface**:
```python
class ProfileRequirementDetector:
    """
    Detects when AWS errors indicate inference profile requirement.
    
    Analyzes ValidationException messages to identify when a model
    requires profile-based access instead of direct model ID invocation.
    """
    
    # Error patterns indicating profile requirement
    PROFILE_REQUIREMENT_PATTERNS = [
        "with on-demand throughput isn't supported",
        "retry your request with the id or arn of an inference profile",
        "inference profile that contains this model",
        "model id.*isn't supported",
    ]
    
    @classmethod
    def is_profile_requirement_error(
        cls,
        error: Exception
    ) -> bool:
        """
        Check if error indicates profile requirement.
        
        Args:
            error: Exception to analyze
            
        Returns:
            True if error indicates profile is required
        """
        
    @classmethod
    def extract_model_id_from_error(
        cls,
        error: Exception
    ) -> Optional[str]:
        """
        Extract model ID from profile requirement error message.
        
        Args:
            error: Profile requirement error
            
        Returns:
            Model ID if found, None otherwise
        """
```

### 2. AccessMethodSelector

**Purpose**: Select the optimal access method for a model/region combination.

**Location**: `src/bestehorn_llmmanager/bedrock/retry/access_method_selector.py`

**Interface**:
```python
@dataclass
class AccessMethodPreference:
    """Preference for accessing a model in a region."""
    
    prefer_direct: bool = True
    prefer_regional_cris: bool = False
    prefer_global_cris: bool = False
    learned_from_error: bool = False
    last_updated: datetime = field(default_factory=datetime.now)


class AccessMethodSelector:
    """
    Selects optimal access method for model/region combinations.
    
    Uses learned preferences and ModelAccessInfo to choose the best
    access method. Preference order: Direct → Regional CRIS → Global CRIS
    """
    
    def __init__(
        self,
        access_method_tracker: 'AccessMethodTracker'
    ) -> None:
        """Initialize selector with access method tracker."""
        
    def select_access_method(
        self,
        access_info: ModelAccessInfo,
        learned_preference: Optional[AccessMethodPreference] = None
    ) -> Tuple[str, str]:
        """
        Select optimal access method and return model ID to use.
        
        Args:
            access_info: Model access information from catalog
            learned_preference: Previously learned preference (if any)
            
        Returns:
            Tuple of (model_id_to_use, access_method_name)
            
        Examples:
            - ("anthropic.claude-3-haiku-20240307-v1:0", "direct")
            - ("arn:aws:bedrock:us-east-1::inference-profile/...", "regional_cris")
        """
        
    def get_fallback_access_methods(
        self,
        access_info: ModelAccessInfo,
        failed_method: str
    ) -> List[Tuple[str, str]]:
        """
        Get fallback access methods after a failure.
        
        Args:
            access_info: Model access information
            failed_method: Access method that failed
            
        Returns:
            List of (model_id, access_method_name) tuples to try
        """
```

### 3. AccessMethodTracker

**Purpose**: Track and learn successful access methods for model/region combinations.

**Location**: `src/bestehorn_llmmanager/bedrock/tracking/access_method_tracker.py`

**Interface**:
```python
class AccessMethodTracker:
    """
    Tracks successful access methods for model/region combinations.
    
    Maintains a process-wide cache of learned access method preferences
    to optimize future requests.
    """
    
    _instance: Optional['AccessMethodTracker'] = None
    _lock: threading.Lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'AccessMethodTracker':
        """Get singleton instance (process-wide)."""
        
    def __init__(self) -> None:
        """Initialize tracker with empty preference cache."""
        self._preferences: Dict[Tuple[str, str], AccessMethodPreference] = {}
        self._lock = threading.Lock()
        
    def record_success(
        self,
        model_id: str,
        region: str,
        access_method: str,
        model_id_used: str
    ) -> None:
        """
        Record successful access method.
        
        Args:
            model_id: Base model ID (e.g., "anthropic.claude-3-haiku-20240307-v1:0")
            region: AWS region
            access_method: Access method used ("direct", "regional_cris", "global_cris")
            model_id_used: Actual ID used in request (model ID or profile ARN)
        """
        
    def record_profile_requirement(
        self,
        model_id: str,
        region: str
    ) -> None:
        """
        Record that a model requires profile-based access.
        
        Args:
            model_id: Model ID that requires profile
            region: AWS region
        """
        
    def get_preference(
        self,
        model_id: str,
        region: str
    ) -> Optional[AccessMethodPreference]:
        """
        Get learned preference for model/region.
        
        Args:
            model_id: Model ID
            region: AWS region
            
        Returns:
            Learned preference if available, None otherwise
        """
        
    def requires_profile(
        self,
        model_id: str,
        region: str
    ) -> bool:
        """
        Check if model is known to require profile access.
        
        Args:
            model_id: Model ID
            region: AWS region
            
        Returns:
            True if model is known to require profile
        """
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tracked access methods.
        
        Returns:
            Dictionary with tracking statistics
        """
```

### 4. RetryManager Integration

**Purpose**: Integrate profile detection and selection into existing retry logic.

**Location**: `src/bestehorn_llmmanager/bedrock/retry/retry_manager.py` (modifications)

**New Methods**:
```python
class RetryManager:
    """Existing retry manager with profile support added."""
    
    def __init__(self, retry_config: RetryConfig) -> None:
        """Initialize with profile support components."""
        # Existing initialization...
        
        # NEW: Initialize profile support components
        self._access_method_tracker = AccessMethodTracker.get_instance()
        self._access_method_selector = AccessMethodSelector(
            access_method_tracker=self._access_method_tracker
        )
        
    def _retry_with_profile(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        model: str,
        region: str,
        access_info: ModelAccessInfo,
        original_error: Exception
    ) -> Tuple[Any, bool, Optional[str]]:
        """
        Retry operation with inference profile after detecting requirement.
        
        This method is called when a profile requirement error is detected.
        It attempts to retry with available CRIS profiles.
        
        Args:
            operation: Function to execute
            operation_args: Original operation arguments
            model: Model name
            region: Region name
            access_info: Model access information
            original_error: The profile requirement error
            
        Returns:
            Tuple of (result, success, warning_message)
        """
        
    def _select_model_id_for_request(
        self,
        access_info: ModelAccessInfo,
        model_name: str,
        region: str
    ) -> Tuple[str, str]:
        """
        Select appropriate model ID for request based on access info and learned preferences.
        
        Args:
            access_info: Model access information from catalog
            model_name: User-provided model name
            region: Target region
            
        Returns:
            Tuple of (model_id_to_use, access_method_name)
        """
```

## Data Models

### AccessMethodPreference

**Purpose**: Store learned preference for accessing a model in a region.

```python
@dataclass
class AccessMethodPreference:
    """
    Learned preference for accessing a model in a region.
    
    Attributes:
        prefer_direct: Prefer direct model ID access
        prefer_regional_cris: Prefer regional CRIS profile
        prefer_global_cris: Prefer global CRIS profile
        learned_from_error: Whether preference was learned from error
        last_updated: When preference was last updated
    """
    
    prefer_direct: bool = True
    prefer_regional_cris: bool = False
    prefer_global_cris: bool = False
    learned_from_error: bool = False
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_preferred_method(self) -> str:
        """Get the preferred access method name."""
        if self.prefer_direct:
            return "direct"
        elif self.prefer_regional_cris:
            return "regional_cris"
        elif self.prefer_global_cris:
            return "global_cris"
        return "unknown"
```

### ProfileRequirementError

**Purpose**: Custom exception for profile requirement detection.

```python
class ProfileRequirementError(Exception):
    """
    Exception indicating a model requires inference profile access.
    
    This is an internal exception used to signal profile requirement
    detection within the retry logic.
    """
    
    def __init__(
        self,
        model_id: str,
        region: str,
        original_error: Exception,
        message: Optional[str] = None
    ) -> None:
        """
        Initialize profile requirement error.
        
        Args:
            model_id: Model ID that requires profile
            region: Region where requirement was detected
            original_error: Original ValidationException from AWS
            message: Optional custom message
        """
        self.model_id = model_id
        self.region = region
        self.original_error = original_error
        super().__init__(message or f"Model {model_id} requires inference profile in {region}")
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Profile Requirement Detection Accuracy
*For any* ValidationException containing profile requirement patterns, the detector must correctly identify it as a profile requirement error.

**Validates: Requirements 1.1, 1.2**

### Property 2: Access Method Selection Consistency
*For any* ModelAccessInfo with multiple access methods available, selecting an access method multiple times with the same learned preference must return the same result.

**Validates: Requirements 2.1, 2.2**

### Property 3: Preference Learning Persistence
*For any* successful request using a specific access method, recording the success and then querying the preference must return a preference matching that access method.

**Validates: Requirements 5.1, 5.2, 5.3**

### Property 4: Fallback Access Method Ordering
*For any* ModelAccessInfo with multiple access methods, the fallback methods must be ordered by preference (direct → regional CRIS → global CRIS) and must not include the failed method.

**Validates: Requirements 2.3, 4.4**

### Property 5: Profile Retry Idempotence
*For any* profile requirement error, retrying with a profile must not increment the retry attempt counter.

**Validates: Requirements 4.2**

### Property 6: Backward Compatibility Preservation
*For any* model with direct access available, the system must attempt direct access first unless a learned preference indicates otherwise.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 7: Tracker Thread Safety
*For any* concurrent access to the AccessMethodTracker from multiple threads, all operations must be thread-safe and maintain consistency.

**Validates: Requirements 5.3**

## Error Handling

### Error Scenarios

1. **Profile Requirement Detected**:
   - **Cause**: AWS returns ValidationException indicating profile required
   - **Handling**: Detect error, select profile, retry immediately
   - **Logging**: WARNING level with model ID and region
   - **User Impact**: Transparent retry, no user action needed

2. **No Profile Available**:
   - **Cause**: Model requires profile but catalog has no profile information
   - **Handling**: Try next model/region combination
   - **Logging**: WARNING level indicating missing profile
   - **User Impact**: Falls back to other models

3. **Profile Retry Fails**:
   - **Cause**: Retry with profile also fails
   - **Handling**: Continue to next model/region combination
   - **Logging**: DEBUG level with failure details
   - **User Impact**: Transparent fallback to other options

4. **All Profiles Exhausted**:
   - **Cause**: All available profiles tried and failed
   - **Handling**: Raise RetryExhaustedError with clear message
   - **Error Message**: "All models require inference profiles but none succeeded. Check catalog data freshness."
   - **User Impact**: Clear error message with actionable guidance

### Error Message Format

```python
# Profile requirement detected
"Model 'anthropic.claude-sonnet-4-20250514-v1:0' requires inference profile in region 'us-east-1'. Retrying with profile..."

# No profile available
"Model 'anthropic.claude-sonnet-4-20250514-v1:0' requires inference profile in 'us-east-1' but no profile information available in catalog"

# Profile retry succeeded
"Request succeeded using inference profile 'arn:aws:bedrock:us-east-1::inference-profile/...' for model 'Claude Sonnet 4.5'"

# All profiles failed
"All retry attempts exhausted. Models tried: ['Claude Sonnet 4.5', 'Claude Haiku 4.5']. All models require inference profiles. Consider refreshing catalog data."
```

## Testing Strategy

### Unit Tests

**Test File**: `test/bestehorn_llmmanager/bedrock/retry/test_profile_requirement_detector.py`

**Test Cases**:
1. **Profile Requirement Detection**:
   - Test detection of various error message patterns
   - Test model ID extraction from error messages
   - Test non-profile errors return False

2. **Access Method Selection**:
   - Test selection with direct access available
   - Test selection with only CRIS access
   - Test selection with multiple CRIS options
   - Test selection with learned preferences
   - Test fallback method ordering

3. **Access Method Tracking**:
   - Test recording successful access methods
   - Test recording profile requirements
   - Test preference retrieval
   - Test thread safety
   - Test statistics generation

**Test File**: `test/bestehorn_llmmanager/bedrock/retry/test_access_method_selector.py`

**Test Cases**:
1. Test access method selection logic
2. Test fallback generation
3. Test preference application
4. Test edge cases (no access methods, all methods failed)

**Test File**: `test/bestehorn_llmmanager/bedrock/tracking/test_access_method_tracker.py`

**Test Cases**:
1. Test singleton pattern
2. Test concurrent access
3. Test preference persistence
4. Test statistics accuracy

### Property-Based Tests

**Test File**: `test/bestehorn_llmmanager/bedrock/retry/test_profile_support_properties.py`

**Property Tests**:
1. **Property 1: Profile Requirement Detection Accuracy** (Requirements 1.1, 1.2)
2. **Property 2: Access Method Selection Consistency** (Requirements 2.1, 2.2)
3. **Property 3: Preference Learning Persistence** (Requirements 5.1, 5.2, 5.3)
4. **Property 4: Fallback Access Method Ordering** (Requirements 2.3, 4.4)
5. **Property 5: Profile Retry Idempotence** (Requirements 4.2)
6. **Property 6: Backward Compatibility Preservation** (Requirements 6.1, 6.2, 6.3)
7. **Property 7: Tracker Thread Safety** (Requirements 5.3)

### Integration Tests

**Test File**: `test/integration/test_integration_profile_support.py`

**Test Cases**:
1. Test end-to-end profile requirement detection and retry
2. Test profile support with real AWS Bedrock calls (mocked)
3. Test parallel processing with profile requirements
4. Test access method learning across multiple requests
5. Test backward compatibility with direct-access-only models

## Implementation Notes

### Performance Considerations

1. **Minimal Overhead**: Profile detection only occurs on ValidationException
2. **Fast Lookup**: Access method tracker uses dictionary for O(1) lookups
3. **Thread-Safe**: Tracker uses locks only for write operations
4. **No API Calls**: All profile information comes from catalog (already loaded)

### Backward Compatibility

1. **Existing Code**: All existing code continues to work without changes
2. **Direct Access**: Models supporting direct access use it by default
3. **No Breaking Changes**: New functionality is additive only
4. **Deprecation**: No existing APIs are deprecated

### Integration Points

1. **RetryManager**: Add profile detection and retry logic
2. **BedrockModelCatalog**: No changes needed (already provides profile IDs)
3. **ModelAccessInfo**: No changes needed (already has orthogonal flags)
4. **BedrockResponse**: Add access method metadata

### Logging Strategy

```python
# Profile requirement detected (WARNING)
logger.warning(
    f"Model '{model_id}' requires inference profile in region '{region}'. "
    f"Retrying with profile..."
)

# Profile selected (INFO)
logger.info(
    f"Using inference profile '{profile_id}' for model '{model_name}' in '{region}'"
)

# Profile retry succeeded (INFO)
logger.info(
    f"Request succeeded using inference profile for model '{model_name}' in '{region}'"
)

# Access method learned (DEBUG)
logger.debug(
    f"Learned access method '{access_method}' for model '{model_id}' in '{region}'"
)

# No profile available (WARNING)
logger.warning(
    f"Model '{model_id}' requires inference profile in '{region}' but no profile available"
)
```

## Migration Guide

### For Existing Users

**No changes required!** The profile support is completely transparent:

```python
# Existing code continues to work
manager = LLMManager(
    models=["Claude Sonnet 4.5", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)

# System automatically detects profile requirement and retries
response = manager.converse(messages=[...])

# Response indicates which access method was used
print(f"Access method: {response.access_method_used}")
```

### Checking Access Method Used

```python
# Check which access method was used
response = manager.converse(messages=[...])

if response.success:
    print(f"Model: {response.model_used}")
    print(f"Region: {response.region_used}")
    print(f"Access method: {response.access_method_used}")
    
    if response.inference_profile_used:
        print(f"Profile ID: {response.inference_profile_id}")
```

### Monitoring Profile Usage

```python
# Get access method statistics
tracker = AccessMethodTracker.get_instance()
stats = tracker.get_statistics()

print(f"Total tracked combinations: {stats['total_tracked']}")
print(f"Profile-required models: {stats['profile_required_count']}")
print(f"Direct-access models: {stats['direct_access_count']}")
```

## Dependencies

**No new external dependencies required.**

All functionality can be implemented using:
- Python standard library (`threading`, `re`, `datetime`)
- Existing project dependencies (`dataclasses`, `typing`)

## Summary

This design implements automatic inference profile support by:

1. **Detecting profile requirements** from AWS ValidationException errors
2. **Automatically selecting profiles** from catalog data using intelligent preference ordering
3. **Learning access methods** over time to optimize future requests
4. **Maintaining backward compatibility** with all existing direct access behavior
5. **Providing transparent operation** requiring no user code changes

The implementation leverages the existing `ModelAccessInfo` structure with orthogonal access flags, requiring minimal changes to the codebase while providing significant user experience improvements by eliminating unnecessary retry attempts.
