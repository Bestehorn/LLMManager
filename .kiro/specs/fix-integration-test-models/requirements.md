# Requirements Document: User-Friendly Model Name Resolution

## Introduction

Integration tests are being skipped because BedrockModelCatalog (introduced in v3.x) uses API-based model names like "Claude Haiku 4 5 20251001" instead of user-friendly names like "Claude 3 Haiku". The deprecated UnifiedModelManager provided user-friendly names, but the new catalog only exposes the raw API names. This breaks existing code and tests that use convenient, memorable model names.

The core issue is that BedrockModelCatalog should provide user-friendly model name aliases and robust name resolution, allowing users to reference models by common names (e.g., "Claude 3 Haiku", "Claude Haiku 4.5") instead of requiring API-specific identifiers.

## Glossary

- **Bedrock_Model_Catalog**: The new API-based catalog system that retrieves model information from AWS Bedrock APIs
- **Unified_Model_Manager**: The deprecated HTML-parsing catalog system that provided user-friendly model names
- **Model_Name_Alias**: A user-friendly name that maps to an API-based model identifier
- **Model_Name_Resolution**: The process of converting a user-provided model name (friendly or API-based) to a valid model identifier
- **API_Model_Name**: The exact model name as returned by AWS Bedrock APIs (e.g., "Claude Haiku 4 5 20251001")
- **Friendly_Model_Name**: A human-readable, memorable model name (e.g., "Claude 3 Haiku", "Claude Haiku 4.5")
- **Model_Identifier**: The unique AWS model ID used in API calls (e.g., "anthropic.claude-3-haiku-20240307-v1:0")

## Requirements

### Requirement 1: User-Friendly Model Name Aliases

**User Story:** As a developer using the LLM Manager, I want to reference models by memorable names like "Claude 3 Haiku" instead of API-specific names like "Claude Haiku 4 5 20251001", so that my code is more readable and maintainable.

#### Acceptance Criteria

1. WHEN Bedrock_Model_Catalog loads model data, THE System SHALL create Friendly_Model_Name aliases for all models
2. WHEN a user queries for a model using a Friendly_Model_Name, THE System SHALL return the corresponding model information
3. WHEN a user queries for a model using an API_Model_Name, THE System SHALL also return the corresponding model information
4. THE System SHALL maintain backward compatibility with model names from Unified_Model_Manager

### Requirement 2: Robust Model Name Resolution

**User Story:** As a developer, I want flexible model name resolution that handles variations in naming (e.g., "Claude 3 Haiku", "Claude Haiku 3", "Claude-3-Haiku"), so that I don't have to memorize exact name formats.

#### Acceptance Criteria

1. WHEN a user provides a model name with different spacing or punctuation, THE System SHALL resolve it to the correct model
2. WHEN a user provides a model name with version numbers in different formats (e.g., "4.5" vs "4 5"), THE System SHALL resolve it to the correct model
3. WHEN a user provides a partial model name that uniquely identifies a model, THE System SHALL resolve it to the correct model
4. WHEN a user provides an ambiguous model name, THE System SHALL return an error with suggestions for matching models

### Requirement 3: Model Name Alias Generation Strategy

**User Story:** As a system maintainer, I want a consistent strategy for generating friendly model names from API names, so that aliases are predictable and intuitive.

#### Acceptance Criteria

1. WHEN generating aliases for Claude models, THE System SHALL use the pattern "Claude {version} {variant}" (e.g., "Claude 3 Haiku", "Claude 3.5 Sonnet")
2. WHEN generating aliases for versioned models, THE System SHALL normalize version numbers (e.g., "4 5 20251001" becomes "4.5")
3. WHEN generating aliases for provider-prefixed models, THE System SHALL create both prefixed and unprefixed versions (e.g., "APAC Claude 3 Haiku" and "Claude 3 Haiku")
4. THE System SHALL maintain a mapping of legacy Unified_Model_Manager names to new Bedrock_Model_Catalog names

### Requirement 4: Integration Test Compatibility

**User Story:** As a test maintainer, I want existing integration tests to work without modification, so that the migration to BedrockModelCatalog doesn't break the test suite.

#### Acceptance Criteria

1. WHEN integration tests use model names like "Claude 3 Haiku", THE System SHALL resolve them successfully
2. WHEN integration tests use model names like "APAC Anthropic Claude 3 Haiku", THE System SHALL resolve them successfully
3. WHEN integration tests use model names like "Llama 3 8B Instruct", THE System SHALL resolve them successfully
4. WHEN a model name from Unified_Model_Manager no longer exists in Bedrock_Model_Catalog, THE System SHALL provide a clear error message with suggested alternatives

### Requirement 5: Clear Error Messages for Name Resolution Failures

**User Story:** As a developer debugging model name issues, I want clear error messages that explain why a model name wasn't found and suggest alternatives, so that I can quickly fix the issue.

#### Acceptance Criteria

1. WHEN a model name cannot be resolved, THE System SHALL include the attempted name in the error message
2. WHEN a model name cannot be resolved, THE System SHALL suggest similar model names that exist in the catalog
3. WHEN a model name is ambiguous, THE System SHALL list all matching models in the error message
4. WHEN a model name resolution fails, THE System SHALL include information about whether the name was found in the legacy Unified_Model_Manager catalog
