# Requirements Document: Inference Profile Support

## Introduction

AWS Bedrock has introduced a new requirement for certain models (particularly newer Claude models like Claude Sonnet 4.5) where direct model ID invocation is no longer supported. Instead, these models must be accessed through **Cross-Region Inference (CRIS) profiles** (also called inference profiles). When attempting to invoke these models directly, AWS returns a ValidationException stating:

```
Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 with on-demand throughput 
isn't supported. Retry your request with the ID or ARN of an inference profile that 
contains this model.
```

This creates a poor user experience with multiple failed retry attempts before eventually falling back to older models that support direct invocation. The system needs to intelligently detect when models require inference profiles and automatically use the appropriate access method.

## Glossary

- **Inference_Profile**: An AWS Bedrock resource (also called CRIS profile) that provides access to foundation models, potentially across multiple regions
- **Direct_Model_Access**: Invoking a model using its model ID directly (e.g., `anthropic.claude-3-haiku-20240307-v1:0`)
- **Profile_Based_Access**: Invoking a model through an inference profile ARN or ID
- **Access_Method**: The method used to invoke a model (direct, profile-only, or both)
- **Model_Access_Info**: Data structure containing information about how to access a model in a specific region
- **Retry_Manager**: Component that handles retry logic and error recovery
- **Bedrock_Model_Catalog**: System that manages model availability and access information
- **Profile_Requirement_Detection**: The process of determining whether a model requires profile-based access
- **Automatic_Profile_Selection**: Choosing the appropriate inference profile for a model/region combination

## Requirements

### Requirement 1: Detect Profile Requirement from Validation Errors

**User Story:** As a developer, I want the system to automatically detect when a model requires inference profile access from AWS error messages, so that subsequent requests use the correct access method without manual intervention.

#### Acceptance Criteria

1. WHEN a ValidationException contains the text "with on-demand throughput isn't supported", THE System SHALL identify it as a profile requirement error
2. WHEN a ValidationException contains the text "Retry your request with the ID or ARN of an inference profile", THE System SHALL identify it as a profile requirement error
3. WHEN a profile requirement error is detected, THE System SHALL extract the model ID from the error message
4. WHEN a profile requirement error is detected, THE System SHALL log the detection at WARNING level
5. WHEN a profile requirement error is detected for a model/region combination, THE System SHALL record this requirement for future requests

### Requirement 2: Automatic Inference Profile Selection

**User Story:** As a developer, I want the system to automatically select and use the appropriate inference profile when a model requires it, so that my requests succeed without manual profile configuration.

#### Acceptance Criteria

1. WHEN a model requires profile-based access, THE System SHALL query the catalog for available inference profiles for that model
2. WHEN multiple inference profiles are available for a model/region, THE System SHALL select the first available profile
3. WHEN an inference profile is selected, THE System SHALL use the profile ID/ARN instead of the direct model ID
4. WHEN no inference profile is available for a required model/region, THE System SHALL try the next model/region combination
5. WHEN using an inference profile, THE System SHALL log the profile ID at DEBUG level

### Requirement 3: Catalog Integration for Profile Information

**User Story:** As a system maintainer, I want the model catalog to provide inference profile information alongside model availability data, so that the system can make informed access method decisions.

#### Acceptance Criteria

1. WHEN the catalog loads model data, THE System SHALL include inference profile IDs for each model/region combination
2. WHEN querying model access information, THE System SHALL return both direct model ID and inference profile ID (if available)
3. WHEN a model has an inference profile, THE System SHALL indicate the access method as "profile_only", "direct", or "both"
4. THE Catalog SHALL expose a method to query inference profiles by model name and region
5. THE Catalog SHALL handle cases where profile information is unavailable gracefully

### Requirement 4: Retry Logic Enhancement for Profile Errors

**User Story:** As a developer, I want the retry manager to automatically retry with inference profiles when direct access fails, so that requests succeed on the first retry instead of exhausting all model/region combinations.

#### Acceptance Criteria

1. WHEN a profile requirement error is detected, THE Retry_Manager SHALL immediately retry with the inference profile for the same model/region
2. WHEN retrying with an inference profile, THE Retry_Manager SHALL NOT count it as a separate retry attempt
3. WHEN the profile-based retry succeeds, THE System SHALL record the successful access method
4. WHEN the profile-based retry fails, THE Retry_Manager SHALL continue to the next model/region combination
5. WHEN all profile-based retries fail, THE Retry_Manager SHALL fall back to models that support direct access

### Requirement 5: Access Method Tracking and Learning

**User Story:** As a system operator, I want the system to learn which models require inference profiles over time, so that future requests use the correct access method immediately without trial-and-error.

#### Acceptance Criteria

1. WHEN a model succeeds with profile-based access, THE System SHALL record this as the preferred access method
2. WHEN a model succeeds with direct access, THE System SHALL record this as the preferred access method
3. THE System SHALL persist access method preferences across LLMManager instances within the same process
4. WHEN access method information is available, THE System SHALL use it to skip known-incompatible access methods
5. THE System SHALL provide a method to query known access methods for model/region combinations

### Requirement 6: Backward Compatibility with Direct Access

**User Story:** As an existing user, I want models that support direct access to continue working without changes, so that the new profile support doesn't break existing functionality.

#### Acceptance Criteria

1. WHEN a model supports direct access, THE System SHALL use direct model ID by default
2. WHEN a model supports both direct and profile access, THE System SHALL prefer direct access unless configured otherwise
3. WHEN the catalog indicates "direct" access method, THE System SHALL NOT attempt profile-based access
4. WHEN the catalog indicates "both" access method, THE System SHALL try direct access first, then profile access on failure
5. THE System SHALL maintain all existing retry and error handling behaviors for direct access

### Requirement 7: Clear Logging for Profile Usage

**User Story:** As a developer debugging model access issues, I want clear logging that indicates when inference profiles are being used, so that I can understand the access method being employed.

#### Acceptance Criteria

1. WHEN switching from direct to profile access, THE System SHALL log the switch at INFO level
2. WHEN using a profile for the first time, THE System SHALL log the profile ID at INFO level
3. WHEN a profile requirement is detected, THE System SHALL log the model ID and error pattern at WARNING level
4. WHEN profile information is unavailable, THE System SHALL log this at WARNING level
5. THE System SHALL include access method information in retry statistics

### Requirement 8: Profile Information in Response Metadata

**User Story:** As a developer, I want response objects to indicate whether an inference profile was used, so that I can track and monitor profile usage in my application.

#### Acceptance Criteria

1. WHEN a request succeeds using an inference profile, THE BedrockResponse SHALL include the profile ID in metadata
2. WHEN a request succeeds using direct access, THE BedrockResponse SHALL indicate "direct" as the access method
3. THE BedrockResponse SHALL expose a method to query the access method used
4. THE ParallelResponse SHALL aggregate access method statistics across all requests
5. THE Response metadata SHALL distinguish between profile ID and model ID

### Requirement 9: Graceful Degradation When Profiles Unavailable

**User Story:** As a developer, I want the system to gracefully handle cases where profile information is unavailable, so that requests can still succeed using available access methods.

#### Acceptance Criteria

1. WHEN the catalog cannot provide profile information, THE System SHALL attempt direct access
2. WHEN direct access fails with a profile requirement error and no profile is available, THE System SHALL try the next model/region
3. WHEN all models require profiles but none are available, THE System SHALL raise a clear error message
4. THE Error message SHALL indicate that profiles are required but unavailable
5. THE System SHALL suggest checking catalog data freshness in the error message

### Requirement 10: Parallel Processing Support for Profiles

**User Story:** As a developer using parallel processing, I want inference profile support to work seamlessly with parallel requests, so that I can process multiple requests efficiently regardless of access method.

#### Acceptance Criteria

1. WHEN parallel requests target models requiring profiles, THE Parallel_LLM_Manager SHALL use profiles automatically
2. WHEN different parallel requests target different models with different access methods, THE System SHALL apply the correct method to each request
3. WHEN a parallel request fails due to profile requirement, THE System SHALL retry that specific request with a profile
4. THE ParallelResponse SHALL include access method statistics for all requests
5. THE Parallel processing SHALL NOT be slowed down by profile detection logic

### Requirement 11: Documentation and Migration Guide

**User Story:** As a developer, I want clear documentation explaining inference profiles and how the system handles them, so that I can understand the behavior and troubleshoot issues.

#### Acceptance Criteria

1. THE System SHALL provide documentation explaining what inference profiles are
2. THE Documentation SHALL explain when and why profiles are required
3. THE Documentation SHALL include examples of profile-based access
4. THE Documentation SHALL explain how to check which access method was used
5. THE Documentation SHALL provide troubleshooting guidance for profile-related errors

### Requirement 12: Testing Infrastructure for Profile Access

**User Story:** As a developer, I want automated tests that verify profile access works correctly, so that I can ensure the system handles both direct and profile-based access properly.

#### Acceptance Criteria

1. THE Test Suite SHALL include tests that simulate profile requirement errors
2. THE Test Suite SHALL verify automatic profile selection and retry logic
3. THE Test Suite SHALL verify access method tracking and learning
4. THE Test Suite SHALL verify backward compatibility with direct access
5. THE Test Suite SHALL verify profile support in parallel processing
