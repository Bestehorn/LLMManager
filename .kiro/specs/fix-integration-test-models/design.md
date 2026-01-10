# Design Document: User-Friendly Model Name Resolution

## Overview

This design adds a model name alias system to BedrockModelCatalog that provides user-friendly model names and robust name resolution. The system will generate memorable aliases (e.g., "Claude 3 Haiku") for API-based model names (e.g., "Claude Haiku 4 5 20251001") and support flexible name matching to handle variations in spacing, punctuation, and version formats.

The design maintains backward compatibility with UnifiedModelManager names while providing a seamless migration path for existing code and tests.

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   BedrockModelCatalog                       │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              ModelNameResolver                        │ │
│  │  - Alias generation                                   │ │
│  │  - Name normalization                                 │ │
│  │  - Fuzzy matching                                     │ │
│  │  - Legacy name mapping                                │ │
│  └───────────────────────────────────────────────────────┘ │
│                          ↓                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              UnifiedCatalog                           │ │
│  │  - models: Dict[str, UnifiedModelInfo]               │ │
│  │  - name_index: Dict[str, str]  (NEW)                 │ │
│  │  - normalized_index: Dict[str, List[str]]  (NEW)     │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Non-Invasive**: Add alias system without modifying existing catalog structure
2. **Lazy Initialization**: Build alias indexes on first query to minimize startup cost
3. **Multiple Indexes**: Maintain separate indexes for exact matches, normalized matches, and fuzzy matches
4. **Backward Compatible**: Support all UnifiedModelManager names through legacy mapping
5. **Extensible**: Design allows adding new alias generation strategies

## Components and Interfaces

### 1. ModelNameResolver

**Purpose**: Central component for model name resolution and alias generation.

**Location**: `src/bestehorn_llmmanager/bedrock/catalog/name_resolver.py`

**Interface**:
```python
class ModelNameResolver:
    """
    Resolves user-provided model names to canonical model names.
    
    Supports:
    - Exact matches (API names)
    - Friendly aliases (generated)
    - Legacy UnifiedModelManager names
    - Normalized matching (spacing/punctuation variations)
    - Fuzzy matching (partial names)
    """
    
    def __init__(self, catalog: UnifiedCatalog) -> None:
        """Initialize resolver with catalog data."""
        
    def resolve_name(
        self,
        user_name: str,
        strict: bool = False
    ) -> Optional[str]:
        """
        Resolve user-provided name to canonical model name.
        
        Args:
            user_name: Name provided by user
            strict: If True, only exact/alias matches (no fuzzy)
            
        Returns:
            Canonical model name if found, None otherwise
        """
        
    def get_suggestions(
        self,
        user_name: str,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Get suggested model names for failed resolution.
        
        Args:
            user_name: Name that failed to resolve
            max_suggestions: Maximum suggestions to return
            
        Returns:
            List of suggested model names
        """
        
    def generate_aliases(
        self,
        model_info: UnifiedModelInfo
    ) -> List[str]:
        """
        Generate friendly aliases for a model.
        
        Args:
            model_info: Model information
            
        Returns:
            List of friendly alias names
        """
```

### 2. Alias Generation Strategies

**Purpose**: Generate user-friendly aliases from API model names.

**Strategies**:

#### Strategy 1: Claude Models
- **Input**: "Claude Haiku 4 5 20251001"
- **Aliases**:
  - "Claude 4.5 Haiku"
  - "Claude Haiku 4.5"
  - "Claude 4 Haiku" (major version only)

#### Strategy 2: Versioned Models
- **Input**: "Llama 3 8B Instruct"
- **Aliases**:
  - "Llama 3 8B Instruct" (already friendly)
  - "Llama3 8B Instruct" (no space)

#### Strategy 3: Provider-Prefixed Models
- **Input**: "APAC Anthropic Claude 3 Haiku"
- **Aliases**:
  - "APAC Claude 3 Haiku" (short prefix)
  - "Claude 3 Haiku" (no prefix)

#### Strategy 4: Legacy Mapping
- **Hardcoded mappings** for known UnifiedModelManager names:
  - "Claude 3 Haiku" → "anthropic.claude-3-haiku-20240307-v1:0"
  - "Titan Text G1 - Lite" → "amazon.titan-tg1-large"
  - etc.

### 3. Name Normalization

**Purpose**: Convert names to normalized form for flexible matching.

**Normalization Rules**:
1. Convert to lowercase
2. Remove special characters (-, _, .)
3. Collapse multiple spaces to single space
4. Trim whitespace
5. Normalize version numbers ("4.5" → "45", "4 5" → "45")

**Examples**:
- "Claude-3-Haiku" → "claude 3 haiku"
- "Claude  3  Haiku" → "claude 3 haiku"
- "Claude 3.5 Sonnet" → "claude 35 sonnet"

### 4. Index Structures

**Purpose**: Fast lookup of models by various name formats.

**Indexes** (added to UnifiedCatalog):

```python
@dataclass
class UnifiedCatalog:
    models: Dict[str, UnifiedModelInfo]  # Existing
    metadata: CatalogMetadata  # Existing
    
    # NEW: Lazy-initialized indexes
    _name_index: Optional[Dict[str, str]] = None
    _normalized_index: Optional[Dict[str, List[str]]] = None
    _legacy_mapping: Optional[Dict[str, str]] = None
```

**Index Types**:

1. **Name Index** (`_name_index`):
   - Maps: alias → canonical_name
   - Example: {"claude 3 haiku": "Claude Haiku 4 5 20251001"}
   - Used for: Exact alias lookups

2. **Normalized Index** (`_normalized_index`):
   - Maps: normalized_name → [canonical_names]
   - Example: {"claude3haiku": ["Claude Haiku 4 5 20251001", "Claude 3 Haiku"]}
   - Used for: Flexible matching with spacing/punctuation variations

3. **Legacy Mapping** (`_legacy_mapping`):
   - Maps: unified_manager_name → catalog_name
   - Example: {"Claude 3 Haiku": "Claude Haiku 4 5 20251001"}
   - Used for: Backward compatibility

## Data Models

### ModelNameMatch

**Purpose**: Represent a successful name resolution with metadata.

```python
@dataclass
class ModelNameMatch:
    """Result of model name resolution."""
    
    canonical_name: str  # The actual model name in catalog
    match_type: MatchType  # How the match was found
    confidence: float  # Match confidence (0.0-1.0)
    user_input: str  # Original user input
    
    
class MatchType(Enum):
    """Type of name match."""
    EXACT = "exact"  # Exact match to canonical name
    ALIAS = "alias"  # Matched via generated alias
    LEGACY = "legacy"  # Matched via legacy mapping
    NORMALIZED = "normalized"  # Matched via normalization
    FUZZY = "fuzzy"  # Matched via fuzzy search
```

### AliasGenerationConfig

**Purpose**: Configure alias generation behavior.

```python
@dataclass
class AliasGenerationConfig:
    """Configuration for alias generation."""
    
    generate_version_variants: bool = True  # "4.5" and "4"
    generate_no_prefix_variants: bool = True  # Remove region prefixes
    generate_spacing_variants: bool = True  # "Claude3" and "Claude 3"
    include_legacy_mappings: bool = True  # Include UnifiedModelManager names
    max_aliases_per_model: int = 10  # Limit aliases to prevent explosion
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Alias Resolution Consistency
*For any* model in the catalog, if an alias is generated for that model, then resolving that alias must return the original model's canonical name.

**Validates: Requirements 1.2, 1.3**

### Property 2: Normalization Idempotence
*For any* model name, normalizing it multiple times must produce the same result as normalizing it once.

**Validates: Requirements 2.1**

### Property 3: Legacy Name Backward Compatibility
*For any* model name that existed in UnifiedModelManager, if that model still exists in BedrockModelCatalog (possibly under a different name), then resolving the legacy name must return a valid model.

**Validates: Requirements 1.4, 4.1, 4.2, 4.3**

### Property 4: Suggestion Relevance
*For any* failed name resolution, all suggested names must have some similarity to the input name (measured by edit distance or substring matching).

**Validates: Requirements 5.2**

### Property 5: No Ambiguous Aliases
*For any* two different models in the catalog, their generated aliases must not overlap (no alias maps to multiple models).

**Validates: Requirements 2.4**

### Property 6: Case Insensitivity
*For any* model name, resolving it with different casing (uppercase, lowercase, mixed) must return the same model.

**Validates: Requirements 2.1**

### Property 7: Version Format Flexibility
*For any* model with a version number, providing the version in different formats ("4.5", "4 5", "45") must resolve to the same model.

**Validates: Requirements 2.2**

## Error Handling

### Error Scenarios

1. **Name Not Found**:
   - **Cause**: User provides name that doesn't match any model
   - **Handling**: Return None from `resolve_name()`, provide suggestions via `get_suggestions()`
   - **Error Message**: "Model '{name}' not found. Did you mean: {suggestions}?"

2. **Ambiguous Name**:
   - **Cause**: Normalized name matches multiple models
   - **Handling**: Return None, list all matches in error
   - **Error Message**: "Ambiguous model name '{name}'. Could refer to: {matches}"

3. **Legacy Name Deprecated**:
   - **Cause**: Legacy name exists but model no longer available
   - **Handling**: Return None, suggest similar current models
   - **Error Message**: "Model '{name}' is no longer available. Similar models: {suggestions}"

4. **Alias Generation Failure**:
   - **Cause**: Model name format doesn't match any generation strategy
   - **Handling**: Log warning, use API name as-is
   - **Impact**: Model still accessible via API name

### Error Message Format

```python
@dataclass
class ModelResolutionError:
    """Detailed error information for failed resolution."""
    
    user_input: str
    error_type: ErrorType
    suggestions: List[str]
    legacy_name_found: bool  # Was this a legacy UnifiedModelManager name?
    similar_models: List[Tuple[str, float]]  # (name, similarity_score)
```

## Testing Strategy

### Unit Tests

**Test File**: `test/bestehorn_llmmanager/bedrock/catalog/test_name_resolver.py`

**Test Cases**:
1. **Exact Name Matching**:
   - Test API names resolve correctly
   - Test case sensitivity

2. **Alias Generation**:
   - Test Claude model alias generation
   - Test versioned model alias generation
   - Test provider-prefixed model alias generation
   - Test alias uniqueness

3. **Name Normalization**:
   - Test spacing variations
   - Test punctuation variations
   - Test version format variations
   - Test normalization idempotence

4. **Legacy Name Mapping**:
   - Test all known UnifiedModelManager names
   - Test deprecated model handling

5. **Suggestion Generation**:
   - Test edit distance suggestions
   - Test substring match suggestions
   - Test suggestion relevance

6. **Error Handling**:
   - Test not found scenarios
   - Test ambiguous name scenarios
   - Test empty input handling

### Property-Based Tests

**Test File**: `test/bestehorn_llmmanager/bedrock/catalog/test_name_resolver_properties.py`

**Property Tests**:
1. **Property 1: Alias Resolution Consistency** (Requirements 1.2, 1.3)
2. **Property 2: Normalization Idempotence** (Requirements 2.1)
3. **Property 3: Legacy Name Backward Compatibility** (Requirements 1.4, 4.1, 4.2, 4.3)
4. **Property 4: Suggestion Relevance** (Requirements 5.2)
5. **Property 5: No Ambiguous Aliases** (Requirements 2.4)
6. **Property 6: Case Insensitivity** (Requirements 2.1)
7. **Property 7: Version Format Flexibility** (Requirements 2.2)

### Integration Tests

**Test File**: `test/integration/test_integration_name_resolution.py`

**Test Cases**:
1. Test LLMManager initialization with friendly names
2. Test LLMManager initialization with legacy names
3. Test existing integration tests pass without modification
4. Test error messages provide helpful suggestions

## Implementation Notes

### Performance Considerations

1. **Lazy Index Building**: Build indexes on first query, not during catalog load
2. **Index Caching**: Cache indexes in memory for subsequent queries
3. **Alias Limit**: Limit aliases per model to prevent memory explosion
4. **Fuzzy Matching**: Only use fuzzy matching as last resort (expensive)

### Backward Compatibility

1. **Existing Code**: All existing code using API names continues to work
2. **UnifiedModelManager Names**: All legacy names mapped to new catalog
3. **Test Suite**: Integration tests work without modification
4. **Migration Path**: Users can gradually migrate to new names

### Future Extensibility

1. **Custom Aliases**: Allow users to register custom aliases
2. **Provider-Specific Strategies**: Add provider-specific alias generation
3. **Localization**: Support non-English model names
4. **Alias Versioning**: Track alias changes over time

## Dependencies

**No new external dependencies required.**

All functionality can be implemented using Python standard library:
- `difflib` for fuzzy matching
- `re` for pattern matching
- `dataclasses` for data structures

## Migration Guide

### For Test Code

**Before**:
```python
# Tests fail because BedrockModelCatalog doesn't recognize this name
manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])
```

**After** (no changes needed):
```python
# Tests now pass - name resolver handles the alias
manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])
```

### For Application Code

**Before**:
```python
# Had to use exact API name
manager = LLMManager(
    models=["anthropic.claude-3-haiku-20240307-v1:0"],
    regions=["us-east-1"]
)
```

**After**:
```python
# Can use friendly name
manager = LLMManager(
    models=["Claude 3 Haiku"],  # Much more readable!
    regions=["us-east-1"]
)
```

### For Integration Test Configuration

**Before**:
```python
# integration_config.py
default_models = {
    "anthropic": "Claude 3 Haiku",  # Fails with BedrockModelCatalog
}
```

**After** (no changes needed):
```python
# integration_config.py
default_models = {
    "anthropic": "Claude 3 Haiku",  # Now works with name resolver
}
```

## Summary

This design adds a comprehensive model name alias system to BedrockModelCatalog that:

1. **Generates user-friendly aliases** for all models automatically
2. **Supports flexible name matching** with normalization and fuzzy search
3. **Maintains backward compatibility** with UnifiedModelManager names
4. **Provides helpful error messages** with suggestions when names don't resolve
5. **Requires no changes** to existing code or tests

The implementation is non-invasive, performant (lazy initialization), and extensible for future enhancements.
