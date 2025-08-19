"""
Constants for parallel processing functionality in LLM Manager system.
Contains string constants and configuration values for parallel execution.
"""

from typing import Final


class ParallelProcessingFields:
    """JSON field constants for parallel processing requests and responses."""

    # BedrockConverseRequest fields
    REQUEST_ID: Final[str] = "request_id"
    MESSAGES: Final[str] = "messages"
    SYSTEM: Final[str] = "system"
    INFERENCE_CONFIG: Final[str] = "inference_config"
    ADDITIONAL_MODEL_REQUEST_FIELDS: Final[str] = "additional_model_request_fields"
    ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS: Final[str] = "additional_model_response_field_paths"
    GUARDRAIL_CONFIG: Final[str] = "guardrail_config"
    TOOL_CONFIG: Final[str] = "tool_config"
    REQUEST_METADATA: Final[str] = "request_metadata"
    PROMPT_VARIABLES: Final[str] = "prompt_variables"

    # ParallelResponse fields
    SUCCESS: Final[str] = "success"
    REQUEST_RESPONSES: Final[str] = "request_responses"
    TOTAL_DURATION_MS: Final[str] = "total_duration_ms"
    PARALLEL_EXECUTION_STATS: Final[str] = "parallel_execution_stats"
    WARNINGS: Final[str] = "warnings"
    FAILED_REQUESTS: Final[str] = "failed_requests"

    # ParallelExecutionStats fields
    TOTAL_REQUESTS: Final[str] = "total_requests"
    SUCCESSFUL_REQUESTS: Final[str] = "successful_requests"
    FAILED_REQUESTS_COUNT: Final[str] = "failed_requests_count"
    AVERAGE_REQUEST_DURATION_MS: Final[str] = "average_request_duration_ms"
    MAX_REQUEST_DURATION_MS: Final[str] = "max_request_duration_ms"
    MIN_REQUEST_DURATION_MS: Final[str] = "min_request_duration_ms"
    CONCURRENT_EXECUTIONS: Final[str] = "concurrent_executions"
    REGION_DISTRIBUTION: Final[str] = "region_distribution"


class ParallelConfig:
    """Configuration constants for parallel processing."""

    # Default values
    DEFAULT_MAX_CONCURRENT_REQUESTS: Final[int] = 5
    DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[int] = 300
    # DEPRECATED: Use auto-calculation based on available regions and max_concurrent_requests
    DEFAULT_TARGET_REGIONS_PER_REQUEST: Final[int] = 5
    DEFAULT_ENABLE_REQUEST_PRIORITIZATION: Final[bool] = True

    # Request ID generation
    REQUEST_ID_PREFIX: Final[str] = "req"
    REQUEST_ID_HASH_LENGTH: Final[int] = 12
    REQUEST_ID_SEPARATOR: Final[str] = "_"

    # Failure handling strategies
    FAILURE_STRATEGY_CONTINUE: Final[str] = "continue_on_failure"
    FAILURE_STRATEGY_STOP: Final[str] = "stop_on_first_failure"
    FAILURE_STRATEGY_THRESHOLD: Final[str] = "stop_on_threshold"

    # Load balancing strategies
    LOAD_BALANCE_ROUND_ROBIN: Final[str] = "round_robin"
    LOAD_BALANCE_RANDOM: Final[str] = "random"
    LOAD_BALANCE_LEAST_LOADED: Final[str] = "least_loaded"


class ParallelLogMessages:
    """Logging message constants for parallel processing."""

    # Initialization messages
    PARALLEL_MANAGER_INITIALIZED: Final[str] = (
        "ParallelLLMManager initialized with {model_count} models, {region_count} regions, max_concurrent: {max_concurrent}"
    )
    REGION_DISTRIBUTION_CALCULATED: Final[str] = (
        "Region distribution calculated for {request_count} requests across {region_count} regions"
    )

    # Request processing messages
    PARALLEL_EXECUTION_STARTED: Final[str] = (
        "Starting parallel execution of {request_count} requests with {concurrent_limit} concurrent executions"
    )
    REQUEST_BATCH_PROCESSING: Final[str] = (
        "Processing batch of {batch_size} requests in regions: {regions}"
    )
    PARALLEL_EXECUTION_COMPLETED: Final[str] = (
        "Parallel execution completed: {successful}/{total} requests successful in {duration_ms}ms"
    )

    # Error and validation messages
    REQUEST_ID_COLLISION_DETECTED: Final[str] = (
        "Request ID collision detected: '{request_id}' used by {collision_count} requests"
    )
    REQUEST_VALIDATION_FAILED: Final[str] = (
        "Request validation failed: {error_count} collisions detected"
    )
    PARALLEL_REQUEST_FAILED: Final[str] = "Parallel request '{request_id}' failed: {error}"

    # Performance messages
    REGION_DISTRIBUTION_STATS: Final[str] = (
        "Region distribution - Total: {total_assignments}, Unique regions: {unique_regions}, Max per region: {max_per_region}"
    )
    EXECUTION_PERFORMANCE: Final[str] = (
        "Execution performance - Avg: {avg_ms}ms, Min: {min_ms}ms, Max: {max_ms}ms"
    )

    # Auto-adjustment messages
    TARGET_REGIONS_AUTO_ADJUSTED: Final[str] = (
        "target_regions_per_request not specified, auto-adjusted to {adjusted_value} "
        "(based on max_concurrent_requests={max_concurrent} and available_regions={available_regions})"
    )
    TARGET_REGIONS_CAPPED_BY_AVAILABILITY: Final[str] = (
        "target_regions_per_request auto-adjusted to {adjusted_value} due to limited region availability "
        "(available_regions={available_regions})"
    )
    TARGET_REGIONS_CAPPED_BY_CONCURRENCY: Final[str] = (
        "target_regions_per_request auto-adjusted to {adjusted_value} based on concurrency limit "
        "(max_concurrent_requests={max_concurrent})"
    )


class ParallelErrorMessages:
    """Error message constants for parallel processing."""

    # Configuration errors
    INVALID_CONCURRENT_LIMIT: Final[str] = "max_concurrent_requests must be positive, got: {value}"
    INVALID_TARGET_REGIONS: Final[str] = "target_regions_per_request must be positive, got: {value}"
    INSUFFICIENT_REGIONS: Final[str] = (
        "Not enough regions available: requested {requested}, available {available}"
    )

    # Request validation errors
    EMPTY_REQUEST_LIST: Final[str] = "Request list cannot be empty"
    REQUEST_ID_COLLISIONS: Final[str] = "Request ID collisions detected for IDs: {collision_ids}"
    INVALID_REQUEST_STRUCTURE: Final[str] = (
        "Invalid request structure in request '{request_id}': {validation_error}"
    )

    # Execution errors
    PARALLEL_EXECUTION_FAILED: Final[str] = (
        "Parallel execution failed: {failed_count}/{total_count} requests failed"
    )
    REQUEST_TIMEOUT_EXCEEDED: Final[str] = (
        "Request '{request_id}' exceeded timeout of {timeout_seconds} seconds"
    )
    ALL_REGIONS_FAILED: Final[str] = "All assigned regions failed for request '{request_id}'"

    # Resource errors
    INSUFFICIENT_RESOURCES: Final[str] = (
        "Insufficient resources for parallel execution: {resource_details}"
    )
    REGION_CAPACITY_EXCEEDED: Final[str] = (
        "Region capacity exceeded for region '{region}': {current_load}/{max_capacity}"
    )
