"""
Data structures for parallel processing functionality in LLM Manager system.
Contains typed data classes for parallel execution configuration, requests, and responses.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .bedrock_response import BedrockResponse
from .parallel_constants import ParallelConfig, ParallelProcessingFields


class FailureHandlingStrategy(Enum):
    """Enumeration of failure handling strategies for parallel processing."""

    CONTINUE_ON_FAILURE = ParallelConfig.FAILURE_STRATEGY_CONTINUE
    STOP_ON_FIRST_FAILURE = ParallelConfig.FAILURE_STRATEGY_STOP
    STOP_ON_THRESHOLD = ParallelConfig.FAILURE_STRATEGY_THRESHOLD


class LoadBalancingStrategy(Enum):
    """Enumeration of load balancing strategies for parallel processing."""

    ROUND_ROBIN = ParallelConfig.LOAD_BALANCE_ROUND_ROBIN
    RANDOM = ParallelConfig.LOAD_BALANCE_RANDOM
    LEAST_LOADED = ParallelConfig.LOAD_BALANCE_LEAST_LOADED


@dataclass
class BedrockConverseRequest:
    """
    Encapsulates all parameters for a Bedrock Converse API request.

    Provides automatic request ID generation and validation to ensure
    uniqueness across parallel processing operations.

    Attributes:
        messages: List of message objects for the conversation
        system: List of system message objects
        inference_config: Inference configuration parameters
        additional_model_request_fields: Model-specific request parameters
        additional_model_response_field_paths: Additional response fields to return
        guardrail_config: Guardrail configuration
        tool_config: Tool use configuration
        request_metadata: Metadata for the request
        prompt_variables: Variables for prompt templates
        request_id: Unique identifier for the request (auto-generated if None)
    """

    messages: List[Dict[str, Any]]
    system: Optional[List[Any]] = None
    inference_config: Optional[Dict[str, Any]] = None
    additional_model_request_fields: Optional[Dict[str, Any]] = None
    additional_model_response_field_paths: Optional[List[str]] = None
    guardrail_config: Optional[Dict[str, Any]] = None
    tool_config: Optional[Dict[str, Any]] = None
    request_metadata: Optional[Dict[str, Any]] = None
    prompt_variables: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Generate request ID if not provided."""
        if self.request_id is None:
            self.request_id = self._generate_request_id()

    def _generate_request_id(self) -> str:
        """
        Generate unique request ID based on content hash and timestamp.

        Returns:
            Unique request ID string
        """
        # Create hash from request content for uniqueness
        content_data = {
            ParallelProcessingFields.MESSAGES: self._sanitize_content_for_hashing(self.messages),
            ParallelProcessingFields.SYSTEM: self.system,
            ParallelProcessingFields.INFERENCE_CONFIG: self.inference_config,
        }

        content_str = json.dumps(obj=content_data, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[
            : ParallelConfig.REQUEST_ID_HASH_LENGTH
        ]

        # Add microsecond timestamp for additional uniqueness
        timestamp = int(time.time() * 1000000)  # microsecond precision

        return f"{ParallelConfig.REQUEST_ID_PREFIX}{ParallelConfig.REQUEST_ID_SEPARATOR}{content_hash}{ParallelConfig.REQUEST_ID_SEPARATOR}{timestamp}"

    def _sanitize_content_for_hashing(self, content: Any) -> Any:
        """
        Sanitize content for JSON serialization by replacing bytes objects with their hashes.

        This method recursively processes content structures and replaces any bytes objects
        with their SHA-256 hash representation, enabling JSON serialization while maintaining
        uniqueness for request ID generation.

        Args:
            content: Content to sanitize (can be dict, list, bytes, or primitive types)

        Returns:
            Sanitized content safe for JSON serialization
        """
        if isinstance(content, bytes):
            # Replace bytes with their hash for uniqueness while enabling JSON serialization
            return f"<bytes_hash:{hashlib.sha256(content).hexdigest()[:16]}>"

        elif isinstance(content, dict):
            # Recursively sanitize dictionary values
            return {
                key: self._sanitize_content_for_hashing(value) for key, value in content.items()
            }

        elif isinstance(content, list):
            # Recursively sanitize list items
            return [self._sanitize_content_for_hashing(item) for item in content]

        else:
            # Return primitive types as-is (str, int, float, bool, None)
            return content

    def to_converse_args(self) -> Dict[str, Any]:
        """
        Convert to dictionary format compatible with LLMManager.converse().

        Returns:
            Dictionary with converse API arguments using Python parameter names
        """
        args: Dict[str, Any] = {"messages": self.messages}

        if self.system is not None:
            args["system"] = self.system
        if self.inference_config is not None:
            args["inference_config"] = self.inference_config
        if self.additional_model_request_fields is not None:
            args["additional_model_request_fields"] = self.additional_model_request_fields
        if self.additional_model_response_field_paths is not None:
            args["additional_model_response_field_paths"] = (
                self.additional_model_response_field_paths
            )
        if self.guardrail_config is not None:
            args["guardrail_config"] = self.guardrail_config
        if self.tool_config is not None:
            args["tool_config"] = self.tool_config
        if self.request_metadata is not None:
            args["request_metadata"] = self.request_metadata
        if self.prompt_variables is not None:
            args["prompt_variables"] = self.prompt_variables

        return args

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the request
        """
        return {
            ParallelProcessingFields.REQUEST_ID: self.request_id,
            ParallelProcessingFields.MESSAGES: self.messages,
            ParallelProcessingFields.SYSTEM: self.system,
            ParallelProcessingFields.INFERENCE_CONFIG: self.inference_config,
            ParallelProcessingFields.ADDITIONAL_MODEL_REQUEST_FIELDS: self.additional_model_request_fields,
            ParallelProcessingFields.ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS: self.additional_model_response_field_paths,
            ParallelProcessingFields.GUARDRAIL_CONFIG: self.guardrail_config,
            ParallelProcessingFields.TOOL_CONFIG: self.tool_config,
            ParallelProcessingFields.REQUEST_METADATA: self.request_metadata,
            ParallelProcessingFields.PROMPT_VARIABLES: self.prompt_variables,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BedrockConverseRequest":
        """
        Create BedrockConverseRequest from dictionary data.

        Args:
            data: Dictionary containing request data

        Returns:
            BedrockConverseRequest instance
        """
        return cls(
            messages=data[ParallelProcessingFields.MESSAGES],
            system=data.get(ParallelProcessingFields.SYSTEM),
            inference_config=data.get(ParallelProcessingFields.INFERENCE_CONFIG),
            additional_model_request_fields=data.get(
                ParallelProcessingFields.ADDITIONAL_MODEL_REQUEST_FIELDS
            ),
            additional_model_response_field_paths=data.get(
                ParallelProcessingFields.ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS
            ),
            guardrail_config=data.get(ParallelProcessingFields.GUARDRAIL_CONFIG),
            tool_config=data.get(ParallelProcessingFields.TOOL_CONFIG),
            request_metadata=data.get(ParallelProcessingFields.REQUEST_METADATA),
            prompt_variables=data.get(ParallelProcessingFields.PROMPT_VARIABLES),
            request_id=data.get(ParallelProcessingFields.REQUEST_ID),
        )

    def __repr__(self) -> str:
        """Return string representation of the BedrockConverseRequest."""
        return (
            f"BedrockConverseRequest(id={self.request_id}, "
            f"messages={len(self.messages)}, "
            f"system={self.system is not None}, "
            f"inference_config={self.inference_config is not None})"
        )


@dataclass(frozen=True)
class ParallelProcessingConfig:
    """
    Configuration for parallel processing behavior.

    Attributes:
        max_concurrent_requests: Maximum number of requests to process concurrently
        request_timeout_seconds: Timeout for individual requests
        enable_request_prioritization: Whether to enable request prioritization
        failure_handling_strategy: Strategy for handling failed requests
        load_balancing_strategy: Strategy for distributing requests across regions
        failure_threshold: Threshold for STOP_ON_THRESHOLD strategy (0.0-1.0)
    """

    max_concurrent_requests: int = ParallelConfig.DEFAULT_MAX_CONCURRENT_REQUESTS
    request_timeout_seconds: int = ParallelConfig.DEFAULT_REQUEST_TIMEOUT_SECONDS
    enable_request_prioritization: bool = ParallelConfig.DEFAULT_ENABLE_REQUEST_PRIORITIZATION
    failure_handling_strategy: FailureHandlingStrategy = FailureHandlingStrategy.CONTINUE_ON_FAILURE
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    failure_threshold: float = 0.5

    def __post_init__(self) -> None:
        """Validate parallel processing configuration."""
        if self.max_concurrent_requests <= 0:
            raise ValueError(
                f"max_concurrent_requests must be positive, got: {self.max_concurrent_requests}"
            )
        if self.request_timeout_seconds <= 0:
            raise ValueError(
                f"request_timeout_seconds must be positive, got: {self.request_timeout_seconds}"
            )
        if not (0.0 <= self.failure_threshold <= 1.0):
            raise ValueError(
                f"failure_threshold must be between 0.0 and 1.0, got: {self.failure_threshold}"
            )


@dataclass
class ParallelExecutionStats:
    """
    Statistics about parallel execution performance.

    Attributes:
        total_requests: Total number of requests processed
        successful_requests: Number of successful requests
        failed_requests_count: Number of failed requests
        average_request_duration_ms: Average duration per request
        max_request_duration_ms: Maximum request duration
        min_request_duration_ms: Minimum request duration
        concurrent_executions: Peak number of concurrent executions
        region_distribution: Distribution of requests across regions
    """

    total_requests: int
    successful_requests: int
    failed_requests_count: int
    average_request_duration_ms: float
    max_request_duration_ms: float
    min_request_duration_ms: float
    concurrent_executions: int
    region_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the stats
        """
        return {
            ParallelProcessingFields.TOTAL_REQUESTS: self.total_requests,
            ParallelProcessingFields.SUCCESSFUL_REQUESTS: self.successful_requests,
            ParallelProcessingFields.FAILED_REQUESTS_COUNT: self.failed_requests_count,
            ParallelProcessingFields.AVERAGE_REQUEST_DURATION_MS: self.average_request_duration_ms,
            ParallelProcessingFields.MAX_REQUEST_DURATION_MS: self.max_request_duration_ms,
            ParallelProcessingFields.MIN_REQUEST_DURATION_MS: self.min_request_duration_ms,
            ParallelProcessingFields.CONCURRENT_EXECUTIONS: self.concurrent_executions,
            ParallelProcessingFields.REGION_DISTRIBUTION: self.region_distribution,
        }

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as a percentage."""
        return 100.0 - self.success_rate


@dataclass
class ParallelResponse:
    """
    Comprehensive response object from parallel LLM processing operations.

    Attributes:
        success: Whether the overall parallel operation was successful
        request_responses: Mapping of request_id to BedrockResponse
        total_duration_ms: Total time taken for parallel execution
        parallel_execution_stats: Statistics about the parallel execution
        warnings: List of warning messages encountered
        failed_requests: List of request IDs that failed completely
    """

    success: bool
    request_responses: Dict[str, BedrockResponse] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    parallel_execution_stats: Optional[ParallelExecutionStats] = None
    warnings: List[str] = field(default_factory=list)
    failed_requests: List[str] = field(default_factory=list)

    def get_successful_responses(self) -> Dict[str, BedrockResponse]:
        """
        Get only the successful responses.

        Returns:
            Dictionary of successful request_id -> BedrockResponse mappings
        """
        return {
            req_id: response
            for req_id, response in self.request_responses.items()
            if response.success
        }

    def get_failed_responses(self) -> Dict[str, BedrockResponse]:
        """
        Get only the failed responses.

        Returns:
            Dictionary of failed request_id -> BedrockResponse mappings
        """
        return {
            req_id: response
            for req_id, response in self.request_responses.items()
            if not response.success
        }

    def get_response_by_id(self, request_id: str) -> Optional[BedrockResponse]:
        """
        Get response for a specific request ID.

        Args:
            request_id: Request ID to look up

        Returns:
            BedrockResponse if found, None otherwise
        """
        return self.request_responses.get(request_id)

    def get_success_rate(self) -> float:
        """
        Calculate overall success rate.

        Returns:
            Success rate as percentage (0.0-100.0)
        """
        if not self.request_responses:
            return 0.0

        successful_count = len(self.get_successful_responses())
        return (successful_count / len(self.request_responses)) * 100.0

    def get_total_tokens_used(self) -> Dict[str, int]:
        """
        Calculate total token usage across all successful requests.

        Returns:
            Dictionary with total token usage statistics
        """
        total_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }

        for response in self.get_successful_responses().values():
            usage = response.get_usage()
            if usage:
                for key in total_usage:
                    total_usage[key] += usage.get(key, 0)

        return total_usage

    def get_average_latency(self) -> Optional[float]:
        """
        Calculate average API latency across all successful requests.

        Returns:
            Average latency in milliseconds, None if no successful requests
        """
        successful_responses = self.get_successful_responses()
        if not successful_responses:
            return None

        latencies = []
        for response in successful_responses.values():
            metrics = response.get_metrics()
            if metrics and "api_latency_ms" in metrics:
                latencies.append(metrics["api_latency_ms"])

        return sum(latencies) / len(latencies) if latencies else None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the parallel response
        """
        return {
            ParallelProcessingFields.SUCCESS: self.success,
            ParallelProcessingFields.REQUEST_RESPONSES: {
                req_id: response.to_dict() for req_id, response in self.request_responses.items()
            },
            ParallelProcessingFields.TOTAL_DURATION_MS: self.total_duration_ms,
            ParallelProcessingFields.PARALLEL_EXECUTION_STATS: (
                self.parallel_execution_stats.to_dict() if self.parallel_execution_stats else None
            ),
            ParallelProcessingFields.WARNINGS: self.warnings,
            ParallelProcessingFields.FAILED_REQUESTS: self.failed_requests,
        }

    def __repr__(self) -> str:
        """Return string representation of the ParallelResponse."""
        success_count = len(self.get_successful_responses())
        total_count = len(self.request_responses)
        return (
            f"ParallelResponse(success={self.success}, "
            f"responses={success_count}/{total_count}, "
            f"duration={self.total_duration_ms:.1f}ms)"
        )


@dataclass
class RegionAssignment:
    """
    Assignment of a request to specific regions for processing.

    Attributes:
        request_id: ID of the request being assigned
        assigned_regions: List of regions assigned to process this request
        priority: Priority level for the request (higher = more priority)
    """

    request_id: str
    assigned_regions: List[str]
    priority: int = 0

    def __repr__(self) -> str:
        """Return string representation of the RegionAssignment."""
        return (
            f"RegionAssignment(id={self.request_id}, "
            f"regions={self.assigned_regions}, priority={self.priority})"
        )


@dataclass
class ParallelExecutionContext:
    """
    Context information for parallel execution tracking.

    Attributes:
        start_time: When parallel execution started
        active_requests: Set of currently active request IDs
        completed_requests: Set of completed request IDs
        failed_requests: Set of failed request IDs
        region_load: Current load per region
        semaphore: Asyncio semaphore for concurrency control
    """

    start_time: datetime
    active_requests: Set[str] = field(default_factory=set)
    completed_requests: Set[str] = field(default_factory=set)
    failed_requests: Set[str] = field(default_factory=set)
    region_load: Dict[str, int] = field(default_factory=dict)
    semaphore: Optional[asyncio.Semaphore] = None

    def get_active_count(self) -> int:
        """Get count of currently active requests."""
        return len(self.active_requests)

    def get_completion_rate(self) -> float:
        """Get completion rate as percentage."""
        total = len(self.completed_requests) + len(self.failed_requests) + len(self.active_requests)
        if total == 0:
            return 0.0
        completed = len(self.completed_requests) + len(self.failed_requests)
        return (completed / total) * 100.0

    def get_elapsed_time_ms(self) -> float:
        """Get elapsed time since start in milliseconds."""
        return (datetime.now() - self.start_time).total_seconds() * 1000
