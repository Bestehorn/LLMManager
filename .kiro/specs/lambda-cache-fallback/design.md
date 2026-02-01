# Design Document: Lambda Cache Fallback

## Overview

This feature implements a multi-location cache strategy for the bestehorn-llmmanager package to ensure successfully retrieved model catalog data is always used, even when cache writes fail due to filesystem constraints (e.g., AWS Lambda's read-only HOME directory).

The current implementation has a critical flaw: when cache writes fail after successful API retrieval, the system falls back to bundled data instead of using the fresh data it just retrieved. This design fixes that by:

1. Supporting multiple cache locations with priority ordering
2. Attempting writes to fallback locations when primary location fails
3. Always using successfully retrieved data regardless of cache write success
4. Providing comprehensive logging for debugging cache behavior

## Architecture

### Current Architecture

```
BedrockModelCatalog.ensure_catalog_available()
  ├─> CacheManager.load_cache() [single location]
  ├─> BedrockAPIFetcher.fetch_all_data()
  ├─> CacheManager.save_cache() [single location, raises CacheError on failure]
  └─> BundledDataLoader.load_bundled_catalog() [fallback on any error]
```

**Problem**: If `save_cache()` raises `CacheError`, the exception propagates and triggers bundled data fallback, discarding the successfully retrieved data.

### New Architecture

```
BedrockModelCatalog.ensure_catalog_available()
  ├─> CacheManager.load_cache() [tries multiple locations]
  ├─> BedrockAPIFetcher.fetch_all_data()
  ├─> CacheManager.save_cache() [tries multiple locations, never raises]
  └─> BundledDataLoader.load_bundled_catalog() [only if retrieval failed]
```

**Solution**: `save_cache()` tries multiple locations and logs warnings instead of raising exceptions. Retrieved data is always used.

## Components and Interfaces

### 1. CatalogFilePaths (Modified)

**File**: `src/bestehorn_llmmanager/bedrock/models/catalog_constants.py`

**New Methods**:
```python
@staticmethod
def get_fallback_cache_directory() -> Path:
    """
    Get fallback cache directory (writable in Lambda).
    
    Returns:
        Path to /tmp/bestehorn-llmmanager-cache/
    """
    return Path("/tmp") / "bestehorn-llmmanager-cache"

@staticmethod
def get_all_cache_locations() -> List[Path]:
    """
    Get all cache locations in priority order.
    
    Returns:
        List of cache directory paths:
        1. Primary (platform-specific)
        2. Fallback (/tmp)
    """
    return [
        CatalogFilePaths.get_default_cache_directory(),
        CatalogFilePaths.get_fallback_cache_directory(),
    ]
```

**Rationale**: Centralize cache location logic in the constants module where other path logic lives.

### 2. CacheManager (Modified)

**File**: `src/bestehorn_llmmanager/bedrock/catalog/cache_manager.py`

**Modified Methods**:

```python
def __init__(
    self,
    mode: CacheMode,
    directory: Optional[Path] = None,
    max_age_hours: float = 24.0,
) -> None:
    """
    Initialize cache manager with mode and settings.
    
    Changes:
    - Store list of cache locations instead of single location
    - Primary location is user-specified or platform default
    - Fallback location is always /tmp
    """
    # ... existing validation ...
    
    if self._mode == CacheMode.FILE:
        primary_dir = directory or CatalogFilePaths.get_default_cache_directory()
        fallback_dir = CatalogFilePaths.get_fallback_cache_directory()
        
        self._cache_locations: List[Path] = [
            primary_dir / CatalogFilePaths.CACHE_FILENAME,
            fallback_dir / CatalogFilePaths.CACHE_FILENAME,
        ]
    else:
        self._cache_locations = []

def load_cache(self) -> Optional[UnifiedCatalog]:
    """
    Load catalog from cache if valid.
    
    Changes:
    - Try each cache location in priority order
    - Log DEBUG for each failed attempt
    - Log INFO for successful load with path
    - Return first valid cache found
    """
    if self._mode == CacheMode.NONE:
        logger.debug(CatalogLogMessages.CACHE_SKIPPED.format(mode=self._mode.value))
        return None

    if self._mode == CacheMode.MEMORY:
        # ... existing memory logic ...
        return self._memory_cache

    # FILE mode - try each location
    for cache_path in self._cache_locations:
        if not cache_path.exists():
            logger.debug(f"Cache file does not exist: {cache_path}")
            continue
            
        if not self._is_cache_file_valid(cache_path=cache_path):
            logger.debug(f"Cache file invalid or expired: {cache_path}")
            continue
            
        try:
            logger.info(f"Loading catalog from cache: {cache_path}")
            with open(cache_path, mode="r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            catalog = UnifiedCatalog.from_dict(data=cache_data)
            logger.info(f"Loaded model catalog cache from {cache_path}")
            logger.info(f"Model catalog loaded: {catalog.model_count} models across {len(catalog.metadata.api_regions_queried)} regions")
            return catalog
            
        except (OSError, IOError, json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to load cache from {cache_path}: {e}")
            continue
    
    # No valid cache found
    logger.debug("No valid cache found in any location")
    return None

def save_cache(self, catalog: UnifiedCatalog) -> None:
    """
    Save catalog to cache based on mode.
    
    Changes:
    - Try each cache location in priority order
    - Log WARNING for each failed attempt with path and error
    - Log WARNING if write succeeds to fallback location
    - Log INFO if write succeeds to primary location
    - Log WARNING if all writes fail but don't raise exception
    - Never raise CacheError (graceful degradation)
    """
    if self._mode == CacheMode.NONE:
        logger.debug(CatalogLogMessages.CACHE_SKIPPED.format(mode=self._mode.value))
        return

    if self._mode == CacheMode.MEMORY:
        # ... existing memory logic ...
        return

    # FILE mode - try each location
    write_succeeded = False
    
    for i, cache_path in enumerate(self._cache_locations):
        is_primary = (i == 0)
        
        try:
            # Create directory if needed
            cache_dir = cache_path.parent
            if not cache_dir.exists():
                logger.debug(f"Creating cache directory: {cache_dir}")
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Serialize catalog
            cache_data = catalog.to_dict()
            
            # Add package version
            try:
                from ..._version import __version__
                cache_data[CatalogCacheFields.PACKAGE_VERSION] = __version__
            except (ImportError, AttributeError):
                logger.warning("Package version not available")
            
            # Write to file
            with open(cache_path, mode="w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # Log success
            if is_primary:
                logger.info(f"Successfully saved catalog to cache: {cache_path}")
            else:
                logger.warning(f"Cache written to alternative location: {cache_path}")
            
            write_succeeded = True
            break  # Success - don't try remaining locations
            
        except (OSError, IOError, PermissionError) as e:
            logger.warning(f"Failed to write cache to {cache_path}: {e}")
            continue
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize cache data for {cache_path}: {e}")
            continue
    
    if not write_succeeded:
        logger.warning(
            "Cache data retrieved successfully but could not be written to disk. "
            "Using retrieved data in memory."
        )

def _is_cache_file_valid(self, cache_path: Path) -> bool:
    """
    Check if a specific cache file is valid.
    
    New helper method to check validity of a specific cache file.
    Extracted from is_cache_valid() to support multi-location checking.
    
    Args:
        cache_path: Path to cache file to validate
        
    Returns:
        True if cache file is valid, False otherwise
    """
    try:
        with open(cache_path, mode="r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        # Validate structure
        if not self._validate_cache_structure(data=cache_data):
            return False
        
        # Check timestamp freshness
        timestamp_str = cache_data[CatalogCacheFields.METADATA][
            CatalogCacheFields.RETRIEVAL_TIMESTAMP
        ]
        cache_timestamp = datetime.fromisoformat(timestamp_str)
        cache_age = datetime.now() - cache_timestamp
        
        if cache_age > timedelta(hours=self._max_age_hours):
            return False
        
        # Check version compatibility
        if not self._check_version_compatibility(cache_data=cache_data):
            return False
        
        return True
        
    except (OSError, IOError, json.JSONDecodeError, KeyError, ValueError):
        return False
```

**Key Changes**:
- `__init__`: Store list of cache locations instead of single path
- `load_cache()`: Try each location in order, return first valid cache
- `save_cache()`: Try each location in order, never raise exceptions
- `_is_cache_file_valid()`: New helper to validate specific cache file
- `is_cache_valid()`: Delegate to `_is_cache_file_valid()` for first location (backward compatibility)

### 3. BedrockModelCatalog (Modified)

**File**: `src/bestehorn_llmmanager/bedrock/catalog/bedrock_catalog.py`

**Modified Method**:

```python
def ensure_catalog_available(self) -> UnifiedCatalog:
    """
    Ensure catalog data is available using the initialization strategy.
    
    Changes:
    - Remove try/except around save_cache() since it no longer raises
    - Add logging for model count and region count after successful load
    """
    # Return cached catalog if already loaded
    if self._catalog is not None:
        logger.debug("Returning in-memory cached catalog")
        return self._catalog

    cache_error: Optional[str] = None
    api_error: Optional[str] = None
    bundled_error: Optional[str] = None

    # Step 1: Try cache
    if not self._force_refresh and self._cache_mode != CacheMode.NONE:
        try:
            catalog = self._cache_manager.load_cache()
            if catalog is not None:
                self._catalog = catalog
                logger.info(
                    f"Model catalog loaded: {catalog.model_count} models "
                    f"across {len(catalog.metadata.api_regions_queried)} regions"
                )
                logger.info(
                    CatalogLogMessages.CATALOG_INIT_COMPLETED.format(
                        source="cache",
                        count=catalog.model_count,
                    )
                )
                return catalog
            else:
                cache_error = "Cache miss or invalid"
                logger.debug(f"Cache load failed: {cache_error}")
        except Exception as e:
            cache_error = str(e)
            logger.warning(
                CatalogLogMessages.ERROR_CACHE_READ_FAILED.format(error=cache_error)
            )

    # Step 2: Try API fetch
    try:
        logger.info("Attempting to fetch catalog from AWS APIs")
        raw_data = self._api_fetcher.fetch_all_data()

        # Transform raw data to unified catalog
        catalog = self._transformer.transform_api_data(raw_data=raw_data)

        # Save to cache if enabled (never raises exception now)
        if self._cache_mode != CacheMode.NONE:
            self._cache_manager.save_cache(catalog=catalog)

        # Cache in memory
        self._catalog = catalog

        logger.info(
            f"Model catalog loaded: {catalog.model_count} models "
            f"across {len(catalog.metadata.api_regions_queried)} regions"
        )
        logger.info(
            CatalogLogMessages.CATALOG_INIT_COMPLETED.format(
                source="API",
                count=catalog.model_count,
            )
        )
        return catalog

    except Exception as e:
        api_error = str(e)
        logger.warning(CatalogLogMessages.ERROR_API_FETCH_FAILED.format(error=api_error))

    # Step 3: Try bundled data (only if API fetch failed)
    if self._fallback_to_bundled:
        try:
            logger.info("Attempting to load bundled fallback data")
            catalog = BundledDataLoader.load_bundled_catalog()

            # Cache in memory
            self._catalog = catalog

            logger.info(
                f"Model catalog loaded: {catalog.model_count} models "
                f"across {len(catalog.metadata.api_regions_queried)} regions"
            )
            logger.info(
                CatalogLogMessages.CATALOG_INIT_COMPLETED.format(
                    source="bundled",
                    count=catalog.model_count,
                )
            )
            return catalog

        except Exception as e:
            bundled_error = str(e)
            logger.error(
                CatalogLogMessages.ERROR_BUNDLED_LOAD_FAILED.format(error=bundled_error)
            )
    else:
        bundled_error = "Bundled fallback disabled"

    # All sources failed
    if self._fallback_to_bundled:
        error_msg = CatalogErrorMessages.CATALOG_UNAVAILABLE.format(
            cache_error=cache_error or "Not attempted",
            api_error=api_error or "Not attempted",
            bundled_error=bundled_error or "Not attempted",
        )
    else:
        error_msg = CatalogErrorMessages.CATALOG_UNAVAILABLE_NO_BUNDLED.format(
            cache_error=cache_error or "Not attempted",
            api_error=api_error or "Not attempted",
        )

    logger.error(CatalogLogMessages.ERROR_ALL_SOURCES_FAILED)
    raise CatalogUnavailableError(message=error_msg)
```

**Key Changes**:
- Remove try/except around `save_cache()` since it no longer raises exceptions
- Add informational logging after successful catalog load (from any source)
- Bundled data fallback only triggers if API fetch fails (not if cache write fails)

### 4. CatalogLogMessages (Modified)

**File**: `src/bestehorn_llmmanager/bedrock/models/catalog_constants.py`

**New Messages**:
```python
# Cache messages (additions)
CACHE_LOAD_ATTEMPT: Final[str] = "Attempting to load cache from: {path}"
CACHE_LOAD_SUCCESS: Final[str] = "Loaded model catalog cache from {path}"
CACHE_LOAD_FAILED: Final[str] = "Failed to load model catalog cache from {path}"
CACHE_WRITE_ATTEMPT: Final[str] = "Attempting to write cache to: {path}"
CACHE_WRITE_SUCCESS_PRIMARY: Final[str] = "Successfully saved catalog to cache: {path}"
CACHE_WRITE_SUCCESS_FALLBACK: Final[str] = "Cache written to alternative location: {path}"
CACHE_WRITE_FAILED: Final[str] = "Failed to write cache to {path}: {error}"
CACHE_ALL_WRITES_FAILED: Final[str] = (
    "Cache data retrieved successfully but could not be written to disk. "
    "Using retrieved data in memory."
)

# Catalog loaded message
CATALOG_LOADED_INFO: Final[str] = (
    "Model catalog loaded: {model_count} models across {region_count} regions"
)
```

## Data Models

No new data models are required. The existing `UnifiedCatalog` and `CacheMode` structures remain unchanged.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Cache Write Location Priority

*For any* catalog data and cache manager configuration, when attempting to write cache data, the cache manager should try the primary cache location first, and only attempt the fallback location if the primary write fails.

**Validates: Requirements 1.1, 1.2**

### Property 2: Cache Read Location Priority

*For any* cache manager configuration, when attempting to load cache data, the cache manager should try the primary cache location first, and only attempt the fallback location if the primary read fails or returns invalid data.

**Validates: Requirements 2.1, 2.2**

### Property 3: Cache Read Failure Returns None

*For any* cache manager configuration, if all cache read attempts fail (all locations are unavailable or invalid), the cache manager should return None to indicate no cache is available.

**Validates: Requirements 2.5, 7.2**

### Property 4: Retrieved Data Always Used

*For any* successfully retrieved catalog data from AWS APIs, the catalog manager should use that retrieved data for all operations, regardless of whether cache write operations succeed or fail.

**Validates: Requirements 3.1, 3.2, 7.3**

### Property 5: No Bundled Fallback When Retrieval Succeeds

*For any* successful API retrieval, the catalog manager should not invoke the bundled data loader, even if all cache write operations fail.

**Validates: Requirements 3.4**

### Property 6: Primary Location Determined by Platform

*For any* cache manager initialization without explicit directory configuration, the primary cache location should be determined using platform-specific defaults (XDG_CACHE_HOME on Linux/Mac, LOCALAPPDATA on Windows).

**Validates: Requirements 4.1**

### Property 7: Directory Creation with Fallback

*For any* cache location where the directory does not exist, the cache manager should attempt to create the directory, and if creation fails, should skip that location and continue with the next location in the priority list.

**Validates: Requirements 4.4, 4.5**

### Property 8: Backward Compatible Cache Loading

*For any* existing valid cache file in the primary cache location, the cache manager should successfully load it using the existing cache file format.

**Validates: Requirements 5.1, 5.2**

### Property 9: Primary Location Priority When Multiple Caches Exist

*For any* cache manager configuration where valid cache files exist in multiple locations, the cache manager should load and use the cache data from the primary location, ignoring cache files in fallback locations.

**Validates: Requirements 5.5**

### Property 10: Log Messages Include Paths

*For any* cache-related operation (read or write), all log messages related to that operation should include the file path being accessed.

**Validates: Requirements 6.4**

### Property 11: Cache Write Never Raises Exceptions

*For any* cache write operation, the cache manager should never raise exceptions to the caller, regardless of whether the write succeeds or fails at any location.

**Validates: Requirements 7.1**

### Property 12: Filesystem Exceptions Caught and Logged

*For any* filesystem-related exception (OSError, IOError, PermissionError) during cache operations, the cache manager should catch the exception, log it appropriately, and continue with fallback behavior rather than propagating the exception.

**Validates: Requirements 7.4**

### Property 13: Fallback Chain Continues After Failures

*For any* cache operation (read or write) with multiple locations, if an operation fails at one location, the cache manager should continue attempting the remaining locations in the priority list.

**Validates: Requirements 7.5**

## Error Handling

### Exception Handling Strategy

**Current Behavior**:
- `CacheManager.save_cache()` raises `CacheError` on write failures
- Exceptions propagate to `BedrockModelCatalog.ensure_catalog_available()`
- Any exception triggers bundled data fallback

**New Behavior**:
- `CacheManager.save_cache()` catches all exceptions internally
- Logs warnings for each failed write attempt
- Never raises exceptions to caller
- Returns silently after attempting all locations

### Error Categories

1. **Filesystem Errors** (OSError, IOError, PermissionError):
   - Caught during directory creation
   - Caught during file write operations
   - Logged at WARNING level with path and error message
   - Trigger fallback to next location

2. **Serialization Errors** (TypeError, ValueError):
   - Caught during JSON serialization
   - Logged at WARNING level
   - Trigger fallback to next location

3. **Read Errors** (json.JSONDecodeError, KeyError):
   - Caught during cache file loading
   - Logged at DEBUG level (expected in some cases)
   - Trigger fallback to next location

### Logging Levels

- **INFO**: Successful operations (cache loaded, cache saved to primary location)
- **WARNING**: Fallback behavior (cache saved to alternative location, all writes failed, cache write failed at specific location)
- **DEBUG**: Expected failures (cache file doesn't exist, cache invalid, cache read failed)
- **ERROR**: Unexpected errors (should not occur with new design)

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests:

- **Unit tests**: Verify specific scenarios, edge cases, and logging behavior
- **Property tests**: Verify universal properties across all inputs

Both are complementary and necessary for comprehensive coverage. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across many inputs.

### Unit Testing Focus

Unit tests should focus on:

1. **Specific Scenarios**:
   - Primary location writable, fallback not needed
   - Primary location read-only, fallback succeeds
   - Both locations read-only, all writes fail
   - Cache exists in primary location only
   - Cache exists in fallback location only
   - Cache exists in both locations (primary takes precedence)

2. **Edge Cases**:
   - Empty /tmp directory
   - Non-existent parent directories
   - Invalid JSON in cache files
   - Expired cache files
   - Version mismatch in cache files

3. **Integration Points**:
   - BedrockModelCatalog uses retrieved data when cache writes fail
   - Bundled data loader not called when API succeeds
   - Logging output verification

4. **Lambda Environment Simulation**:
   - Mock read-only HOME directory
   - Verify fallback to /tmp succeeds
   - Verify retrieved data is used

### Property-Based Testing Configuration

- **Library**: Use `hypothesis` for Python property-based testing
- **Iterations**: Minimum 100 iterations per property test
- **Tagging**: Each property test must reference its design document property
- **Tag format**: `# Feature: lambda-cache-fallback, Property {number}: {property_text}`

### Property Test Implementation

Each correctness property must be implemented by a single property-based test:

1. **Property 1**: Generate random catalog data, mock filesystem to fail primary writes, verify fallback is attempted
2. **Property 2**: Generate random cache configurations, mock filesystem to fail primary reads, verify fallback is attempted
3. **Property 3**: Generate random configurations, mock all reads to fail, verify None is returned
4. **Property 4**: Generate random catalog data, mock cache writes to fail, verify retrieved data is used
5. **Property 5**: Generate random catalog data, mock cache writes to fail, verify bundled loader not called
6. **Property 6**: Test on different platform configurations, verify correct primary location
7. **Property 7**: Generate random directory states, mock directory creation failures, verify fallback continues
8. **Property 8**: Generate random valid cache files, verify they load successfully
9. **Property 9**: Generate cache files in multiple locations, verify primary is used
10. **Property 10**: Generate random cache operations, verify all logs include paths
11. **Property 11**: Generate random write scenarios including failures, verify no exceptions raised
12. **Property 12**: Generate random filesystem exceptions, verify they are caught and logged
13. **Property 13**: Generate random failure patterns, verify remaining locations are tried

### Test File Organization

```
test/
├── unit/
│   └── bedrock/
│       └── catalog/
│           ├── test_cache_manager_multi_location.py
│           └── test_bedrock_catalog_cache_fallback.py
└── property/
    └── bedrock/
        └── catalog/
            └── test_cache_fallback_properties.py
```

### Mock Strategy

For testing cache behavior without actual filesystem operations:

```python
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

# Mock Path.exists() to simulate file presence
with patch.object(Path, 'exists', return_value=False):
    # Test cache miss scenario
    pass

# Mock Path.mkdir() to simulate directory creation failure
with patch.object(Path, 'mkdir', side_effect=PermissionError("Read-only filesystem")):
    # Test fallback behavior
    pass

# Mock open() to simulate write failures
with patch('builtins.open', side_effect=PermissionError("Read-only filesystem")):
    # Test write failure handling
    pass
```

## Implementation Notes

### Backward Compatibility

1. **API Compatibility**:
   - No changes to public method signatures
   - `CacheManager.__init__()` accepts same parameters
   - `save_cache()` and `load_cache()` have same signatures
   - `BedrockModelCatalog` API unchanged

2. **Behavior Compatibility**:
   - Existing cache files in primary location continue to work
   - Cache file format unchanged
   - Default cache location unchanged
   - Only new behavior: fallback locations and graceful degradation

3. **Configuration Compatibility**:
   - No new required configuration parameters
   - Existing code works without changes
   - Fallback behavior is automatic

### Performance Considerations

1. **Cache Read Performance**:
   - Minimal overhead: only checks additional locations if primary fails
   - Primary location checked first (most common case)
   - Early return on first valid cache found

2. **Cache Write Performance**:
   - Minimal overhead: only tries fallback if primary fails
   - No performance impact when primary location is writable
   - Fallback adds ~10-50ms in failure cases (acceptable for initialization)

3. **Lambda Cold Start**:
   - No impact on cold start time
   - Fallback to /tmp is fast (in-memory filesystem)
   - Retrieved data used immediately regardless of cache write

### Security Considerations

1. **File Permissions**:
   - Cache directories created with default permissions (0o755)
   - Cache files created with default permissions (0o644)
   - No sensitive data in cache files (public model catalog)

2. **Path Traversal**:
   - All paths constructed using Path objects
   - No user-supplied path components
   - Fallback location is hardcoded constant

3. **Temporary Directory**:
   - /tmp is standard temporary directory on Unix systems
   - Lambda provides isolated /tmp per execution environment
   - Cache files cleaned up by Lambda after execution

### Lambda-Specific Considerations

1. **Filesystem Layout**:
   - HOME directory: Read-only (mounted from container image)
   - /tmp directory: Writable, 512MB limit, ephemeral
   - Cache files are small (~100KB), well within /tmp limits

2. **Execution Environment**:
   - Each Lambda execution has isolated /tmp
   - Cache persists across invocations in same execution environment
   - Cache lost when execution environment is recycled

3. **Logging**:
   - CloudWatch Logs captures all log output
   - WARNING logs help diagnose cache issues
   - INFO logs confirm successful cache operations

## Dependencies

No new dependencies required. All functionality uses existing Python standard library modules:
- `pathlib` for path operations
- `json` for serialization
- `logging` for logging
- `typing` for type hints

## Migration Path

No migration required. The feature is fully backward compatible:

1. **Existing Deployments**:
   - Continue using primary cache location
   - No behavior changes if primary location is writable
   - Automatic fallback if primary location becomes read-only

2. **Lambda Deployments**:
   - Automatically use /tmp fallback
   - No configuration changes needed
   - Retrieved data always used

3. **Testing**:
   - Existing tests continue to pass
   - New tests verify fallback behavior
   - Property tests verify correctness properties
