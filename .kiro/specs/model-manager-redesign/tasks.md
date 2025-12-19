# Implementation Plan: Model Manager Redesign

## Current Status Summary

**Completed:**
- ✅ Phase 1: Core Implementation - All new catalog components implemented
- ✅ Phase 2: Integration and Deprecation - LLMManager integrated, deprecation warnings added, examples and documentation updated
- ✅ Bundled data generated and included in package

**In Progress:**
- 🔄 Phase 3: Testing - Unit tests needed for new components (API fetcher, transformer, catalog)

**Pending:**
- ⏳ Phase 4: CI/CD - GitHub Actions workflow for automated bundled data generation
- ⏳ Phase 5: Code Cleanup - Scheduled for version 4.0.0 after 12-month deprecation period

## Phase 1: Core Implementation (New System)

- [x] 1. Set up new catalog module structure
  - Create `src/bestehorn_llmmanager/bedrock/catalog/` directory
  - Create `__init__.py` with public exports
  - _Requirements: 5.1, 5.2_

- [x] 2. Implement data models and constants

- [x] 2.1 Create catalog data structures
  - Implement `UnifiedCatalog` dataclass
  - Implement `CatalogMetadata` dataclass
  - Implement `CacheMode` enum
  - Implement `CatalogSource` enum
  - Create `models/catalog_structures.py`
  - _Requirements: 6.2, 6.3_

- [x] 2.2 Create catalog constants
  - Define cache-related constants
  - Define API endpoint constants
  - Define error messages
  - Define log messages
  - Define default values
  - Create `models/catalog_constants.py`
  - _Requirements: 4.3_

- [x] 2.3 Add catalog exceptions
  - Add `APIFetchError` to exceptions module
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 3. Implement API fetcher for foundation models

- [x] 3.1 Create BedrockAPIFetcher class structure
  - Initialize with AuthManager
  - Set up parallel execution framework
  - Create `catalog/api_fetcher.py`
  - Create `RawCatalogData` container class
  - _Requirements: 1.1, 10.1_

- [x] 3.2 Implement foundation models API fetching
  - Implement `_fetch_foundation_models()` method
  - Use `aws bedrock list-foundation-models` API
  - Handle per-region errors gracefully
  - Add retry logic with exponential backoff
  - _Requirements: 1.1, 9.5_

- [x] 3.3 Implement inference profiles API fetching
  - Implement `_fetch_inference_profiles()` method
  - Use `aws bedrock list-inference-profiles` API
  - Filter for SYSTEM_DEFINED profiles
  - Handle per-region errors gracefully
  - _Requirements: 1.2, 9.4_

- [x] 3.4 Implement parallel multi-region fetching
  - Implement `fetch_all_data()` method
  - Use ThreadPoolExecutor with configurable workers
  - Collect results from all regions
  - Log accessible vs inaccessible regions
  - _Requirements: 10.1, 10.4_

- [x] 4. Implement data transformer





- [x] 4.1 Create CatalogTransformer class


  - Create `catalog/transformer.py`
  - Initialize with correlation logic
  - Accept RawCatalogData as input
  - _Requirements: 1.5_

- [x] 4.2 Implement model data transformation


  - Transform API response to UnifiedModelInfo structures
  - Extract regions, modalities, streaming support from API response
  - Handle missing or malformed data gracefully
  - Map API field names using catalog constants
  - _Requirements: 1.5_

- [x] 4.3 Implement CRIS data transformation


  - Transform API response to CRIS structures
  - Extract inference profile IDs and region mappings
  - Identify global vs regional profiles
  - Map API field names using catalog constants
  - _Requirements: 1.5_

- [x] 4.4 Implement data correlation


  - Correlate models with CRIS profiles using existing ModelCRISCorrelator
  - Build unified access information
  - Handle models without CRIS profiles
  - Handle CRIS profiles without matching models
  - Return UnifiedCatalog with metadata
  - _Requirements: 5.3_

- [x] 5. Implement cache manager






- [x] 5.1 Create CacheManager class





  - Support FILE, MEMORY, NONE modes
  - Accept configurable cache directory
  - Create `catalog/cache_manager.py`
  - Add CacheError and related exceptions to exceptions module

  - _Requirements: 2.1, 4.1, 6.1_

- [x] 5.2 Implement cache loading










  - Implement `load_cache()` method
  - Validate cache file structure using UnifiedCatalog.from_dict()
  - Check cache age against max_age_hours
  - Check package version compatibility
  - Return None if cache invalid
  - _Requirements: 6.3, 10.2_



- [x] 5.3 Implement cache saving




  - Implement `save_cache()` method for FILE mode
  - Implement in-memory storage for MEMORY mode
  - Skip saving for NONE mode
  - Create cache directory if needed using pathlib
  - Handle write errors gracefully
  - Use UnifiedCatalog.to_dict() for serialization
  - _Requirements: 2.1, 4.2, 4.4, 6.2_



- [x] 5.4 Implement cache validation




  - Implement `is_cache_valid()` method
  - Check file existence
  - Check timestamp freshness
  - Validate JSON structure
  - Check package version compatibility
  - _Requirements: 6.5_



- [x] 6. Implement bundled data loader



- [x] 6.1 Create BundledDataLoader class


  - Create `catalog/bundled_loader.py`
  - Define bundled data location in package using importlib.resources
  - Add BundledDataError to exceptions module
  - _Requirements: 3.1_

- [x] 6.2 Implement bundled data loading


  - Implement `load_bundled_catalog()` method
  - Load from package_data directory
  - Validate bundled data structure using UnifiedCatalog.from_dict()
  - Handle missing bundled data with clear error
  - _Requirements: 3.2, 3.4_

- [x] 6.3 Implement bundled data metadata


  - Implement `get_bundled_data_metadata()` method
  - Return generation timestamp
  - Return data version
  - _Requirements: 3.4_

- [x] 7. Implement main BedrockModelCatalog class



- [x] 7.1 Create BedrockModelCatalog class structure


  - Create `catalog/bedrock_catalog.py`
  - Initialize with all configuration parameters
  - Set up component managers (API fetcher, cache, bundled loader, transformer)
  - Add CatalogUnavailableError to exceptions module
  - _Requirements: 5.1, 5.2_

- [x] 7.2 Implement initialization strategy


  - Implement `ensure_catalog_available()` method
  - Try cache first (if enabled)
  - Try API fetch on cache miss/invalid
  - Try bundled data on API failure
  - Raise CatalogUnavailableError if all fail
  - _Requirements: 2.2, 3.2, 9.1, 9.2, 9.3_

- [x] 7.3 Implement query methods


  - Implement `get_model_info()` method
  - Implement `is_model_available()` method
  - Implement `list_models()` method with filtering
  - Implement `get_catalog_metadata()` method
  - _Requirements: 5.4_

- [x] 7.4 Implement in-memory caching


  - Cache catalog in instance variable after first load
  - Reuse cached catalog for subsequent queries
  - _Requirements: 8.3, 10.3_

- [x] 7.5 Update catalog __init__.py exports


  - Export BedrockModelCatalog
  - Export CacheMode, CatalogSource
  - Export UnifiedCatalog, CatalogMetadata
  - Export all catalog exceptions
  - _Requirements: 5.1_

- [x] 8. Generate initial bundled data












- [x] 8.1 Create bundled data generation script

  - Create `scripts/generate_bundled_data.py`
  - Use BedrockAPIFetcher to fetch fresh data
  - Use CatalogTransformer to transform to UnifiedCatalog
  - Save to `src/bestehorn_llmmanager/bedrock/package_data/bedrock_catalog_bundled.json`
  - Include generation timestamp and version metadata
  - _Requirements: 3.1, 3.5_




- [x] 8.2 Add bundled data to package

  - Create `src/bestehorn_llmmanager/bedrock/package_data/` directory
  - Update `MANIFEST.in` to include package_data
  - Update `pyproject.toml` to include package_data
  - Verify bundled data is included in built package
  - _Requirements: 3.1_


- [x] 9. Checkpoint - Ensure all tests pass









  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Integration and Deprecation



- [x] 10. Add deprecation warnings to old managers






- [x] 10.1 Add deprecation to ModelManager

  - Add deprecation warning to `__init__`
  - Emit warning with migration guidance
  - Update docstring with deprecation notice
  - _Requirements: 7.1, 7.4_


- [x] 10.2 Add deprecation to CRISManager

  - Add deprecation warning to `__init__`
  - Emit warning with migration guidance
  - Update docstring with deprecation notice
  - _Requirements: 7.1, 7.4_


- [x] 10.3 Add deprecation to UnifiedModelManager

  - Add deprecation warning to `__init__`
  - Emit warning with migration guidance
  - Update docstring with deprecation notice
  - _Requirements: 7.1, 7.4_

- [x] 11. Update LLMManager to use new catalog








- [x] 11.1 Integrate BedrockModelCatalog into LLMManager


  - Replace internal usage of UnifiedModelManager
  - Use BedrockModelCatalog transparently
  - Maintain backward compatibility
  - _Requirements: 7.2_

- [x] 11.2 Add configuration options to LLMManager

  - Add `catalog_cache_mode` parameter
  - Add `catalog_cache_directory` parameter
  - Pass through to BedrockModelCatalog
  - _Requirements: 4.1, 8.1_


- [x] 12. Update examples





- [x] 12.1 Update Lambda examples


  - Update `examples/lambda_unified_model_manager.py`
  - Update `examples/lambda_llm_manager_with_model_cache.py`
  - Update `examples/lambda_complete_serverless_app.py`
  - Show all three cache modes
  - _Requirements: 8.1, 8.2_

- [x] 12.2 Create new catalog usage examples


  - Create `examples/catalog_basic_usage.py`
  - Create `examples/catalog_cache_modes.py`
  - Create `examples/catalog_lambda_usage.py`
  - _Requirements: 7.3_

- [x] 12.3 Update existing examples


  - Update `examples/caching_example.py` if needed
  - Update any other examples using old managers
  - _Requirements: 7.3_


- [x] 13. Update documentation




- [x] 13.1 Update main README


  - Add BedrockModelCatalog usage section
  - Update quick start guide
  - Add cache modes explanation
  - _Requirements: 7.3_

- [x] 13.2 Create migration guide


  - Create `docs/MIGRATION_GUIDE.md`
  - Document old vs new API
  - Provide code examples
  - Explain deprecation timeline
  - _Requirements: 7.4_

- [x] 13.3 Update API reference


  - Update `docs/forLLMConsumption.md`
  - Document BedrockModelCatalog API
  - Document cache modes
  - Document bundled data fallback
  - _Requirements: 7.3_

- [x] 13.4 Update Lambda examples README


  - Update `examples/LAMBDA_EXAMPLES_README.md`
  - Remove workaround sections
  - Show proper usage with new system
  - _Requirements: 8.1_

- [x] 13.5 Update notebooks


  - Update `notebooks/CRISManager.ipynb` with BedrockModelCatalog examples
  - Update `notebooks/ModelIDManager.ipynb` to use new catalog
  - Update `notebooks/UnifiedModelManager.ipynb` with BedrockModelCatalog examples
  - Update `notebooks/Caching.ipynb` to document new cache modes
  - Verify other notebooks for compatibility
  - _Requirements: 7.3_


- [x] 14. Checkpoint - Ensure all tests pass




  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: Testing

- [-] 15. Write unit tests for new components







- [x] 15.1 Write tests for BedrockAPIFetcher






  - Test foundation models API fetching
  - Test inference profiles API fetching
  - Test parallel execution
  - Test error handling per region
  - Test retry logic
  - Create `test/bestehorn_llmmanager/bedrock/catalog/test_api_fetcher.py`
  - _Requirements: 1.1, 1.2, 9.5, 10.1_


- [x] 15.2 Write tests for CatalogTransformer

  - Test model data transformation
  - Test CRIS data transformation
  - Test data correlation
  - Test handling of missing data
  - Create `test/bestehorn_llmmanager/bedrock/catalog/test_transformer.py`
  - _Requirements: 1.5, 5.3_


- [x] 15.3 Write tests for BedrockModelCatalog





  - Test initialization with different modes
  - Test initialization strategy (cache → API → bundled)
  - Test query methods
  - Test error handling
  - Test in-memory caching
  - Create `test/bestehorn_llmmanager/bedrock/catalog/test_bedrock_catalog.py`
  - _Requirements: 2.2, 3.2, 5.4, 8.3, 9.1, 9.2, 9.3_

- [x] 16. Write integration tests





- [x] 16.1 Write integration test for API fetching


  - Test with real AWS APIs (requires credentials)
  - Test multi-region fetching
  - Test data transformation
  - Create `test/integration/test_integration_catalog_api.py`
  - _Requirements: 1.1, 1.2, 10.1_

- [x] 16.2 Write integration test for cache persistence


  - Test cache file creation
  - Test cache loading
  - Test cache expiration
  - Create `test/integration/test_integration_catalog_cache.py`
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 16.3 Write integration test for LLMManager


  - Test LLMManager with new catalog
  - Test model validation
  - Test Lambda-like scenarios
  - Create `test/integration/test_integration_llmmanager_catalog.py`
  - _Requirements: 7.2, 8.1_

- [x] 17. Write property-based tests









- [x] 17.1 Property test: Initialization always succeeds with bundled data

  - **Property 1: Initialization always succeeds with bundled data**
  - For any configuration, if bundled data exists, initialization SHALL NOT fail
  - Use hypothesis to generate random configurations
  - Create `test/bestehorn_llmmanager/bedrock/catalog/test_properties.py`
  - **Validates: Requirements 3.2, 9.2**

- [x] 17.2 Property test: Cache mode determines file system usage


  - **Property 2: Cache mode determines file system usage**
  - For any catalog with cache_mode="none", no files SHALL be written
  - Verify no file I/O occurs
  - **Validates: Requirements 2.1, 4.2**

- [x] 17.3 Property test: API data freshness


  - **Property 3: API data freshness**
  - For any catalog from API, retrieval_timestamp SHALL be recent (< 1 minute old)
  - **Validates: Requirements 1.5, 10.3**


- [x] 17.4 Property test: Model availability consistency


  - **Property 4: Model availability consistency**
  - For any model M and region R, if is_model_available(M, R) returns True, then get_model_info(M, R) SHALL NOT return None
  - **Validates: Requirements 5.4**



- [x] 17.5 Property test: Cache round-trip consistency





  - **Property 5: Cache round-trip consistency**
  - For any catalog C, saving then loading SHALL produce equivalent catalog
  - **Validates: Requirements 6.3**

- [x] 18. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: CI/CD and Build Process

**Note:** These tasks are for future implementation when setting up automated bundled data generation.

- [ ] 19. Add bundled data generation to CI/CD

- [ ] 19.1 Create GitHub Actions workflow
  - Create `.github/workflows/generate-bundled-data.yml`
  - Run on pre-release or scheduled basis
  - Fetch fresh data from AWS APIs using generate_bundled_data.py script
  - Commit updated bundled data
  - _Requirements: 3.5_

- [ ] 19.2 Add bundled data validation to CI
  - Verify bundled data is not too old (< 30 days)
  - Verify bundled data structure is valid using test_bundled_data_validation.py
  - Fail build if bundled data is missing or invalid
  - _Requirements: 3.4_

- [ ] 20. Verify package build configuration

- [ ] 20.1 Verify pyproject.toml configuration
  - Ensure package_data is included (already configured)
  - Verify dependencies are correct
  - Update package description if needed
  - _Requirements: 3.1_

- [ ] 20.2 Verify MANIFEST.in configuration
  - Ensure `package_data/bedrock_catalog_bundled.json` is included (already configured)
  - Verify all necessary files are included
  - _Requirements: 3.1_

- [ ] 21. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Code Cleanup (After Deprecation Period)

**Note:** These tasks should be executed after the 12-month deprecation period (version 4.0.0). The deprecated managers currently have deprecation warnings and documentation but remain functional for backward compatibility.

- [ ] 22. Remove deprecated manager classes

- [ ] 22.1 Delete ModelManager
  - Delete `src/bestehorn_llmmanager/bedrock/ModelManager.py`
  - Remove from `__init__.py` exports
  - _Requirements: 5.5_

- [ ] 22.2 Delete CRISManager
  - Delete `src/bestehorn_llmmanager/bedrock/CRISManager.py`
  - Remove from `__init__.py` exports
  - _Requirements: 5.5_

- [ ] 22.3 Delete UnifiedModelManager
  - Delete `src/bestehorn_llmmanager/bedrock/UnifiedModelManager.py`
  - Remove from `__init__.py` exports
  - _Requirements: 5.5_

- [ ] 23. Remove HTML parsing infrastructure

- [ ] 23.1 Delete downloaders directory
  - Delete `src/bestehorn_llmmanager/bedrock/downloaders/`
  - Remove all HTML downloading code
  - _Requirements: 1.3_

- [ ] 23.2 Delete parsers directory
  - Delete `src/bestehorn_llmmanager/bedrock/parsers/`
  - Remove all HTML parsing code
  - _Requirements: 1.4_

- [ ] 24. Clean up data structures and constants

- [ ] 24.1 Remove HTML-specific constants
  - Clean up `models/constants.py`
  - Remove `HTMLTableColumns`, `URLs.BEDROCK_MODELS_DOCUMENTATION`
  - Remove `FilePaths.DEFAULT_HTML_OUTPUT`
  - _Requirements: 1.3, 1.4_

- [ ] 24.2 Remove CRIS HTML constants
  - Clean up `models/cris_constants.py`
  - Remove `CRISHTMLSelectors`, `CRISHTMLAttributes`
  - Remove `CRISURLs.DOCUMENTATION`
  - Remove `CRISFilePaths.DEFAULT_HTML_OUTPUT`
  - _Requirements: 1.4_

- [ ] 24.3 Remove obsolete data structures
  - Review `models/data_structures.py` for unused structures
  - Remove any structures only used by old managers
  - _Requirements: 5.5_

- [ ] 25. Update dependencies

- [ ] 25.1 Remove BeautifulSoup4 from dependencies
  - Update `pyproject.toml`
  - Remove `beautifulsoup4` from `[project.dependencies]`
  - _Requirements: 1.3_

- [ ] 25.2 Remove lxml from dependencies
  - Update `pyproject.toml`
  - Remove `lxml` from `[project.dependencies]`
  - _Requirements: 1.3_

- [ ] 25.3 Remove requests from dependencies (if not used elsewhere)
  - Check if `requests` is used by other components
  - If not, remove from `pyproject.toml`
  - _Requirements: 1.3_

- [ ] 26. Delete old tests

- [ ] 26.1 Delete ModelManager tests
  - Delete `test/bestehorn_llmmanager/bedrock/test_ModelManager.py`
  - Delete related test fixtures
  - _Requirements: 5.5_

- [ ] 26.2 Delete CRISManager tests
  - Delete `test/bestehorn_llmmanager/bedrock/test_CRISManager.py`
  - Delete related test fixtures
  - _Requirements: 5.5_

- [ ] 26.3 Delete UnifiedModelManager tests
  - Delete `test/bestehorn_llmmanager/bedrock/test_UnifiedModelManager.py`
  - Delete related test fixtures
  - _Requirements: 5.5_

- [ ] 26.4 Delete HTML parser tests
  - Delete `test/bestehorn_llmmanager/bedrock/parsers/test_bedrock_parser.py`
  - Delete `test/bestehorn_llmmanager/bedrock/parsers/test_cris_parser.py`
  - Delete `test/bestehorn_llmmanager/bedrock/parsers/test_enhanced_bedrock_parser.py`
  - _Requirements: 1.4_

- [ ] 26.5 Delete HTML downloader tests
  - Delete `test/bestehorn_llmmanager/bedrock/downloaders/test_html_downloader.py`
  - Delete related test fixtures
  - _Requirements: 1.3_

- [ ] 26.6 Delete constants tests for removed code
  - Update `test/bestehorn_llmmanager/bedrock/models/test_constants.py`
  - Remove tests for deleted constants
  - _Requirements: 1.3, 1.4_

- [ ] 27. Update integration tests

- [ ] 27.1 Remove old manager integration tests
  - Delete `test/integration/test_integration_unified_model_manager.py`
  - Delete `test/integration/test_integration_bedrock_api.py` (if specific to old system)
  - _Requirements: 5.5_

- [ ] 27.2 Ensure new catalog integration tests cover all scenarios
  - Verify coverage is maintained or improved
  - Add any missing integration test scenarios
  - _Requirements: 5.5_

- [ ] 28. Update all documentation

- [ ] 28.1 Remove old manager references from docs
  - Update `docs/forLLMConsumption.md`
  - Remove ModelManager, CRISManager, UnifiedModelManager sections
  - _Requirements: 7.3_

- [ ] 28.2 Update migration guide
  - Update `docs/MIGRATION_GUIDE.md`
  - Note that old managers have been removed
  - Provide clear upgrade path
  - _Requirements: 7.4_

- [ ] 28.3 Update README
  - Remove any references to old managers
  - Ensure all examples use new system
  - _Requirements: 7.3_

- [ ] 28.4 Update CHANGELOG
  - Document breaking changes
  - List removed components
  - Provide migration guidance
  - _Requirements: 7.1_

- [ ] 29. Update package metadata

- [ ] 29.1 Bump major version
  - Update version in `pyproject.toml`
  - Follow semantic versioning (breaking change = major bump)
  - _Requirements: 7.1_

- [ ] 29.2 Update package description
  - Update description in `pyproject.toml` if needed
  - Update classifiers if needed
  - _Requirements: 7.3_

- [ ] 30. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Verify package builds successfully
  - Verify no broken imports
  - Verify documentation builds
