# Requirements Document

## Introduction

The bestehorn-llmmanager package currently provides no mechanism to configure boto3 client-level settings (read timeout, connect timeout, retries, connection pooling, etc.) for AWS Bedrock API calls. The default boto3 read timeout of 60 seconds is insufficient for large models like Claude Sonnet 4.5, especially in AWS Lambda environments where inference can take several minutes. Users must resort to modifying the global `boto3.DEFAULT_SESSION`, which is fragile and affects all boto3 clients in the process. This feature adds first-class support for configuring boto3 client behavior through a dedicated `Boto3ClientConfig` dataclass with Bedrock-optimized defaults, passed directly through the LLMManager and ParallelLLMManager constructors.

## Glossary

- **LLMManager**: The main class for single AWS Bedrock Converse API requests with retry logic
- **ParallelLLMManager**: Extended class for parallel processing of multiple requests, delegates to an internal LLMManager instance
- **AuthManager**: Internal component responsible for creating boto3 sessions and bedrock-runtime clients
- **Boto3Config**: A new dataclass that wraps boto3 client configuration parameters with Bedrock-optimized defaults, internally converted to a `botocore.config.Config` object when creating clients
- **Read_Timeout**: The maximum time in seconds to wait for a response from the server after a request has been sent
- **Connect_Timeout**: The maximum time in seconds to wait when establishing a connection to the server
- **BedrockModelCatalog**: Internal component that manages model availability data, also creates boto3 clients for API calls

## Requirements

### Requirement 1: Boto3Config Dataclass

**User Story:** As a developer, I want a dedicated configuration class with Bedrock-optimized defaults for boto3 client settings, so that I get sensible timeout behavior out of the box without needing to know botocore internals.

#### Acceptance Criteria

1. THE Boto3Config SHALL be a frozen dataclass with explicit parameters for `read_timeout`, `connect_timeout`, `max_pool_connections`, and `retries_max_attempts`
2. THE Boto3Config SHALL default `read_timeout` to 600 seconds to accommodate long-running Bedrock inference calls
3. THE Boto3Config SHALL default `connect_timeout` to 60 seconds, matching the boto3 default
4. THE Boto3Config SHALL default `max_pool_connections` to 10, matching the boto3 default
5. THE Boto3Config SHALL default `retries_max_attempts` to 3, matching the boto3 default
6. THE Boto3Config SHALL provide a method to convert itself to a `botocore.config.Config` object for use when creating boto3 clients
7. WHEN converting to `botocore.config.Config`, THE Boto3Config SHALL wrap `retries_max_attempts` in a dictionary as `{"max_attempts": value}` because the botocore Config expects retries as a dict parameter

### Requirement 2: Accept Boto3Config in LLMManager

**User Story:** As a developer using LLMManager in AWS Lambda, I want to pass a `Boto3Config` to the LLMManager constructor, so that I can configure boto3 client behavior without modifying global boto3 session state.

#### Acceptance Criteria

1. WHEN a user provides a `boto3_config` parameter of type `Boto3Config` to the LLMManager constructor, THE LLMManager SHALL store the configuration and pass it to the AuthManager
2. WHEN the AuthManager creates a bedrock-runtime client and a `Boto3Config` has been provided, THE AuthManager SHALL convert the config to a `botocore.config.Config` and pass it to the `session.client()` call via the `config` parameter
3. WHEN a user does not provide a `boto3_config` parameter, THE LLMManager SHALL create and use a default `Boto3Config` instance with Bedrock-optimized defaults
4. THE LLMManager SHALL default the `boto3_config` parameter to `None`, which triggers creation of the default `Boto3Config` instance

### Requirement 3: Config Propagation to ParallelLLMManager

**User Story:** As a developer using ParallelLLMManager, I want the same `Boto3Config` support to be available through the ParallelLLMManager constructor, so that parallel requests also benefit from custom boto3 client configuration.

#### Acceptance Criteria

1. THE ParallelLLMManager SHALL expose a `boto3_config` constructor parameter with the same type and default as the LLMManager
2. WHEN a user provides a `boto3_config` parameter to the ParallelLLMManager constructor, THE ParallelLLMManager SHALL forward the value to the internal LLMManager instance it creates
3. WHEN a user creates a ParallelLLMManager with a `Boto3Config` specifying `read_timeout=900`, THE underlying boto3 clients used for parallel request execution SHALL use that read timeout value

### Requirement 4: Config Validation

**User Story:** As a developer, I want clear error messages when I provide invalid config values, so that I can quickly fix configuration mistakes.

#### Acceptance Criteria

1. WHEN a user provides a `boto3_config` value that is not an instance of `Boto3Config` and is not `None`, THE LLMManager SHALL raise a `ConfigurationError` with a descriptive message indicating the expected type
2. WHEN a user creates a `Boto3Config` with a `read_timeout` value that is not a positive number, THE Boto3Config SHALL raise a `ValueError` with a descriptive message
3. WHEN a user creates a `Boto3Config` with a `connect_timeout` value that is not a positive number, THE Boto3Config SHALL raise a `ValueError` with a descriptive message
4. WHEN a user creates a `Boto3Config` with a `max_pool_connections` value that is not a positive integer, THE Boto3Config SHALL raise a `ValueError` with a descriptive message
5. WHEN a user creates a `Boto3Config` with a `retries_max_attempts` value that is a negative integer, THE Boto3Config SHALL raise a `ValueError` with a descriptive message

### Requirement 5: Config Application to All Client Types

**User Story:** As a developer, I want the boto3 config to apply consistently to all boto3 clients created by the library, so that client behavior is predictable across all API interactions.

#### Acceptance Criteria

1. WHEN a `Boto3Config` is configured, THE AuthManager SHALL apply the resulting `botocore.config.Config` to bedrock-runtime clients created via `get_bedrock_client`
2. WHEN a `Boto3Config` is configured, THE AuthManager SHALL apply the resulting `botocore.config.Config` to bedrock control plane clients created via `get_bedrock_control_client`
3. WHEN a `Boto3Config` is configured, THE BedrockModelCatalog SHALL receive the same config for any boto3 clients it creates internally

### Requirement 6: Backward Compatibility

**User Story:** As an existing user of the library, I want the new `boto3_config` parameter to be optional with sensible defaults, so that my existing code continues to work without changes.

#### Acceptance Criteria

1. THE LLMManager SHALL default `boto3_config` to `None`
2. THE ParallelLLMManager SHALL default `boto3_config` to `None`
3. WHEN `boto3_config` is `None`, THE LLMManager SHALL create and use a default `Boto3Config` instance, which means existing users automatically benefit from the Bedrock-optimized 600-second read timeout
