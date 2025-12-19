# Requirements Document: Model Manager Redesign

## Introduction

This document outlines the requirements for redesigning the Model Manager system in bestehorn-llmmanager to address critical limitations with file system dependencies, simplify the architecture, and improve usability in constrained environments like AWS Lambda.

## Glossary

- **Model Manager**: System responsible for retrieving and caching AWS Bedrock model availability data
- **CRIS**: Cross-Region Inference Service - AWS Bedrock feature for routing requests across regions
- **Inference Profile**: AWS Bedrock identifier for CRIS-enabled models
- **API-Only Mode**: Operation mode that retrieves data exclusively from AWS APIs without file system caching
- **Bundled Fallback Data**: Pre-packaged model data distributed with the package for offline/fallback scenarios
- **Cache Directory**: Configurable directory path for storing cached model data files
- **Unified Catalog**: Single consolidated data structure containing both model and CRIS information

## Requirements

### Requirement 1: API-Only Data Retrieval

**User Story:** As a developer, I want to retrieve model data exclusively from AWS APIs, so that I don't depend on HTML parsing or file downloads.

#### Acceptance Criteria

1. WHEN the system retrieves model data THEN it SHALL use AWS Bedrock `list-foundation-models` API
2. WHEN the system retrieves CRIS data THEN it SHALL use AWS Bedrock `list-inference-profiles` API  
3. WHEN the system processes model data THEN it SHALL NOT download or parse HTML files
4. WHEN the system processes CRIS data THEN it SHALL NOT download or parse HTML files
5. WHEN API calls complete successfully THEN the system SHALL transform API responses into unified catalog structures

### Requirement 2: No-Cache Operation Mode

**User Story:** As a Lambda developer, I want to run the LLMManager without file system caching, so that I can operate in read-only environments.

#### Acceptance Criteria

1. WHEN cache_mode is set to "none" THEN the system SHALL NOT attempt to write any files
2. WHEN cache_mode is set to "none" THEN the system SHALL retrieve fresh data from APIs on every initialization
3. WHEN cache_mode is set to "none" AND API calls fail THEN the system SHALL fall back to bundled data
4. WHEN operating in no-cache mode THEN the system SHALL store catalog data in memory only
5. WHEN the system operates without caching THEN LLMManager SHALL function normally with in-memory data

### Requirement 3: Bundled Fallback Data

**User Story:** As a package user, I want the package to include default model data, so that basic functionality works even when API calls fail.

#### Acceptance Criteria

1. WHEN the package is installed THEN it SHALL include a bundled unified catalog JSON file
2. WHEN API retrieval fails THEN the system SHALL automatically load bundled fallback data
3. WHEN bundled data is loaded THEN the system SHALL log a warning about using potentially stale data
4. WHEN bundled data is used THEN the system SHALL include a timestamp indicating data freshness
5. WHEN the package is built THEN the build process SHALL generate fresh bundled data from AWS APIs

### Requirement 4: Configurable Cache Directory

**User Story:** As a developer, I want to control where cache files are written, so that I can adapt to different deployment environments.

#### Acceptance Criteria

1. WHEN initializing the model manager THEN the system SHALL accept a cache_directory parameter
2. WHEN cache_directory is provided THEN the system SHALL write all cache files to that directory
3. WHEN cache_directory is not provided THEN the system SHALL use a sensible default location
4. WHEN the cache directory does not exist THEN the system SHALL create it automatically
5. WHEN the cache directory is not writable THEN the system SHALL raise a clear error with fallback suggestions

### Requirement 5: Simplified Architecture

**User Story:** As a maintainer, I want a single unified manager class, so that the codebase is simpler and easier to maintain.

#### Acceptance Criteria

1. WHEN using the new system THEN there SHALL be a single `BedrockModelCatalog` class
2. WHEN `BedrockModelCatalog` initializes THEN it SHALL retrieve both model and CRIS data internally
3. WHEN the catalog is created THEN it SHALL automatically correlate model and CRIS data
4. WHEN querying model information THEN the unified catalog SHALL provide all access methods
5. WHEN the new system is used THEN the legacy `ModelManager`, `CRISManager`, and `UnifiedModelManager` SHALL be deprecated

### Requirement 6: Single Cache File

**User Story:** As a developer, I want all model data in a single cache file, so that cache management is simpler and more efficient.

#### Acceptance Criteria

1. WHEN caching is enabled THEN the system SHALL write exactly one cache file
2. WHEN the cache file is written THEN it SHALL contain both model and CRIS data in unified format
3. WHEN the cache file is read THEN the system SHALL reconstruct the complete catalog from it
4. WHEN the cache file exists THEN the system SHALL NOT create additional HTML or intermediate JSON files
5. WHEN cache validation occurs THEN the system SHALL check only the single unified cache file

### Requirement 7: Backward Compatibility

**User Story:** As an existing user, I want my current code to continue working, so that I can migrate gradually to the new system.

#### Acceptance Criteria

1. WHEN using legacy `UnifiedModelManager` THEN the system SHALL emit deprecation warnings
2. WHEN using legacy managers THEN they SHALL continue to function with existing behavior
3. WHEN the package is updated THEN existing code SHALL NOT break immediately
4. WHEN deprecation warnings are emitted THEN they SHALL include migration guidance
5. WHEN the new `BedrockModelCatalog` is used THEN it SHALL provide equivalent functionality to legacy managers

### Requirement 8: Lambda-Friendly Design

**User Story:** As a Lambda developer, I want the model manager to work seamlessly in Lambda, so that I don't need workarounds.

#### Acceptance Criteria

1. WHEN used in Lambda with cache_directory="/tmp" THEN the system SHALL write only to /tmp
2. WHEN used in Lambda with cache_mode="none" THEN the system SHALL require no file system access
3. WHEN used in Lambda THEN the system SHALL support warm start optimization through in-memory caching
4. WHEN Lambda cold starts occur THEN the system SHALL minimize initialization time through efficient API calls
5. WHEN Lambda memory is limited THEN the system SHALL operate within reasonable memory constraints

### Requirement 9: API Error Handling

**User Story:** As a developer, I want graceful handling of API failures, so that my application remains resilient.

#### Acceptance Criteria

1. WHEN AWS API calls fail THEN the system SHALL attempt to use cached data if available
2. WHEN both API and cache fail THEN the system SHALL fall back to bundled data
3. WHEN all data sources fail THEN the system SHALL raise a clear error with troubleshooting guidance
4. WHEN partial API failures occur THEN the system SHALL use successfully retrieved data
5. WHEN API rate limits are encountered THEN the system SHALL implement exponential backoff retry logic

### Requirement 10: Performance Optimization

**User Story:** As a developer, I want fast model catalog initialization, so that my application startup time is minimized.

#### Acceptance Criteria

1. WHEN retrieving data from multiple regions THEN the system SHALL use parallel API calls
2. WHEN cache is valid THEN the system SHALL load from cache instead of calling APIs
3. WHEN in-memory catalog exists THEN subsequent queries SHALL use cached data without file I/O
4. WHEN API calls are made THEN the system SHALL use connection pooling for efficiency
5. WHEN the catalog is large THEN the system SHALL use efficient data structures for fast lookups
