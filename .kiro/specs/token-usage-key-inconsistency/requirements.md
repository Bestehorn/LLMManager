# Requirements Document

## Introduction

This specification addresses a bug in the ExtendedContext_Demo.ipynb notebook where token usage appears as 0 because the notebook's `display_response()` function is using incorrect key names (camelCase) to access token usage data from `BedrockResponse.get_usage()`, which returns snake_case keys.

Additionally, this specification proposes adding individual accessor methods to `BedrockResponse` to provide better encapsulation and shield client code from internal dictionary structure changes.

## Glossary

- **BedrockResponse**: The response object returned by LLMManager operations containing response data and metadata
- **get_usage()**: Method on BedrockResponse that extracts token usage information and returns a dictionary with snake_case keys
- **Token Usage**: Information about input tokens, output tokens, and total tokens consumed by an LLM request
- **AWS Converse API**: The AWS Bedrock API that returns response data with camelCase field names
- **Snake_case**: Naming convention using underscores (e.g., `input_tokens`) - used by the library's public API
- **CamelCase**: Naming convention with capital letters (e.g., `inputTokens`) - used by AWS API internally
- **ConverseAPIFields**: Constants class defining field names from AWS Converse API (camelCase)
- **Accessor Method**: A method that provides controlled access to an object's data without exposing internal structure

## Requirements

### Requirement 1: Fix Notebook Token Usage Display

**User Story:** As a user running the ExtendedContext_Demo.ipynb notebook, I want to see accurate token usage statistics, so that I can understand the cost and performance of my requests.

#### Acceptance Criteria

1. WHEN the notebook's `display_response()` function accesses usage data with `usage.get('input_tokens')`, THEN the System SHALL return the correct input token count
2. WHEN the notebook's `display_response()` function accesses usage data with `usage.get('output_tokens')`, THEN the System SHALL return the correct output token count
3. WHEN the notebook's `display_response()` function accesses usage data with `usage.get('total_tokens')`, THEN the System SHALL return the correct total token count
4. WHEN the notebook runs Example 1 with large text input, THEN the System SHALL display token usage greater than 0
5. WHEN the notebook displays token usage, THEN the System SHALL show accurate counts matching the actual API response

### Requirement 2: Add Individual Token Accessor Methods

**User Story:** As a developer using the LLMManager library, I want individual accessor methods for token counts, so that I don't need to access dictionary keys directly and my code is protected from internal structure changes.

#### Acceptance Criteria

1. WHEN `get_input_tokens()` is called on a successful BedrockResponse, THEN the System SHALL return the input token count as an integer
2. WHEN `get_output_tokens()` is called on a successful BedrockResponse, THEN the System SHALL return the output token count as an integer
3. WHEN `get_total_tokens()` is called on a successful BedrockResponse, THEN the System SHALL return the total token count as an integer
4. WHEN any token accessor is called on an unsuccessful response, THEN the System SHALL return 0
5. WHEN any token accessor is called on a response without usage data, THEN the System SHALL return 0

### Requirement 3: Add Cache Token Accessor Methods

**User Story:** As a developer using prompt caching features, I want individual accessor methods for cache token counts, so that I can easily check cache performance without dictionary access.

#### Acceptance Criteria

1. WHEN `get_cache_read_tokens()` is called on a BedrockResponse, THEN the System SHALL return the cache read token count as an integer
2. WHEN `get_cache_write_tokens()` is called on a BedrockResponse, THEN the System SHALL return the cache write token count as an integer
3. WHEN cache accessor methods are called on a response without cache data, THEN the System SHALL return 0
4. WHEN cache accessor methods are called, THEN the System SHALL not raise exceptions for missing data

### Requirement 4: Maintain Backward Compatibility

**User Story:** As a developer with existing code using `get_usage()`, I want my code to continue working unchanged, so that I don't have to update all my existing scripts.

#### Acceptance Criteria

1. WHEN existing code calls `get_usage()`, THEN the System SHALL continue to return a dictionary with snake_case keys
2. WHEN existing code accesses `usage.get('input_tokens')`, THEN the System SHALL return the correct value
3. WHEN the library is updated, THEN the System SHALL not break any existing code using `get_usage()`
4. WHEN new accessor methods are added, THEN the System SHALL not modify the behavior of `get_usage()`

### Requirement 5: Consistent API Design

**User Story:** As a maintainer of the LLMManager library, I want consistent accessor method patterns across the BedrockResponse class, so that the API is predictable and easy to use.

#### Acceptance Criteria

1. WHEN accessor methods are added, THEN the System SHALL follow the existing naming pattern (`get_*`)
2. WHEN accessor methods return numeric values, THEN the System SHALL return 0 for missing data (not None)
3. WHEN accessor methods are documented, THEN the System SHALL include clear return type annotations
4. WHEN accessor methods are implemented, THEN the System SHALL use the existing `get_usage()` method internally to avoid duplication
