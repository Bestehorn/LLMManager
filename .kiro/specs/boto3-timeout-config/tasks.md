# Implementation Plan: Boto3 Timeout Configuration

## Overview

Incremental implementation of `Boto3Config` dataclass and its propagation through LLMManager → AuthManager → boto3 clients. Each task builds on the previous, with tests validating correctness at each step.

## Tasks

- [x] 1. Create Boto3Config dataclass and validation
  - [x] 1.1 Add `Boto3Config` frozen dataclass to `src/bestehorn_llmmanager/bedrock/models/llm_manager_structures.py`
    - Add `import botocore.config` at top of file
    - Define `Boto3Config` with fields: `read_timeout=600`, `connect_timeout=60`, `max_pool_connections=10`, `retries_max_attempts=3`
    - Implement `__post_init__` validation: `read_timeout > 0`, `connect_timeout > 0`, `max_pool_connections > 0`, `retries_max_attempts >= 0`
    - Implement `to_botocore_config()` method returning `botocore.config.Config` with `retries={"max_attempts": value}`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 4.2, 4.3, 4.4, 4.5_

  - [x] 1.2 Write property tests for Boto3Config
    - **Property 1: Round-trip preservation** — For any valid Boto3Config, to_botocore_config() preserves all field values
    - **Validates: Requirements 1.6, 1.7**
    - **Property 2: Positive-value validation** — For any non-positive int in read_timeout/connect_timeout/max_pool_connections, ValueError is raised
    - **Validates: Requirements 4.2, 4.3, 4.4**
    - **Property 3: Negative retries validation** — For any negative int in retries_max_attempts, ValueError is raised
    - **Validates: Requirements 4.5**
    - Create test file: `test/bestehorn_llmmanager/bedrock/models/test_boto3_config.py`

  - [x] 1.3 Write unit tests for Boto3Config defaults and immutability
    - Test default values match requirements (600, 60, 10, 3)
    - Test frozen behavior (assignment raises FrozenInstanceError)
    - Test to_botocore_config() returns botocore.config.Config instance
    - Test retries is wrapped as dict with max_attempts key
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 2. Integrate Boto3Config into AuthManager
  - [x] 2.1 Modify `AuthManager.__init__` to accept `boto3_config: Optional[Boto3Config] = None`
    - Store converted `botocore.config.Config` as `self._botocore_config` (or `None`)
    - Pass `config=self._botocore_config` in `get_bedrock_client()` → `session.client("bedrock-runtime", ..., config=...)`
    - Pass `config=self._botocore_config` in `get_bedrock_control_client()` → `session.client("bedrock", ..., config=...)`
    - _Requirements: 2.2, 5.1, 5.2_

  - [x] 2.2 Write unit tests for AuthManager config propagation
    - Mock `boto3.Session` and verify `session.client()` receives `config=` kwarg when Boto3Config is provided
    - Verify both bedrock-runtime and bedrock control plane clients receive the config
    - Verify no `config=` kwarg when Boto3Config is None (backward compat)
    - Create test file: `test/bestehorn_llmmanager/bedrock/auth/test_auth_manager_boto3_config.py`
    - _Requirements: 2.2, 5.1, 5.2_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Integrate Boto3Config into LLMManager and ParallelLLMManager
  - [x] 4.1 Add `boto3_config: Optional[Boto3Config] = None` parameter to `LLMManager.__init__`
    - Add type validation: if not None and not isinstance Boto3Config, raise ConfigurationError
    - Create default `Boto3Config()` when None
    - Pass to `AuthManager(auth_config=auth_config, boto3_config=boto3_config)`
    - Pass the configured `AuthManager` to `BedrockModelCatalog` (already done — catalog receives auth_manager)
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 5.3, 6.1, 6.3_

  - [x] 4.2 Add `boto3_config: Optional[Boto3Config] = None` parameter to `ParallelLLMManager.__init__`
    - Forward to internal `LLMManager` constructor call
    - _Requirements: 3.1, 3.2, 3.3, 6.2_

  - [x] 4.3 Write property test for invalid type rejection
    - **Property 4: Invalid type rejection** — For any non-Boto3Config, non-None value, LLMManager raises ConfigurationError
    - **Validates: Requirements 4.1**
    - Mock AuthManager and BedrockModelCatalog to isolate type check
    - Create test file: `test/bestehorn_llmmanager/test_LLMManager_boto3_config.py`

  - [x] 4.4 Write unit tests for LLMManager and ParallelLLMManager integration
    - Test LLMManager creates default Boto3Config when None
    - Test ParallelLLMManager forwards boto3_config to internal LLMManager
    - Test end-to-end: ParallelLLMManager with read_timeout=900 propagates to boto3 clients
    - _Requirements: 2.1, 2.3, 3.1, 3.2, 3.3_

- [x] 5. Export Boto3Config from package __init__.py
  - Add `Boto3Config` to `src/bestehorn_llmmanager/__init__.py` exports
  - _Requirements: 1.1_

- [x] 6. Update documentation
  - Update `docs/forLLMConsumption.md` with Boto3Config in constructor signatures and a usage example
  - Update `docs/ProjectStructure.md` if any new files were added
  - _Requirements: all_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- No new files are created for `Boto3Config` — it lives in the existing `llm_manager_structures.py` alongside `AuthConfig` and `RetryConfig`
- `botocore` is already a project dependency
