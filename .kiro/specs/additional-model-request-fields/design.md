# Design Document: Additional Model Request Fields Support

## Overview

This design extends the LLM Manager to support AWS Bedrock's `additionalModelRequestFields` parameter, enabling developers to leverage model-specific features beyond the base Converse API. The design provides both a general mechanism for arbitrary parameters and a convenient high-level API for common features like extended context windows.

### Key Design Goals

1. **Flexibility**: Support arbitrary model-specific parameters without hardcoding
2. **Usability**: Provide simple flags for common features (e.g., extended context)
3. **Resilience**: Automatically recover from parameter incompatibility errors
4. **Intelligence**: Learn and cache parameter compatibility across model/region combinations
5. **Backward Compatibility**: Maintain existing API contracts and behavior

### Design Principles

- **Fail gracefully**: When parameters aren't supported, retry without them rather than failing completely
- **Learn from failures**: Track which parameters work with which models/regions to optimize future requests
- **Explicit over implicit**: Require opt-in for new features to avoid breaking existing code
- **Separation of concerns**: Keep parameter management separate from core retry logic

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      LLM Manager                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ModelSpecificConfig                                    │ │
│  │  - enable_extended_context: bool                        │ │
│  │  - custom_fields: Dict[str, Any]                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Parameter Builder                                      │ │
│  │  - Merges enable_extended_context flag                  │ │
│  │  - Merges custom_fields                                 │ │
│  │  - Validates parameter structure                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Retry Manager (Enhanced)                               │ │
│  │  - Detects parameter compatibility errors               │ │
│  │  - Retries without incompatible parameters              │ │
│  │  - Tracks compatibility information                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Parameter Compatibility Tracker                        │ │
│  │  - Records successful parameter combinations            │ │
│  │  - Records failed parameter combinations                │ │
│  │  - Provides compatibility queries                       │ │
│  │  - Shared across instances (process-level)              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```


## Components and Interfaces

### 1. ModelSpecificConfig

A configuration class that encapsulates model-specific parameters.

```python
@dataclass
class ModelSpecificConfig:
    """Configuration for model-specific request parameters."""
    
    enable_extended_context: bool = False
    custom_fields: Optional[Dict[str, Any]] = None
    
    def to_additional_model_request_fields(
        self, 
        model_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convert configuration to additionalModelRequestFields dictionary.
        
        Args:
            model_name: Name of the model for compatibility checking
            
        Returns:
            Dictionary for additionalModelRequestFields or None
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging."""
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelSpecificConfig':
        """Deserialize from dictionary."""
        pass
```

**Design Rationale:**
- Dataclass for clean serialization and immutability
- Separate method for conversion to allow model-specific logic
- Support for both high-level flags and low-level custom fields


### 2. Parameter Builder

Internal component responsible for building the final `additionalModelRequestFields` dictionary.

```python
class ParameterBuilder:
    """Builds additionalModelRequestFields from various sources."""
    
    # Model compatibility mappings
    EXTENDED_CONTEXT_MODELS = {
        "Claude 3.5 Sonnet v2",
        "Claude Sonnet 4",
        "us.anthropic.claude-sonnet-4-20250514-v1:0"
    }
    
    EXTENDED_CONTEXT_BETA_HEADER = "context-1m-2025-08-07"
    
    def build_additional_fields(
        self,
        model_name: str,
        model_specific_config: Optional[ModelSpecificConfig] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build final additionalModelRequestFields dictionary.
        
        Priority order:
        1. Start with additional_model_request_fields (backward compatibility)
        2. Merge in model_specific_config.custom_fields
        3. Apply enable_extended_context if set
        
        Args:
            model_name: Name of the model
            model_specific_config: High-level configuration
            additional_model_request_fields: Direct fields (legacy)
            
        Returns:
            Merged additionalModelRequestFields or None
        """
        pass
    
    def _merge_anthropic_beta(
        self,
        existing_fields: Dict[str, Any],
        new_beta_values: List[str]
    ) -> Dict[str, Any]:
        """
        Merge anthropic_beta arrays without duplicates.
        
        Args:
            existing_fields: Existing additionalModelRequestFields
            new_beta_values: New beta values to add
            
        Returns:
            Merged fields with combined beta array
        """
        pass
    
    def _is_extended_context_compatible(self, model_name: str) -> bool:
        """Check if model supports extended context."""
        pass
```

**Design Rationale:**
- Centralized logic for parameter building
- Clear priority order for merging
- Model compatibility checks isolated in one place
- Special handling for anthropic_beta array merging


### 3. Parameter Compatibility Tracker

Process-level singleton that tracks which parameters work with which model/region combinations.

```python
class ParameterCompatibilityTracker:
    """
    Tracks parameter compatibility across model/region combinations.
    Implemented as a process-level singleton.
    """
    
    _instance: Optional['ParameterCompatibilityTracker'] = None
    _lock: threading.Lock = threading.Lock()
    
    def __init__(self):
        self._compatible: Dict[Tuple[str, str, str], bool] = {}
        # Key: (model_id, region, parameter_hash)
        # Value: True if compatible, False if incompatible
        
        self._parameter_hashes: Dict[str, str] = {}
        # Maps parameter dict to hash for efficient lookup
    
    @classmethod
    def get_instance(cls) -> 'ParameterCompatibilityTracker':
        """Get or create singleton instance."""
        pass
    
    def record_success(
        self,
        model_id: str,
        region: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Record successful parameter usage."""
        pass
    
    def record_failure(
        self,
        model_id: str,
        region: str,
        parameters: Dict[str, Any],
        error: Exception
    ) -> None:
        """Record parameter incompatibility."""
        pass
    
    def is_known_incompatible(
        self,
        model_id: str,
        region: str,
        parameters: Dict[str, Any]
    ) -> bool:
        """Check if combination is known to be incompatible."""
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compatibility tracking statistics."""
        pass
    
    def _hash_parameters(self, parameters: Dict[str, Any]) -> str:
        """Create stable hash of parameter dictionary."""
        pass
```

**Design Rationale:**
- Singleton pattern for process-wide sharing
- Thread-safe for concurrent access
- Hash-based lookup for efficient queries
- Separate tracking of successes and failures


### 4. Enhanced Retry Manager

Extensions to the existing RetryManager to handle parameter compatibility errors.

```python
class RetryManager:
    """Enhanced with parameter compatibility error handling."""
    
    def __init__(self, retry_config: RetryConfig):
        # Existing initialization
        self._parameter_tracker = ParameterCompatibilityTracker.get_instance()
        self._parameter_builder = ParameterBuilder()
    
    def is_parameter_compatibility_error(self, error: Exception) -> Tuple[bool, Optional[str]]:
        """
        Determine if error is due to unsupported parameters.
        
        Args:
            error: The error to evaluate
            
        Returns:
            Tuple of (is_parameter_error, parameter_name_if_identified)
        """
        pass
    
    def execute_with_retry(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        retry_targets: List[Tuple[str, str, ModelAccessInfo]],
        disabled_features: Optional[List[str]] = None,
        model_specific_config: Optional[ModelSpecificConfig] = None
    ) -> Tuple[Any, List[RequestAttempt], List[str]]:
        """
        Enhanced execute_with_retry that handles parameter compatibility.
        
        New behavior:
        1. Check if model/region/parameter combination is known incompatible
        2. Skip known incompatible combinations
        3. On parameter error, retry without additionalModelRequestFields
        4. Record compatibility information for future use
        """
        pass
    
    def _retry_without_parameters(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        model: str,
        region: str,
        access_info: ModelAccessInfo
    ) -> Tuple[Any, bool, Optional[str]]:
        """
        Retry operation without additionalModelRequestFields.
        
        Returns:
            Tuple of (result, success, warning_message)
        """
        pass
```

**Design Rationale:**
- Extends existing retry logic rather than replacing it
- Integrates with compatibility tracker for learning
- Provides fallback mechanism for parameter errors
- Maintains separation from content compatibility errors


### 5. LLM Manager API Extensions

Extensions to LLMManager.converse() and converse_stream() methods.

```python
class LLMManager:
    """Enhanced with model-specific parameter support."""
    
    def __init__(
        self,
        models: List[str],
        regions: List[str],
        # ... existing parameters ...
        model_specific_config: Optional[ModelSpecificConfig] = None
    ):
        """
        Initialize LLM Manager.
        
        New parameter:
            model_specific_config: Default configuration for model-specific parameters
        """
        self._default_model_specific_config = model_specific_config
        self._parameter_builder = ParameterBuilder()
    
    def converse(
        self,
        messages: List[Dict[str, Any]],
        # ... existing parameters ...
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
        model_specific_config: Optional[ModelSpecificConfig] = None,
        enable_extended_context: bool = False
    ) -> BedrockResponse:
        """
        Enhanced converse with model-specific parameter support.
        
        New parameters:
            model_specific_config: Per-request configuration (overrides default)
            enable_extended_context: Convenience flag for extended context
        
        Parameter priority:
        1. enable_extended_context flag (if True)
        2. model_specific_config (if provided)
        3. additional_model_request_fields (backward compatibility)
        4. Default model_specific_config from __init__
        """
        pass
```

**Design Rationale:**
- Backward compatible: existing code continues to work
- Multiple ways to specify parameters: flag, config object, or direct dict
- Clear priority order for parameter sources
- Per-request override of default configuration


## Data Models

### Extended BedrockResponse

```python
@dataclass
class BedrockResponse:
    """Enhanced with parameter compatibility information."""
    
    # Existing fields...
    
    # New fields
    parameters_removed: Optional[List[str]] = None
    # List of parameter names that were removed due to incompatibility
    
    original_additional_fields: Optional[Dict[str, Any]] = None
    # Original additionalModelRequestFields before any removal
    
    final_additional_fields: Optional[Dict[str, Any]] = None
    # Final additionalModelRequestFields actually used
    
    def had_parameters_removed(self) -> bool:
        """Check if any parameters were removed during retry."""
        return bool(self.parameters_removed)
    
    def get_parameter_warnings(self) -> List[str]:
        """Get warnings related to parameter compatibility."""
        pass
```

### Extended ParallelResponse

```python
@dataclass
class ParallelResponse:
    """Enhanced with parameter compatibility tracking."""
    
    # Existing fields...
    
    def get_requests_with_removed_parameters(self) -> Dict[str, List[str]]:
        """
        Get mapping of request IDs to removed parameters.
        
        Returns:
            Dict mapping request_id to list of removed parameter names
        """
        pass
    
    def get_parameter_compatibility_summary(self) -> Dict[str, Any]:
        """
        Get summary of parameter compatibility across all requests.
        
        Returns:
            Summary including:
            - Total requests with parameters
            - Requests with removed parameters
            - Most common incompatible parameters
        """
        pass
```


## Error Handling

### Error Classification

The system distinguishes between three types of errors:

1. **Parameter Compatibility Errors**: Parameters not supported by model/region
   - Error patterns: "unsupported parameter", "invalid field", "unknown parameter"
   - Recovery: Retry without additionalModelRequestFields
   - Tracking: Record incompatibility for future optimization

2. **Content Compatibility Errors**: Content type not supported by model
   - Error patterns: "doesn't support video", "image not supported"
   - Recovery: Try different model (existing behavior)
   - No parameter removal

3. **Other Errors**: Throttling, access, network, etc.
   - Recovery: Existing retry logic
   - No parameter-specific handling

### Error Recovery Flow

```
Request with additionalModelRequestFields
    │
    ├─> Check compatibility tracker
    │   └─> Skip if known incompatible
    │
    ├─> Execute request
    │
    ├─> Success?
    │   ├─> Yes: Record success, return
    │   └─> No: Classify error
    │
    ├─> Parameter compatibility error?
    │   ├─> Yes:
    │   │   ├─> Log warning
    │   │   ├─> Record incompatibility
    │   │   ├─> Retry without parameters
    │   │   └─> Add warning to response
    │   └─> No: Use existing retry logic
    │
    └─> Return result or raise error
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Parameter Pass-Through Preservation

*For any* valid additionalModelRequestFields dictionary (including nested structures and multiple key-value pairs), when passed to the LLM_Manager, the complete structure SHALL be preserved and passed to the Bedrock Converse API without modification.

**Validates: Requirements 1.1, 1.2, 1.5**

### Property 2: Parameter Coexistence

*For any* valid inferenceConfig and additionalModelRequestFields, when both are provided to the LLM_Manager, both parameters SHALL be included in the API call without interference.

**Validates: Requirements 1.4**

### Property 3: Extended Context Beta Merging

*For any* existing additionalModelRequestFields containing an anthropic_beta array, when enable_extended_context=True is set, the system SHALL merge the beta arrays without creating duplicates of the context-1m-2025-08-07 value.

**Validates: Requirements 2.4**

### Property 4: ModelSpecificConfig Extraction

*For any* ModelSpecificConfig instance provided to converse(), the LLM_Manager SHALL correctly extract and apply the additionalModelRequestFields, including both enable_extended_context transformations and custom_fields.

**Validates: Requirements 3.2, 3.4**

### Property 5: Configuration Serialization Round-Trip

*For any* valid ModelSpecificConfig instance, serializing to dictionary and then deserializing SHALL produce an equivalent configuration object.

**Validates: Requirements 3.5**

### Property 6: Parameter Compatibility Error Classification

*For any* AWS error response, when the error message contains patterns indicating unsupported parameters (e.g., "unsupported parameter", "invalid field"), the Retry_Manager SHALL correctly classify it as a parameter compatibility error.

**Validates: Requirements 4.1**

### Property 7: Retry Warning Logging

*For any* request that requires retry without additionalModelRequestFields, the system SHALL log a warning message that includes the names of the removed parameters.

**Validates: Requirements 4.3**

### Property 8: Response Warning Inclusion

*For any* request where parameters are removed due to incompatibility, the BedrockResponse SHALL include this information in the warnings list.

**Validates: Requirements 4.5**

### Property 9: Compatibility Tracking

*For any* request that succeeds or fails with specific additionalModelRequestFields, the system SHALL record the model/region/parameter combination in the compatibility tracker with the appropriate success or failure status.

**Validates: Requirements 5.1, 5.2**

### Property 10: Compatibility-Based Retry Optimization

*For any* retry attempt, when compatibility information indicates a model/region/parameter combination is known to be incompatible, the system SHALL skip that combination during retry target generation.

**Validates: Requirements 5.4**

### Property 11: Parallel Request Field Independence

*For any* set of parallel requests with different additionalModelRequestFields, the Parallel_LLM_Manager SHALL apply the correct fields to each request independently without cross-contamination.

**Validates: Requirements 6.1, 6.2**

### Property 12: Parallel Request Model-Specific Filtering

*For any* parallel requests targeting different models, the system SHALL apply model-specific parameter filtering independently for each request based on the target model's capabilities.

**Validates: Requirements 6.4**

### Property 13: Parallel Response Parameter Metadata

*For any* parallel execution where some requests have parameters removed, the ParallelResponse SHALL include complete information about which requests had which parameters removed.

**Validates: Requirements 6.5**

### Property 14: Backward Compatibility Preservation

*For any* request that does not provide model-specific parameters (no additionalModelRequestFields, no ModelSpecificConfig, enable_extended_context=False), the system SHALL behave identically to the implementation before this feature was added.

**Validates: Requirements 8.1, 8.2, 8.3, 8.5**

### Property 15: Input Validation

*For any* invalid input where additionalModelRequestFields is not a dictionary or enable_extended_context is not a boolean, the system SHALL raise a RequestValidationError with a descriptive message indicating the specific validation failure.

**Validates: Requirements 9.1, 9.2**

### Property 16: Error Message Parameter Inclusion

*For any* error where all retry attempts fail due to parameter incompatibility, the final error message SHALL include the names of the incompatible parameters.

**Validates: Requirements 9.4**

### Property 17: Error Type Distinction in Logs

*For any* error, the system SHALL produce log messages that clearly distinguish between parameter incompatibility errors and other validation errors through distinct message patterns or log levels.

**Validates: Requirements 9.5**

### Property 18: Logging Level Compliance

*For any* request with additionalModelRequestFields, the system SHALL log parameter names at DEBUG level; for any parameter removal, log at WARNING level; and for extended context enablement, log at INFO level.

**Validates: Requirements 10.1, 10.2, 10.3**

### Property 19: Response Metadata Completeness

*For any* request where parameters are removed during retry, the BedrockResponse SHALL include metadata indicating this occurred, and retry statistics SHALL include parameter compatibility information.

**Validates: Requirements 10.4, 10.5**


## Testing Strategy

### Dual Testing Approach

The implementation will use both unit tests and property-based tests:

- **Unit tests**: Verify specific examples, edge cases, and integration scenarios
- **Property tests**: Verify universal properties across randomized inputs

### Property-Based Testing Configuration

- **Framework**: Hypothesis (Python property-based testing library)
- **Iterations**: Minimum 100 iterations per property test
- **Tagging**: Each property test references its design document property number

### Test Categories

#### 1. Parameter Building Tests

**Unit Tests:**
- Extended context with Claude Sonnet 4 (Requirement 2.1)
- Extended context with incompatible model (Requirement 2.2)
- Extended context disabled (Requirement 2.3)
- Empty/None additionalModelRequestFields (Requirement 1.3)
- Default enable_extended_context value (Requirement 8.4)
- Extended context logging (Requirement 10.3)

**Property Tests:**
- Property 1: Parameter pass-through preservation
- Property 2: Parameter coexistence
- Property 3: Extended context beta merging
- Property 4: ModelSpecificConfig extraction
- Property 5: Configuration serialization round-trip

#### 2. Error Handling and Retry Tests

**Unit Tests:**
- Parameter compatibility error with retry (Requirement 4.2)
- Multiple model/region retry order (Requirement 4.4)
- Extended context with unsupported region (Requirement 2.5)
- Cross-instance compatibility persistence (Requirement 5.5)

**Property Tests:**
- Property 6: Parameter compatibility error classification
- Property 7: Retry warning logging
- Property 8: Response warning inclusion
- Property 9: Compatibility tracking
- Property 10: Compatibility-based retry optimization

#### 3. Parallel Processing Tests

**Unit Tests:**
- Parallel request with parameter incompatibility (Requirement 6.3)

**Property Tests:**
- Property 11: Parallel request field independence
- Property 12: Parallel request model-specific filtering
- Property 13: Parallel response parameter metadata

#### 4. Backward Compatibility Tests

**Unit Tests:**
- Existing additionalModelRequestFields usage (Requirement 8.2)
- Plain dictionary without ModelSpecificConfig (Requirement 8.3)

**Property Tests:**
- Property 14: Backward compatibility preservation

#### 5. Validation and Error Message Tests

**Property Tests:**
- Property 15: Input validation
- Property 16: Error message parameter inclusion
- Property 17: Error type distinction in logs
- Property 18: Logging level compliance
- Property 19: Response metadata completeness

#### 6. Integration Tests

**Integration tests** (require actual AWS Bedrock access):
- Send supported parameters to compatible models (Requirement 12.1)
- Send unsupported parameters to incompatible models (Requirement 12.2)
- Verify errors without retry configuration (Requirement 12.3)
- Extended context with Claude Sonnet 4 (Requirement 12.4)
- Extended context with incompatible models (Requirement 12.5)

### Test Data Generation

For property-based tests, we'll use Hypothesis strategies:

```python
from hypothesis import strategies as st

# Strategy for valid additionalModelRequestFields
additional_fields_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50),
    values=st.recursive(
        st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
        lambda children: st.lists(children) | st.dictionaries(st.text(), children)
    )
)

# Strategy for ModelSpecificConfig
model_config_strategy = st.builds(
    ModelSpecificConfig,
    enable_extended_context=st.booleans(),
    custom_fields=st.one_of(st.none(), additional_fields_strategy)
)

# Strategy for model names
model_name_strategy = st.sampled_from([
    "Claude 3 Haiku",
    "Claude 3 Sonnet",
    "Claude 3.5 Sonnet v2",
    "Claude Sonnet 4",
    "Claude 3 Opus",
    "Titan Text Express",
    "Llama 3.1 70B"
])
```


## Implementation Notes

### Extended Context Window Details

Based on AWS documentation, the extended context window feature:

- **Beta header**: `context-1m-2025-08-07`
- **Compatible models**: Claude Sonnet 4 (us.anthropic.claude-sonnet-4-20250514-v1:0)
- **Token limit**: Up to 1 million tokens
- **Pricing**: Separate pricing applies (see AWS Bedrock Pricing page)
- **Service quotas**: Separate quotas apply
- **Status**: Beta service as defined in AWS Service Terms

### Known Model-Specific Parameters

From AWS documentation research, common additionalModelRequestFields include:

**Anthropic Claude:**
- `anthropic_beta`: Array of beta feature headers
  - `context-1m-2025-08-07`: 1M token context
  - `computer-use-2025-01-24`: Computer use API
  - `token-efficient-tools-2025-02-19`: Token-efficient tools
  - `interleaved-thinking-2025-05-14`: Interleaved thinking
  - `output-128k-2025-02-19`: Extended output tokens
  - `context-management-2025-06-27`: Context management
  - `effort-2025-11-24`: Effort parameter
  - `tool-search-tool-2025-10-19`: Tool search
  - `tool-examples-2025-10-29`: Tool use examples

**Other Models:**
- Additional parameters vary by model family
- Refer to AWS Bedrock model parameters documentation

### Compatibility Detection Heuristics

Error messages indicating parameter incompatibility:

```python
PARAMETER_INCOMPATIBILITY_PATTERNS = [
    "unsupported parameter",
    "invalid field",
    "unknown parameter",
    "parameter not supported",
    "unrecognized field",
    "invalid request field",
    "does not support parameter",
    "parameter is not valid for this model"
]
```

### Performance Considerations

1. **Compatibility Tracker**: In-memory cache, no persistence across process restarts
2. **Hash Computation**: Use stable JSON serialization for parameter hashing
3. **Thread Safety**: Use threading.Lock for tracker access
4. **Memory**: Bounded cache size (e.g., max 1000 entries) with LRU eviction

### Migration Path

For existing users:

1. **Phase 1**: No changes required, existing code works as-is
2. **Phase 2**: Opt-in to new features via enable_extended_context flag
3. **Phase 3**: Migrate to ModelSpecificConfig for better structure
4. **Phase 4**: Leverage compatibility tracking for optimization


## Example Usage

### Example 1: Simple Extended Context

```python
from bestehorn_llmmanager import LLMManager, create_user_message

# Initialize manager
manager = LLMManager(
    models=["Claude Sonnet 4"],
    regions=["us-east-1"]
)

# Create a very large message (approaching 1M tokens)
large_text = "Very long document content... " * 100_000

message = create_user_message()\
    .add_text(f"Summarize this document: {large_text}")\
    .build()

# Use extended context with simple flag
response = manager.converse(
    messages=[message],
    enable_extended_context=True,
    inference_config={"maxTokens": 512}
)

print(f"Input tokens: {response.get_usage()['inputTokens']:,}")
print(f"Output tokens: {response.get_usage()['outputTokens']:,}")
```

### Example 2: ModelSpecificConfig

```python
from bestehorn_llmmanager import LLMManager, ModelSpecificConfig

# Create reusable configuration
config = ModelSpecificConfig(
    enable_extended_context=True,
    custom_fields={
        "anthropic_beta": ["token-efficient-tools-2025-02-19"]
    }
)

# Initialize manager with default config
manager = LLMManager(
    models=["Claude Sonnet 4"],
    regions=["us-east-1"],
    model_specific_config=config
)

# All requests use the config by default
response = manager.converse(messages=[message])
```

### Example 3: Custom Parameters

```python
# Pass custom model-specific parameters directly
response = manager.converse(
    messages=[message],
    additional_model_request_fields={
        "anthropic_beta": [
            "context-1m-2025-08-07",
            "interleaved-thinking-2025-05-14"
        ]
    }
)
```

### Example 4: Handling Incompatibility

```python
# Request with parameters that might not be supported everywhere
manager = LLMManager(
    models=["Claude Sonnet 4", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)

response = manager.converse(
    messages=[message],
    enable_extended_context=True
)

# Check if parameters were removed
if response.had_parameters_removed():
    print(f"Parameters removed: {response.parameters_removed}")
    print(f"Warnings: {response.get_parameter_warnings()}")
    print(f"Model used: {response.model_used}")
```

### Example 5: Parallel Processing

```python
from bestehorn_llmmanager import ParallelLLMManager, BedrockConverseRequest

parallel_manager = ParallelLLMManager(
    models=["Claude Sonnet 4"],
    regions=["us-east-1", "us-west-2"]
)

# Create requests with different parameters
requests = [
    BedrockConverseRequest(
        request_id="extended-context",
        messages=[large_message],
        additional_model_request_fields={
            "anthropic_beta": ["context-1m-2025-08-07"]
        }
    ),
    BedrockConverseRequest(
        request_id="standard",
        messages=[standard_message]
    )
]

parallel_response = parallel_manager.converse_parallel(requests=requests)

# Check parameter compatibility summary
summary = parallel_response.get_parameter_compatibility_summary()
print(f"Requests with removed parameters: {summary['requests_with_removed_parameters']}")
```

### Example 6: Querying Compatibility

```python
from bestehorn_llmmanager.bedrock.models.parameter_compatibility import (
    ParameterCompatibilityTracker
)

# Get compatibility tracker
tracker = ParameterCompatibilityTracker.get_instance()

# Check if combination is known to be incompatible
is_incompatible = tracker.is_known_incompatible(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region="us-east-1",
    parameters={"anthropic_beta": ["context-1m-2025-08-07"]}
)

# Get statistics
stats = tracker.get_statistics()
print(f"Total tracked combinations: {stats['total_combinations']}")
print(f"Compatible: {stats['compatible_count']}")
print(f"Incompatible: {stats['incompatible_count']}")
```

