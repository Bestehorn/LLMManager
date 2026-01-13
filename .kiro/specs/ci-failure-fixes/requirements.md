# Requirements Document

## Introduction

This specification addresses critical CI failures and code quality issues in the bestehorn-llmmanager project. The CI pipeline is currently failing due to a flaky property-based test and generating over 50,000 deprecation warnings from using outdated APIs. These issues must be resolved to enable new releases and maintain code quality.

## Glossary

- **System**: The bestehorn-llmmanager library
- **RetryManager**: Component responsible for retry logic with model access method selection
- **AccessMethodSelector**: Component that selects optimal access method (direct, regional CRIS, or global CRIS)
- **ModelAccessInfo**: Data structure containing model availability and access method information
- **Property-Based Test (PBT)**: Test that validates universal properties across many generated inputs using Hypothesis
- **Flaky Test**: Test that intermittently passes and fails without code changes
- **Deprecation Warning**: Warning indicating use of deprecated API that will be removed in future version
- **Direct Access**: Accessing a model using its model ID directly
- **CRIS**: Cross-Region Inference Service - allows accessing models via inference profiles
- **Regional CRIS**: CRIS profile scoped to a specific region
- **Global CRIS**: CRIS profile that works across regions

## Requirements

### Requirement 1: Fix Flaky Property-Based Test

**User Story:** As a developer, I want the CI pipeline to pass reliably, so that I can confidently merge code and release new versions.

#### Acceptance Criteria

1. WHEN the property-based test `test_direct_access_preferred_by_default` is executed THEN the System SHALL produce consistent results across all test runs
2. WHEN a model has direct access available and no learned preference exists THEN the AccessMethodSelector SHALL always select direct access as the first attempt
3. WHEN the test generates random ModelAccessInfo with direct access enabled THEN the System SHALL use the direct model ID (not a profile ARN) for the first attempt
4. WHEN the test is run 100 times consecutively THEN the System SHALL pass all 100 runs without flakiness
5. IF the AccessMethodSelector has non-deterministic behavior THEN the System SHALL identify and eliminate the source of non-determinism

### Requirement 2: Eliminate Deprecated API Usage in Production Code

**User Story:** As a maintainer, I want the production code to use only current APIs, so that the library remains compatible with future versions and doesn't generate warnings for users.

#### Acceptance Criteria

1. WHEN production code accesses model access information THEN the System SHALL use orthogonal access flags (has_direct_access, has_regional_cris, has_global_cris) instead of the deprecated access_method property
2. WHEN production code needs a CRIS profile ID THEN the System SHALL use regional_cris_profile_id or global_cris_profile_id instead of the deprecated inference_profile_id property
3. WHEN production code creates ModelAccessInfo instances THEN the System SHALL not use deprecated enum values (ModelAccessMethod.BOTH, ModelAccessMethod.CRIS_ONLY)
4. WHEN the test suite runs THEN the System SHALL generate zero deprecation warnings from production code
5. THE System SHALL maintain backward compatibility for deprecated APIs while internal code uses current APIs

### Requirement 3: Update Test Code to Use Current APIs

**User Story:** As a developer, I want test code to demonstrate best practices, so that tests serve as examples and don't generate noise in test output.

#### Acceptance Criteria

1. WHEN test code creates ModelAccessInfo instances THEN the System SHALL use the current constructor with orthogonal flags
2. WHEN test code validates access methods THEN the System SHALL check orthogonal flags instead of using deprecated properties
3. WHEN test code uses deprecated manager classes (ModelManager, CRISManager, UnifiedModelManager) THEN the System SHALL update to use BedrockModelCatalog or clearly mark as legacy compatibility tests
4. WHEN the test suite runs THEN the System SHALL generate fewer than 100 deprecation warnings total (down from 50,000+)
5. WHEN tests validate backward compatibility of deprecated APIs THEN the System SHALL clearly document these as intentional deprecation tests

### Requirement 4: Improve Test Determinism

**User Story:** As a developer, I want property-based tests to be deterministic, so that failures are reproducible and debuggable.

#### Acceptance Criteria

1. WHEN the AccessMethodSelector selects an access method THEN the System SHALL follow a deterministic algorithm based on input parameters
2. WHEN multiple access methods are available THEN the System SHALL apply a consistent preference order (direct → regional CRIS → global CRIS)
3. WHEN a learned preference exists THEN the System SHALL consistently apply that preference before falling back to default order
4. WHEN the test strategy generates ModelAccessInfo THEN the System SHALL ensure generated data is valid and consistent
5. WHEN debugging a test failure THEN the System SHALL provide clear logging of which access method was selected and why

### Requirement 5: Validate CI Pipeline Health

**User Story:** As a team, I want the CI pipeline to pass cleanly, so that we can release new versions with confidence.

#### Acceptance Criteria

1. WHEN all fixes are applied THEN the System SHALL pass all unit tests without failures
2. WHEN all fixes are applied THEN the System SHALL pass all property-based tests without flakiness
3. WHEN the test suite runs THEN the System SHALL complete in reasonable time (under 20 minutes)
4. WHEN code quality checks run THEN the System SHALL pass black, isort, flake8, mypy, and bandit without errors
5. WHEN the full CI workflow executes THEN the System SHALL report success and be ready for release

### Requirement 6: Document Root Cause and Prevention

**User Story:** As a maintainer, I want to understand what caused these issues, so that we can prevent similar problems in the future.

#### Acceptance Criteria

1. WHEN the root cause analysis is complete THEN the System SHALL document why the test was flaky
2. WHEN the root cause analysis is complete THEN the System SHALL document why deprecation warnings accumulated
3. WHEN fixes are implemented THEN the System SHALL include code comments explaining the deterministic behavior
4. WHEN the spec is complete THEN the System SHALL provide recommendations for preventing similar issues
5. THE System SHALL update development guidelines to catch deprecation warnings early
