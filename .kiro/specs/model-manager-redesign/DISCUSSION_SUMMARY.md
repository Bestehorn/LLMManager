# Model Manager Redesign - Discussion Summary

## Executive Summary

This redesign addresses critical limitations in the current Model Manager system by:
1. Eliminating HTML parsing in favor of AWS API calls
2. Consolidating three manager classes into one (`BedrockModelCatalog`)
3. Supporting no-cache operation for Lambda and read-only environments
4. Including bundled fallback data for offline/failure scenarios
5. Making all file paths configurable

## Current Problems Verified

### Problem 1: HTML Parsing is Obsolete ✅ CONFIRMED

**Current State:**
- `ModelManager` downloads and parses HTML from AWS documentation
- `CRISManager` has BOTH HTML parsing AND API fetching (use_api flag)
- HTML files: `docs/FoundationalModels.htm`, `docs/CRIS.htm`

**Evidence:**
```python
# ModelManager.py - Line 130
self._downloader = HTMLDocumentationDownloader(timeout=download_timeout)
self._parser = EnhancedBedrockHTMLParser()

# CRISManager.py - Line 115
self._downloader = HTMLDocumentationDownloader(timeout=download_timeout)
self._parser = CRISHTMLParser()
self._api_fetcher = CRISAPIFetcher(...)  # API method exists!
```

**Conclusion:** CRISManager already has API support (`use_api=True`). ModelManager needs API implementation.

### Problem 2: Multiple Files are Clunky ✅ CONFIRMED

**Current Files Created:**
1. `docs/FoundationalModels.htm` (HTML download)
2. `docs/FoundationalModels.json` (Parsed model data)
3. `docs/CRIS.htm` (HTML download - only if use_api=False)
4. `docs/CRIS.json` (Parsed CRIS data)
5. `src/docs/UnifiedModels.json` (Unified catalog)

**Total:** 4-5 files depending on configuration

**Proposed:** 1 file (`bedrock_catalog.json`)

### Problem 3: Lambda Incompatibility ✅ CONFIRMED

**Current Issue:**
```python
# UnifiedModelManager.py - Line 130-131
self._model_manager = ModelManager(download_timeout=download_timeout)
self._cris_manager = CRISManager(download_timeout=download_timeout)
```

**Problem:** No way to pass custom paths to internal managers!

**Impact:** Cannot use in Lambda without workarounds

### Problem 4: No Fallback Data ✅ CONFIRMED

**Current State:** If API/cache fails, system fails completely

**Proposed:** Bundle pre-generated data in package for fallback

## Proposed Solution Architecture

### New Class: BedrockModelCatalog

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode

# Lambda-friendly usage
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.NONE,  # No file system access
    fallback_to_bundled=True     # Use bundled data if API fails
)

# Traditional usage with caching
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("/tmp"),  # Configurable!
    cache_max_age_hours=24.0
)

# Query models
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
is_available = catalog.is_model_available("Claude 3 Haiku", "us-east-1")
models = catalog.list_models(region="us-east-1", streaming_only=True)
```

### Initialization Strategy (Waterfall)

```
1. Try Cache (if cache_mode != NONE)
   ├─> Valid? → Use it ✓
   └─> Invalid/Missing? → Continue

2. Try AWS APIs (parallel calls)
   ├─> Success? → Cache it (if enabled) → Use it ✓
   └─> Failure? → Continue

3. Try Bundled Data (if fallback_to_bundled=True)
   ├─> Exists? → Use it ✓ (with warning)
   └─> Missing? → FAIL ✗

4. Raise CatalogUnavailableError
```

### AWS APIs to Use

Based on MCP server investigation:

**For Models:**
```bash
aws bedrock list-foundation-models
```
Returns: model ID, name, provider, regions, modalities, streaming support

**For CRIS:**
```bash
aws bedrock list-inference-profiles --type-equals SYSTEM_DEFINED
```
Returns: profile ID, name, model ARNs, region mappings

**Advantages:**
- No HTML parsing
- Always up-to-date
- Faster (parallel API calls)
- More reliable

## Key Design Decisions

### Decision 1: Single Cache File ✅ RECOMMENDED

**Current:** 4-5 files
**Proposed:** 1 file (`bedrock_catalog.json`)

**Benefits:**
- Simpler cache management
- Atomic updates (one file write)
- Easier to validate
- Smaller disk footprint

### Decision 2: Three Cache Modes ✅ RECOMMENDED

```python
class CacheMode(Enum):
    FILE = "file"      # Write to disk (default)
    MEMORY = "memory"  # Keep in memory only (process lifetime)
    NONE = "none"      # No caching, always fetch fresh
```

**Use Cases:**
- `FILE`: Normal usage, persistent cache
- `MEMORY`: Lambda warm starts, no disk I/O
- `NONE`: Lambda cold starts, read-only filesystems

### Decision 3: Bundled Fallback Data ✅ RECOMMENDED

**Approach:**
1. Generate fresh data during package build (CI/CD)
2. Include in package as `package_data/bedrock_catalog_bundled.json`
3. Load automatically if API/cache fails
4. Include generation timestamp in metadata

**Benefits:**
- Works offline
- Resilient to API failures
- No external dependencies for basic functionality

**Trade-offs:**
- Slightly larger package (~500 KB)
- Data may be stale (updated with each release)

### Decision 4: Deprecate Old Managers ✅ RECOMMENDED

**Timeline:**
- **Now:** Implement new system alongside old
- **Release N:** Add deprecation warnings to old managers
- **Release N+4 (12 months):** Remove old managers (major version bump)

**Migration Path:**
```python
# Old (deprecated)
from bestehorn_llmmanager.bedrock import UnifiedModelManager
manager = UnifiedModelManager()

# New (recommended)
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog
catalog = BedrockModelCatalog()
```

## Open Questions for Discussion

### 🔴 CRITICAL: Question 1 - Default Cache Directory

**Where should cache files be stored by default?**

**Options:**

**A) User Home Directory (Cross-Platform)**
```
Windows: C:\Users\<user>\.bestehorn-llmmanager\cache\
Linux/Mac: ~/.bestehorn-llmmanager/cache/
```
✅ Pros: Works everywhere, persists across sessions
❌ Cons: Non-standard location

**B) XDG Cache Standard (Linux/Mac) + AppData (Windows)**
```
Linux/Mac: ~/.cache/bestehorn-llmmanager/
Windows: %LOCALAPPDATA%\bestehorn-llmmanager\cache\
```
✅ Pros: Follows OS conventions, system tools can clean it
❌ Cons: More complex implementation

**C) Temp Directory**
```
All: /tmp/bestehorn-llmmanager/ (or OS equivalent)
```
✅ Pros: Simple, no permission issues
❌ Cons: Cleared on reboot, not persistent

**RECOMMENDATION:** Option B (XDG/AppData) - follows OS best practices

---

### 🔴 CRITICAL: Question 2 - LLMManager Integration

**Should LLMManager automatically use the new BedrockModelCatalog?**

**Options:**

**A) Transparent Replacement**
- LLMManager internally uses BedrockModelCatalog
- Users don't need to change anything
- Old managers deprecated but not used internally

✅ Pros: Seamless upgrade, no user action needed
❌ Cons: Hidden behavior change

**B) Explicit Opt-In**
- Users must explicitly pass BedrockModelCatalog to LLMManager
- Old behavior preserved by default

✅ Pros: Explicit, no surprises
❌ Cons: Requires user migration effort

**C) Configurable**
- Environment variable or parameter to choose
- Default to new system after deprecation period

✅ Pros: Flexible, gradual migration
❌ Cons: More complex, two code paths

**RECOMMENDATION:** Option A (transparent) - best user experience

---

### 🟡 IMPORTANT: Question 3 - Bundled Data Update Strategy

**How often should bundled data be updated?**

**Options:**

**A) Every Package Release**
- CI/CD generates fresh data before build
- Always included in package

✅ Pros: Always reasonably fresh
❌ Cons: Requires AWS credentials in CI/CD

**B) Monthly Automated Process**
- Separate job updates bundled data
- Committed to repo monthly

✅ Pros: Decoupled from releases
❌ Cons: May be stale between updates

**C) Manual Updates**
- Updated when significant model changes occur
- Maintainer-triggered

✅ Pros: Full control
❌ Cons: May forget to update

**RECOMMENDATION:** Option A (every release) - most reliable

---

### 🟡 IMPORTANT: Question 4 - API Rate Limiting

**How should we handle AWS API rate limits?**

**Current Situation:**
- `list-foundation-models`: 10 TPS per region
- `list-inference-profiles`: 10 TPS per region
- We query multiple regions in parallel

**Options:**

**A) Exponential Backoff**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def fetch_data():
    ...
```
✅ Pros: Simple, handles transient errors
❌ Cons: May still hit limits with many regions

**B) Rate Limiter**
```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=10, period=1)  # 10 calls per second
def fetch_data():
    ...
```
✅ Pros: Prevents rate limit errors
❌ Cons: Slower, adds dependency

**C) Circuit Breaker**
```python
from circuitbreaker import circuit

@circuit(failure_threshold=3, recovery_timeout=60)
def fetch_data():
    ...
```
✅ Pros: Protects against cascading failures
❌ Cons: Complex, may be overkill

**RECOMMENDATION:** Option A (exponential backoff) - sufficient for our use case

---

### 🟢 NICE-TO-HAVE: Question 5 - Cache Validation

**How should we validate cache integrity?**

**Options:**

**A) Timestamp Only (Current)**
- Check if cache is older than max_age_hours
- Simple, fast

**B) Checksum Validation**
- Include SHA256 hash in metadata
- Verify on load

**C) Schema Version**
- Include schema version in cache
- Invalidate if schema changes

**D) All of the Above**
- Timestamp + Checksum + Schema Version

**RECOMMENDATION:** Option D (comprehensive) - ensures data integrity

---

### 🟢 NICE-TO-HAVE: Question 6 - Parallel API Optimization

**How many parallel workers for multi-region API calls?**

**Considerations:**
- ~25 AWS regions support Bedrock
- Each region needs 2 API calls (models + profiles)
- Total: ~50 API calls

**Options:**

**A) Conservative (10 workers)**
- Default: `max_workers=10`
- Slower but safer

**B) Aggressive (25 workers)**
- Default: `max_workers=25`
- Faster but may hit rate limits

**C) Adaptive**
- Start with 10, increase if no errors
- Decrease if rate limits hit

**RECOMMENDATION:** Option A (10 workers) - reliable default, users can increase

---

## Implementation Checklist

### Phase 1: Core Implementation
- [ ] Create `catalog/` module structure
- [ ] Implement `BedrockAPIFetcher` for models API
- [ ] Implement `BedrockAPIFetcher` for CRIS API
- [ ] Implement `CacheManager` with three modes
- [ ] Implement `BundledDataLoader`
- [ ] Implement `CatalogTransformer`
- [ ] Implement `BedrockModelCatalog` main class
- [ ] Generate initial bundled data
- [ ] Add comprehensive unit tests

### Phase 2: Integration
- [ ] Integrate with LLMManager (transparent replacement)
- [ ] Add deprecation warnings to old managers
- [ ] Update all examples to use new system
- [ ] Update Lambda examples
- [ ] Add integration tests with real AWS APIs

### Phase 3: Documentation
- [ ] Update README with new usage
- [ ] Create migration guide
- [ ] Update API reference
- [ ] Add troubleshooting guide
- [ ] Document cache modes and use cases

### Phase 4: CI/CD
- [ ] Add bundled data generation to build process
- [ ] Add tests for bundled data freshness
- [ ] Update release process documentation

## Estimated Effort

- **Phase 1 (Core):** 3-4 days
- **Phase 2 (Integration):** 2-3 days
- **Phase 3 (Documentation):** 1-2 days
- **Phase 4 (CI/CD):** 1 day

**Total:** ~7-10 days of development

## Next Steps

1. **Review and discuss open questions** (this document)
2. **Make decisions on critical questions** (cache directory, LLMManager integration)
3. **Create implementation tasks** (break down into subtasks)
4. **Begin Phase 1 implementation**

## Questions for You

1. **Do you agree with the overall architecture?**
2. **Which options do you prefer for the open questions?**
3. **Are there any additional requirements or concerns?**
4. **Should we proceed with implementation?**
