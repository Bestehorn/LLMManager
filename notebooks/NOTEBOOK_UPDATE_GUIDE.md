# Notebook Update Guide for BedrockModelCatalog

This guide documents the updates needed for Jupyter notebooks to use the new `BedrockModelCatalog` system.

## Overview

The following notebooks need to be updated to use `BedrockModelCatalog` instead of the deprecated manager classes:

1. **CRISManager.ipynb** - Replace with BedrockModelCatalog examples
2. **ModelIDManager.ipynb** - Update to use new catalog
3. **UnifiedModelManager.ipynb** - Replace with BedrockModelCatalog examples
4. **Caching.ipynb** - Document new cache modes
5. **Other notebooks** - Verify compatibility

## Update Instructions

### 1. CRISManager.ipynb

**Current Status:** Uses deprecated `CRISManager` class

**Required Changes:**

#### Cell 1: Import Statement
**Old:**
```python
from bestehorn_llmmanager.bedrock import CRISManager
```

**New:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
```

#### Cell 2: Initialization
**Old:**
```python
cris_manager = CRISManager()
cris_manager.refresh_cris_data()
```

**New:**
```python
catalog = BedrockModelCatalog()
# Data is automatically fetched and cached
```

#### Cell 3: Getting CRIS Information
**Old:**
```python
cris_info = cris_manager.get_cris_info("Claude 3 Haiku")
```

**New:**
```python
# Get model info which includes CRIS data
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
if model_info:
    print(f"Inference Profile: {model_info.inference_profile_id}")
    print(f"Access Method: {model_info.access_method.value}")
```

#### Cell 4: Listing Models
**Old:**
```python
all_cris_models = cris_manager.list_cris_models()
```

**New:**
```python
# List all models (includes CRIS information)
all_models = catalog.list_models()
for model in all_models:
    print(f"{model.model_name}: {model.inference_profile_id}")
```

#### New Cell: Catalog Metadata
**Add:**
```python
# Get catalog metadata
metadata = catalog.get_catalog_metadata()
print(f"Source: {metadata.source.value}")
print(f"Retrieved: {metadata.retrieval_timestamp}")
print(f"Regions: {metadata.api_regions_queried}")
```

### 2. ModelIDManager.ipynb

**Current Status:** Uses deprecated `ModelManager` class

**Required Changes:**

#### Cell 1: Import Statement
**Old:**
```python
from bestehorn_llmmanager.bedrock import ModelManager
```

**New:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
```

#### Cell 2: Initialization
**Old:**
```python
model_manager = ModelManager()
model_manager.refresh_model_data()
```

**New:**
```python
catalog = BedrockModelCatalog()
# Data is automatically fetched and cached
```

#### Cell 3: Getting Model Information
**Old:**
```python
model_info = model_manager.get_model_info("Claude 3 Haiku", "us-east-1")
```

**New:**
```python
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
if model_info:
    print(f"Model ID: {model_info.model_id}")
    print(f"Regions: {model_info.regions}")
    print(f"Streaming: {model_info.supports_streaming}")
```

#### Cell 4: Checking Availability
**Old:**
```python
is_available = model_manager.is_model_available("Claude 3 Haiku", "us-east-1")
```

**New:**
```python
is_available = catalog.is_model_available("Claude 3 Haiku", "us-east-1")
print(f"Available: {is_available}")
```

#### Cell 5: Listing Models
**Old:**
```python
all_models = model_manager.list_models()
```

**New:**
```python
all_models = catalog.list_models()
print(f"Total models: {len(all_models)}")

# Filter by provider
anthropic_models = catalog.list_models(provider="Anthropic")
print(f"Anthropic models: {len(anthropic_models)}")
```

### 3. UnifiedModelManager.ipynb

**Current Status:** Uses deprecated `UnifiedModelManager` class

**Required Changes:**

#### Cell 1: Import Statement
**Old:**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager
```

**New:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
```

#### Cell 2: Initialization
**Old:**
```python
unified_manager = UnifiedModelManager()
unified_manager.refresh_unified_data()
```

**New:**
```python
catalog = BedrockModelCatalog()
# Data is automatically fetched and cached
```

#### Cell 3: Getting Unified Information
**Old:**
```python
model_info = unified_manager.get_model_info("Claude 3 Haiku", "us-east-1")
```

**New:**
```python
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
if model_info:
    print(f"Model ID: {model_info.model_id}")
    print(f"Inference Profile: {model_info.inference_profile_id}")
    print(f"Access Method: {model_info.access_method.value}")
    print(f"Regions: {model_info.regions}")
    print(f"Streaming: {model_info.supports_streaming}")
```

#### New Cell: Cache Modes
**Add:**
```python
from bestehorn_llmmanager.bedrock.catalog import CacheMode
from pathlib import Path

# FILE mode (default)
catalog_file = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("./notebook_cache")
)

# MEMORY mode
catalog_memory = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)

# NONE mode
catalog_none = BedrockModelCatalog(cache_mode=CacheMode.NONE)
```

### 4. Caching.ipynb

**Current Status:** Documents Bedrock prompt caching (not model catalog caching)

**Required Changes:**

#### New Section: Model Catalog Caching

**Add after existing prompt caching content:**

```markdown
## Model Catalog Caching

The BedrockModelCatalog supports three cache modes for managing model availability data:

### Cache Modes Overview

1. **FILE Mode** - Persistent file-based caching
2. **MEMORY Mode** - In-memory caching (process lifetime)
3. **NONE Mode** - No caching (always fresh)
```

#### New Cell: FILE Mode Example
**Add:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode
from pathlib import Path
import time

# FILE mode - persistent cache
print("Testing FILE mode...")
start = time.time()
catalog_file = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("./demo_cache"),
    cache_max_age_hours=24.0
)
duration = time.time() - start
print(f"Initialization time: {duration:.2f}s")

# Check metadata
metadata = catalog_file.get_catalog_metadata()
print(f"Source: {metadata.source.value}")
print(f"Cache file: {metadata.cache_file_path}")
```

#### New Cell: MEMORY Mode Example
**Add:**
```python
# MEMORY mode - in-memory cache
print("\nTesting MEMORY mode...")
start = time.time()
catalog_memory = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)
duration = time.time() - start
print(f"Initialization time: {duration:.2f}s")

metadata = catalog_memory.get_catalog_metadata()
print(f"Source: {metadata.source.value}")
print("Note: Cache stored in memory only")
```

#### New Cell: NONE Mode Example
**Add:**
```python
# NONE mode - no caching
print("\nTesting NONE mode...")
start = time.time()
catalog_none = BedrockModelCatalog(
    cache_mode=CacheMode.NONE,
    fallback_to_bundled=True
)
duration = time.time() - start
print(f"Initialization time: {duration:.2f}s")

metadata = catalog_none.get_catalog_metadata()
print(f"Source: {metadata.source.value}")
print("Note: Always fetches fresh data")
```

#### New Cell: Cache Mode Comparison
**Add:**
```python
import pandas as pd

# Compare cache modes
comparison = pd.DataFrame({
    'Cache Mode': ['FILE', 'MEMORY', 'NONE'],
    'File I/O': ['Yes', 'No', 'No'],
    'Warm Start': ['Fast', 'Fast', 'Slow'],
    'Persistent': ['Yes', 'No', 'No'],
    'Use Case': [
        'Production, Lambda with /tmp',
        'Read-only environments',
        'Security-critical, always fresh'
    ]
})

print(comparison.to_string(index=False))
```

#### New Cell: Cache Configuration
**Add:**
```python
# Advanced cache configuration
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("./my_cache"),
    cache_max_age_hours=12.0,  # Refresh after 12 hours
    force_refresh=False,        # Set True to bypass cache
    timeout=30,                 # API timeout
    max_workers=10,             # Parallel workers
    fallback_to_bundled=True    # Use bundled data on failure
)

print("Cache configuration:")
print(f"  Mode: {catalog._cache_mode.value}")
print(f"  Directory: {catalog._cache_directory}")
print(f"  Max age: {catalog._cache_max_age_hours} hours")
```

### 5. Other Notebooks - Compatibility Verification

#### HelloWorld_LLMManager.ipynb
**Status:** ✅ Compatible - No changes needed  
**Reason:** LLMManager automatically uses BedrockModelCatalog internally

#### HelloWorld_MessageBuilder.ipynb
**Status:** ✅ Compatible - No changes needed  
**Reason:** MessageBuilder is independent of catalog system

#### HelloWorld_MessageBuilder_Demo.ipynb
**Status:** ✅ Compatible - No changes needed  
**Reason:** MessageBuilder is independent of catalog system

#### HelloWorld_MessageBuilder_Paths.ipynb
**Status:** ✅ Compatible - No changes needed  
**Reason:** MessageBuilder is independent of catalog system

#### HelloWorld_Streaming_Demo.ipynb
**Status:** ✅ Compatible - No changes needed  
**Reason:** Streaming uses LLMManager which handles catalog internally

#### ParallelLLMManager_Demo.ipynb
**Status:** ✅ Compatible - No changes needed  
**Reason:** ParallelLLMManager uses LLMManager which handles catalog internally

#### ResponseValidation.ipynb
**Status:** ✅ Compatible - No changes needed  
**Reason:** Response validation is independent of catalog system

## Testing Checklist

After updating notebooks, verify:

- [ ] All cells execute without errors
- [ ] Deprecation warnings are not present
- [ ] Model lookups return correct data
- [ ] Cache modes work as expected
- [ ] Metadata displays correctly
- [ ] Examples are clear and educational
- [ ] Output is properly formatted

## Common Issues and Solutions

### Issue 1: Import Error
**Error:** `ImportError: cannot import name 'BedrockModelCatalog'`

**Solution:**
```python
# Wrong
from bestehorn_llmmanager.bedrock import BedrockModelCatalog

# Correct
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
```

### Issue 2: Cache Directory Permissions
**Error:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```python
# Use a writable directory
from pathlib import Path
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("./notebook_cache")  # Local directory
)
```

### Issue 3: API Timeout
**Error:** `APIFetchError: Timeout fetching model data`

**Solution:**
```python
# Increase timeout or use bundled data
catalog = BedrockModelCatalog(
    timeout=60,  # Increase timeout
    fallback_to_bundled=True  # Use bundled data on failure
)
```

## Additional Resources

- **Migration Guide:** `docs/MIGRATION_GUIDE.md`
- **API Reference:** `docs/forLLMConsumption.md`
- **Examples:** `examples/catalog_*.py`
- **README:** `README.md` (BedrockModelCatalog section)

## Summary

The notebook updates are straightforward:

1. **Update imports:** Change to `bedrock.catalog`
2. **Update class names:** Use `BedrockModelCatalog`
3. **Remove refresh calls:** Data is fetched automatically
4. **Add cache mode examples:** Show FILE, MEMORY, NONE modes
5. **Test thoroughly:** Ensure all cells execute correctly

The new system provides better reliability, flexibility, and ease of use while maintaining API compatibility.
