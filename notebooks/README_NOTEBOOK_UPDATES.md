# Notebook Updates for BedrockModelCatalog

## Status

The notebooks in this directory need to be updated to use the new `BedrockModelCatalog` system instead of the deprecated manager classes.

## Notebooks Requiring Updates

### High Priority (Use Deprecated Classes)

1. **CRISManager.ipynb** ⚠️ NEEDS UPDATE
   - Currently uses: `CRISManager`
   - Should use: `BedrockModelCatalog`
   - See: `NOTEBOOK_UPDATE_GUIDE.md` Section 1

2. **ModelIDManager.ipynb** ⚠️ NEEDS UPDATE
   - Currently uses: `ModelManager`
   - Should use: `BedrockModelCatalog`
   - See: `NOTEBOOK_UPDATE_GUIDE.md` Section 2

3. **UnifiedModelManager.ipynb** ⚠️ NEEDS UPDATE
   - Currently uses: `UnifiedModelManager`
   - Should use: `BedrockModelCatalog`
   - See: `NOTEBOOK_UPDATE_GUIDE.md` Section 3

4. **Caching.ipynb** ⚠️ NEEDS ENHANCEMENT
   - Currently documents: Bedrock prompt caching only
   - Should add: Model catalog cache modes documentation
   - See: `NOTEBOOK_UPDATE_GUIDE.md` Section 4

### Compatible (No Changes Needed)

5. **HelloWorld_LLMManager.ipynb** ✅ COMPATIBLE
   - Uses `LLMManager` which automatically uses `BedrockModelCatalog` internally
   - No changes required

6. **HelloWorld_MessageBuilder.ipynb** ✅ COMPATIBLE
   - Uses `MessageBuilder` which is independent of catalog system
   - No changes required

7. **HelloWorld_MessageBuilder_Demo.ipynb** ✅ COMPATIBLE
   - Uses `MessageBuilder` which is independent of catalog system
   - No changes required

8. **HelloWorld_MessageBuilder_Paths.ipynb** ✅ COMPATIBLE
   - Uses `MessageBuilder` which is independent of catalog system
   - No changes required

9. **HelloWorld_Streaming_Demo.ipynb** ✅ COMPATIBLE
   - Uses `LLMManager` streaming which handles catalog internally
   - No changes required

10. **ParallelLLMManager_Demo.ipynb** ✅ COMPATIBLE
    - Uses `ParallelLLMManager` which handles catalog internally
    - No changes required

11. **ResponseValidation.ipynb** ✅ COMPATIBLE
    - Response validation is independent of catalog system
    - No changes required

## Quick Migration Summary

### Import Changes
```python
# Old
from bestehorn_llmmanager.bedrock import UnifiedModelManager, ModelManager, CRISManager

# New
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
```

### Initialization Changes
```python
# Old
manager = UnifiedModelManager()
manager.refresh_unified_data()

# New
catalog = BedrockModelCatalog()  # Automatic data fetching
```

### Method Calls (Same API)
```python
# These work the same in both old and new systems
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
is_available = catalog.is_model_available("Claude 3 Haiku", "us-east-1")
all_models = catalog.list_models()
```

## New Features to Demonstrate

### Cache Modes
```python
from bestehorn_llmmanager.bedrock.catalog import CacheMode

# FILE mode (persistent)
catalog_file = BedrockModelCatalog(cache_mode=CacheMode.FILE)

# MEMORY mode (process lifetime)
catalog_memory = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)

# NONE mode (always fresh)
catalog_none = BedrockModelCatalog(cache_mode=CacheMode.NONE)
```

### Catalog Metadata
```python
metadata = catalog.get_catalog_metadata()
print(f"Source: {metadata.source.value}")  # API, CACHE, or BUNDLED
print(f"Retrieved: {metadata.retrieval_timestamp}")
print(f"Regions: {metadata.api_regions_queried}")
```

## Update Instructions

For detailed step-by-step instructions on updating each notebook, see:

**`NOTEBOOK_UPDATE_GUIDE.md`**

This guide includes:
- Cell-by-cell update instructions
- Code examples for each notebook
- New cells to add
- Common issues and solutions
- Testing checklist

## Timeline

- **Current:** Notebooks use deprecated classes (with warnings)
- **Target:** Update notebooks before version 4.0.0 release
- **Deadline:** Before old managers are removed (12 months from deprecation)

## Resources

- **Update Guide:** `NOTEBOOK_UPDATE_GUIDE.md` (detailed instructions)
- **Migration Guide:** `../docs/MIGRATION_GUIDE.md` (general migration)
- **API Reference:** `../docs/forLLMConsumption.md` (API documentation)
- **Examples:** `../examples/catalog_*.py` (working examples)

## Notes

- The old manager classes still work but emit deprecation warnings
- The new `BedrockModelCatalog` provides the same functionality with better reliability
- All method signatures remain compatible
- The update is primarily import and initialization changes
- LLMManager users don't need to change anything (automatic integration)

## Support

For questions or issues:
- See `NOTEBOOK_UPDATE_GUIDE.md` for detailed instructions
- Check `../docs/MIGRATION_GUIDE.md` for troubleshooting
- Review `../examples/catalog_*.py` for working examples
