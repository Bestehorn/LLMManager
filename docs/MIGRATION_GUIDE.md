# Migration Guide: Moving to BedrockModelCatalog

This guide helps you migrate from the deprecated model management classes (`ModelManager`, `CRISManager`, `UnifiedModelManager`) to the new `BedrockModelCatalog` system.

## Table of Contents

- [Why Migrate?](#why-migrate)
- [What's Changing?](#whats-changing)
- [Deprecation Timeline](#deprecation-timeline)
- [Quick Migration Examples](#quick-migration-examples)
- [Detailed Migration Scenarios](#detailed-migration-scenarios)
- [Breaking Changes](#breaking-changes)
- [Troubleshooting](#troubleshooting)

## Why Migrate?

The new `BedrockModelCatalog` system provides significant improvements:

### Old System Issues
- ❌ Required HTML parsing from AWS documentation pages
- ❌ Multiple manager classes to coordinate (`ModelManager`, `CRISManager`, `UnifiedModelManager`)
- ❌ Complex file system dependencies
- ❌ Difficult to use in Lambda and restricted environments
- ❌ No support for read-only environments
- ❌ Multiple cache files to manage

### New System Benefits
- ✅ API-only data retrieval (no HTML parsing)
- ✅ Single unified `BedrockModelCatalog` class
- ✅ Flexible cache modes (FILE, MEMORY, NONE)
- ✅ Lambda-friendly design with /tmp support
- ✅ Bundled fallback data for offline scenarios
- ✅ Single cache file for all data
- ✅ Better error handling and reliability

## What's Changing?

### Deprecated Classes

The following classes are deprecated and will be removed in version 4.0.0:

- `ModelManager` - Use `BedrockModelCatalog` instead
- `CRISManager` - Use `BedrockModelCatalog` instead
- `UnifiedModelManager` - Use `BedrockModelCatalog` instead

### Removed Dependencies (Future)

After the deprecation period, these dependencies will be removed:
- `beautifulsoup4` - No longer needed without HTML parsing
- `lxml` - No longer needed without HTML parsing
- `requests` - No longer needed without HTML downloads

### LLMManager Integration

**Good News:** If you only use `LLMManager` and don't directly use the old manager classes, **no code changes are required**. The `LLMManager` automatically uses `BedrockModelCatalog` internally.

## Deprecation Timeline

| Version | Status | Timeline |
|---------|--------|----------|
| **3.x** | Deprecation warnings added | Current |
| **3.x - 3.5** | Both systems coexist | 6-12 months |
| **4.0.0** | Old managers removed | After 12 months |

### Current Status (Version 3.x)

- ✅ New `BedrockModelCatalog` available
- ⚠️ Old managers emit deprecation warnings
- ✅ Both systems fully functional
- ✅ Time to migrate gradually

### Future (Version 4.0.0)

- ❌ Old managers will be removed
- ❌ HTML parsing code will be removed
- ❌ BeautifulSoup4 and lxml dependencies removed
- ✅ Smaller package size
- ✅ Faster installation

## Quick Migration Examples

### Example 1: Basic Model Lookup

**Old Code (UnifiedModelManager):**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager

manager = UnifiedModelManager()
model_info = manager.get_model_info(
    model_name="Claude 3 Haiku",
    region="us-east-1"
)
```

**New Code (BedrockModelCatalog):**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()
model_info = catalog.get_model_info(
    model_name="Claude 3 Haiku",
    region="us-east-1"
)
```

**Changes:**
- Import from `bedrock.catalog` instead of `bedrock`
- Class name changed from `UnifiedModelManager` to `BedrockModelCatalog`
- Method signatures remain the same

### Example 2: Check Model Availability

**Old Code:**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager

manager = UnifiedModelManager()
is_available = manager.is_model_available(
    model_name="Claude 3 Haiku",
    region="us-east-1"
)
```

**New Code:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()
is_available = catalog.is_model_available(
    model_name="Claude 3 Haiku",
    region="us-east-1"
)
```

**Changes:**
- Same method signature
- Same return type
- Just update the import and class name

### Example 3: List Models

**Old Code:**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager

manager = UnifiedModelManager()
all_models = manager.list_models()
anthropic_models = manager.list_models(provider="Anthropic")
```

**New Code:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()
all_models = catalog.list_models()
anthropic_models = catalog.list_models(provider="Anthropic")
```

**Changes:**
- Same method signature
- Same filtering options
- Just update the import and class name

## Detailed Migration Scenarios

### Scenario 1: Direct Manager Usage

If you're directly using `UnifiedModelManager`, `ModelManager`, or `CRISManager`:

**Before:**
```python
from bestehorn_llmmanager.bedrock import (
    UnifiedModelManager,
    ModelManager,
    CRISManager
)

# Old approach - multiple managers
model_manager = ModelManager()
cris_manager = CRISManager()
unified_manager = UnifiedModelManager()

# Get model info
model_info = unified_manager.get_model_info("Claude 3 Haiku", "us-east-1")
```

**After:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

# New approach - single catalog
catalog = BedrockModelCatalog()

# Get model info (same method)
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
```

### Scenario 2: Custom Cache Configuration

**Before:**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager

# Old system - limited cache control
manager = UnifiedModelManager(
    force_refresh=True  # Only option was force refresh
)
```

**After:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode
from pathlib import Path

# New system - flexible cache modes
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,  # FILE, MEMORY, or NONE
    cache_directory=Path("/tmp/my_cache"),
    cache_max_age_hours=12.0,
    force_refresh=False
)
```

**New Features:**
- Three cache modes: FILE, MEMORY, NONE
- Configurable cache directory
- Configurable cache age
- Better control over refresh behavior

### Scenario 3: Lambda Deployment

**Before:**
```python
# Old system - required workarounds for Lambda
from bestehorn_llmmanager.bedrock import UnifiedModelManager
import os

def lambda_handler(event, context):
    # Had to set environment variables or use complex workarounds
    os.environ['CACHE_DIR'] = '/tmp'
    manager = UnifiedModelManager()
    # ... rest of code
```

**After:**
```python
# New system - Lambda-friendly by design
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode
from pathlib import Path

def lambda_handler(event, context):
    # Simple, explicit configuration
    catalog = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("/tmp/bedrock_cache")
    )
    # ... rest of code
```

**Improvements:**
- Explicit cache directory configuration
- Support for read-only environments (MEMORY mode)
- No environment variable hacks needed
- Better error messages

### Scenario 4: LLMManager Integration

**Before:**
```python
from bestehorn_llmmanager import LLMManager

# Old system - no control over model catalog
manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"]
)
```

**After:**
```python
from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.catalog import CacheMode
from pathlib import Path

# New system - configure catalog through LLMManager
manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    catalog_cache_mode=CacheMode.FILE,
    catalog_cache_directory=Path("/tmp/my_cache")
)
```

**New Features:**
- Configure catalog behavior through LLMManager
- No need to create catalog separately
- Transparent integration

### Scenario 5: Offline/Workshop Scenarios

**Before:**
```python
# Old system - required pre-downloading HTML files
from bestehorn_llmmanager.bedrock import UnifiedModelManager

# Had to manually download and cache HTML files
manager = UnifiedModelManager()
```

**After:**
```python
# New system - bundled data included
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

# Works offline with bundled data
catalog = BedrockModelCatalog(
    fallback_to_bundled=True  # Uses bundled data if API fails
)

# Check data source
metadata = catalog.get_catalog_metadata()
if metadata.source.value == "BUNDLED":
    print(f"Using bundled data (version: {metadata.bundled_data_version})")
```

**Improvements:**
- Bundled data included in package
- No manual download required
- Works completely offline
- Automatic fallback on API failure

## Breaking Changes

### API Changes

#### 1. Import Paths

**Old:**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager
```

**New:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
```

#### 2. Class Names

| Old Class | New Class |
|-----------|-----------|
| `ModelManager` | `BedrockModelCatalog` |
| `CRISManager` | `BedrockModelCatalog` |
| `UnifiedModelManager` | `BedrockModelCatalog` |

#### 3. Initialization Parameters

**Old (UnifiedModelManager):**
```python
manager = UnifiedModelManager(
    force_refresh=True
)
```

**New (BedrockModelCatalog):**
```python
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("./cache"),
    cache_max_age_hours=24.0,
    force_refresh=False,
    timeout=30,
    max_workers=10,
    fallback_to_bundled=True
)
```

**New Parameters:**
- `cache_mode`: CacheMode enum (FILE, MEMORY, NONE)
- `cache_directory`: Path object for cache location
- `cache_max_age_hours`: Float for cache expiration
- `timeout`: API timeout in seconds
- `max_workers`: Parallel workers for API calls
- `fallback_to_bundled`: Boolean for bundled data fallback

### Method Signatures

Good news: All query methods have the same signatures!

```python
# These work the same in both old and new systems
get_model_info(model_name: str, region: str)
is_model_available(model_name: str, region: str)
list_models(region: Optional[str], provider: Optional[str], streaming_only: bool)
```

### Return Types

Return types are compatible:
- `get_model_info()` returns `ModelAccessInfo` (same as before)
- `is_model_available()` returns `bool` (same as before)
- `list_models()` returns `List[ModelInfo]` (same as before)

## Troubleshooting

### Issue 1: Deprecation Warnings

**Symptom:**
```
DeprecationWarning: UnifiedModelManager is deprecated and will be removed in version 4.0.0.
Please migrate to BedrockModelCatalog. See migration guide: ...
```

**Solution:**
This is expected. Update your code to use `BedrockModelCatalog` as shown in this guide.

**Temporary Suppression (not recommended):**
```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

### Issue 2: Import Errors

**Symptom:**
```
ImportError: cannot import name 'BedrockModelCatalog' from 'bestehorn_llmmanager.bedrock'
```

**Solution:**
Update your import path:
```python
# Wrong
from bestehorn_llmmanager.bedrock import BedrockModelCatalog

# Correct
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
```

### Issue 3: Cache Directory Errors in Lambda

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/var/task/.cache'
```

**Solution:**
Explicitly set cache directory to /tmp:
```python
from pathlib import Path

catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("/tmp/bedrock_cache")
)
```

Or use MEMORY mode:
```python
catalog = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)
```

### Issue 4: API Timeout Errors

**Symptom:**
```
APIFetchError: Timeout fetching model data from AWS APIs
```

**Solution:**
Increase timeout or use bundled data:
```python
catalog = BedrockModelCatalog(
    timeout=60,  # Increase timeout
    fallback_to_bundled=True  # Use bundled data on failure
)
```

### Issue 5: Stale Bundled Data Warning

**Symptom:**
```
WARNING: Using bundled fallback data (may be stale)
```

**Solution:**
This means the catalog couldn't fetch fresh data from AWS APIs and is using bundled data. To get fresh data:

1. Check AWS credentials are configured
2. Check internet connectivity
3. Force refresh:
```python
catalog = BedrockModelCatalog(force_refresh=True)
```

### Issue 6: Missing Model Information

**Symptom:**
```python
model_info = catalog.get_model_info("My Model", "us-east-1")
# model_info is None
```

**Solution:**
1. Check model name spelling (case-sensitive)
2. Check region availability
3. Force refresh to get latest data:
```python
catalog = BedrockModelCatalog(force_refresh=True)
```

## Migration Checklist

Use this checklist to ensure complete migration:

### Code Changes
- [ ] Replace `UnifiedModelManager` imports with `BedrockModelCatalog`
- [ ] Replace `ModelManager` imports with `BedrockModelCatalog`
- [ ] Replace `CRISManager` imports with `BedrockModelCatalog`
- [ ] Update class instantiation to use `BedrockModelCatalog`
- [ ] Add cache mode configuration if needed
- [ ] Update Lambda functions to use explicit cache directories

### Testing
- [ ] Test with FILE cache mode
- [ ] Test with MEMORY cache mode (if using read-only environments)
- [ ] Test with NONE cache mode (if always need fresh data)
- [ ] Test Lambda deployments with /tmp cache
- [ ] Test offline scenarios with bundled data
- [ ] Verify model lookups work correctly
- [ ] Check cache file creation and loading

### Documentation
- [ ] Update internal documentation
- [ ] Update deployment guides
- [ ] Update Lambda deployment instructions
- [ ] Document cache mode choices
- [ ] Update troubleshooting guides

### Cleanup (After Migration)
- [ ] Remove old manager imports
- [ ] Remove workarounds for old system
- [ ] Clean up old cache files (if any)
- [ ] Update dependencies (after v4.0.0 release)

## Getting Help

If you encounter issues during migration:

1. **Check Examples:** See `examples/catalog_*.py` for working examples
2. **Read Documentation:** See `docs/forLLMConsumption.md` for API reference
3. **Check Logs:** Enable DEBUG logging to see what's happening:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
4. **GitHub Issues:** Report bugs or ask questions on GitHub
5. **AWS Credentials:** Ensure AWS credentials are properly configured

## Summary

Migration to `BedrockModelCatalog` is straightforward:

1. **Update imports:** Change import path to `bedrock.catalog`
2. **Update class name:** Use `BedrockModelCatalog` instead of old managers
3. **Configure cache mode:** Choose FILE, MEMORY, or NONE based on your environment
4. **Test thoroughly:** Verify functionality in your deployment environment

The new system provides better reliability, flexibility, and Lambda support while maintaining API compatibility with the old system.
