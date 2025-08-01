"""
Tests for BedrockResponse and StreamingResponse classes.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.models.bedrock_response import (
    BedrockResponse,
    StreamingResponse,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RequestAttempt,
    ValidationAttempt,
    ValidationResult,
)


class TestBedrockResponse:
    """Test BedrockResponse functionality."""

    def test_init_successful_response(self):
        """Test basic successful response initialization."""
        response = BedrockResponse(success=True)
        assert response.success is True
        assert response.response_data is None
        assert response.model_used is None
        assert response.region_used is None
        assert response.attempts == []
        assert response.warnings == []
        assert response.features_disabled == []

    def test_init_failed_response(self):
        """Test basic failed response initialization."""
        response = BedrockResponse(success=False)
        assert response.success is False
        assert response.was_successful() is False

    def test_get_content_successful(self):
        """Test get_content with successful response."""
        response_data = {"output": {"message": {"content": [{"text": "Hello"}, {"text": "World"}]}}}
        response = BedrockResponse(success=True, response_data=response_data)
        content = response.get_content()
        assert content == "Hello\nWorld"

    def test_get_content_no_response_data(self):
        """Test get_content with no response data."""
        response = BedrockResponse(success=True, response_data=None)
        assert response.get_content() is None

    def test_get_content_failed_response(self):
        """Test get_content with failed response."""
        response = BedrockResponse(success=False, response_data={"some": "data"})
        assert response.get_content() is None

    def test_get_content_malformed_data(self):
        """Test get_content with malformed response data."""
        # Missing content blocks
        response_data = {"output": {"message": {}}}
        response = BedrockResponse(success=True, response_data=response_data)
        assert response.get_content() is None

        # Invalid structure
        response_data = {"output": None}
        response = BedrockResponse(success=True, response_data=response_data)
        assert response.get_content() is None

        # Non-dict content blocks
        response_data = {"output": {"message": {"content": ["not_a_dict", {"text": "valid"}]}}}
        response = BedrockResponse(success=True, response_data=response_data)
        assert response.get_content() == "valid"

    def test_get_content_exception_handling(self):
        """Test get_content exception handling."""
        # Test with response data that will cause KeyError/TypeError/AttributeError
        response_data = {"malformed": True}
        response = BedrockResponse(success=True, response_data=response_data)
        assert response.get_content() is None

    def test_get_usage_successful(self):
        """Test get_usage with successful response."""
        response_data = {
            "usage": {
                "inputTokens": 100,
                "outputTokens": 50,
                "totalTokens": 150,
                "cacheReadInputTokens": 10,
                "cacheWriteInputTokens": 5,
            }
        }
        response = BedrockResponse(success=True, response_data=response_data)
        usage = response.get_usage()

        expected = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cache_read_tokens": 10,
            "cache_write_tokens": 5,
        }
        assert usage == expected

    def test_get_usage_no_data(self):
        """Test get_usage with no response data."""
        response = BedrockResponse(success=True, response_data=None)
        assert response.get_usage() is None

        response = BedrockResponse(success=False, response_data={"usage": {}})
        assert response.get_usage() is None

    def test_get_usage_partial_data(self):
        """Test get_usage with partial data."""
        response_data = {"usage": {"inputTokens": 100}}
        response = BedrockResponse(success=True, response_data=response_data)
        usage = response.get_usage()

        expected = {
            "input_tokens": 100,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        assert usage == expected

    def test_get_usage_exception_handling(self):
        """Test get_usage exception handling."""
        response_data = {"usage": None}
        response = BedrockResponse(success=True, response_data=response_data)
        assert response.get_usage() is None

    def test_get_metrics_successful(self):
        """Test get_metrics with successful response."""
        attempt = RequestAttempt(
            model_id="claude-3",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=True,
        )

        response_data = {"metrics": {"latencyMs": 1500}}
        response = BedrockResponse(
            success=True, response_data=response_data, total_duration_ms=2000.0, attempts=[attempt]
        )

        metrics = response.get_metrics()
        assert metrics is not None
        assert metrics["api_latency_ms"] == 1500
        assert metrics["total_duration_ms"] == 2000.0
        assert metrics["attempts_made"] == 1
        assert metrics["successful_attempt_number"] == 1

    def test_get_metrics_no_data(self):
        """Test get_metrics with no data."""
        response = BedrockResponse(success=True, response_data=None)
        assert response.get_metrics() is None

        response = BedrockResponse(success=False, response_data={})
        assert response.get_metrics() is None

    def test_get_metrics_exception_handling(self):
        """Test get_metrics exception handling."""
        response_data = {"metrics": None}
        response = BedrockResponse(success=True, response_data=response_data)
        metrics = response.get_metrics()
        assert metrics is not None
        assert metrics["attempts_made"] == 0

    def test_get_stop_reason_successful(self):
        """Test get_stop_reason with successful response."""
        response_data = {"stopReason": "max_tokens"}
        response = BedrockResponse(success=True, response_data=response_data)
        assert response.get_stop_reason() == "max_tokens"

    def test_get_stop_reason_no_data(self):
        """Test get_stop_reason with no data."""
        response = BedrockResponse(success=True, response_data=None)
        assert response.get_stop_reason() is None

        response = BedrockResponse(success=False, response_data={})
        assert response.get_stop_reason() is None

    def test_get_additional_model_response_fields(self):
        """Test get_additional_model_response_fields."""
        response_data = {"additionalModelResponseFields": {"custom_field": "custom_value"}}
        response = BedrockResponse(success=True, response_data=response_data)
        fields = response.get_additional_model_response_fields()
        assert fields == {"custom_field": "custom_value"}

        # Test no data cases
        response = BedrockResponse(success=True, response_data=None)
        assert response.get_additional_model_response_fields() is None

        response = BedrockResponse(success=False, response_data=response_data)
        assert response.get_additional_model_response_fields() is None

    def test_get_warnings(self):
        """Test get_warnings method."""
        warnings = ["Warning 1", "Warning 2"]
        response = BedrockResponse(success=True, warnings=warnings)

        result = response.get_warnings()
        assert result == warnings
        assert result is not warnings  # Should be a copy

    def test_get_disabled_features(self):
        """Test get_disabled_features method."""
        features = ["feature1", "feature2"]
        response = BedrockResponse(success=True, features_disabled=features)

        result = response.get_disabled_features()
        assert result == features
        assert result is not features  # Should be a copy

    def test_get_last_error(self):
        """Test get_last_error method."""
        error1 = ValueError("First error")
        error2 = RuntimeError("Second error")

        attempt1 = RequestAttempt(
            model_id="model1",
            region="region1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=error1,
        )

        attempt2 = RequestAttempt(
            model_id="model2",
            region="region2",
            access_method="direct",
            attempt_number=2,
            start_time=datetime.now(),
            success=False,
            error=error2,
        )

        response = BedrockResponse(success=False, attempts=[attempt1, attempt2])
        assert response.get_last_error() is error2

        # Test no errors
        response = BedrockResponse(success=True, attempts=[])
        assert response.get_last_error() is None

    def test_get_all_errors(self):
        """Test get_all_errors method."""
        error1 = ValueError("First error")
        error2 = RuntimeError("Second error")

        attempt1 = RequestAttempt(
            model_id="model1",
            region="region1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=error1,
        )

        attempt2 = RequestAttempt(
            model_id="model2",
            region="region2",
            access_method="direct",
            attempt_number=2,
            start_time=datetime.now(),
            success=True,
            error=None,
        )

        attempt3 = RequestAttempt(
            model_id="model3",
            region="region3",
            access_method="direct",
            attempt_number=3,
            start_time=datetime.now(),
            success=False,
            error=error2,
        )

        response = BedrockResponse(success=False, attempts=[attempt1, attempt2, attempt3])
        errors = response.get_all_errors()
        assert errors == [error1, error2]

    def test_get_attempt_count(self):
        """Test get_attempt_count method."""
        attempt = RequestAttempt(
            model_id="model",
            region="region",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=True,
        )

        response = BedrockResponse(success=True, attempts=[attempt])
        assert response.get_attempt_count() == 1

        response = BedrockResponse(success=True, attempts=[])
        assert response.get_attempt_count() == 0

    def test_get_successful_attempt(self):
        """Test get_successful_attempt method."""
        failed_attempt = RequestAttempt(
            model_id="model1",
            region="region1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
        )

        successful_attempt = RequestAttempt(
            model_id="model2",
            region="region2",
            access_method="direct",
            attempt_number=2,
            start_time=datetime.now(),
            success=True,
        )

        response = BedrockResponse(success=True, attempts=[failed_attempt, successful_attempt])
        assert response.get_successful_attempt() is successful_attempt

        # Test no successful attempts
        response = BedrockResponse(success=False, attempts=[failed_attempt])
        assert response.get_successful_attempt() is None

    def test_get_cached_tokens_info(self):
        """Test get_cached_tokens_info method."""
        # Test with cache info
        response_data = {"usage": {"cacheReadInputTokens": 100, "cacheWriteInputTokens": 50}}
        response = BedrockResponse(success=True, response_data=response_data)
        cache_info = response.get_cached_tokens_info()

        expected = {
            "cache_read_tokens": 100,
            "cache_write_tokens": 50,
            "cache_hit": True,
            "cache_write": True,
        }
        assert cache_info == expected

        # Test with no cache activity
        response_data = {"usage": {}}
        response = BedrockResponse(success=True, response_data=response_data)
        cache_info = response.get_cached_tokens_info()
        expected_no_cache = {
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "cache_hit": False,
            "cache_write": False,
        }
        assert cache_info == expected_no_cache

        # Test with no usage data
        response = BedrockResponse(success=True, response_data=None)
        assert response.get_cached_tokens_info() is None

    def test_validation_methods(self):
        """Test validation-related methods."""
        validation_result = ValidationResult(success=False, error_message="Test error")
        validation_attempt = ValidationAttempt(
            attempt_number=1, validation_result=validation_result, failed_content="failed content"
        )

        validation_error = {
            "error_message": "Validation failed",
            "error_details": {"field": "value"},
        }

        response = BedrockResponse(
            success=True,
            validation_attempts=[validation_attempt],
            validation_errors=[validation_error],
        )

        assert response.had_validation_failures() is True
        assert response.get_validation_attempt_count() == 1
        assert response.get_validation_errors() == [validation_error]
        assert response.get_last_validation_error() == validation_error

        # Test validation metrics
        metrics = response.get_validation_metrics()
        assert metrics["validation_attempts"] == 1
        assert metrics["validation_errors"] == 1
        assert metrics["had_validation_failures"] is True

        # Test no validation failures
        response = BedrockResponse(success=True)
        assert response.had_validation_failures() is False
        assert response.get_validation_attempt_count() == 0
        assert response.get_validation_errors() == []
        assert response.get_last_validation_error() is None

    def test_validation_metrics_with_successful_validation(self):
        """Test validation metrics with successful validation attempt."""
        success_result = ValidationResult(success=True)
        success_attempt = ValidationAttempt(attempt_number=2, validation_result=success_result)

        failed_result = ValidationResult(success=False, error_message="Failed")
        failed_attempt = ValidationAttempt(attempt_number=1, validation_result=failed_result)

        response = BedrockResponse(
            success=True, validation_attempts=[failed_attempt, success_attempt]
        )

        metrics = response.get_validation_metrics()
        assert metrics["successful_validation_attempt"] == 2

    def test_to_dict(self):
        """Test to_dict method."""
        start_time = datetime.now()
        end_time = datetime.now()

        attempt = RequestAttempt(
            model_id="claude-3",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=start_time,
            end_time=end_time,
            success=True,
            error=None,
        )

        validation_result = ValidationResult(success=True)
        validation_attempt = ValidationAttempt(
            attempt_number=1, validation_result=validation_result, failed_content="content"
        )

        response = BedrockResponse(
            success=True,
            response_data={"test": "data"},
            model_used="claude-3",
            region_used="us-east-1",
            access_method_used="direct",
            total_duration_ms=1000.0,
            api_latency_ms=500.0,
            warnings=["warning1"],
            features_disabled=["feature1"],
            attempts=[attempt],
            validation_attempts=[validation_attempt],
            validation_errors=[{"error": "test"}],
        )

        result = response.to_dict()

        assert result["success"] is True
        assert result["response_data"] == {"test": "data"}
        assert result["model_used"] == "claude-3"
        assert result["region_used"] == "us-east-1"
        assert result["access_method_used"] == "direct"
        assert result["total_duration_ms"] == 1000.0
        assert result["api_latency_ms"] == 500.0
        assert result["warnings"] == ["warning1"]
        assert result["features_disabled"] == ["feature1"]
        assert len(result["attempts"]) == 1
        assert len(result["validation_attempts"]) == 1
        assert result["validation_errors"] == [{"error": "test"}]

    def test_to_dict_with_error(self):
        """Test to_dict method with error in attempt."""
        error = ValueError("Test error")
        attempt = RequestAttempt(
            model_id="claude-3",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=error,
        )

        response = BedrockResponse(success=False, attempts=[attempt])
        result = response.to_dict()

        assert result["attempts"][0]["error"] == str(error)

    def test_to_json(self):
        """Test to_json method."""
        response = BedrockResponse(success=True, model_used="claude-3")

        # Test compact JSON
        json_str = response.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["model_used"] == "claude-3"

        # Test indented JSON
        json_str = response.to_json(indent=2)
        assert isinstance(json_str, str)
        assert "\n" in json_str  # Should be formatted

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "success": True,
            "response_data": {"test": "data"},
            "model_used": "claude-3",
            "region_used": "us-east-1",
            "access_method_used": "direct",
            "total_duration_ms": 1000.0,
            "api_latency_ms": 500.0,
            "warnings": ["warning1"],
            "features_disabled": ["feature1"],
            "attempts": [
                {
                    "model_id": "claude-3",
                    "region": "us-east-1",
                    "access_method": "direct",
                    "attempt_number": 1,
                    "start_time": "2023-01-01T12:00:00",
                    "end_time": "2023-01-01T12:00:01",
                    "success": True,
                    "error": None,
                }
            ],
            "validation_attempts": [
                {
                    "attempt_number": 1,
                    "validation_result": {
                        "success": True,
                        "error_message": None,
                        "error_details": None,
                    },
                    "failed_content": "content",
                }
            ],
            "validation_errors": [{"error": "test"}],
        }

        response = BedrockResponse.from_dict(data)

        assert response.success is True
        assert response.response_data == {"test": "data"}
        assert response.model_used == "claude-3"
        assert response.region_used == "us-east-1"
        assert response.access_method_used == "direct"
        assert response.total_duration_ms == 1000.0
        assert response.api_latency_ms == 500.0
        assert response.warnings == ["warning1"]
        assert response.features_disabled == ["feature1"]
        assert len(response.attempts) == 1
        assert len(response.validation_attempts) == 1
        assert response.validation_errors == [{"error": "test"}]

    def test_from_dict_with_error(self):
        """Test from_dict with error in attempt."""
        data = {
            "success": False,
            "attempts": [
                {
                    "model_id": "claude-3",
                    "region": "us-east-1",
                    "access_method": "direct",
                    "attempt_number": 1,
                    "start_time": "2023-01-01T12:00:00",
                    "end_time": None,
                    "success": False,
                    "error": "Test error message",
                }
            ],
        }

        response = BedrockResponse.from_dict(data)
        assert response.success is False
        assert len(response.attempts) == 1
        assert response.attempts[0].error is not None
        assert str(response.attempts[0].error) == "Test error message"

    def test_repr(self):
        """Test __repr__ method."""
        response = BedrockResponse(
            success=True, model_used="claude-3", region_used="us-east-1", attempts=[Mock(), Mock()]
        )

        repr_str = repr(response)
        assert "SUCCESS" in repr_str
        assert "claude-3" in repr_str
        assert "us-east-1" in repr_str
        assert "attempts=2" in repr_str

        # Test failed response
        response = BedrockResponse(success=False)
        repr_str = repr(response)
        assert "FAILED" in repr_str


class TestStreamingResponse:
    """Test StreamingResponse functionality."""

    def test_init_basic(self):
        """Test basic StreamingResponse initialization."""
        response = StreamingResponse(success=True)
        assert response.success is True
        assert response.content_parts == []
        assert response.stream_errors == []
        assert response.stream_position == 0
        assert response._stream_completed is False
        assert response._start_time is not None

    def test_add_content_part(self):
        """Test add_content_part method."""
        response = StreamingResponse(success=True)

        response.add_content_part("Hello")
        assert response.content_parts == ["Hello"]
        assert response.stream_position == 5

        response.add_content_part(" World")
        assert response.content_parts == ["Hello", " World"]
        assert response.stream_position == 11

    def test_get_full_content(self):
        """Test get_full_content method."""
        response = StreamingResponse(success=True)
        response.add_content_part("Hello")
        response.add_content_part(" World")

        assert response.get_full_content() == "Hello World"

    def test_get_content_parts(self):
        """Test get_content_parts method."""
        response = StreamingResponse(success=True)
        response.add_content_part("Part1")
        response.add_content_part("Part2")

        parts = response.get_content_parts()
        assert parts == ["Part1", "Part2"]
        assert parts is not response.content_parts  # Should be a copy

    def test_add_stream_error(self):
        """Test add_stream_error method."""
        response = StreamingResponse(success=True)
        error = ValueError("Test error")

        response.add_stream_error(error)
        assert response.stream_errors == [error]

    def test_get_stream_errors(self):
        """Test get_stream_errors method."""
        response = StreamingResponse(success=True)
        error1 = ValueError("Error 1")
        error2 = RuntimeError("Error 2")

        response.add_stream_error(error1)
        response.add_stream_error(error2)

        errors = response.get_stream_errors()
        assert errors == [error1, error2]
        assert errors is not response.stream_errors  # Should be a copy

    def test_get_usage(self):
        """Test get_usage method."""
        usage_info = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cache_read_tokens": 10,
            "cache_write_tokens": 5,
        }

        response = StreamingResponse(success=True, usage_info=usage_info)
        usage = response.get_usage()

        assert usage == usage_info

        # Test no usage info
        response = StreamingResponse(success=True)
        assert response.get_usage() is None

    def test_get_usage_exception_handling(self):
        """Test get_usage exception handling."""
        response = StreamingResponse(success=True, usage_info=None)
        assert response.get_usage() is None

    def test_get_metrics(self):
        """Test get_metrics method."""
        response = StreamingResponse(success=True, api_latency_ms=1000.0, total_duration_ms=2000.0)
        response.add_content_part("Part1")
        response.add_content_part("Part2")

        metrics = response.get_metrics()

        assert metrics is not None
        assert metrics["api_latency_ms"] == 1000.0
        assert metrics["total_duration_ms"] == 2000.0
        assert metrics["content_parts"] == 2
        assert metrics["stream_position"] == 10  # "Part1Part2"
        assert metrics["stream_errors"] == 0

    def test_get_metrics_with_timing(self):
        """Test get_metrics with timing information."""
        response = StreamingResponse(success=True)

        # Simulate timing
        response._start_time = datetime(2023, 1, 1, 12, 0, 0)
        response._first_token_time = datetime(2023, 1, 1, 12, 0, 1)
        response._last_token_time = datetime(2023, 1, 1, 12, 0, 2)

        metrics = response.get_metrics()

        assert metrics is not None
        assert metrics["time_to_first_token_ms"] == 1000.0
        assert metrics["time_to_last_token_ms"] == 2000.0
        assert metrics["token_generation_duration_ms"] == 1000.0

    def test_get_metrics_no_data(self):
        """Test get_metrics with no data."""
        response = StreamingResponse(success=True)
        metrics = response.get_metrics()

        # Should still return basic metrics
        assert metrics is not None
        assert metrics["content_parts"] == 0
        assert metrics["stream_position"] == 0
        assert metrics["stream_errors"] == 0

    def test_is_streaming_complete(self):
        """Test is_streaming_complete method."""
        response = StreamingResponse(success=True)
        assert response.is_streaming_complete() is False

        response._stream_completed = True
        assert response.is_streaming_complete() is True

    def test_get_mid_stream_exceptions_no_iterator(self):
        """Test get_mid_stream_exceptions without retrying iterator."""
        response = StreamingResponse(success=True)
        assert response.get_mid_stream_exceptions() == []

    def test_get_target_switches_no_iterator(self):
        """Test get_target_switches without retrying iterator."""
        response = StreamingResponse(success=True)
        assert response.get_target_switches() == 0

    def test_get_recovery_info_no_iterator(self):
        """Test get_recovery_info without retrying iterator."""
        response = StreamingResponse(success=True)
        info = response.get_recovery_info()

        expected = {
            "total_exceptions": 0,
            "recovered_exceptions": 0,
            "target_switches": 0,
            "recovery_enabled": False,
        }
        assert info == expected

    def test_get_recovery_info_with_iterator(self):
        """Test get_recovery_info with retrying iterator."""
        mock_iterator = Mock()
        mock_iterator.mid_stream_exceptions = [Mock(recovered=True), Mock(recovered=False)]
        mock_iterator.target_switches = 2
        mock_iterator.current_model = "claude-3"
        mock_iterator.current_region = "us-east-1"
        mock_iterator.partial_content = ["content"]

        response = StreamingResponse(success=True)
        response._retrying_iterator = mock_iterator

        info = response.get_recovery_info()

        assert info["total_exceptions"] == 2
        assert info["recovered_exceptions"] == 1
        assert info["target_switches"] == 2
        assert info["recovery_enabled"] is True
        assert info["final_model"] == "claude-3"
        assert info["final_region"] == "us-east-1"
        assert info["partial_content_preserved"] is True

    def test_repr_streaming(self):
        """Test __repr__ while streaming."""
        response = StreamingResponse(success=True)
        response.add_content_part("Hello")

        repr_str = repr(response)
        assert "STREAMING" in repr_str
        assert "parts=1" in repr_str
        assert "position=5" in repr_str
        assert "errors=0" in repr_str

    def test_repr_completed_success(self):
        """Test __repr__ after successful completion."""
        response = StreamingResponse(success=True)
        response._stream_completed = True

        repr_str = repr(response)
        assert "SUCCESS" in repr_str

    def test_repr_completed_failed(self):
        """Test __repr__ after failed completion."""
        response = StreamingResponse(success=False)
        response._stream_completed = True

        repr_str = repr(response)
        assert "FAILED" in repr_str

    def test_get_metrics_timing_edge_cases(self):
        """Test get_metrics with timing edge cases."""
        response = StreamingResponse(success=True)

        # Test with only start time
        response._start_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics = response.get_metrics()
        assert metrics is not None
        assert "time_to_first_token_ms" not in metrics
        assert "time_to_last_token_ms" not in metrics
        assert "token_generation_duration_ms" not in metrics

        # Test with start and first token time only
        response._first_token_time = datetime(2023, 1, 1, 12, 0, 1)
        metrics = response.get_metrics()
        assert metrics is not None
        assert metrics["time_to_first_token_ms"] == 1000.0
        assert "time_to_last_token_ms" not in metrics
        assert "token_generation_duration_ms" not in metrics


class TestBedrockResponseCacheEfficiency:
    """Test BedrockResponse cache efficiency functionality."""

    def test_get_cache_efficiency_successful(self):
        """Test get_cache_efficiency with cache data."""
        response_data = {
            "usage": {
                "inputTokens": 1000,
                "outputTokens": 200,
                "totalTokens": 1200,
                "cacheReadInputTokens": 500,
                "cacheWriteInputTokens": 100,
            }
        }
        response = BedrockResponse(success=True, response_data=response_data)

        cache_efficiency = response.get_cache_efficiency()

        assert cache_efficiency is not None
        assert cache_efficiency["cache_hit_ratio"] == 0.5  # 500/1000
        assert cache_efficiency["cache_savings_tokens"] == 500
        assert (
            cache_efficiency["cache_savings_cost"] == "$0.01"
        )  # (500/1000) * 0.03 = 0.015 rounds to $0.01
        assert cache_efficiency["latency_reduction_ms"] == 5  # 500/100
        assert cache_efficiency["cache_write_tokens"] == 100
        assert cache_efficiency["cache_read_tokens"] == 500
        assert cache_efficiency["cache_effectiveness"] == 50.0  # 0.5 * 100

    def test_get_cache_efficiency_no_cache_info(self):
        """Test get_cache_efficiency with no cache info."""
        response = BedrockResponse(success=True, response_data=None)
        assert response.get_cache_efficiency() is None

    def test_get_cache_efficiency_no_usage(self):
        """Test get_cache_efficiency with no usage data."""
        response_data = {"usage": {"cacheReadInputTokens": 100}}
        response = BedrockResponse(success=True, response_data=response_data)

        # This will have usage but input_tokens will be 0
        cache_efficiency = response.get_cache_efficiency()
        assert cache_efficiency is None  # Should return None for zero division case

    def test_get_cache_efficiency_zero_input_tokens(self):
        """Test get_cache_efficiency with zero input tokens."""
        response_data = {
            "usage": {
                "inputTokens": 0,
                "cacheReadInputTokens": 100,
                "cacheWriteInputTokens": 50,
            }
        }
        response = BedrockResponse(success=True, response_data=response_data)

        cache_efficiency = response.get_cache_efficiency()
        assert cache_efficiency is None

    def test_get_cache_efficiency_no_cache_activity(self):
        """Test get_cache_efficiency with no cache activity."""
        response_data = {
            "usage": {
                "inputTokens": 1000,
                "outputTokens": 200,
                "totalTokens": 1200,
                "cacheReadInputTokens": 0,
                "cacheWriteInputTokens": 0,
            }
        }
        response = BedrockResponse(success=True, response_data=response_data)

        cache_efficiency = response.get_cache_efficiency()

        assert cache_efficiency is not None
        assert cache_efficiency["cache_hit_ratio"] == 0.0
        assert cache_efficiency["cache_savings_tokens"] == 0
        assert cache_efficiency["cache_savings_cost"] == "$0.00"
        assert cache_efficiency["latency_reduction_ms"] == 0
        assert cache_efficiency["cache_effectiveness"] == 0.0


class TestStreamingResponseIteratorProtocol:
    """Test StreamingResponse iterator protocol and event processing."""

    def test_iter_protocol(self):
        """Test iterator protocol implementation."""
        response = StreamingResponse(success=True)
        assert iter(response) is response

    def test_set_event_stream(self):
        """Test _set_event_stream method."""
        response = StreamingResponse(success=True)
        mock_stream = Mock()
        mock_stream.__iter__ = Mock(return_value=iter([]))

        response._set_event_stream(mock_stream)
        assert response._event_stream is mock_stream
        assert response._stream_iterator is not None

    def test_set_event_stream_none(self):
        """Test _set_event_stream with None."""
        response = StreamingResponse(success=True)
        response._set_event_stream(None)
        assert response._event_stream is None
        assert response._stream_iterator is None

    def test_set_retrying_iterator(self):
        """Test _set_retrying_iterator method."""
        response = StreamingResponse(success=True)
        mock_iterator = Mock()
        mock_iterator.__iter__ = Mock(return_value=iter([]))

        response._set_retrying_iterator(mock_iterator)
        assert response._retrying_iterator is mock_iterator
        assert response._stream_iterator is not None

    def test_next_stream_completed(self):
        """Test __next__ when stream is already completed."""
        response = StreamingResponse(success=True)
        response._stream_completed = True

        with pytest.raises(StopIteration):
            next(response)

    def test_next_no_stream_iterator(self):
        """Test __next__ when no stream iterator is set."""
        response = StreamingResponse(success=True)
        response._stream_iterator = None

        with pytest.raises(StopIteration):
            next(response)

        assert response._stream_completed is True

    def test_next_normal_stop_iteration(self):
        """Test __next__ when stream ends normally."""
        response = StreamingResponse(success=True)
        response._stream_iterator = iter([])

        with pytest.raises(StopIteration):
            next(response)

        assert response._stream_completed is True

    def test_next_with_exception(self):
        """Test __next__ when an exception occurs during iteration."""
        response = StreamingResponse(success=True)

        def error_iterator():
            raise RuntimeError("Stream error")
            yield  # Never reached but makes it a generator

        response._stream_iterator = error_iterator()

        with pytest.raises(StopIteration):
            next(response)

        assert response._stream_completed is True
        assert len(response.stream_errors) == 1
        assert isinstance(response.stream_errors[0], RuntimeError)

    @patch(
        "bestehorn_llmmanager.bedrock.models.bedrock_response.StreamingResponse._process_streaming_event"
    )
    def test_next_with_content(self, mock_process_event):
        """Test __next__ successfully returning content."""
        mock_process_event.return_value = "Hello"

        response = StreamingResponse(success=True)
        mock_event = {"contentBlockDelta": {"delta": {"text": "Hello"}}}
        response._stream_iterator = iter([mock_event])

        content = next(response)
        assert content == "Hello"
        mock_process_event.assert_called_once_with(mock_event)

    @patch(
        "bestehorn_llmmanager.bedrock.models.bedrock_response.StreamingResponse._process_streaming_event"
    )
    def test_next_with_no_content_event(self, mock_process_event):
        """Test __next__ with event that has no content."""
        mock_process_event.side_effect = [None, "Hello"]  # First event has no content, second does

        response = StreamingResponse(success=True)
        mock_events = [
            {"messageStart": {"role": "assistant"}},
            {"contentBlockDelta": {"delta": {"text": "Hello"}}},
        ]
        response._stream_iterator = iter(mock_events)

        content = next(response)
        assert content == "Hello"
        assert mock_process_event.call_count == 2

    @patch("bestehorn_llmmanager.bedrock.streaming.event_handlers.StreamEventHandler")
    def test_process_streaming_event(self, mock_handler_class):
        """Test _process_streaming_event method."""
        # Set up mocks
        mock_handler = Mock()
        mock_handler_instance = Mock()
        mock_handler_instance.get_event_handler.return_value = mock_handler
        mock_handler_class.return_value = mock_handler_instance

        mock_handler.return_value = {"content": "processed"}

        response = StreamingResponse(success=True)

        # Mock the event type determination
        with patch.object(response, "_determine_event_type") as mock_determine, patch.object(
            response, "_update_from_streaming_event"
        ) as mock_update:

            mock_event_type = Mock()
            mock_event_type.value = "contentBlockDelta"
            mock_determine.return_value = mock_event_type
            mock_update.return_value = "Hello"

            event = {"contentBlockDelta": {"delta": {"text": "Hello"}}}
            result = response._process_streaming_event(event)

            assert result == "Hello"
            mock_determine.assert_called_once_with(event)
            mock_handler_instance.get_event_handler.assert_called_once_with(mock_event_type)
            mock_update.assert_called_once_with(mock_event_type, {"content": "processed"})

    def test_process_streaming_event_exception(self):
        """Test _process_streaming_event with exception."""
        response = StreamingResponse(success=True)

        # Mock to raise an exception
        with patch.object(response, "_determine_event_type", side_effect=ValueError("Bad event")):
            event = {"invalid": "event"}
            result = response._process_streaming_event(event)

            assert result is None
            assert len(response.stream_errors) == 1
            assert isinstance(response.stream_errors[0], ValueError)

    # Note: Complex streaming event processing methods are tested through integration
    # tests rather than unit tests due to complex import dependencies

    def test_finalize_streaming_basic(self):
        """Test _finalize_streaming basic functionality."""
        response = StreamingResponse(success=True)
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        response._start_time = start_time

        with patch(
            "bestehorn_llmmanager.bedrock.models.bedrock_response.datetime"
        ) as mock_datetime:
            end_time = datetime(2023, 1, 1, 12, 0, 2)
            mock_datetime.now.return_value = end_time

            response._finalize_streaming()

            assert response._stream_completed is True
            assert response.total_duration_ms == 2000.0  # 2 seconds

    def test_finalize_streaming_with_retrying_iterator(self):
        """Test _finalize_streaming with retrying iterator."""
        response = StreamingResponse(success=True)

        mock_iterator = Mock()
        mock_iterator.current_model = "claude-3"
        mock_iterator.current_region = "us-east-1"
        mock_iterator.get_timing_metrics.return_value = {"total_duration_ms": 3000.0}

        response._retrying_iterator = mock_iterator

        response._finalize_streaming()

        assert response.model_used == "claude-3"
        assert response.region_used == "us-east-1"
        assert response.total_duration_ms == 3000.0

    def test_finalize_streaming_success_determination(self):
        """Test _finalize_streaming success determination logic."""
        response = StreamingResponse(success=True)

        # Test with content - should be successful
        response.content_parts = ["Hello"]
        response._finalize_streaming()
        assert response.success is True

        # Test with stop reason - should be successful
        response = StreamingResponse(success=True)
        response.stop_reason = "end_turn"
        response._finalize_streaming()
        assert response.success is True

        # Test with unrecovered errors
        response = StreamingResponse(success=True)
        error = RuntimeError("Unrecovered error")
        response.stream_errors = [error]
        with patch.object(response, "_is_recovered_error", return_value=False):
            response._finalize_streaming()
            assert response.success is False

        # Test with recovered errors
        response = StreamingResponse(success=True)
        error = RuntimeError("Recovered error")
        response.stream_errors = [error]
        response.content_parts = ["Content"]
        with patch.object(response, "_is_recovered_error", return_value=True):
            response._finalize_streaming()
            assert response.success is True

    def test_is_recovered_error_no_iterator(self):
        """Test _is_recovered_error without retrying iterator."""
        response = StreamingResponse(success=True)
        error = RuntimeError("Test error")

        result = response._is_recovered_error(error)
        assert result is False

    def test_is_recovered_error_with_iterator(self):
        """Test _is_recovered_error with retrying iterator."""
        response = StreamingResponse(success=True)
        error = RuntimeError("Test error")

        mock_exception = Mock()
        mock_exception.recovered = True
        mock_exception.error = error

        mock_iterator = Mock()
        mock_iterator.mid_stream_exceptions = [mock_exception]
        response._retrying_iterator = mock_iterator

        result = response._is_recovered_error(error)
        assert result is True

    def test_get_mid_stream_exceptions_with_iterator(self):
        """Test get_mid_stream_exceptions with retrying iterator."""
        response = StreamingResponse(success=True)

        mock_exception = Mock()
        mock_exception.error = RuntimeError("Test error")
        mock_exception.position = 100
        mock_exception.model = "claude-3"
        mock_exception.region = "us-east-1"
        mock_exception.timestamp = datetime(2023, 1, 1, 12, 0, 0)
        mock_exception.recovered = True

        mock_iterator = Mock()
        mock_iterator.mid_stream_exceptions = [mock_exception]
        response._retrying_iterator = mock_iterator

        exceptions = response.get_mid_stream_exceptions()

        assert len(exceptions) == 1
        exc = exceptions[0]
        assert exc["error_type"] == "RuntimeError"
        assert exc["error_message"] == "Test error"
        assert exc["position"] == 100
        assert exc["model"] == "claude-3"
        assert exc["region"] == "us-east-1"
        assert exc["timestamp"] == "2023-01-01T12:00:00"
        assert exc["recovered"] is True

    def test_get_target_switches_with_iterator(self):
        """Test get_target_switches with retrying iterator."""
        response = StreamingResponse(success=True)

        mock_iterator = Mock()
        mock_iterator.target_switches = 3
        response._retrying_iterator = mock_iterator

        switches = response.get_target_switches()
        assert switches == 3
