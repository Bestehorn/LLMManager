# Requirements Document: Notebook Updates for BedrockModelCatalog

## Introduction

This specification defines the requirements for updating all Jupyter notebooks in the `notebooks/` directory to use the new `BedrockModelCatalog` system instead of the deprecated manager classes (`CRISManager`, `ModelManager`, `UnifiedModelManager`).

## Glossary

- **BedrockModelCatalog**: The new unified system for managing AWS Bedrock model availability data
- **CRISManager**: Deprecated class for managing Cross-Region Inference Service data
- **ModelManager**: Deprecated class for managing foundational model information  
- **UnifiedModelManager**: Deprecated class that combined CRIS and model data
- **Cache Mode**: The strategy for storing/retrieving model catalog data (FILE, MEMORY, NONE)
- **Notebook**: A Jupyter notebook file (.ipynb) containing executable Python code cells
- **MessageBuilder**: The fluent interface system for constructing Bedrock API messages

## Requirements

### Requirement 1: Update CRISManager.ipynb

**User Story:** As a developer, I want the CRISManager notebook to demonstrate BedrockModelCatalog functionality, so that I can learn the new API for accessing CRIS data.

#### Acceptance Criteria

1. WHEN the notebook imports classes THEN it SHALL import `BedrockModelCatalog` from `bestehorn_llmmanager.bedrock.catalog`
2. WHEN the notebook initializes the catalog THEN it SHALL use `BedrockModelCatalog(force_refresh=True)` to ensure fresh data
3. WHEN the notebook retrieves model information THEN it SHALL use `get_model_info()` method which includes CRIS data
4. WHEN the notebook lists models THEN it SHALL use `list_models()` method which includes inference profile information
5. WHEN the notebook displays metadata THEN it SHALL use `get_catalog_metadata()` to show source, timestamp, and regions

### Requirement 2: Update ModelIDManager.ipynb

**User Story:** As a developer, I want the ModelIDManager notebook to use BedrockModelCatalog, so that I can learn how to query model availability with the new system.

#### Acceptance Criteria

1. WHEN the notebook imports classes THEN it SHALL import `BedrockModelCatalog` from `bestehorn_llmmanager.bedrock.catalog`
2. WHEN the notebook initializes the catalog THEN it SHALL use `BedrockModelCatalog(force_refresh=True)` to ensure fresh data
3. WHEN the notebook checks model availability THEN it SHALL use `is_model_available()` method
4. WHEN the notebook retrieves model details THEN it SHALL use `get_model_info()` which returns comprehensive model data
5. WHEN the notebook filters models THEN it SHALL use `list_models(provider="...")` for provider-based filtering

### Requirement 3: Update UnifiedModelManager.ipynb

**User Story:** As a developer, I want the UnifiedModelManager notebook to demonstrate BedrockModelCatalog's unified capabilities, so that I understand how the new system replaces the old unified manager.

#### Acceptance Criteria

1. WHEN the notebook imports classes THEN it SHALL import `BedrockModelCatalog` from `bestehorn_llmmanager.bedrock.catalog`
2. WHEN the notebook initializes the catalog THEN it SHALL use `BedrockModelCatalog(force_refresh=True)` to ensure fresh data
3. WHEN the notebook retrieves model information THEN it SHALL use `get_model_info()` which includes both model ID and inference profile data
4. WHEN the notebook displays access methods THEN it SHALL show the `access_method` field from model info
5. WHEN the notebook demonstrates regional analysis THEN it SHALL use the unified model data structure

### Requirement 4: Add Cache Mode Examples to Caching.ipynb

**User Story:** As a developer, I want to understand BedrockModelCatalog caching strategies, so that I can choose the appropriate cache mode for my use case.

#### Acceptance Criteria

1. WHEN the notebook demonstrates FILE mode THEN it SHALL show initialization with `CacheMode.FILE` and `force_refresh=True` for fresh data
2. WHEN the notebook demonstrates MEMORY mode THEN it SHALL show initialization with `CacheMode.MEMORY` and `force_refresh=True` for fresh data
3. WHEN the notebook demonstrates NONE mode THEN it SHALL show initialization with `CacheMode.NONE` which always fetches fresh data
4. WHEN the notebook compares cache modes THEN it SHALL create a comparison table showing file I/O, warm start, persistence, and use cases
5. WHEN the notebook shows advanced configuration THEN it SHALL demonstrate `cache_max_age_hours`, `force_refresh`, and `fallback_to_bundled` parameters

### Requirement 5: Verify Compatibility of Other Notebooks

**User Story:** As a developer, I want to ensure all other notebooks continue working correctly, so that existing examples remain valid.

#### Acceptance Criteria

1. WHEN HelloWorld_LLMManager.ipynb executes THEN it SHALL complete without errors because LLMManager uses BedrockModelCatalog internally
2. WHEN HelloWorld_MessageBuilder.ipynb executes THEN it SHALL complete without errors because MessageBuilder is independent of catalog
3. WHEN HelloWorld_MessageBuilder_Demo.ipynb executes THEN it SHALL complete without errors because it doesn't depend on catalog
4. WHEN HelloWorld_MessageBuilder_Paths.ipynb executes THEN it SHALL complete without errors because it doesn't depend on catalog
5. WHEN HelloWorld_Streaming_Demo.ipynb executes THEN it SHALL complete without errors because streaming uses LLMManager internally
6. WHEN ParallelLLMManager_Demo.ipynb executes THEN it SHALL complete without errors because ParallelLLMManager uses LLMManager internally
7. WHEN ResponseValidation.ipynb executes THEN it SHALL complete without errors because validation is independent of catalog
8. WHEN InferenceProfile_Demo.ipynb executes THEN it SHALL complete without errors because it demonstrates automatic profile support
9. WHEN ExtendedContext_Demo.ipynb executes THEN it SHALL complete without errors because it demonstrates extended context feature

### Requirement 6: Maintain Notebook Structure and Educational Value

**User Story:** As a developer learning the system, I want notebooks to maintain clear structure and educational content, so that I can understand both what and why.

#### Acceptance Criteria

1. WHEN a notebook is updated THEN it SHALL preserve the original educational structure with markdown explanations
2. WHEN a notebook demonstrates a feature THEN it SHALL include clear print statements showing what is happening
3. WHEN a notebook shows output THEN it SHALL format results in a readable way with appropriate labels
4. WHEN a notebook encounters errors THEN it SHALL include helpful error messages and troubleshooting tips
5. WHEN a notebook completes THEN it SHALL include a summary section highlighting key takeaways

### Requirement 7: Update Import Statements

**User Story:** As a developer, I want correct import statements in all notebooks, so that I can run them without import errors.

#### Acceptance Criteria

1. WHEN CRISManager.ipynb imports THEN it SHALL use `from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog`
2. WHEN ModelIDManager.ipynb imports THEN it SHALL use `from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog`
3. WHEN UnifiedModelManager.ipynb imports THEN it SHALL use `from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog`
4. WHEN Caching.ipynb imports cache modes THEN it SHALL use `from bestehorn_llmmanager.bedrock.catalog import CacheMode`
5. WHEN any notebook imports Path THEN it SHALL use `from pathlib import Path` for cache directory configuration

### Requirement 8: Remove Deprecated API Calls

**User Story:** As a developer, I want notebooks to use only current APIs, so that I don't learn deprecated patterns.

#### Acceptance Criteria

1. WHEN a notebook initializes a catalog THEN it SHALL NOT call `refresh_model_data()`, `refresh_cris_data()`, or `refresh_unified_data()`
2. WHEN a notebook accesses model data THEN it SHALL NOT use deprecated manager classes
3. WHEN a notebook demonstrates caching THEN it SHALL use the new cache mode system, not old caching mechanisms
4. WHEN a notebook shows examples THEN it SHALL NOT reference deprecated class names in explanations
5. WHEN a notebook provides code snippets THEN it SHALL use only BedrockModelCatalog APIs

### Requirement 9: Add Troubleshooting Sections

**User Story:** As a developer, I want troubleshooting guidance in notebooks, so that I can resolve common issues independently.

#### Acceptance Criteria

1. WHEN a notebook demonstrates imports THEN it SHALL include a troubleshooting section for import errors
2. WHEN a notebook uses cache directories THEN it SHALL include guidance for permission errors
3. WHEN a notebook makes API calls THEN it SHALL include guidance for timeout errors
4. WHEN a notebook shows examples THEN it SHALL include fallback behavior for missing files or data
5. WHEN a notebook completes THEN it SHALL reference additional resources like migration guides and API documentation

### Requirement 10: Preserve Existing Working Notebooks

**User Story:** As a developer, I want notebooks that don't use deprecated managers to remain unchanged, so that working examples stay stable.

#### Acceptance Criteria

1. WHEN HelloWorld_LLMManager.ipynb is reviewed THEN it SHALL remain unchanged because it uses LLMManager correctly
2. WHEN HelloWorld_MessageBuilder.ipynb is reviewed THEN it SHALL remain unchanged because MessageBuilder is independent
3. WHEN HelloWorld_MessageBuilder_Demo.ipynb is reviewed THEN it SHALL remain unchanged because it doesn't use deprecated APIs
4. WHEN HelloWorld_MessageBuilder_Paths.ipynb is reviewed THEN it SHALL remain unchanged because it doesn't use deprecated APIs
5. WHEN HelloWorld_Streaming_Demo.ipynb is reviewed THEN it SHALL remain unchanged because streaming is independent
6. WHEN ParallelLLMManager_Demo.ipynb is reviewed THEN it SHALL remain unchanged because it uses current APIs
7. WHEN ResponseValidation.ipynb is reviewed THEN it SHALL remain unchanged because validation is independent
8. WHEN InferenceProfile_Demo.ipynb is reviewed THEN it SHALL remain unchanged because it demonstrates current features
9. WHEN ExtendedContext_Demo.ipynb is reviewed THEN it SHALL remain unchanged because it demonstrates current features
