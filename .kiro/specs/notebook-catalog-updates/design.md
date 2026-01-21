# Design Document: Notebook Updates for BedrockModelCatalog

## Overview

This design specifies the updates needed for Jupyter notebooks to migrate from deprecated manager classes (`CRISManager`, `ModelManager`, `UnifiedModelManager`) to the new `BedrockModelCatalog` system. The migration maintains educational value while demonstrating modern APIs and best practices.

## Architecture

### Migration Strategy

The notebook updates follow a **targeted replacement** strategy:

1. **Direct Replacement**: Three notebooks using deprecated managers get complete rewrites
2. **Compatibility Verification**: Nine notebooks using current APIs remain unchanged
3. **Enhancement**: One notebook (Caching.ipynb) gets additional content for catalog caching

### Component Interaction

```
Notebooks (Educational Layer)
    ↓
BedrockModelCatalog (Unified API)
    ↓
┌─────────────┬──────────────┬────────────────┐
│ CacheManager│ APIFetcher   │ BundledLoader  │
└─────────────┴──────────────┴────────────────┘
```

The notebooks interact only with `BedrockModelCatalog`, which internally manages caching, API fetching, and fallback data.

## Components and Interfaces

### 1. Updated Notebooks (Deprecated Manager Replacements)

#### CRISManager.ipynb → BedrockModelCatalog Demo

**Purpose**: Demonstrate CRIS (Cross-Region Inference) data access

**Key Changes**:
- Replace `CRISManager` imports with `BedrockModelCatalog`
- Remove manual `refresh_cris_data()` calls
- Use `get_model_info()` to access inference profile data
- Show `access_method` field for understanding access patterns

**Example Code Pattern**:
```python
# Old
from bedrock.CRISManager import CRISManager
cris_manager = CRISManager()
catalog = cris_manager.refresh_cris_data(force_download=True)

# New
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
catalog = BedrockModelCatalog(force_refresh=True)
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
```

#### ModelIDManager.ipynb → BedrockModelCatalog Demo

**Purpose**: Demonstrate model availability and filtering

**Key Changes**:
- Replace `ModelManager` imports with `BedrockModelCatalog`
- Remove manual `refresh_model_data()` calls
- Use `list_models()` for filtering by provider/region
- Use `is_model_available()` for availability checks

**Example Code Pattern**:
```python
# Old
from bedrock.ModelManager import ModelManager
manager = ModelManager()
catalog = manager.refresh_model_data()

# New
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
catalog = BedrockModelCatalog(force_refresh=True)
models = catalog.list_models(provider="Anthropic")
```

#### UnifiedModelManager.ipynb → BedrockModelCatalog Unified Demo

**Purpose**: Demonstrate unified model and CRIS data access

**Key Changes**:
- Replace `UnifiedModelManager` imports with `BedrockModelCatalog`
- Remove manual `refresh_unified_data()` calls
- Show how `get_model_info()` provides both model ID and inference profile
- Demonstrate access method detection

**Example Code Pattern**:
```python
# Old
from bedrock.UnifiedModelManager import UnifiedModelManager
manager = UnifiedModelManager()
catalog = manager.refresh_unified_data()

# New
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
catalog = BedrockModelCatalog(force_refresh=True)
model_info = catalog.get_model_info("Claude Sonnet 4.5", "us-east-1")
print(f"Access Method: {model_info.access_method.value}")
```

### 2. Enhanced Notebook (Cache Mode Addition)

#### Caching.ipynb Enhancement

**Purpose**: Document both prompt caching (existing) and catalog caching (new)

**New Content Structure**:
```markdown
## Existing Content: Prompt Caching
[Keep all existing prompt caching demonstrations]

## New Section: Model Catalog Caching

### Cache Modes Overview
[Explain FILE, MEMORY, NONE modes]

### FILE Mode Example
[Show persistent file-based caching]

### MEMORY Mode Example
[Show in-memory caching]

### NONE Mode Example
[Show no-cache always-fresh mode]

### Cache Mode Comparison
[Table comparing modes]

### Advanced Configuration
[Show cache_max_age_hours, force_refresh, etc.]
```

**New Code Cells**:
```python
# FILE mode
catalog_file = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("./demo_cache"),
    cache_max_age_hours=24.0,
    force_refresh=True
)

# MEMORY mode
catalog_memory = BedrockModelCatalog(
    cache_mode=CacheMode.MEMORY,
    force_refresh=True
)

# NONE mode
catalog_none = BedrockModelCatalog(
    cache_mode=CacheMode.NONE,
    fallback_to_bundled=True
)
```

### 3. Unchanged Notebooks (Compatibility Verification)

These notebooks require no changes but should be verified:

- **HelloWorld_LLMManager.ipynb**: Uses LLMManager which internally uses BedrockModelCatalog
- **HelloWorld_MessageBuilder.ipynb**: MessageBuilder is independent of catalog
- **HelloWorld_MessageBuilder_Demo.ipynb**: Demonstrates MessageBuilder only
- **HelloWorld_MessageBuilder_Paths.ipynb**: Path-based methods independent of catalog
- **HelloWorld_Streaming_Demo.ipynb**: Streaming uses LLMManager internally
- **ParallelLLMManager_Demo.ipynb**: ParallelLLMManager uses LLMManager internally
- **ResponseValidation.ipynb**: Validation is independent of catalog
- **InferenceProfile_Demo.ipynb**: Already demonstrates BedrockModelCatalog usage
- **ExtendedContext_Demo.ipynb**: Extended context is independent of catalog

## Data Models

### BedrockModelCatalog Configuration

```python
@dataclass
class CatalogConfig:
    """Configuration for BedrockModelCatalog initialization."""
    cache_mode: CacheMode = CacheMode.FILE
    cache_directory: Optional[Path] = None
    cache_max_age_hours: float = 24.0
    force_refresh: bool = False
    timeout: int = 30
    max_workers: int = 10
    fallback_to_bundled: bool = True
```

### ModelAccessInfo Structure

```python
@dataclass
class ModelAccessInfo:
    """Access information for a model in a region."""
    model_id: str
    inference_profile_id: Optional[str]
    access_method: AccessMethod  # direct, regional_cris, global_cris
    supports_streaming: bool
    input_modalities: List[str]
    output_modalities: List[str]
```

### CatalogMetadata Structure

```python
@dataclass
class CatalogMetadata:
    """Metadata about catalog source and freshness."""
    source: CatalogSource  # api, cache, bundled
    retrieval_timestamp: datetime
    api_regions_queried: List[str]
    bundled_data_version: Optional[str]
    cache_file_path: Optional[Path]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing the acceptance criteria, I identified that most requirements are specific examples rather than universal properties. The requirements specify exact patterns that should exist in specific notebooks (e.g., "CRISManager.ipynb should have import X"). These are concrete examples to verify, not properties that hold across all inputs.

The key insight is that notebook updates are deterministic transformations - we're checking for the presence or absence of specific code patterns in specific files. This is best validated through example-based testing rather than property-based testing.

### Property 1: Correct Import Statement Presence

*For any* updated notebook file (CRISManager.ipynb, ModelIDManager.ipynb, UnifiedModelManager.ipynb), parsing the notebook JSON should find the import statement `from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog` in at least one code cell

**Validates: Requirements 1.1, 2.1, 3.1, 7.1, 7.2, 7.3**

### Property 2: Deprecated Import Absence

*For any* updated notebook file, parsing the notebook JSON should NOT find any deprecated import statements (`CRISManager`, `ModelManager`, `UnifiedModelManager` from old paths)

**Validates: Requirements 8.2, 8.4**

### Property 3: Deprecated Method Call Absence

*For any* updated notebook file, parsing the code cells should NOT find calls to deprecated refresh methods (`refresh_model_data()`, `refresh_cris_data()`, `refresh_unified_data()`)

**Validates: Requirements 8.1, 8.5**

### Property 4: Force Refresh Parameter Presence

*For any* BedrockModelCatalog initialization in updated notebooks, the initialization should include `force_refresh=True` parameter

**Validates: Requirements 1.2, 2.2, 3.2**

### Property 5: Cache Mode Completeness

*For any* cache mode value (FILE, MEMORY, NONE), the Caching.ipynb notebook should contain at least one code cell demonstrating initialization with that cache mode

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 6: Unchanged Notebook Preservation

*For any* notebook in the unchanged list (HelloWorld_LLMManager, HelloWorld_MessageBuilder, etc.), the notebook should NOT contain deprecated manager imports

**Validates: Requirements 5.1-5.9, 10.1-10.9**

### Property 7: Troubleshooting Content Presence

*For any* updated notebook, there should be at least one markdown or code cell containing troubleshooting guidance (identified by keywords like "troubleshooting", "error", "💡", "⚠️")

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

### Property 8: Summary Section Presence

*For any* updated notebook, there should be a markdown cell near the end containing "Summary" or "summary" in its content

**Validates: Requirements 6.5**

## Error Handling

### Import Errors

**Scenario**: BedrockModelCatalog import fails

**Handling**:
```python
try:
    from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
    print("✅ Imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Ensure you're running from notebooks directory")
    print("   and src directory contains the catalog module")
```

### Cache Permission Errors

**Scenario**: Cannot write to cache directory

**Handling**:
```python
try:
    catalog = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("./notebook_cache")
    )
except PermissionError as e:
    print(f"❌ Permission error: {e}")
    print("💡 Use a writable directory or switch to MEMORY mode")
    catalog = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)
```

### API Timeout Errors

**Scenario**: API fetch times out

**Handling**:
```python
try:
    catalog = BedrockModelCatalog(
        force_refresh=True,
        timeout=30
    )
except Exception as e:
    print(f"❌ API error: {e}")
    print("💡 Using bundled fallback data")
    catalog = BedrockModelCatalog(
        cache_mode=CacheMode.NONE,
        fallback_to_bundled=True
    )
```

### Model Not Found

**Scenario**: Queried model doesn't exist

**Handling**:
```python
model_info = catalog.get_model_info("NonExistentModel", "us-east-1")
if model_info is None:
    print("❌ Model not found in catalog")
    print("💡 Check model name spelling or use list_models() to see available models")
else:
    print(f"✅ Model found: {model_info.model_id}")
```

## Testing Strategy

### Unit Testing Approach

**Test Scope**: Verify notebook code patterns are correct

**Test Files**:
- `test/unit/test_notebook_imports.py`: Verify import statements
- `test/unit/test_notebook_api_usage.py`: Verify API method calls

**Example Test**:
```python
def test_crismanager_notebook_uses_correct_import():
    """Verify CRISManager.ipynb uses BedrockModelCatalog import."""
    notebook_path = Path("notebooks/CRISManager.ipynb")
    with open(notebook_path) as f:
        content = f.read()
    
    # Should have new import
    assert "from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog" in content
    
    # Should not have old import
    assert "from bedrock.CRISManager import CRISManager" not in content
```

### Integration Testing Approach

**Test Scope**: Verify notebooks execute without errors

**Test Files**:
- `test/integration/test_notebook_execution.py`: Execute notebooks and verify success

**Example Test**:
```python
def test_crismanager_notebook_executes():
    """Verify CRISManager.ipynb executes without errors."""
    result = execute_notebook("notebooks/CRISManager.ipynb")
    assert result.success, f"Notebook failed: {result.errors}"
```

### Manual Testing Approach

**Test Scope**: Verify educational value and output quality

**Test Process**:
1. Open each updated notebook in Jupyter
2. Execute all cells sequentially
3. Verify output is clear and educational
4. Check that examples demonstrate intended features
5. Confirm troubleshooting sections are helpful

## Implementation Notes

### Notebook Cell Structure

Each updated notebook should follow this structure:

1. **Title and Overview** (Markdown)
2. **Setup and Imports** (Code)
3. **Helper Functions** (Code, if needed)
4. **Example 1: Basic Usage** (Markdown + Code)
5. **Example 2-N: Advanced Features** (Markdown + Code)
6. **Troubleshooting** (Markdown + Code)
7. **Summary** (Markdown + Code)

### Code Style in Notebooks

- Use clear variable names: `catalog`, `model_info`, `metadata`
- Include print statements showing what's happening
- Format output with emojis and labels for readability
- Handle errors gracefully with try/except blocks
- Show both success and failure paths

### Markdown Style in Notebooks

- Use headers (##, ###) to organize sections
- Include brief explanations before code cells
- Use bullet points for feature lists
- Include code snippets in markdown for comparison
- Add "💡" tips and "⚠️" warnings where appropriate

### Force Refresh Pattern

All updated notebooks should use `force_refresh=True` to demonstrate fresh data fetching:

```python
# Initialize with force refresh for demonstration
catalog = BedrockModelCatalog(
    force_refresh=True,  # Always fetch fresh data for demo
    timeout=60,          # Longer timeout for reliability
    fallback_to_bundled=True  # Fallback if API fails
)
```

### Cache Mode Demonstration Pattern

The Caching.ipynb notebook should demonstrate each mode clearly:

```python
# FILE mode - persistent cache
catalog_file = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("./demo_cache"),
    force_refresh=True
)
metadata = catalog_file.get_catalog_metadata()
print(f"Source: {metadata.source.value}")
print(f"Cache file: {metadata.cache_file_path}")

# MEMORY mode - in-memory only
catalog_memory = BedrockModelCatalog(
    cache_mode=CacheMode.MEMORY,
    force_refresh=True
)
metadata = catalog_memory.get_catalog_metadata()
print(f"Source: {metadata.source.value}")

# NONE mode - always fresh
catalog_none = BedrockModelCatalog(
    cache_mode=CacheMode.NONE
)
metadata = catalog_none.get_catalog_metadata()
print(f"Source: {metadata.source.value}")
```

### Metadata Display Pattern

All updated notebooks should show catalog metadata:

```python
metadata = catalog.get_catalog_metadata()
print(f"📊 Catalog Metadata:")
print(f"   Source: {metadata.source.value}")
print(f"   Retrieved: {metadata.retrieval_timestamp}")
print(f"   Regions Queried: {len(metadata.api_regions_queried)}")
if metadata.cache_file_path:
    print(f"   Cache File: {metadata.cache_file_path}")
```

### Model Info Display Pattern

Show comprehensive model information:

```python
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
if model_info:
    print(f"🤖 Model Information:")
    print(f"   Model ID: {model_info.model_id}")
    print(f"   Inference Profile: {model_info.inference_profile_id or 'N/A'}")
    print(f"   Access Method: {model_info.access_method.value}")
    print(f"   Streaming: {'✅' if model_info.supports_streaming else '❌'}")
    print(f"   Input Modalities: {', '.join(model_info.input_modalities)}")
    print(f"   Output Modalities: {', '.join(model_info.output_modalities)}")
else:
    print("❌ Model not found")
```

### List Models Pattern

Demonstrate filtering capabilities:

```python
# List all models
all_models = catalog.list_models()
print(f"Total models: {len(all_models)}")

# Filter by provider
anthropic_models = catalog.list_models(provider="Anthropic")
print(f"Anthropic models: {len(anthropic_models)}")

# Filter by region
us_east_models = catalog.list_models(region="us-east-1")
print(f"Models in us-east-1: {len(us_east_models)}")

# Filter by streaming support
streaming_models = catalog.list_models(streaming_only=True)
print(f"Streaming-capable models: {len(streaming_models)}")

# Combine filters
anthropic_streaming = catalog.list_models(
    provider="Anthropic",
    streaming_only=True
)
print(f"Anthropic streaming models: {len(anthropic_streaming)}")
```

## Migration Mapping

### API Method Mapping

| Old API | New API | Notes |
|---------|---------|-------|
| `CRISManager.refresh_cris_data()` | `BedrockModelCatalog(force_refresh=True)` | Automatic on init |
| `ModelManager.refresh_model_data()` | `BedrockModelCatalog(force_refresh=True)` | Automatic on init |
| `UnifiedModelManager.refresh_unified_data()` | `BedrockModelCatalog(force_refresh=True)` | Automatic on init |
| `manager.get_model_info(name, region)` | `catalog.get_model_info(name, region)` | Same signature |
| `manager.is_model_available(name, region)` | `catalog.is_model_available(name, region)` | Same signature |
| `manager.get_models_by_provider(provider)` | `catalog.list_models(provider=provider)` | Returns list not dict |
| `manager.get_models_by_region(region)` | `catalog.list_models(region=region)` | Returns list not dict |
| `manager.get_streaming_models()` | `catalog.list_models(streaming_only=True)` | Returns list not dict |

### Import Statement Mapping

| Old Import | New Import |
|------------|------------|
| `from bedrock.CRISManager import CRISManager` | `from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog` |
| `from bedrock.ModelManager import ModelManager` | `from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog` |
| `from bedrock.UnifiedModelManager import UnifiedModelManager` | `from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog` |
| N/A | `from bestehorn_llmmanager.bedrock.catalog import CacheMode` |

## Validation Checklist

After updating each notebook, verify:

- [ ] All cells execute without errors
- [ ] No deprecation warnings appear
- [ ] Import statements use correct module paths
- [ ] `force_refresh=True` is used in initialization
- [ ] Model lookups return correct data
- [ ] Metadata displays correctly
- [ ] Examples are clear and educational
- [ ] Output is properly formatted with labels
- [ ] Troubleshooting sections are present
- [ ] Summary sections highlight key takeaways

## Additional Resources

The notebooks should reference:

- **Migration Guide**: `docs/MIGRATION_GUIDE.md` - Detailed migration instructions
- **API Reference**: `docs/forLLMConsumption.md` - Complete API documentation
- **Examples**: `examples/catalog_*.py` - Code examples
- **README**: `README.md` - BedrockModelCatalog overview section

## Summary

This design provides a clear migration path from deprecated manager classes to BedrockModelCatalog while:

1. **Maintaining Educational Value**: Notebooks remain clear teaching tools
2. **Demonstrating Best Practices**: Using `force_refresh=True` for demos
3. **Showing Modern APIs**: BedrockModelCatalog's unified interface
4. **Preserving Working Code**: Unchanged notebooks stay stable
5. **Adding New Content**: Cache mode demonstrations in Caching.ipynb

The migration is straightforward with clear patterns for each type of update.
