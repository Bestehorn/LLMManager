# Design Document

## Overview

This design addresses two issues:

1. **Notebook Bug**: The ExtendedContext_Demo.ipynb notebook uses incorrect key names (camelCase) when accessing token usage data, causing it to display 0 tokens even when the API returns valid usage data.

2. **API Enhancement**: Add individual accessor methods to `BedrockResponse` and `StreamingResponse` to provide better encapsulation and protect client code from internal dictionary structure changes.

The solution maintains full backward compatibility with existing code while providing a cleaner, more maintainable API for accessing token usage information.

## Architecture

### Current Architecture

```
BedrockResponse
├── get_usage() -> Dict[str, int]  # Returns {"input_tokens": X, "output_tokens": Y, ...}
└── get_cached_tokens_info() -> Dict[str, int]  # Returns cache-specific info

Client Code (Notebook)
└── usage = response.get_usage()
    └── usage.get('inputTokens', 0)  # ❌ WRONG KEY - Returns 0
```

### Proposed Architecture

```
BedrockResponse
├── get_usage() -> Dict[str, int]  # Unchanged - backward compatible
├── get_input_tokens() -> int  # NEW - Direct accessor
├── get_output_tokens() -> int  # NEW - Direct accessor
├── get_total_tokens() -> int  # NEW - Direct accessor
├── get_cache_read_tokens() -> int  # NEW - Direct accessor
├── get_cache_write_tokens() -> int  # NEW - Direct accessor
└── get_cached_tokens_info() -> Dict[str, int]  # Unchanged

Client Code (Notebook) - Fixed
└── usage = response.get_usage()
    └── usage.get('input_tokens', 0)  # ✅ CORRECT KEY

Client Code (New Pattern) - Recommended
└── input_tokens = response.get_input_tokens()  # ✅ BETTER - No dict access
```

## Components and Interfaces

### Component 1: BedrockResponse Token Accessors

**Location**: `src/bestehorn_llmmanager/bedrock/models/bedrock_response.py`

**New Methods**:

```python
def get_input_tokens(self) -> int:
    """
    Get the number of input tokens used in the request.
    
    Returns:
        Number of input tokens, 0 if not available
    """
    usage = self.get_usage()
    return usage.get("input_tokens", 0) if usage else 0

def get_output_tokens(self) -> int:
    """
    Get the number of output tokens generated in the response.
    
    Returns:
        Number of output tokens, 0 if not available
    """
    usage = self.get_usage()
    return usage.get("output_tokens", 0) if usage else 0

def get_total_tokens(self) -> int:
    """
    Get the total number of tokens (input + output) used.
    
    Returns:
        Total number of tokens, 0 if not available
    """
    usage = self.get_usage()
    return usage.get("total_tokens", 0) if usage else 0

def get_cache_read_tokens(self) -> int:
    """
    Get the number of tokens read from prompt cache.
    
    Returns:
        Number of cache read tokens, 0 if not available
    """
    usage = self.get_usage()
    return usage.get("cache_read_tokens", 0) if usage else 0

def get_cache_write_tokens(self) -> int:
    """
    Get the number of tokens written to prompt cache.
    
    Returns:
        Number of cache write tokens, 0 if not available
    """
    usage = self.get_usage()
    return usage.get("cache_write_tokens", 0) if usage else 0
```

**Design Rationale**:
- All methods return `int` (not `Optional[int]`) with default value 0 for consistency with existing patterns
- Methods delegate to `get_usage()` to avoid code duplication
- Methods handle None case gracefully (when `get_usage()` returns None)
- Method names follow existing naming convention (`get_*`)

### Component 2: StreamingResponse Token Accessors

**Location**: `src/bestehorn_llmmanager/bedrock/models/bedrock_response.py`

**New Methods**: Same interface as BedrockResponse

The `StreamingResponse` class already has a `get_usage()` method that returns the same dictionary structure. We'll add the same accessor methods for consistency.

### Component 3: Notebook Display Function Fix

**Location**: `notebooks/ExtendedContext_Demo.ipynb`

**Current Code** (Broken):
```python
def display_response(response, title="Response"):
    # ...
    usage = response.get_usage()
    if usage:
        print(f"\n📊 Token Usage:")
        print(f"   Input Tokens: {usage.get('inputTokens', 0):,}")  # ❌ Wrong key
        print(f"   Output Tokens: {usage.get('outputTokens', 0):,}")  # ❌ Wrong key
        print(f"   Total Tokens: {usage.get('totalTokens', 0):,}")  # ❌ Wrong key
```

**Fixed Code** (Option 1 - Minimal Change):
```python
def display_response(response, title="Response"):
    # ...
    usage = response.get_usage()
    if usage:
        print(f"\n📊 Token Usage:")
        print(f"   Input Tokens: {usage.get('input_tokens', 0):,}")  # ✅ Correct key
        print(f"   Output Tokens: {usage.get('output_tokens', 0):,}")  # ✅ Correct key
        print(f"   Total Tokens: {usage.get('total_tokens', 0):,}")  # ✅ Correct key
```

**Fixed Code** (Option 2 - Recommended with New Accessors):
```python
def display_response(response, title="Response"):
    # ...
    # Use new accessor methods - cleaner and more maintainable
    input_tokens = response.get_input_tokens()
    output_tokens = response.get_output_tokens()
    total_tokens = response.get_total_tokens()
    
    if total_tokens > 0:  # Only show if we have token data
        print(f"\n📊 Token Usage:")
        print(f"   Input Tokens: {input_tokens:,}")
        print(f"   Output Tokens: {output_tokens:,}")
        print(f"   Total Tokens: {total_tokens:,}")
```

**Design Decision**: We'll implement Option 2 (using new accessor methods) as it demonstrates the recommended pattern and provides better encapsulation.

### Component 4: Other Notebook Fixes

**Location**: `notebooks/ExtendedContext_Demo.ipynb` - Example 3

**Current Code** (Broken):
```python
usage = response.get_usage()
results.append({
    "label": label,
    "estimated": estimated_tokens,
    "actual_input": usage.get('inputTokens', 0),  # ❌ Wrong key
    "output": usage.get('outputTokens', 0),  # ❌ Wrong key
    "total": usage.get('totalTokens', 0)  # ❌ Wrong key
})
```

**Fixed Code**:
```python
results.append({
    "label": label,
    "estimated": estimated_tokens,
    "actual_input": response.get_input_tokens(),  # ✅ Use accessor
    "output": response.get_output_tokens(),  # ✅ Use accessor
    "total": response.get_total_tokens()  # ✅ Use accessor
})
```

## Data Models

### Token Usage Dictionary Structure (Unchanged)

The `get_usage()` method continues to return:

```python
{
    "input_tokens": int,      # Number of input tokens
    "output_tokens": int,     # Number of output tokens
    "total_tokens": int,      # Total tokens (input + output)
    "cache_read_tokens": int, # Tokens read from cache
    "cache_write_tokens": int # Tokens written to cache
}
```

This structure is maintained for backward compatibility.

### Accessor Method Return Types

All new accessor methods return `int` with a default value of 0:

```python
get_input_tokens() -> int       # Returns 0 if no data
get_output_tokens() -> int      # Returns 0 if no data
get_total_tokens() -> int       # Returns 0 if no data
get_cache_read_tokens() -> int  # Returns 0 if no data
get_cache_write_tokens() -> int # Returns 0 if no data
```

**Design Rationale**: Returning 0 instead of None is consistent with:
- The existing `get_usage()` behavior (returns 0 for missing keys)
- Common patterns in the codebase
- Easier to use in arithmetic operations without None checks

## Error Handling

### Graceful Degradation

All accessor methods handle missing data gracefully:

1. **No response data**: Returns 0
2. **Unsuccessful response**: Returns 0
3. **Missing usage field**: Returns 0
4. **Missing specific token field**: Returns 0

### No Exceptions

The accessor methods will NOT raise exceptions for missing data. This is consistent with the existing `get_usage()` behavior and makes the API easier to use.

### Example Error Handling

```python
# All of these return 0 without raising exceptions
response_failed = BedrockResponse(success=False)
tokens = response_failed.get_input_tokens()  # Returns 0

response_no_data = BedrockResponse(success=True, response_data=None)
tokens = response_no_data.get_input_tokens()  # Returns 0

response_no_usage = BedrockResponse(success=True, response_data={})
tokens = response_no_usage.get_input_tokens()  # Returns 0
```

## Testing Strategy

### Unit Tests

**Test File**: `test/bestehorn_llmmanager/bedrock/models/test_bedrock_response.py`

**Test Cases**:

1. **Test accessor methods with valid data**
   - Create BedrockResponse with complete usage data
   - Verify each accessor returns correct value
   - Example: `assert response.get_input_tokens() == 100`

2. **Test accessor methods with missing data**
   - Create BedrockResponse with no usage data
   - Verify each accessor returns 0
   - Example: `assert response.get_input_tokens() == 0`

3. **Test accessor methods with unsuccessful response**
   - Create BedrockResponse with success=False
   - Verify each accessor returns 0
   - Example: `assert failed_response.get_input_tokens() == 0`

4. **Test accessor methods with partial usage data**
   - Create BedrockResponse with some fields missing
   - Verify accessors return 0 for missing fields
   - Example: Usage dict has input_tokens but not cache_read_tokens

5. **Test backward compatibility of get_usage()**
   - Verify get_usage() still returns dictionary
   - Verify dictionary has snake_case keys
   - Verify existing code patterns still work

6. **Test StreamingResponse accessor methods**
   - Same test cases as BedrockResponse
   - Verify consistency between the two classes

### Integration Tests

**Test File**: `test/integration/test_integration_llm_manager.py`

**Test Cases**:

1. **Test accessor methods with real API response**
   - Make actual Bedrock API call
   - Verify accessor methods return non-zero values
   - Compare accessor values with get_usage() dictionary values
   - Example: `assert response.get_input_tokens() == response.get_usage()['input_tokens']`

2. **Test notebook display function**
   - Run notebook cells programmatically
   - Verify token usage displays correctly
   - Verify no "0" values for successful requests

### Property-Based Tests

Property-based tests will be defined after prework analysis in the next section.


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Accessor Methods Return Values Matching get_usage()

*For any* BedrockResponse with valid usage data, calling an accessor method (get_input_tokens(), get_output_tokens(), get_total_tokens()) should return the same value as accessing the corresponding key in the get_usage() dictionary.

**Validates: Requirements 2.1, 2.2, 2.3**

**Rationale**: This property ensures that the new accessor methods are consistent with the existing get_usage() API. It validates that we're not introducing any discrepancies between the two access patterns.

### Property 2: Accessor Methods Return Zero for Missing Data

*For any* BedrockResponse without valid usage data (unsuccessful response, missing response_data, or missing usage field), all token accessor methods should return 0.

**Validates: Requirements 2.4, 2.5, 3.3, 5.2**

**Rationale**: This property ensures graceful error handling across all accessor methods. It validates that the API is safe to use without explicit None checks and handles all edge cases consistently.

### Property 3: Cache Accessor Methods Return Correct Values

*For any* BedrockResponse with cache usage data, calling get_cache_read_tokens() or get_cache_write_tokens() should return the same value as accessing the corresponding key in the get_usage() dictionary.

**Validates: Requirements 3.1, 3.2**

**Rationale**: This property ensures cache-specific accessors work correctly and consistently with the main usage dictionary.

### Property 4: get_usage() Maintains Backward Compatible Structure

*For any* BedrockResponse, calling get_usage() should return either None or a dictionary with snake_case keys ('input_tokens', 'output_tokens', 'total_tokens', 'cache_read_tokens', 'cache_write_tokens').

**Validates: Requirements 4.1, 4.2, 4.4**

**Rationale**: This property ensures backward compatibility. Existing code that accesses usage data through the dictionary should continue to work without modification.

### Property 5: Accessor Methods Delegate to get_usage()

*For any* BedrockResponse, the value returned by an accessor method should be derivable from the get_usage() dictionary, ensuring no independent data sources.

**Validates: Requirements 5.4**

**Rationale**: This property ensures implementation consistency. By delegating to get_usage(), we avoid code duplication and ensure all access patterns use the same underlying data source.

### Property 6: Total Tokens Equals Input Plus Output

*For any* BedrockResponse with valid usage data, get_total_tokens() should equal get_input_tokens() plus get_output_tokens().

**Validates: Requirements 2.3** (additional validation)

**Rationale**: This is an invariant property that validates the mathematical relationship between token counts. It helps catch data corruption or calculation errors.

