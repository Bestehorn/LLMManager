# Design Document: Model Manager Redesign

## Overview

This design proposes a complete redesign of the Model Manager system to address critical limitations and simplify the architecture. The new design eliminates HTML parsing, consolidates multiple managers into a single class, supports no-cache operation, and includes bundled fallback data.

### Key Changes

1. **API-Only Approach**: Replace HTML parsing with AWS Bedrock API calls
2. **Single Manager Class**: Consolidate `ModelManager`, `CRISManager`, and `UnifiedModelManager` into `BedrockModelCatalog`
3. **Single Cache File**: Replace multiple files (HTML + JSON) with one unified JSON cache
4. **No-Cache Mode**: Support operation without file system access
5. **Bundled Fallback**: Include pre-generated model data in the package
6. **Configurable Paths**: All file paths controllable via parameters

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BedrockModelCatalog                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Initialization Strategy                    │ │
│  │  1. Try: Load from cache (if enabled & valid)          │ │
│  │  2. Try: Fetch from AWS APIs                           │ │
│  │  3. Fallback: Load bundled data                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ API Fetcher  │  │ Cache Manager│  │ Bundled Data     │  │
│  │              │  │              │  │ Loader           │  │
│  │ - Models API │  │ - Read/Write │  │                  │  │
│  │ - CRIS API   │  │ - Validation │  │ - Package data   │  │
│  │ - Parallel   │  │ - Expiration │  │ - Version check  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Unified Catalog (In-Memory)                   │ │
│  │  - Models + CRIS data                                   │ │
│  │  - Fast lookups                                         │ │
│  │  - Query methods                                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Initialization
    │
    ├─> Cache Mode Check
    │   ├─> "none": Skip to API Fetch
    │   ├─> "memory": Skip to API Fetch (store in memory only)
    │   └─> "file": Check cache validity
    │       ├─> Valid: Load from cache → Done
    │       └─> Invalid/Missing: Continue to API Fetch
    │
    ├─> API Fetch (Parallel)
    │   ├─> list-foundation-models (all regions)
    │   ├─> list-inference-profiles (all regions)
    │   ├─> Success: Transform & Cache → Done
    │   └─> Failure: Continue to Fallback
    │
    └─> Bundled Fallback
        ├─> Load from package data
        ├─> Log warning about stale data
        └─> Done
```

## Components and Interfaces

### 1. BedrockModelCatalog (Main Class)

```python
class BedrockModelCatalog:
    """
    Unified catalog for AWS Bedrock model and CRIS data.
    
    Replaces: ModelManager, CRISManager, UnifiedModelManager
    """
    
    def __init__(
        self,
        cache_mode: CacheMode = CacheMode.FILE,
        cache_directory: Optional[Path] = None,
        cache_max_age_hours: float = 24.0,
        force_refresh: bool = False,
        timeout: int = 30,
        max_workers: int = 10,
        fallback_to_bundled: bool = True,
    ) -> None:
        """
        Initialize the Bedrock model catalog.
        
        Args:
            cache_mode: Caching strategy (FILE, MEMORY, NONE)
            cache_directory: Directory for cache file (default: ~/.bestehorn-llmmanager/cache)
            cache_max_age_hours: Maximum cache age before refresh
            force_refresh: Force API refresh even if cache is valid
            timeout: API call timeout in seconds
            max_workers: Parallel workers for multi-region API calls
            fallback_to_bundled: Use bundled data if API fails
        """
        
    def ensure_catalog_available(self) -> UnifiedCatalog:
        """
        Ensure catalog data is available using the initialization strategy.
        
        Returns:
            UnifiedCatalog with model and CRIS data
            
        Raises:
            CatalogUnavailableError: If all data sources fail
        """
        
    def get_model_info(self, model_name: str, region: str) -> Optional[ModelAccessInfo]:
        """Get access information for a model in a region."""
        
    def is_model_available(self, model_name: str, region: str) -> bool:
        """Check if model is available in region."""
        
    def list_models(
        self,
        region: Optional[str] = None,
        provider: Optional[str] = None,
        streaming_only: bool = False
    ) -> List[ModelInfo]:
        """List models with optional filtering."""
        
    def get_catalog_metadata(self) -> CatalogMetadata:
        """Get metadata about the catalog (source, timestamp, version)."""
```

### 2. API Fetcher

```python
class BedrockAPIFetcher:
    """
    Fetches model and CRIS data from AWS Bedrock APIs.
    """
    
    def fetch_all_data(self, regions: List[str]) -> RawCatalogData:
        """
        Fetch both model and CRIS data from all regions in parallel.
        
        Returns:
            RawCatalogData containing API responses
        """
        
    def _fetch_foundation_models(self, region: str) -> List[Dict]:
        """Fetch foundation models from a single region."""
        # Uses: aws bedrock list-foundation-models
        
    def _fetch_inference_profiles(self, region: str) -> List[Dict]:
        """Fetch inference profiles from a single region."""
        # Uses: aws bedrock list-inference-profiles
```

### 3. Cache Manager

```python
class CacheManager:
    """
    Manages catalog caching with configurable modes.
    """
    
    def __init__(
        self,
        mode: CacheMode,
        directory: Optional[Path] = None,
        max_age_hours: float = 24.0
    ) -> None:
        """Initialize cache manager with mode and settings."""
        
    def load_cache(self) -> Optional[UnifiedCatalog]:
        """
        Load catalog from cache if valid.
        
        Returns:
            UnifiedCatalog if cache is valid, None otherwise
        """
        
    def save_cache(self, catalog: UnifiedCatalog) -> None:
        """
        Save catalog to cache based on mode.
        
        Args:
            catalog: Catalog to cache
        """
        
    def is_cache_valid(self) -> bool:
        """Check if cache exists and is not expired."""
        
    def get_cache_path(self) -> Path:
        """Get the path to the cache file."""
        # Returns: {cache_directory}/bedrock_catalog.json
```

### 4. Bundled Data Loader

```python
class BundledDataLoader:
    """
    Loads pre-packaged fallback data from the package.
    """
    
    @staticmethod
    def load_bundled_catalog() -> UnifiedCatalog:
        """
        Load bundled catalog from package data.
        
        Returns:
            UnifiedCatalog from bundled JSON
            
        Raises:
            BundledDataError: If bundled data is missing or corrupt
        """
        
    @staticmethod
    def get_bundled_data_path() -> Path:
        """Get path to bundled data file in package."""
        # Returns: package_data/bedrock_catalog_bundled.json
        
    @staticmethod
    def get_bundled_data_metadata() -> Dict[str, Any]:
        """Get metadata about bundled data (generation time, version)."""
```

### 5. Data Transformer

```python
class CatalogTransformer:
    """
    Transforms raw API data into unified catalog structures.
    """
    
    def transform_api_data(self, raw_data: RawCatalogData) -> UnifiedCatalog:
        """
        Transform raw API responses into unified catalog.
        
        Args:
            raw_data: Raw API responses from fetcher
            
        Returns:
            UnifiedCatalog with correlated data
        """
        
    def _transform_models(self, models_data: List[Dict]) -> Dict[str, ModelInfo]:
        """Transform foundation models API data."""
        
    def _transform_cris(self, cris_data: List[Dict]) -> Dict[str, CRISInfo]:
        """Transform inference profiles API data."""
        
    def _correlate_data(
        self,
        models: Dict[str, ModelInfo],
        cris: Dict[str, CRISInfo]
    ) -> UnifiedCatalog:
        """Correlate model and CRIS data into unified view."""
```

## Data Models

### UnifiedCatalog

```python
@dataclass
class UnifiedCatalog:
    """
    Unified catalog containing all model and CRIS information.
    """
    models: Dict[str, UnifiedModelInfo]
    metadata: CatalogMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for caching."""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedCatalog":
        """Deserialize from dictionary."""
        
    def get_model(self, name: str) -> Optional[UnifiedModelInfo]:
        """Get model by name."""
        
    def filter_models(self, **criteria) -> List[UnifiedModelInfo]:
        """Filter models by criteria."""
```

### CatalogMetadata

```python
@dataclass
class CatalogMetadata:
    """
    Metadata about the catalog source and freshness.
    """
    source: CatalogSource  # API, CACHE, BUNDLED
    retrieval_timestamp: datetime
    api_regions_queried: List[str]
    bundled_data_version: Optional[str]
    cache_file_path: Optional[Path]
```

### CacheMode

```python
class CacheMode(Enum):
    """
    Caching strategy for the catalog.
    """
    FILE = "file"      # Cache to file system
    MEMORY = "memory"  # Cache in memory only (process lifetime)
    NONE = "none"      # No caching, always fetch fresh
```

## File Structure

### New Structure

```
src/bestehorn_llmmanager/bedrock/
├── catalog/
│   ├── __init__.py
│   ├── bedrock_catalog.py          # Main BedrockModelCatalog class
│   ├── api_fetcher.py              # API data fetching
│   ├── cache_manager.py            # Cache management
│   ├── bundled_loader.py           # Bundled data loading
│   └── transformer.py              # Data transformation
├── models/
│   ├── catalog_structures.py       # UnifiedCatalog, CatalogMetadata
│   └── catalog_constants.py        # Constants for new system
└── package_data/
    └── bedrock_catalog_bundled.json # Pre-generated fallback data
```

### Deprecated (Keep for Backward Compatibility)

```
src/bestehorn_llmmanager/bedrock/
├── ModelManager.py                  # DEPRECATED
├── CRISManager.py                   # DEPRECATED
├── UnifiedModelManager.py           # DEPRECATED
├── downloaders/                     # DEPRECATED (HTML parsing)
└── parsers/                         # DEPRECATED (HTML parsing)
```

## Migration Strategy

### Phase 1: Implement New System (Non-Breaking)

1. Create new `catalog/` module with `BedrockModelCatalog`
2. Implement API-only fetching
3. Implement cache management with modes
4. Generate and bundle fallback data
5. Add comprehensive tests

### Phase 2: Deprecation Warnings

1. Add deprecation warnings to old managers
2. Update documentation to recommend new system
3. Provide migration examples
4. Update all examples to use new system

### Phase 3: Migration Period (6-12 months)

1. Both systems coexist
2. Users migrate gradually
3. Monitor usage and provide support

### Phase 4: Code Cleanup and Removal (Major Version Bump)

1. **Remove deprecated manager classes**
   - Delete `ModelManager.py`
   - Delete `CRISManager.py`
   - Delete `UnifiedModelManager.py`

2. **Remove HTML parsing infrastructure**
   - Delete `downloaders/` directory (HTML downloading)
   - Delete `parsers/` directory (HTML parsing)
   - Remove `BeautifulSoup4` and `lxml` from dependencies

3. **Remove obsolete data structures**
   - Remove HTML-specific constants from `models/constants.py`
   - Remove HTML-specific constants from `models/cris_constants.py`
   - Clean up unused model structures

4. **Update imports and references**
   - Update `__init__.py` files to remove old exports
   - Update any internal code that referenced old managers
   - Ensure no broken imports remain

5. **Update test suite**
   - Delete tests for removed managers (`test_ModelManager.py`, `test_CRISManager.py`, `test_UnifiedModelManager.py`)
   - Delete tests for HTML parsing (`test_bedrock_parser.py`, `test_cris_parser.py`, etc.)
   - Delete tests for HTML downloading
   - Update integration tests to use new system
   - Ensure test coverage for new `BedrockModelCatalog`

6. **Update documentation**
   - Remove references to old managers from all docs
   - Update migration guide to reflect removal
   - Update API reference documentation
   - Update examples and tutorials

7. **Clean up package metadata**
   - Update `pyproject.toml` to remove unused dependencies
   - Update package description if needed
   - Bump major version number

## Error Handling

### Error Hierarchy

```python
class CatalogError(Exception):
    """Base exception for catalog operations."""

class CatalogUnavailableError(CatalogError):
    """Raised when catalog cannot be obtained from any source."""

class APIFetchError(CatalogError):
    """Raised when API fetching fails."""

class CacheError(CatalogError):
    """Raised when cache operations fail."""

class BundledDataError(CatalogError):
    """Raised when bundled data is missing or corrupt."""
```

### Error Handling Strategy

1. **API Failures**: Log warning, try cache
2. **Cache Failures**: Log warning, try API
3. **Both Fail**: Try bundled data
4. **All Fail**: Raise `CatalogUnavailableError` with detailed message

## Testing Strategy

### Unit Tests

1. Test each component in isolation
2. Mock AWS API calls
3. Test cache modes (FILE, MEMORY, NONE)
4. Test error handling and fallbacks
5. Test data transformation logic

### Integration Tests

1. Test with real AWS APIs (requires credentials)
2. Test cache file creation and loading
3. Test bundled data loading
4. Test end-to-end initialization strategies

### Property-Based Tests

1. **Property 1: Initialization always succeeds with bundled data**
   - For any configuration, if bundled data exists, initialization SHALL NOT fail
   - **Validates: Requirements 3.2, 9.2**

2. **Property 2: Cache mode determines file system usage**
   - For any catalog with cache_mode="none", no files SHALL be written
   - **Validates: Requirements 2.1, 4.2**

3. **Property 3: API data freshness**
   - For any catalog from API, retrieval_timestamp SHALL be recent (< 1 minute old)
   - **Validates: Requirements 1.5, 10.3**

4. **Property 4: Model availability consistency**
   - For any model M and region R, if is_model_available(M, R) returns True, then get_model_info(M, R) SHALL NOT return None
   - **Validates: Requirements 5.4**

5. **Property 5: Cache round-trip consistency**
   - For any catalog C, saving then loading SHALL produce equivalent catalog
   - **Validates: Requirements 6.3**

## Performance Considerations

### Optimization Strategies

1. **Parallel API Calls**: Use ThreadPoolExecutor for multi-region queries
2. **Connection Pooling**: Reuse boto3 clients across calls
3. **Lazy Loading**: Load catalog only when first accessed
4. **In-Memory Caching**: Keep catalog in memory after first load
5. **Efficient Data Structures**: Use dictionaries for O(1) lookups

### Expected Performance

- **Cold start (no cache)**: 2-5 seconds (parallel API calls)
- **Warm start (valid cache)**: < 100ms (file load)
- **Memory usage**: ~5-10 MB for full catalog
- **Cache file size**: ~500 KB - 1 MB

## Decisions Made

### Decision 1: Default Cache Directory ✅ APPROVED

**Selected Option:** XDG Cache Standard

**Implementation:**
- **Linux/Mac**: `~/.cache/bestehorn-llmmanager/`
- **Windows**: `%LOCALAPPDATA%\bestehorn-llmmanager\cache\`

**Rationale:** Follows OS conventions, allows system tools to manage cache cleanup

**Implementation Details:**
```python
def get_default_cache_directory() -> Path:
    """Get platform-appropriate default cache directory."""
    if platform.system() == "Windows":
        # Windows: Use LOCALAPPDATA
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "bestehorn-llmmanager" / "cache"
        # Fallback to user home
        return Path.home() / ".bestehorn-llmmanager" / "cache"
    else:
        # Linux/Mac: Use XDG_CACHE_HOME or default
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            return Path(xdg_cache) / "bestehorn-llmmanager"
        return Path.home() / ".cache" / "bestehorn-llmmanager"
```

### Decision 2: Bundled Data Update Frequency ✅ APPROVED

**Selected Option:** Update with every package release

**Implementation:**
- Add pre-build step to CI/CD pipeline
- Generate fresh bundled data from AWS APIs before building package
- Include generation timestamp and package version in metadata
- Fail build if bundled data generation fails (ensures data freshness)

**CI/CD Integration:**
```yaml
# .github/workflows/build.yml
- name: Generate Bundled Model Data
  run: |
    python scripts/generate_bundled_data.py
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Decision 3: Cache Invalidation Strategy ✅ APPROVED

**Selected Option:** Hybrid (time-based + version-based)

**Implementation:**
- Cache includes package version in metadata
- Invalidate cache if package version changes (major/minor)
- Also invalidate if cache age exceeds max_cache_age_hours
- Allow patch version updates to use existing cache

**Logic:**
```python
def is_cache_valid(self, cache_data: Dict) -> bool:
    # Check package version compatibility
    cache_version = cache_data.get("package_version")
    current_version = get_package_version()
    
    if not versions_compatible(cache_version, current_version):
        return False  # Version mismatch
    
    # Check cache age
    cache_age = get_cache_age_hours(cache_data["timestamp"])
    if cache_age > self.max_cache_age_hours:
        return False  # Too old
    
    return True  # Valid
```

### Decision 4: API Rate Limiting ✅ APPROVED

**Selected Option:** Exponential backoff with retries

**Implementation:**
- Use exponential backoff for transient errors
- Maximum 3 retry attempts per API call
- Initial wait: 1 second, max wait: 10 seconds
- Log rate limit warnings for monitoring

**Implementation:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ClientError, BotoCoreError))
)
def fetch_with_retry(self, client, method: str, **kwargs):
    """Fetch data with exponential backoff retry."""
    return getattr(client, method)(**kwargs)
```

### Decision 5: Bundled Data Size ✅ APPROVED

**Selected Option:** Full data (~500 KB)

**Rationale:** 
- Size is acceptable for modern systems
- Provides complete fallback coverage
- Ensures all models are available offline
- Simplifies implementation (no filtering logic needed)

### Decision 6: Backward Compatibility Duration ✅ APPROVED

**Selected Option:** 12 months (4-6 releases)

**Timeline:**
- **Release N (Now)**: Implement new system, add deprecation warnings
- **Release N+1 to N+5**: Both systems coexist, encourage migration
- **Release N+6 (12 months)**: Remove deprecated managers (major version bump)

**Deprecation Warning:**
```python
warnings.warn(
    "UnifiedModelManager is deprecated and will be removed in version X.0.0. "
    "Please migrate to BedrockModelCatalog. "
    "See migration guide: https://...",
    DeprecationWarning,
    stacklevel=2
)
```

### Decision 7: LLMManager Integration ✅ APPROVED

**Selected Option:** Transparent replacement

**Implementation:**
- LLMManager internally uses BedrockModelCatalog
- No user code changes required
- Old managers deprecated but not used internally
- Seamless upgrade experience

**Internal Change:**
```python
# LLMManager.py - Internal change (transparent to users)
class LLMManager:
    def __init__(self, ...):
        # OLD: self._model_manager = UnifiedModelManager()
        # NEW: 
        self._catalog = BedrockModelCatalog(
            cache_mode=CacheMode.FILE,
            fallback_to_bundled=True
        )
```

## Additional Scope Items

### Notebooks to Update

The following notebooks need to be reviewed and updated:

1. **notebooks/CRISManager.ipynb** - Replace with BedrockModelCatalog examples
2. **notebooks/ModelIDManager.ipynb** - Update to use new catalog
3. **notebooks/UnifiedModelManager.ipynb** - Replace with BedrockModelCatalog examples
4. **notebooks/HelloWorld_LLMManager.ipynb** - Verify compatibility (should work transparently)
5. **notebooks/ParallelLLMManager_Demo.ipynb** - Verify compatibility
6. **notebooks/Caching.ipynb** - Update to document new cache modes
7. **notebooks/ResponseValidation.ipynb** - Verify compatibility

**Actions Required:**
- Replace old manager imports with new catalog
- Update file path examples to show configurability
- Add examples of cache modes (FILE, MEMORY, NONE)
- Add bundled data fallback examples
- Test all notebooks for functionality

### Documentation Files to Update

#### Critical Updates (Must Review)

1. **docs/forLLMConsumption.md** ⚠️ CRITICAL
   - Primary API documentation for LLM consumption
   - Complete rewrite of model management section
   - Remove all HTML parsing references
   - Document BedrockModelCatalog comprehensively

2. **README.md** ⚠️ CRITICAL
   - Main entry point for users
   - Update all code examples
   - Document new features (cache modes, bundled data)
   - Update installation instructions

3. **docs/ProjectStructure.md**
   - Update architecture diagrams
   - Document new catalog/ module
   - Mark deprecated modules

#### Files to Review and Update

4. **docs/CRIS_API_IMPLEMENTATION_PLAN.md**
   - May be obsolete (CRIS API already implemented)
   - Review and archive or update

5. **docs/AWS_DOCUMENTATION_CHANGES.md**
   - May reference HTML parsing
   - Update or remove if obsolete

6. **docs/caching.md**
   - Update to document new cache modes
   - Document cache directory configuration

7. **docs/migration_guide_v3.md**
   - Review for relevance
   - May need new migration guide for v4

#### Files to Remove (After Deprecation Period)

8. **docs/CRIS.htm** - Generated file, will be removed
9. **docs/CRIS.json** - Generated file, will be removed
10. **docs/FoundationalModels.htm** - Generated file, will be removed
11. **docs/FoundationalModels.json** - Generated file, will be removed

**Note:** These files should be added to .gitignore immediately

### Examples to Update

All Lambda examples in `examples/` directory:
- ✅ Already created new examples (lambda_unified_model_manager.py, etc.)
- Need to review and ensure they demonstrate new system
- Add examples for all cache modes
- Add bundled data fallback examples

## Dependencies

### New Dependencies

None - all required dependencies (boto3, botocore) already exist

**Note:** May need to add `tenacity` for retry logic (lightweight, ~50 KB)

### Removed Dependencies (After Deprecation Period)

- `beautifulsoup4` - No longer needed without HTML parsing
- `lxml` - No longer needed without HTML parsing
- `requests` - No longer needed without HTML downloads

### Dependency Impact

- **Package size reduction**: ~2-3 MB (after removing BS4 and lxml)
- **Installation time**: Faster (fewer dependencies)
- **Security**: Fewer dependencies = smaller attack surface

## Security Considerations

1. **AWS Credentials**: Use standard boto3 credential chain
2. **File Permissions**: Cache files should be user-readable only (0600)
3. **Path Traversal**: Validate cache_directory parameter
4. **Bundled Data Integrity**: Include checksum in metadata
5. **API Timeouts**: Prevent hanging on slow/unresponsive APIs

## Remaining Open Points

### Minor Implementation Details (To Be Decided During Implementation)

1. **Tenacity Dependency**
   - **Question:** Add `tenacity` library for retry logic or implement custom?
   - **Options:** 
     - A: Add tenacity (~50 KB, well-tested)
     - B: Implement custom retry logic
   - **Recommendation:** Add tenacity (battle-tested, minimal overhead)

2. **Cache File Format**
   - **Question:** Use compressed JSON or plain JSON?
   - **Options:**
     - A: Plain JSON (human-readable, ~500 KB)
     - B: Gzipped JSON (smaller, ~100 KB, not human-readable)
   - **Recommendation:** Plain JSON (size is acceptable, easier debugging)

3. **Bundled Data Location**
   - **Question:** Where in package structure?
   - **Options:**
     - A: `src/bestehorn_llmmanager/bedrock/package_data/`
     - B: `src/bestehorn_llmmanager/data/`
   - **Recommendation:** Option A (keeps it with bedrock module)

4. **Logging Verbosity**
   - **Question:** Default log level for catalog operations?
   - **Options:**
     - A: INFO (shows cache hits/misses, API calls)
     - B: WARNING (only shows problems)
     - C: DEBUG (detailed information)
   - **Recommendation:** INFO for initialization, DEBUG for details

5. **API Pagination**
   - **Question:** Handle pagination for list-foundation-models?
   - **Current:** API returns all models in single response
   - **Action:** Implement pagination support for future-proofing

6. **Model Name Normalization**
   - **Question:** How to handle model name variations?
   - **Current:** ModelCRISCorrelator has normalization logic
   - **Action:** Reuse existing normalization in new transformer

### Non-Blocking Questions (Can Be Addressed Later)

7. **Metrics and Monitoring**
   - Add optional metrics for cache hit rates?
   - Track API call latencies?
   - **Decision:** Add in future release if needed

8. **Cache Warming**
   - Provide CLI tool to pre-warm cache?
   - **Decision:** Add in future release if requested

9. **Multi-Account Support**
   - Support different AWS accounts/profiles?
   - **Decision:** Already supported via boto3 credential chain

10. **Async API Support**
    - Provide async version of BedrockModelCatalog?
    - **Decision:** Add in future release if requested

## Documentation Updates Required

### Critical Documentation Updates

1. **README.md**
   - Update all examples to use `BedrockModelCatalog`
   - Remove references to HTML parsing
   - Document new cache modes
   - Update installation instructions (fewer dependencies)

2. **docs/forLLMConsumption.md** (CRITICAL)
   - Complete rewrite of model management section
   - Remove all HTML parsing references
   - Document new `BedrockModelCatalog` API
   - Update all code examples
   - Document cache modes and use cases
   - Add Lambda-specific guidance

3. **docs/** Directory Review
   - Audit all files for old manager references
   - Remove or update HTML parsing documentation
   - Update architecture diagrams
   - Review and update all code examples

4. **notebooks/** Directory
   - Review all Jupyter notebooks
   - Update file loading approaches
   - Replace old manager usage with new catalog
   - Test all notebooks for functionality

5. **examples/** Directory
   - Update Lambda examples (already created, need review)
   - Update all other examples
   - Add new examples for cache modes
   - Add bundled data fallback examples

6. **Migration Guide** (NEW)
   - Create comprehensive migration guide
   - Side-by-side code comparisons
   - Common migration scenarios
   - Troubleshooting section

7. **API Reference**
   - Document `BedrockModelCatalog` class
   - Document all cache modes
   - Document bundled data system
   - Mark old managers as deprecated
