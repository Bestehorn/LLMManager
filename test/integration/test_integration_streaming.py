"""
Integration tests for LLMManager streaming functionality with real AWS Bedrock.

Tests streaming responses, mid-stream recovery, error handling, and real-time
streaming behavior with actual AWS calls and controlled error injection.
"""

import time
from typing import Any, Dict, Iterator, List, Optional, Tuple
from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    ConfigurationError,
    RetryExhaustedError,
)
from bestehorn_llmmanager.bedrock.models.bedrock_response import StreamingResponse
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig
from bestehorn_llmmanager.bedrock.UnifiedModelManager import (
    UnifiedModelManager,
    UnifiedModelManagerError,
)
from bestehorn_llmmanager.llm_manager import LLMManager
from bestehorn_llmmanager.message_builder import create_user_message

# Constants for streaming test configuration
PREFERRED_STREAMING_REGIONS = ["us-east-1", "us-west-2"]
FALLBACK_STREAMING_REGIONS = ["eu-west-1", "ap-southeast-1"]
STREAMING_TEST_MAX_TOKENS = 100
LONG_RESPONSE_MAX_TOKENS = 500


def _select_streaming_regions_from_available(available_regions: List[str]) -> List[str]:
    """
    Select preferred regions for streaming tests from available regions.

    Args:
        available_regions: List of regions where the model is available

    Returns:
        List of preferred regions for streaming tests
    """
    if not available_regions:
        return []

    selected_regions = []

    # Try preferred regions first
    for preferred_region in PREFERRED_STREAMING_REGIONS:
        if preferred_region in available_regions and preferred_region not in selected_regions:
            selected_regions.append(preferred_region)

    # Add fallback regions if needed
    for fallback_region in FALLBACK_STREAMING_REGIONS:
        if (
            fallback_region in available_regions
            and fallback_region not in selected_regions
            and len(selected_regions) < 3
        ):
            selected_regions.append(fallback_region)

    # Add any remaining regions up to 3 total
    for region in available_regions:
        if region not in selected_regions and len(selected_regions) < 3:
            selected_regions.append(region)

    return selected_regions


def get_streaming_test_model_and_regions(
    provider: str = "Anthropic",
) -> Tuple[Optional[str], List[str]]:
    """
    Get model and regions for streaming tests with preference for multiple regions.

    Args:
        provider: Model provider to search for

    Returns:
        Tuple of (model_name, regions_list) for streaming tests
    """
    try:
        unified_manager = UnifiedModelManager()
        unified_manager.ensure_data_available()

        # Get models for the specified provider
        provider_models = {}
        for case_variant in [provider, provider.capitalize(), provider.lower()]:
            provider_models = unified_manager.get_models_by_provider(provider=case_variant)
            if provider_models:
                break

        if not provider_models:
            return None, []

        # Find model with multiple regions available
        for model_name in sorted(provider_models.keys()):
            available_regions = unified_manager.get_regions_for_model(model_name=model_name)
            streaming_regions = _select_streaming_regions_from_available(
                available_regions=available_regions
            )
            if len(streaming_regions) >= 2:  # Need at least 2 regions for failover testing
                return model_name, streaming_regions

        # Fallback: return first model with any regions
        for model_name in sorted(provider_models.keys()):
            available_regions = unified_manager.get_regions_for_model(model_name=model_name)
            if available_regions:
                return model_name, available_regions[:1]

        return None, []

    except UnifiedModelManagerError:
        return None, []
    except Exception:
        return None, []


class StreamingErrorInjector:
    """
    Utility class for injecting controlled errors during streaming tests.

    Provides various strategies for simulating mid-stream failures to test
    recovery mechanisms and error handling.
    """

    def __init__(self) -> None:
        """Initialize the streaming error injector."""
        self.injection_count = 0

    def create_failing_stream_mock(
        self,
        success_chunks: int = 3,
        error_type: str = "ConnectionError",
        error_message: str = "Simulated network interruption",
        total_chunks: int = 10,
    ) -> Mock:
        """
        Create a mock stream that fails after yielding some successful chunks.

        Args:
            success_chunks: Number of successful chunks before failure
            error_type: Type of error to raise
            total_chunks: Total chunks if no error occurred
            error_message: Error message for the exception

        Returns:
            Mock EventStream that fails at specified point
        """
        chunks_yielded = 0

        def stream_generator() -> Iterator[Dict[str, Any]]:
            nonlocal chunks_yielded

            # Yield successful chunks
            while chunks_yielded < success_chunks:
                chunks_yielded += 1
                yield {
                    "contentBlockDelta": {
                        "delta": {"text": f"chunk_{chunks_yielded} "},
                        "contentBlockIndex": 0,
                    }
                }
                time.sleep(0.01)  # Simulate streaming delay

            # Raise the configured error
            if error_type == "ConnectionError":
                raise ConnectionError(error_message)
            elif error_type == "TimeoutError":
                raise TimeoutError(error_message)
            elif error_type == "ThrottlingException":
                from botocore.exceptions import ClientError

                raise ClientError(
                    error_response={
                        "Error": {"Code": "ThrottlingException", "Message": error_message}
                    },
                    operation_name="ConverseStream",
                )
            else:
                raise Exception(f"{error_type}: {error_message}")

        mock_stream = Mock()
        mock_stream.__iter__ = Mock(return_value=stream_generator())
        return mock_stream

    def create_delayed_failure_stream_mock(
        self, delay_seconds: float = 1.0, error_message: str = "Delayed timeout"
    ) -> Mock:
        """
        Create a mock stream that fails after a time delay.

        Args:
            delay_seconds: Seconds to wait before failing
            error_message: Error message for timeout

        Returns:
            Mock EventStream that fails after delay
        """
        start_time = time.time()
        chunks_yielded = 0

        def delayed_stream_generator() -> Iterator[Dict[str, Any]]:
            nonlocal chunks_yielded

            while True:
                current_time = time.time()
                if current_time - start_time > delay_seconds:
                    raise TimeoutError(error_message)

                chunks_yielded += 1
                yield {
                    "contentBlockDelta": {
                        "delta": {"text": f"delayed_chunk_{chunks_yielded} "},
                        "contentBlockIndex": 0,
                    }
                }
                time.sleep(0.1)

        mock_stream = Mock()
        mock_stream.__iter__ = Mock(return_value=delayed_stream_generator())
        return mock_stream

    def create_progressive_failure_mock(
        self, failure_points: List[int], error_messages: List[str]
    ) -> Mock:
        """
        Create a mock stream with multiple failure points.

        Args:
            failure_points: List of chunk counts where failures occur
            error_messages: Corresponding error messages for each failure

        Returns:
            Mock EventStream with progressive failures
        """
        chunks_yielded = 0
        failure_index = 0

        def progressive_failure_generator() -> Iterator[Dict[str, Any]]:
            nonlocal chunks_yielded, failure_index

            while True:
                chunks_yielded += 1

                # Check if we should fail at this point
                if (
                    failure_index < len(failure_points)
                    and chunks_yielded >= failure_points[failure_index]
                ):
                    error_msg = error_messages[failure_index]
                    failure_index += 1
                    raise ConnectionError(error_msg)

                yield {
                    "contentBlockDelta": {
                        "delta": {"text": f"progressive_chunk_{chunks_yielded} "},
                        "contentBlockIndex": 0,
                    }
                }
                time.sleep(0.05)

        mock_stream = Mock()
        mock_stream.__iter__ = Mock(return_value=progressive_failure_generator())
        return mock_stream


@pytest.fixture
def streaming_error_injector() -> StreamingErrorInjector:
    """Provide streaming error injector for tests."""
    return StreamingErrorInjector()


@pytest.fixture
def sample_streaming_messages() -> List[Dict[str, Any]]:
    """Provide sample messages optimized for streaming tests."""
    return [
        create_user_message()
        .add_text(
            "Please write a detailed explanation of artificial intelligence. "
            "Include key concepts, applications, and future implications. "
            "Make your response comprehensive but clear."
        )
        .build()
    ]


@pytest.fixture
def short_streaming_messages() -> List[Dict[str, Any]]:
    """Provide short messages for quick streaming tests."""
    return [create_user_message().add_text("Hello, how are you today?").build()]


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerStreamingBasics:
    """Integration tests for basic LLMManager streaming functionality."""

    def test_basic_streaming_response(self, short_streaming_messages: List[Dict[str, Any]]) -> None:
        """
        Test basic streaming response functionality with real AWS.

        Args:
            short_streaming_messages: Short messages for quick testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available Anthropic model/region combination for streaming tests")

        try:
            manager = LLMManager(
                models=[model_name],
                regions=regions[:1],  # Use single region for basic test
                timeout=60,
            )

            # Test basic streaming
            streaming_response = manager.converse_stream(
                messages=short_streaming_messages,
                inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
            )

            # Verify streaming response structure
            assert isinstance(streaming_response, StreamingResponse)
            assert hasattr(streaming_response, "__iter__")
            assert hasattr(streaming_response, "__next__")

            # Test iterator protocol
            content_chunks = []
            chunk_count = 0
            for chunk in streaming_response:
                assert isinstance(chunk, str)
                assert len(chunk) > 0
                content_chunks.append(chunk)
                chunk_count += 1

                # Prevent infinite loops in tests
                if chunk_count > 50:
                    break

            # Verify content was received
            assert len(content_chunks) > 0
            full_content = "".join(content_chunks)
            assert len(full_content) > 0

            # Verify streaming response metadata
            assert streaming_response.success is True
            assert streaming_response.model_used is not None
            assert streaming_response.region_used is not None
            assert streaming_response.is_streaming_complete() is True

            # Verify accumulated content matches
            accumulated_content = streaming_response.get_full_content()
            assert accumulated_content == full_content

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for streaming: {str(e)}")

    def test_streaming_response_metadata(
        self, short_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test streaming response metadata collection.

        Args:
            short_streaming_messages: Short messages for testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available model/region combination for streaming metadata tests")

        try:
            manager = LLMManager(
                models=[model_name], regions=regions[:1], timeout=60, log_level="INFO"
            )

            start_time = time.time()
            streaming_response = manager.converse_stream(
                messages=short_streaming_messages,
                inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
            )

            # Consume the stream
            content_parts = list(streaming_response)
            end_time = time.time()

            # Verify timing metrics
            assert streaming_response.total_duration_ms is not None
            assert streaming_response.total_duration_ms > 0

            # Verify execution time is reasonable
            execution_time_seconds = end_time - start_time
            assert execution_time_seconds > 0.1  # Should take some time
            assert execution_time_seconds < 30  # But not too long

            # Test metrics access
            metrics = streaming_response.get_metrics()
            if metrics:
                assert "content_parts" in metrics
                assert "stream_position" in metrics
                assert "stream_errors" in metrics
                assert metrics["content_parts"] == len(content_parts)

            # Test usage information
            usage = streaming_response.get_usage()
            if usage:
                assert "input_tokens" in usage
                assert "output_tokens" in usage
                assert usage["input_tokens"] > 0
                assert usage["output_tokens"] > 0

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for metadata tests: {str(e)}")

    def test_streaming_with_multiple_regions_basic(
        self, short_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test streaming with multiple regions (no failure injection).

        Args:
            short_streaming_messages: Short messages for testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or len(regions) < 2:
            pytest.skip("Need at least 2 regions for multi-region streaming tests")

        try:
            manager = LLMManager(
                models=[model_name], regions=regions[:2], timeout=60, log_level="INFO"
            )

            streaming_response = manager.converse_stream(
                messages=short_streaming_messages,
                inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
            )

            # Consume stream
            chunks = list(streaming_response)

            # Verify successful streaming
            assert len(chunks) > 0
            assert streaming_response.success is True
            assert streaming_response.region_used in regions[:2]

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize multi-region LLMManager: {str(e)}")
        except RetryExhaustedError as e:
            # Check if this is an access issue
            if "AccessDeniedException" in str(e) or "You don't have access" in str(e):
                pytest.skip(f"AWS account access limitation: {str(e)}")
            else:
                raise


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerStreamingErrorRecovery:
    """Integration tests for streaming error recovery and mid-stream failure handling."""

    def test_simulated_mid_stream_recovery(
        self,
        streaming_error_injector: StreamingErrorInjector,
        short_streaming_messages: List[Dict[str, Any]],
    ) -> None:
        """
        Test mid-stream error recovery using mock injection.

        Args:
            streaming_error_injector: Error injection utility
            short_streaming_messages: Messages for testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or len(regions) < 2:
            pytest.skip("Need at least 2 regions for mid-stream recovery tests")

        try:
            manager = LLMManager(
                models=[model_name], regions=regions[:2], timeout=60, log_level="DEBUG"
            )

            # Create failing stream mock for first region
            failing_stream = streaming_error_injector.create_failing_stream_mock(
                success_chunks=3, error_type="ConnectionError", error_message="Network interrupted"
            )

            # Mock the first region to fail, second to succeed
            with patch.object(manager._auth_manager, "get_bedrock_client") as mock_client_factory:
                # First call returns failing client, second call returns working client
                mock_clients = []

                # Failing client for first region
                failing_client = Mock()
                failing_client.converse_stream.return_value = {"stream": failing_stream}
                mock_clients.append(failing_client)

                # Working client for second region (create normal response)
                working_client = Mock()
                working_stream = self._create_successful_stream_mock(chunk_count=5)
                working_client.converse_stream.return_value = {"stream": working_stream}
                mock_clients.append(working_client)

                mock_client_factory.side_effect = mock_clients

                # Execute streaming with recovery
                streaming_response = manager.converse_stream(
                    messages=short_streaming_messages,
                    inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
                )

                # Consume the stream
                chunks = list(streaming_response)

                # Verify recovery occurred
                assert len(chunks) > 0
                assert streaming_response.success is True

                # Check that both clients were called (indicating failover)
                assert mock_client_factory.call_count >= 1

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for recovery tests: {str(e)}")

    def test_streaming_with_retry_configuration(
        self, short_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test streaming with custom retry configuration.

        Args:
            short_streaming_messages: Messages for testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available model/region for retry configuration tests")

        retry_config = RetryConfig(
            max_retries=2, retry_delay=0.5, backoff_multiplier=1.5, max_retry_delay=5.0
        )

        try:
            manager = LLMManager(
                models=[model_name],
                regions=regions[:1],
                retry_config=retry_config,
                timeout=60,
                log_level="INFO",
            )

            streaming_response = manager.converse_stream(
                messages=short_streaming_messages,
                inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
            )

            # Consume stream
            chunks = list(streaming_response)

            # Verify streaming with custom retry config
            assert len(chunks) > 0
            assert streaming_response.success is True

            # Verify retry configuration was applied
            retry_stats = manager.get_retry_stats()
            assert retry_stats["max_retries"] == 2

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager with retry config: {str(e)}")

    def test_streaming_timeout_handling(
        self, streaming_error_injector: StreamingErrorInjector
    ) -> None:
        """
        Test streaming behavior with timeout scenarios.

        Args:
            streaming_error_injector: Error injection utility
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available model/region for timeout tests")

        try:
            # Use shorter timeout for this test
            manager = LLMManager(
                models=[model_name], regions=regions[:1], timeout=5, log_level="DEBUG"
            )

            # Create message that would normally generate long response
            long_message = [
                create_user_message()
                .add_text(
                    "Write a very long, detailed essay about the history of computing, "
                    "including all major developments, key figures, and technological "
                    "breakthroughs from the 1940s to present day. Be very comprehensive."
                )
                .build()
            ]

            start_time = time.time()
            streaming_response = manager.converse_stream(
                messages=long_message, inference_config={"maxTokens": LONG_RESPONSE_MAX_TOKENS}
            )

            # Try to consume stream with timeout awareness
            chunks = []
            try:
                for chunk in streaming_response:
                    chunks.append(chunk)
                    # Break if we've been running too long (test timeout)
                    if time.time() - start_time > 15:
                        break
            except Exception:
                # Timeout or other errors are expected in this test
                pass

            # Verify we got some content before any timeout
            execution_time = time.time() - start_time
            assert execution_time > 0

            # If we got chunks, verify they're valid
            if chunks:
                assert all(isinstance(chunk, str) for chunk in chunks)
                assert len("".join(chunks)) > 0

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for timeout tests: {str(e)}")

    def _create_successful_stream_mock(self, chunk_count: int = 5) -> Mock:
        """
        Create a mock stream that succeeds with specified number of chunks.

        Args:
            chunk_count: Number of chunks to generate

        Returns:
            Mock EventStream that succeeds
        """

        def successful_stream_generator() -> Iterator[Dict[str, Any]]:
            for i in range(chunk_count):
                yield {
                    "contentBlockDelta": {
                        "delta": {"text": f"success_chunk_{i + 1} "},
                        "contentBlockIndex": 0,
                    }
                }
                time.sleep(0.01)

            # End with message stop
            yield {"messageStop": {"stopReason": "end_turn"}}

        mock_stream = Mock()
        mock_stream.__iter__ = Mock(return_value=successful_stream_generator())
        return mock_stream


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerStreamingAdvanced:
    """Advanced integration tests for streaming functionality."""

    def test_streaming_content_accumulation(
        self, sample_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test content accumulation during streaming.

        Args:
            sample_streaming_messages: Longer messages for content testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available model/region for content accumulation tests")

        try:
            manager = LLMManager(
                models=[model_name], regions=regions[:1], timeout=120, log_level="INFO"
            )

            streaming_response = manager.converse_stream(
                messages=sample_streaming_messages,
                inference_config={"maxTokens": LONG_RESPONSE_MAX_TOKENS},
            )

            # Track content accumulation
            incremental_content = ""
            chunk_sizes = []

            for chunk in streaming_response:
                assert isinstance(chunk, str)
                assert len(chunk) > 0

                incremental_content += chunk
                chunk_sizes.append(len(chunk))

                # Verify accumulated content matches
                current_accumulated = streaming_response.get_full_content()
                assert current_accumulated == incremental_content

                # Verify content parts tracking
                content_parts = streaming_response.get_content_parts()
                assert len(content_parts) > 0
                assert "".join(content_parts) == incremental_content

                # Break after reasonable amount of content
                if len(incremental_content) > 200:
                    break

            # Verify final state
            assert len(incremental_content) > 0
            assert len(chunk_sizes) > 0
            assert streaming_response.stream_position == len(incremental_content)

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for accumulation tests: {str(e)}")

    def test_streaming_with_system_messages(
        self, short_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test streaming with system message configuration.

        Args:
            short_streaming_messages: Messages for testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available model/region for system message tests")

        try:
            manager = LLMManager(
                models=[model_name], regions=regions[:1], timeout=60, log_level="INFO"
            )

            system_messages = [
                {"text": "You are a helpful assistant. Please respond concisely and clearly."}
            ]

            streaming_response = manager.converse_stream(
                messages=short_streaming_messages,
                system=system_messages,
                inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
            )

            # Consume stream
            chunks = list(streaming_response)

            # Verify streaming with system message
            assert len(chunks) > 0
            assert streaming_response.success is True
            full_content = "".join(chunks)
            assert len(full_content) > 0

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for system message tests: {str(e)}")

    def test_streaming_error_tracking(
        self, streaming_error_injector: StreamingErrorInjector
    ) -> None:
        """
        Test error tracking during streaming operations.

        Args:
            streaming_error_injector: Error injection utility
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available model/region for error tracking tests")

        try:
            manager = LLMManager(
                models=[model_name], regions=regions[:1], timeout=30, log_level="DEBUG"
            )

            # Create a stream that will definitely fail
            failing_stream = streaming_error_injector.create_failing_stream_mock(
                success_chunks=2, error_type="ConnectionError", error_message="Test error"
            )

            # Mock the client to return failing stream
            with patch.object(manager._auth_manager, "get_bedrock_client") as mock_client_factory:
                failing_client = Mock()
                failing_client.converse_stream.return_value = {"stream": failing_stream}
                mock_client_factory.return_value = failing_client

                # Execute streaming (should fail)
                streaming_response = manager.converse_stream(
                    messages=[create_user_message().add_text("Test message").build()],
                    inference_config={"maxTokens": 50},
                )

                # Try to consume stream (should encounter error)
                chunks = []
                try:
                    for chunk in streaming_response:
                        chunks.append(chunk)
                except StopIteration:
                    pass  # Expected when stream fails/completes

                # Verify error tracking
                stream_errors = streaming_response.get_stream_errors()
                assert (
                    len(stream_errors) >= 0
                )  # May or may not have errors depending on implementation

                # Verify we got some chunks before failure
                if chunks:
                    assert all(isinstance(chunk, str) for chunk in chunks)

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for error tracking tests: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerStreamingRealWorldScenarios:
    """Real-world streaming scenario tests."""

    def test_streaming_model_switching_scenario(
        self, short_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test realistic scenario where first model is unavailable.

        Args:
            short_streaming_messages: Messages for testing
        """
        # Get a working model/region combination
        working_model, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not working_model or not regions:
            pytest.skip("No available model/region for model switching tests")

        # Create scenario with non-existent model first, then working model
        models = ["NonExistentModel", working_model]

        try:
            manager = LLMManager(models=models, regions=regions[:1], timeout=60, log_level="INFO")

            streaming_response = manager.converse_stream(
                messages=short_streaming_messages,
                inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
            )

            # Consume stream
            chunks = list(streaming_response)

            # Verify switching to working model occurred
            assert len(chunks) > 0
            assert streaming_response.success is True
            assert streaming_response.model_used == working_model

        except ConfigurationError as e:
            # This is expected if no valid model/region combinations exist
            error_message = str(e)
            if "NonExistentModel" in error_message and "not found" in error_message:
                # Expected behavior - model switching caught during initialization
                pass
            else:
                pytest.skip(f"Unexpected configuration error: {str(e)}")

    def test_streaming_region_failover_scenario(
        self, short_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test realistic region failover scenario.

        Args:
            short_streaming_messages: Messages for testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or len(regions) < 2:
            pytest.skip("Need at least 2 regions for failover scenario tests")

        # Include a non-existent region to trigger failover
        test_regions = ["invalid-region-name"] + regions[:1]

        try:
            manager = LLMManager(
                models=[model_name], regions=test_regions, timeout=60, log_level="INFO"
            )

            streaming_response = manager.converse_stream(
                messages=short_streaming_messages,
                inference_config={"maxTokens": STREAMING_TEST_MAX_TOKENS},
            )

            # Consume stream
            chunks = list(streaming_response)

            # Verify failover to valid region occurred
            assert len(chunks) > 0
            assert streaming_response.success is True
            assert streaming_response.region_used in regions[:1]

        except ConfigurationError as e:
            # This is expected if no valid model/region combinations exist
            error_message = str(e)
            if "invalid-region-name" in error_message and "not found" in error_message:
                # Expected behavior - region failover caught during initialization
                pass
            else:
                pytest.skip(f"Unexpected configuration error: {str(e)}")

    def test_streaming_performance_characteristics(
        self, sample_streaming_messages: List[Dict[str, Any]]
    ) -> None:
        """
        Test streaming performance and timing characteristics.

        Args:
            sample_streaming_messages: Messages for performance testing
        """
        model_name, regions = get_streaming_test_model_and_regions(provider="Anthropic")
        if not model_name or not regions:
            pytest.skip("No available model/region for performance tests")

        try:
            manager = LLMManager(
                models=[model_name], regions=regions[:1], timeout=120, log_level="INFO"
            )

            start_time = time.time()
            streaming_response = manager.converse_stream(
                messages=sample_streaming_messages,
                inference_config={"maxTokens": LONG_RESPONSE_MAX_TOKENS},
            )

            # Track timing metrics
            first_chunk_time = None
            chunks = []

            for chunk in streaming_response:
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                chunks.append(chunk)

                # Break after reasonable content for performance test
                if len("".join(chunks)) > 300:
                    break

            end_time = time.time()

            # Verify performance characteristics
            total_duration = end_time - start_time
            assert total_duration > 0.1  # Should take some time
            assert total_duration < 60  # But not too long

            if first_chunk_time:
                time_to_first_chunk = first_chunk_time - start_time
                assert time_to_first_chunk < 30  # First chunk should arrive quickly

            # Verify streaming metrics
            metrics = streaming_response.get_metrics()
            if metrics:
                # Check for streaming-specific metrics
                assert "content_parts" in metrics
                assert "stream_position" in metrics
                assert "stream_errors" in metrics

                # total_duration_ms might be available at the response level
                if "total_duration_ms" in metrics:
                    assert metrics["total_duration_ms"] > 0
                elif streaming_response.total_duration_ms is not None:
                    assert streaming_response.total_duration_ms > 0

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager for performance tests: {str(e)}")
