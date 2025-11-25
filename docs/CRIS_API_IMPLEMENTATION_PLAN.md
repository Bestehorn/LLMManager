# CRIS API Implementation Plan

## Executive Summary

This document outlines the comprehensive plan to replace HTML-based CRIS (Cross-Region Inference Service) data fetching with AWS Bedrock API calls. This change eliminates fragile HTML parsing dependencies and provides a more reliable, maintainable solution using official AWS APIs.

**Status**: ✅ IMPLEMENTED  
**Target Version**: 0.3.0  
**Implementation Date**: 2025-11-25  
**Priority**: High - Resolves critical parsing failures

---

## 1. Background & Motivation

### Current State
- CRIS data is obtained by scraping AWS HTML documentation
- AWS has moved to JavaScript-based dynamic content loading
- HTML tables only appear when expandable sections are clicked
- Static HTML parsing no longer works, causing CRIS manager failures

### Proposed Solution
- Use AWS Bedrock Control Plane API (`ListInferenceProfiles`, `GetInferenceProfile`)
- Query all Bedrock-enabled regions in parallel for performance
- Use dynamic region discovery via boto3 (not hardcoded lists)
- Maintain existing data structures for cache compatibility
- Keep HTML parser as fallback for backward compatibility

### Benefits
- **Reliability**: Official AWS API vs fragile HTML scraping
- **Maintainability**: No breaking when AWS changes their documentation
- **Performance**: Parallel API calls across regions
- **Future-proof**: Automatic discovery of new regions
- **Accuracy**: Direct from source of truth

---

## 2. Technical Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CRISManager                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Orchestration Layer                                   │  │
│  │  - Coordinates API fetcher and HTML parser            │  │
│  │  - Manages caching and fallback logic                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│         ┌─────────────────┴─────────────────┐               │
│         │                                   │               │
│  ┌──────▼────────┐                  ┌──────▼──────────┐    │
│  │ CRISAPIFetcher│                  │ CRISHTMLParser  │    │
│  │ (NEW - Primary)│                 │ (Existing-      │    │
│  │               │                  │  Fallback)      │    │
│  └───────┬───────┘                  └─────────────────┘    │
│          │                                                   │
│          │                                                   │
│  ┌───────▼───────────────────────────────────────────────┐  │
│  │         BedrockRegionDiscovery                        │  │
│  │         (NEW)                                         │  │
│  │  - Dynamic region discovery                           │  │
│  │  - File-based caching                                 │  │
│  └───────┬───────────────────────────────────────────────┘  │
│          │                                                   │
│  ┌───────▼───────────────────────────────────────────────┐  │
│  │         AuthManager (Enhanced)                        │  │
│  │  - New: get_bedrock_control_client()                  │  │
│  │  - Existing: get_session(), get_bedrock_client()      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
1. CRISManager.refresh_cris_data(use_api=True)
   │
   ├─> BedrockRegionDiscovery.get_bedrock_regions()
   │   ├─> Check cache file (bedrock_regions.json)
   │   ├─> If stale: boto3.Session().get_available_regions('bedrock')
   │   └─> Return: List[str] of regions
   │
   ├─> CRISAPIFetcher.fetch_cris_data(regions)
   │   ├─> ThreadPoolExecutor (parallel across regions)
   │   │   ├─> Region 1: ListInferenceProfiles
   │   │   ├─> Region 2: ListInferenceProfiles
   │   │   └─> Region N: ListInferenceProfiles
   │   ├─> Merge all regional inference profiles
   │   └─> Return: Dict[str, CRISModelInfo]
   │
   ├─> Create CRISCatalog with timestamp
   │
   └─> Save to JSON cache
```

---

## 3. Implementation Components

### 3.1 BedrockRegionDiscovery Class

**Location**: `src/bestehorn_llmmanager/bedrock/discovery/region_discovery.py`

**Purpose**: Dynamic discovery of Bedrock-enabled AWS regions with caching

**Key Methods**:
```python
class BedrockRegionDiscovery:
    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl_hours: int = 24)
    def get_bedrock_regions(self, force_refresh: bool = False) -> List[str]
    def _fetch_regions_from_aws(self) -> List[str]
    def _load_cached_regions(self) -> Optional[List[str]]
    def _save_cached_regions(self, regions: List[str]) -> None
    def _is_cache_valid(self) -> bool
```

**Cache Format**:
```json
{
  "retrieval_timestamp": "2025-11-25T10:00:00",
  "regions": ["us-east-1", "us-west-2", "eu-west-1", ...]
}
```

**Implementation Details**:
- Uses `boto3.Session().get_available_regions('bedrock')` for discovery
- Caches results to `docs/bedrock_regions.json` (configurable)
- Cache TTL: 24 hours (configurable)
- Returns sorted list of region identifiers
- Thread-safe implementation

### 3.2 CRISAPIFetcher Class

**Location**: `src/bestehorn_llmmanager/bedrock/fetchers/cris_api_fetcher.py`

**Purpose**: Fetch CRIS data from AWS Bedrock API across multiple regions in parallel

**Key Methods**:
```python
class CRISAPIFetcher:
    def __init__(self, auth_manager: AuthManager, max_workers: int = 10)
    def fetch_cris_data(self, regions: List[str]) -> Dict[str, CRISModelInfo]
    def _fetch_region_profiles(self, region: str) -> List[InferenceProfileSummary]
    def _parse_profile_to_model_info(self, profiles: List[InferenceProfileSummary]) -> Dict[str, CRISModelInfo]
    def _extract_model_name_from_arn(self, model_arn: str) -> str
    def _extract_regions_from_models(self, models: List[Dict]) -> List[str]
```

**API Interaction**:
```python
# For each region in parallel:
client = auth_manager.get_bedrock_control_client(region)
response = client.list_inference_profiles()

# Structure returned:
{
    'inferenceProfileSummaries': [
        {
            'inferenceProfileId': 'us.amazon.nova-lite-v1:0',
            'inferenceProfileName': 'Nova Lite',
            'type': 'SYSTEM_DEFINED',
            'status': 'ACTIVE',
            'models': [
                {
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0'
                },
                {
                    'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-lite-v1:0'
                }
            ]
        }
    ]
}
```

**Data Transformation Logic**:
1. Extract model ARNs from each inference profile
2. Parse regions from ARNs (e.g., `us-east-1` from the ARN)
3. Group inference profiles by base model name
4. Build region mappings: source region → destination regions
5. Create CRISInferenceProfile and CRISModelInfo objects

**Parallel Execution**:
- Uses ThreadPoolExecutor with configurable max_workers (default: 10)
- Each region queried independently
- Error handling per region (failed regions logged but don't fail entire fetch)
- Results merged into single catalog

### 3.3 AuthManager Enhancement

**Location**: `src/bestehorn_llmmanager/bedrock/auth/auth_manager.py`

**New Method**:
```python
def get_bedrock_control_client(self, region: str) -> Any:
    """
    Get a Bedrock control plane client for the specified region.
    
    This is different from get_bedrock_client() which returns a bedrock-runtime
    client. The control plane client is used for management operations like
    ListInferenceProfiles.
    
    Args:
        region: AWS region for the client
        
    Returns:
        Bedrock control plane client
        
    Raises:
        AuthenticationError: If client creation fails
    """
    try:
        session = self.get_session(region=region)
        client = session.client("bedrock", region_name=region)
        return client
    except Exception as e:
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(
            message=f"Failed to create Bedrock control plane client: {str(e)}",
            auth_type=self._auth_config.auth_type.value,
            region=region,
        ) from e
```

### 3.4 CRISManager Enhancements

**Location**: `src/bestehorn_llmmanager/bedrock/CRISManager.py`

**Changes**:

1. **Add `use_api` parameter to `__init__`**:
```python
def __init__(
    self,
    html_output_path: Optional[Path] = None,
    json_output_path: Optional[Path] = None,
    documentation_url: Optional[str] = None,
    download_timeout: int = 30,
    use_api: bool = True,  # NEW: Default to API method
    auth_manager: Optional[AuthManager] = None,  # NEW: Required for API
) -> None:
```

2. **Update `refresh_cris_data` method**:
```python
def refresh_cris_data(self, force_download: bool = True) -> CRISCatalog:
    """
    Refresh CRIS data using API (preferred) or HTML parsing (fallback).
    
    Args:
        force_download: If True, always fetch fresh data
        
    Returns:
        CRISCatalog containing all parsed CRIS model information
        
    Raises:
        CRISManagerError: If both API and HTML methods fail
    """
    try:
        if self._use_api:
            # Try API method first
            try:
                return self._refresh_via_api()
            except Exception as e:
                self._logger.warning(f"API fetch failed: {e}, falling back to HTML")
                # Fall through to HTML method
        
        # Use HTML method
        return self._refresh_via_html(force_download)
        
    except Exception as e:
        error_msg = f"Failed to refresh CRIS data: {str(e)}"
        self._logger.error(error_msg)
        raise CRISManagerError(error_msg) from e
```

3. **Add new internal methods**:
```python
def _refresh_via_api(self) -> CRISCatalog:
    """Refresh using AWS Bedrock API."""
    # Discover regions
    regions = self._region_discovery.get_bedrock_regions()
    
    # Fetch data via API
    models_dict = self._api_fetcher.fetch_cris_data(regions)
    
    # Create and save catalog
    catalog = CRISCatalog(
        retrieval_timestamp=datetime.now(),
        cris_models=models_dict
    )
    self._save_catalog_to_json(catalog=catalog)
    self._cached_catalog = catalog
    return catalog

def _refresh_via_html(self, force_download: bool) -> CRISCatalog:
    """Refresh using HTML parsing (existing logic)."""
    # Existing implementation
    ...
```

---

## 4. Testing Strategy

### 4.1 Unit Tests

**Location**: `test/bestehorn_llmmanager/bedrock/discovery/test_region_discovery.py`
- Test region discovery with mocked boto3 responses
- Test caching mechanism (save, load, TTL)
- Test cache invalidation
- Test error handling

**Location**: `test/bestehorn_llmmanager/bedrock/fetchers/test_cris_api_fetcher.py`
- Test API response parsing
- Test parallel execution
- Test regional error handling
- Test data transformation to CRISModelInfo
- Test merging of regional results

**Location**: `test/bestehorn_llmmanager/bedrock/auth/test_auth_manager.py` (additions)
- Test `get_bedrock_control_client()` method
- Test client caching
- Test error handling

**Location**: `test/bestehorn_llmmanager/bedrock/test_CRISManager.py` (updates)
- Test API-based refresh
- Test HTML fallback mechanism
- Test `use_api` parameter
- Test existing functionality still works

### 4.2 Integration Tests

**Location**: `test/integration/test_integration_cris_api.py`
- Test real API calls to AWS (with proper markers)
- Test end-to-end CRIS data retrieval
- Test cache round-trip (API → cache → load)
- Test performance with parallel execution

### 4.3 Test Data

Create mock API responses for unit tests:
```python
MOCK_INFERENCE_PROFILE_RESPONSE = {
    'inferenceProfileSummaries': [
        {
            'inferenceProfileId': 'us.amazon.nova-lite-v1:0',
            'inferenceProfileName': 'Nova Lite',
            'type': 'SYSTEM_DEFINED',
            'status': 'ACTIVE',
            'models': [
                {
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0'
                },
                {
                    'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-lite-v1:0'
                }
            ]
        }
    ]
}
```

---

## 5. Documentation Updates

### 5.1 User-Facing Documentation

**File**: `docs/CRIS_API_USAGE.md` (NEW)
- Explain new API-based approach
- Show usage examples
- Document configuration options
- Explain fallback behavior

**File**: `README.md` (UPDATE)
- Add note about API-based CRIS fetching
- Update examples if needed

**File**: `docs/migration_guide_v3.md` (UPDATE)
- Add section on v0.2.0 changes
- Explain migration from HTML to API
- Note backward compatibility

### 5.2 Developer Documentation

**File**: `docs/CRIS_ARCHITECTURE.md` (NEW)
- Document component architecture
- Explain data flow
- Detail API interactions
- Document caching strategy

**File**: `docs/forLLMConsumption.md` (UPDATE)
- Add information about new components
- Update architecture diagrams
- Document API fetching logic

### 5.3 Changelog

**File**: `CHANGELOG.md` (UPDATE)
```markdown
## [0.2.0] - 2025-XX-XX

### Added
- AWS Bedrock API-based CRIS data fetching (replaces HTML parsing)
- BedrockRegionDiscovery for dynamic region discovery
- CRISAPIFetcher for parallel API calls across regions
- Automatic fallback to HTML parsing if API fails
- Enhanced AuthManager with control plane client support

### Changed
- CRISManager now uses AWS Bedrock API by default (HTML parsing as fallback)
- Improved reliability of CRIS data retrieval
- Better performance through parallel regional API calls

### Fixed
- CRIS data fetch failures due to AWS documentation structure changes
- Eliminated dependency on fragile HTML parsing
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Day 1, Morning)
**Goal**: Implement core components

- [ ] Create `BedrockRegionDiscovery` class with caching
- [ ] Add `get_bedrock_control_client()` to AuthManager
- [ ] Create comprehensive unit tests for both components
- [ ] Test region discovery with real AWS API

**Acceptance Criteria**:
- Region discovery returns valid region list
- Caching works correctly with TTL
- Auth manager creates control plane clients
- All unit tests pass

### Phase 2: API Fetcher (Day 1, Afternoon)
**Goal**: Implement parallel API fetching

- [ ] Create `CRISAPIFetcher` class
- [ ] Implement parallel execution with ThreadPoolExecutor
- [ ] Implement data transformation logic (API → CRISModelInfo)
- [ ] Create comprehensive unit tests with mocked API responses

**Acceptance Criteria**:
- API fetcher queries multiple regions in parallel
- Data correctly transforms to existing structures
- Error handling works per-region
- All unit tests pass

### Phase 3: Integration (Day 2, Morning)
**Goal**: Integrate with CRISManager

- [ ] Update CRISManager to use API fetcher
- [ ] Implement fallback logic (API → HTML)
- [ ] Update existing CRISManager tests
- [ ] Create integration tests with real API

**Acceptance Criteria**:
- CRISManager successfully fetches via API
- Fallback to HTML works when API fails
- Existing functionality preserved
- All tests (unit + integration) pass

### Phase 4: Documentation & Release (Day 2, Afternoon)
**Goal**: Complete documentation and prepare release

- [ ] Create CRIS_API_USAGE.md
- [ ] Update migration_guide_v3.md
- [ ] Update CHANGELOG.md
- [ ] Update README.md
- [ ] Review all code changes
- [ ] Run full test suite
- [ ] Create release notes

**Acceptance Criteria**:
- All documentation complete and accurate
- CHANGELOG updated
- All tests pass
- Code review completed
- Ready for version tag

### Phase 5: Release (Day 3)
**Goal**: Package and release

- [ ] Bump version to 0.2.0
- [ ] Create git tag
- [ ] Build package
- [ ] Test package installation
- [ ] Publish to PyPI
- [ ] Create GitHub release

**Acceptance Criteria**:
- Version 0.2.0 available on PyPI
- GitHub release created
- Installation from PyPI works
- Basic smoke tests pass

---

## 7. Rollback Plan

If issues arise after release:

1. **Immediate Mitigation**: Users can disable API fetching:
   ```python
   manager = CRISManager(use_api=False)
   ```

2. **Quick Fix Release**: If API method has bugs:
   - Revert default to `use_api=False`
   - Release as patch version (0.2.1)
   - Fix API method and re-enable in 0.2.2

3. **Full Rollback**: If critical issues:
   - Revert entire 0.2.0 release
   - Release 0.1.14 with HTML parser fixes only
   - Address API method offline

---

## 8. Dependencies

### Required
- boto3 >= 1.28.0 (already present in pyproject.toml)
- No new external dependencies needed

### Internal Dependencies
- AuthManager (existing, enhanced)
- CRIS data structures (existing, no changes)
- JSON serializer (existing)

---

## 9. Performance Considerations

### Expected Improvements
- **Parallel execution**: 10-20 regions queried simultaneously
- **Reduced latency**: Direct API calls vs HTML download + parsing
- **Caching**: Region list cached for 24 hours

### Estimated Timing
- Region discovery: ~500ms (first time), <1ms (cached)
- API fetch (10 regions, parallel): ~2-3 seconds
- Total refresh: ~3-4 seconds vs ~10-15 seconds for HTML method

### Resource Usage
- ThreadPoolExecutor with max 10 workers
- Memory: ~5-10MB for API responses
- Network: Multiple simultaneous connections to AWS

---

## 10. Security Considerations

### AWS Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ListInferenceProfiles",
        "bedrock:GetInferenceProfile"
      ],
      "Resource": "*"
    }
  ]
}
```

### Security Notes
- Uses existing AuthManager authentication
- No new credentials required
- All API calls use secure AWS SDK
- No sensitive data stored in cache

---

## 11. Backward Compatibility

### Maintained
- All existing CRISManager APIs unchanged
- Data structures remain identical
- JSON cache format unchanged
- Existing code continues to work

### New Optional Parameters
- `use_api` parameter (defaults to True)
- `auth_manager` parameter (optional, created if not provided)

### Migration Path
- Automatic - no code changes required
- API method used by default
- HTML parsing still available as fallback

---

## 12. Success Criteria

### Functional
- ✓ CRIS data successfully fetched via API
- ✓ All regions discovered dynamically
- ✓ Data structures match existing format
- ✓ Fallback to HTML works when needed
- ✓ All existing tests pass
- ✓ New tests achieve >90% coverage

### Performance
- ✓ API fetch completes in <5 seconds
- ✓ Cache reduces subsequent calls to <1 second
- ✓ Parallel execution scales with region count

### Quality
- ✓ No breaking changes to public API
- ✓ Comprehensive documentation
- ✓ Clear error messages
- ✓ Proper logging at all levels

---

## 13. Future Enhancements (Out of Scope)

These are not part of 0.2.0 but could be considered later:

1. **Incremental updates**: Only fetch changed profiles
2. **WebSocket streaming**: Real-time profile updates
3. **Region filtering**: Only query specific regions
4. **Profile details caching**: Cache GetInferenceProfile responses
5. **Metrics**: Track API call latency and success rates

---

## 14. Questions & Decisions

### Decided
- ✓ Use API by default, HTML as fallback
- ✓ Parallel execution with ThreadPoolExecutor
- ✓ Dynamic region discovery via boto3
- ✓ File-based caching for regions (24h TTL)
- ✓ No breaking changes to data structures

### Open Questions
None - plan is ready for implementation.

---

## Appendix A: File Structure

```
src/bestehorn_llmmanager/bedrock/
├── discovery/
│   ├── __init__.py
│   └── region_discovery.py          (NEW)
├── fetchers/
│   ├── __init__.py
│   └── cris_api_fetcher.py          (NEW)
├── auth/
│   └── auth_manager.py               (MODIFIED)
├── CRISManager.py                    (MODIFIED)
└── ...

test/bestehorn_llmmanager/bedrock/
├── discovery/
│   ├── __init__.py
│   └── test_region_discovery.py     (NEW)
├── fetchers/
│   ├── __init__.py
│   └── test_cris_api_fetcher.py     (NEW)
├── auth/
│   └── test_auth_manager.py         (MODIFIED)
├── test_CRISManager.py               (MODIFIED)
└── ...

test/integration/
└── test_integration_cris_api.py     (NEW)

docs/
├── CRIS_API_USAGE.md                (NEW)
├── CRIS_ARCHITECTURE.md             (NEW)
├── CRIS_API_IMPLEMENTATION_PLAN.md  (THIS FILE)
├── migration_guide_v3.md            (MODIFIED)
└── forLLMConsumption.md             (MODIFIED)

docs/bedrock_regions.json            (GENERATED - Cache file)
```

---

## Appendix B: Example Usage

```python
# Default usage (API-based)
from bestehorn_llmmanager.bedrock import CRISManager

manager = CRISManager()
catalog = manager.refresh_cris_data()
print(f"Found {catalog.model_count} CRIS models")

# Explicit API usage
manager = CRISManager(use_api=True)
catalog = manager.refresh_cris_data()

# Force HTML fallback
manager = CRISManager(use_api=False)
catalog = manager.refresh_cris_data()

# Custom auth
from bestehorn_llmmanager.bedrock.auth import AuthManager
auth = AuthManager()
manager = CRISManager(use_api=True, auth_manager=auth)
catalog = manager.refresh_cris_data()
```

---

**Document Version**: 1.0  
**Date**: 2025-11-25  
**Author**: LLMManager Development Team  
**Status**: Ready for Implementation
