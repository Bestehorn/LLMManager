"""
Tests for parallel processing data structures.
"""

import json
import time

import pytest

from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse
from bestehorn_llmmanager.bedrock.models.parallel_structures import (
    BedrockConverseRequest,
    FailureHandlingStrategy,
    LoadBalancingStrategy,
    ParallelExecutionContext,
    ParallelExecutionStats,
    ParallelProcessingConfig,
    ParallelResponse,
    RegionAssignment,
)


class TestBedrockConverseRequest:
    """Test cases for BedrockConverseRequest."""

    def test_initialization_with_auto_generated_id(self) -> None:
        """Test request creation with auto-generated ID."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages)

        assert request.messages == messages
        assert request.request_id is not None
        assert request.request_id.startswith("req_")
        assert len(request.request_id.split("_")) == 3  # req_hash_timestamp

    def test_initialization_with_provided_id(self) -> None:
        """Test request creation with provided ID."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        custom_id = "custom_request_123"

        request = BedrockConverseRequest(messages=messages, request_id=custom_id)

        assert request.request_id == custom_id

    def test_initialization_with_all_parameters(self) -> None:
        """Test request creation with all parameters."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        system = [{"text": "You are a helpful assistant"}]
        inference_config = {"maxTokens": 100, "temperature": 0.7}

        request = BedrockConverseRequest(
            messages=messages,
            system=system,
            inference_config=inference_config,
            request_id="test_123",
        )

        assert request.messages == messages
        assert request.system == system
        assert request.inference_config == inference_config
        assert request.request_id == "test_123"

    def test_to_converse_args(self) -> None:
        """Test conversion to converse API arguments."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        system = [{"text": "You are helpful"}]
        inference_config = {"maxTokens": 100}

        request = BedrockConverseRequest(
            messages=messages, system=system, inference_config=inference_config
        )

        args = request.to_converse_args()

        assert args["messages"] == messages
        assert args["system"] == system
        assert args["inference_config"] == inference_config  # Fixed: now snake_case
        assert "request_id" not in args  # Should not be in converse args

    def test_to_converse_args_with_optional_fields(self) -> None:
        """Test conversion with only required fields."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages)

        args = request.to_converse_args()

        assert args["messages"] == messages
        assert len(args) == 1  # Only messages should be present

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages, request_id="test_123")

        result_dict = request.to_dict()

        assert result_dict["request_id"] == "test_123"
        assert result_dict["messages"] == messages
        assert result_dict["system"] is None

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "request_id": "test_123",
            "messages": [{"role": "user", "content": [{"text": "Hello"}]}],
            "system": [{"text": "You are helpful"}],
            "inference_config": {"maxTokens": 100},
        }

        request = BedrockConverseRequest.from_dict(data)

        assert request.request_id == "test_123"
        assert request.messages == data["messages"]
        assert request.system == data["system"]
        assert request.inference_config == data["inference_config"]

    def test_unique_id_generation(self) -> None:
        """Test that multiple requests generate unique IDs."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]

        request1 = BedrockConverseRequest(messages=messages)
        time.sleep(0.001)  # Small delay to ensure different timestamps
        request2 = BedrockConverseRequest(messages=messages)

        assert request1.request_id != request2.request_id

    def test_repr(self) -> None:
        """Test string representation."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages, request_id="test_123")

        repr_str = repr(request)

        assert "BedrockConverseRequest" in repr_str
        assert "test_123" in repr_str
        assert "messages=1" in repr_str

    def test_image_content_serialization(self) -> None:
        """Test that requests with image bytes content can be processed without JSON serialization errors."""
        # Create a message with image content (similar to MessageBuilder output)
        test_image_bytes = b"fake_image_data_for_testing_purposes"

        message_with_image = {
            "role": "user",
            "content": [
                {"text": "Analyze this image"},
                {
                    "image": {
                        "format": "jpeg",
                        "source": {
                            "bytes": test_image_bytes  # This would cause JSON serialization error
                        },
                    }
                },
            ],
        }

        # This should not raise a JSON serialization error during request ID generation
        request = BedrockConverseRequest(
            messages=[message_with_image], inference_config={"maxTokens": 800, "temperature": 0.3}
        )

        # Verify request was created successfully
        assert request.request_id is not None
        assert request.request_id.startswith("req_")
        assert len(request.messages) == 1

        # Verify original bytes are preserved in the message structure
        image_block = None
        for content_block in message_with_image["content"]:
            if isinstance(content_block, dict) and "image" in content_block:
                image_block = content_block
                break

        assert image_block is not None
        assert isinstance(image_block, dict)
        assert image_block["image"]["source"]["bytes"] == test_image_bytes

        # Verify to_converse_args() works with the image content
        converse_args = request.to_converse_args()
        assert "messages" in converse_args
        assert len(converse_args["messages"]) == 1

    def test_sanitize_content_for_hashing(self) -> None:
        """Test the content sanitization method for different data types."""
        messages = [{"role": "user", "content": [{"text": "test"}]}]
        request = BedrockConverseRequest(messages=messages)

        # Test various content types
        from typing import Any, Dict, List, Tuple, Union

        test_cases: List[
            Tuple[str, Union[str, bytes, int, bool, None, Dict[str, Any], List[Any]]]
        ] = [
            # Simple types
            ("text", "hello world"),
            ("bytes", b"binary data"),
            ("number", 42),
            ("boolean", True),
            ("none", None),
            # Complex structures with bytes
            ("dict_with_bytes", {"text": "hello", "image": {"bytes": b"image_data"}}),
            ("list_with_bytes", ["text", b"bytes", {"nested": b"more_bytes"}]),
            # Nested structure similar to actual message content
            (
                "message_structure",
                {
                    "role": "user",
                    "content": [
                        {"text": "analyze this"},
                        {"image": {"source": {"bytes": b"fake_image_data"}}},
                    ],
                },
            ),
        ]

        for test_name, test_content in test_cases:
            # Sanitize the content
            sanitized = request._sanitize_content_for_hashing(test_content)

            # Should be able to JSON serialize the result
            try:
                json.dumps(sanitized)
            except TypeError as e:
                pytest.fail(
                    f"Failed to JSON serialize sanitized content for test '{test_name}': {e}"
                )

            # Verify bytes objects are replaced with hash strings
            if isinstance(test_content, bytes):
                assert isinstance(sanitized, str)
                assert sanitized.startswith("<bytes_hash:")
                assert sanitized.endswith(">")
            elif test_name in ["dict_with_bytes", "message_structure"]:
                # For specific dict test cases with bytes values, check that bytes are replaced
                from typing import Any, Dict, List, Union

                def check_no_bytes(obj: Union[bytes, Dict[str, Any], List[Any], Any]) -> bool:
                    if isinstance(obj, bytes):
                        return False
                    elif isinstance(obj, dict):
                        return all(check_no_bytes(v) for v in obj.values())
                    elif isinstance(obj, list):
                        return all(check_no_bytes(item) for item in obj)
                    return True

                assert check_no_bytes(
                    sanitized
                ), f"Sanitized content still contains bytes objects for test '{test_name}'"


class TestParallelProcessingConfig:
    """Test cases for ParallelProcessingConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ParallelProcessingConfig()

        assert config.max_concurrent_requests == 5
        assert config.request_timeout_seconds == 300
        assert config.enable_request_prioritization is True
        assert config.failure_handling_strategy == FailureHandlingStrategy.CONTINUE_ON_FAILURE
        assert config.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN
        assert config.failure_threshold == 0.5

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ParallelProcessingConfig(
            max_concurrent_requests=10,
            request_timeout_seconds=120,
            enable_request_prioritization=False,
            failure_handling_strategy=FailureHandlingStrategy.STOP_ON_THRESHOLD,
            load_balancing_strategy=LoadBalancingStrategy.RANDOM,
            failure_threshold=0.3,
        )

        assert config.max_concurrent_requests == 10
        assert config.request_timeout_seconds == 120
        assert config.enable_request_prioritization is False
        assert config.failure_handling_strategy == FailureHandlingStrategy.STOP_ON_THRESHOLD
        assert config.load_balancing_strategy == LoadBalancingStrategy.RANDOM
        assert config.failure_threshold == 0.3

    def test_invalid_max_concurrent_requests(self) -> None:
        """Test validation of max_concurrent_requests."""
        with pytest.raises(ValueError) as exc_info:
            ParallelProcessingConfig(max_concurrent_requests=0)

        assert "max_concurrent_requests must be positive" in str(exc_info.value)

    def test_invalid_request_timeout(self) -> None:
        """Test validation of request_timeout_seconds."""
        with pytest.raises(ValueError) as exc_info:
            ParallelProcessingConfig(request_timeout_seconds=-1)

        assert "request_timeout_seconds must be positive" in str(exc_info.value)

    def test_invalid_failure_threshold(self) -> None:
        """Test validation of failure_threshold."""
        with pytest.raises(ValueError) as exc_info:
            ParallelProcessingConfig(failure_threshold=1.5)

        assert "failure_threshold must be between 0.0 and 1.0" in str(exc_info.value)


class TestParallelExecutionStats:
    """Test cases for ParallelExecutionStats."""

    def test_initialization(self) -> None:
        """Test stats initialization."""
        stats = ParallelExecutionStats(
            total_requests=10,
            successful_requests=8,
            failed_requests_count=2,
            average_request_duration_ms=150.5,
            max_request_duration_ms=300.0,
            min_request_duration_ms=50.0,
            concurrent_executions=5,
        )

        assert stats.total_requests == 10
        assert stats.successful_requests == 8
        assert stats.failed_requests_count == 2
        assert stats.average_request_duration_ms == 150.5
        assert stats.max_request_duration_ms == 300.0
        assert stats.min_request_duration_ms == 50.0
        assert stats.concurrent_executions == 5

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        stats = ParallelExecutionStats(
            total_requests=10,
            successful_requests=8,
            failed_requests_count=2,
            average_request_duration_ms=100.0,
            max_request_duration_ms=200.0,
            min_request_duration_ms=50.0,
            concurrent_executions=5,
        )

        assert stats.success_rate == 80.0
        assert stats.failure_rate == 20.0

    def test_success_rate_zero_requests(self) -> None:
        """Test success rate with zero requests."""
        stats = ParallelExecutionStats(
            total_requests=0,
            successful_requests=0,
            failed_requests_count=0,
            average_request_duration_ms=0.0,
            max_request_duration_ms=0.0,
            min_request_duration_ms=0.0,
            concurrent_executions=0,
        )

        assert stats.success_rate == 0.0
        assert stats.failure_rate == 100.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        region_dist = {"us-east-1": 5, "us-west-2": 3}
        stats = ParallelExecutionStats(
            total_requests=8,
            successful_requests=6,
            failed_requests_count=2,
            average_request_duration_ms=120.0,
            max_request_duration_ms=250.0,
            min_request_duration_ms=75.0,
            concurrent_executions=4,
            region_distribution=region_dist,
        )

        result_dict = stats.to_dict()

        assert result_dict["total_requests"] == 8
        assert result_dict["successful_requests"] == 6
        assert result_dict["failed_requests_count"] == 2
        assert result_dict["region_distribution"] == region_dist


class TestParallelResponse:
    """Test cases for ParallelResponse."""

    def test_initialization(self) -> None:
        """Test parallel response initialization."""
        responses = {"req1": BedrockResponse(success=True), "req2": BedrockResponse(success=False)}

        parallel_response = ParallelResponse(
            success=True, request_responses=responses, total_duration_ms=1500.0
        )

        assert parallel_response.success is True
        assert len(parallel_response.request_responses) == 2
        assert parallel_response.total_duration_ms == 1500.0

    def test_get_successful_responses(self) -> None:
        """Test getting only successful responses."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False),
            "req3": BedrockResponse(success=True),
        }

        parallel_response = ParallelResponse(success=True, request_responses=responses)

        successful = parallel_response.get_successful_responses()

        assert len(successful) == 2
        assert "req1" in successful
        assert "req3" in successful
        assert "req2" not in successful

    def test_get_failed_responses(self) -> None:
        """Test getting only failed responses."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False),
            "req3": BedrockResponse(success=True),
        }

        parallel_response = ParallelResponse(success=True, request_responses=responses)

        failed = parallel_response.get_failed_responses()

        assert len(failed) == 1
        assert "req2" in failed
        assert "req1" not in failed
        assert "req3" not in failed

    def test_get_response_by_id(self) -> None:
        """Test getting response by ID."""
        response1 = BedrockResponse(success=True)
        responses = {"req1": response1}

        parallel_response = ParallelResponse(success=True, request_responses=responses)

        assert parallel_response.get_response_by_id("req1") == response1
        assert parallel_response.get_response_by_id("nonexistent") is None

    def test_get_success_rate(self) -> None:
        """Test success rate calculation."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False),
            "req3": BedrockResponse(success=True),
            "req4": BedrockResponse(success=True),
        }

        parallel_response = ParallelResponse(success=True, request_responses=responses)

        assert parallel_response.get_success_rate() == 75.0

    def test_get_success_rate_empty(self) -> None:
        """Test success rate with no responses."""
        parallel_response = ParallelResponse(success=False)

        assert parallel_response.get_success_rate() == 0.0

    def test_repr(self) -> None:
        """Test string representation."""
        responses = {"req1": BedrockResponse(success=True), "req2": BedrockResponse(success=False)}

        parallel_response = ParallelResponse(
            success=True, request_responses=responses, total_duration_ms=1234.5
        )

        repr_str = repr(parallel_response)

        assert "ParallelResponse" in repr_str
        assert "success=True" in repr_str
        assert "responses=1/2" in repr_str  # 1 successful out of 2 total
        assert "1234.5ms" in repr_str


class TestRegionAssignment:
    """Test cases for RegionAssignment."""

    def test_initialization(self) -> None:
        """Test region assignment initialization."""
        assignment = RegionAssignment(
            request_id="req_123", assigned_regions=["us-east-1", "us-west-2"], priority=5
        )

        assert assignment.request_id == "req_123"
        assert assignment.assigned_regions == ["us-east-1", "us-west-2"]
        assert assignment.priority == 5

    def test_default_priority(self) -> None:
        """Test default priority value."""
        assignment = RegionAssignment(request_id="req_123", assigned_regions=["us-east-1"])

        assert assignment.priority == 0

    def test_repr(self) -> None:
        """Test string representation."""
        assignment = RegionAssignment(
            request_id="req_123", assigned_regions=["us-east-1", "us-west-2"], priority=3
        )

        repr_str = repr(assignment)

        assert "RegionAssignment" in repr_str
        assert "req_123" in repr_str
        assert "us-east-1" in repr_str
        assert "priority=3" in repr_str


class TestParallelExecutionContext:
    """Test cases for ParallelExecutionContext."""

    def test_initialization(self) -> None:
        """Test execution context initialization."""
        from datetime import datetime

        start_time = datetime.now()

        context = ParallelExecutionContext(start_time=start_time)

        assert context.start_time == start_time
        assert len(context.active_requests) == 0
        assert len(context.completed_requests) == 0
        assert len(context.failed_requests) == 0
        assert len(context.region_load) == 0

    def test_get_active_count(self) -> None:
        """Test active request count."""
        from datetime import datetime

        context = ParallelExecutionContext(start_time=datetime.now())

        context.active_requests.add("req1")
        context.active_requests.add("req2")

        assert context.get_active_count() == 2

    def test_get_completion_rate(self) -> None:
        """Test completion rate calculation."""
        from datetime import datetime

        context = ParallelExecutionContext(start_time=datetime.now())

        context.active_requests.add("req1")
        context.completed_requests.add("req2")
        context.failed_requests.add("req3")

        # 2 completed (completed + failed) out of 3 total
        assert context.get_completion_rate() == (2 / 3) * 100

    def test_get_completion_rate_empty(self) -> None:
        """Test completion rate with no requests."""
        from datetime import datetime

        context = ParallelExecutionContext(start_time=datetime.now())

        assert context.get_completion_rate() == 0.0

    def test_get_elapsed_time_ms(self) -> None:
        """Test elapsed time calculation."""
        from datetime import datetime

        start_time = datetime.now()

        # Use a real time difference by sleeping briefly
        import time

        time.sleep(0.01)  # Sleep for 10ms to ensure elapsed time

        # No need to mock datetime - use real elapsed time
        context = ParallelExecutionContext(start_time=start_time)
        elapsed = context.get_elapsed_time_ms()

        # Should be approximately 10ms (0.01 seconds)
        assert elapsed >= 5.0  # Should be at least 5ms due to our sleep
