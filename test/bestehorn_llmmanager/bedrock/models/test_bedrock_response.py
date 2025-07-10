"""
Unit tests for bedrock.models.bedrock_response module.
Tests for BedrockResponse and StreamingResponse classes.
"""

import json
from datetime import datetime

from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse, StreamingResponse
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RequestAttempt,
    ValidationAttempt,
    ValidationResult,
)


class TestBedrockResponse:
    """Test cases for BedrockResponse class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.sample_response_data = {
            ConverseAPIFields.OUTPUT: {
                ConverseAPIFields.MESSAGE: {
                    ConverseAPIFields.CONTENT: [
                        {ConverseAPIFields.TEXT: "Hello, how can I help you?"},
                        {ConverseAPIFields.TEXT: "I'm here to assist."},
                    ]
                }
            },
            ConverseAPIFields.USAGE: {
                ConverseAPIFields.INPUT_TOKENS: 10,
                ConverseAPIFields.OUTPUT_TOKENS: 15,
                ConverseAPIFields.TOTAL_TOKENS: 25,
                ConverseAPIFields.CACHE_READ_INPUT_TOKENS_COUNT: 5,
                ConverseAPIFields.CACHE_WRITE_INPUT_TOKENS_COUNT: 3,
            },
            ConverseAPIFields.METRICS: {ConverseAPIFields.LATENCY_MS: 250.5},
            ConverseAPIFields.STOP_REASON: "end_turn",
            ConverseAPIFields.ADDITIONAL_MODEL_RESPONSE_FIELDS: {"custom_field": "custom_value"},
        }

        self.sample_attempt = RequestAttempt(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=True,
            error=None,
        )

    def test_successful_response_creation(self) -> None:
        """Test creation of successful BedrockResponse."""
        response = BedrockResponse(
            success=True,
            response_data=self.sample_response_data,
            model_used="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_used="us-east-1",
            access_method_used="direct",
            attempts=[self.sample_attempt],
            total_duration_ms=500.0,
            api_latency_ms=250.5,
            warnings=["Test warning"],
            features_disabled=["streaming"],
            validation_attempts=[],
            validation_errors=[],
        )

        assert response.success is True
        assert response.model_used == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert response.region_used == "us-east-1"
        assert response.access_method_used == "direct"
        assert len(response.attempts) == 1
        assert response.total_duration_ms == 500.0
        assert response.api_latency_ms == 250.5
        assert response.warnings == ["Test warning"]
        assert response.features_disabled == ["streaming"]

    def test_failed_response_creation(self) -> None:
        """Test creation of failed BedrockResponse."""
        failed_attempt = RequestAttempt(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=Exception("API Error"),
        )

        response = BedrockResponse(success=False, attempts=[failed_attempt])

        assert response.success is False
        assert response.response_data is None
        assert response.model_used is None
        assert len(response.attempts) == 1

    def test_get_content_success(self) -> None:
        """Test extracting content from successful response."""
        response = BedrockResponse(success=True, response_data=self.sample_response_data)

        content = response.get_content()

        assert content == "Hello, how can I help you?\nI'm here to assist."

    def test_get_content_no_response_data(self) -> None:
        """Test get_content when no response data available."""
        response = BedrockResponse(success=True, response_data=None)

        content = response.get_content()

        assert content is None

    def test_get_content_failed_response(self) -> None:
        """Test get_content on failed response."""
        response = BedrockResponse(success=False, response_data=self.sample_response_data)

        content = response.get_content()

        assert content is None

    def test_get_content_malformed_data(self) -> None:
        """Test get_content with malformed response data."""
        malformed_data = {ConverseAPIFields.OUTPUT: "invalid_structure"}

        response = BedrockResponse(success=True, response_data=malformed_data)

        content = response.get_content()

        assert content is None

    def test_get_content_empty_content_blocks(self) -> None:
        """Test get_content with empty content blocks."""
        empty_content_data: dict = {
            ConverseAPIFields.OUTPUT: {ConverseAPIFields.MESSAGE: {ConverseAPIFields.CONTENT: []}}
        }

        response = BedrockResponse(success=True, response_data=empty_content_data)

        content = response.get_content()

        assert content is None

    def test_get_usage_success(self) -> None:
        """Test getting usage information from response."""
        response = BedrockResponse(success=True, response_data=self.sample_response_data)

        usage = response.get_usage()

        expected = {
            "input_tokens": 10,
            "output_tokens": 15,
            "total_tokens": 25,
            "cache_read_tokens": 5,
            "cache_write_tokens": 3,
        }

        assert usage == expected

    def test_get_usage_no_response_data(self) -> None:
        """Test get_usage when no response data available."""
        response = BedrockResponse(success=True, response_data=None)

        usage = response.get_usage()

        assert usage is None

    def test_get_usage_failed_response(self) -> None:
        """Test get_usage on failed response."""
        response = BedrockResponse(success=False, response_data=self.sample_response_data)

        usage = response.get_usage()

        assert usage is None

    def test_get_usage_malformed_data(self) -> None:
        """Test get_usage with malformed response data."""
        malformed_data = {ConverseAPIFields.USAGE: "invalid_structure"}

        response = BedrockResponse(success=True, response_data=malformed_data)

        usage = response.get_usage()

        assert usage is None

    def test_get_metrics_success(self) -> None:
        """Test getting metrics from response."""
        response = BedrockResponse(
            success=True,
            response_data=self.sample_response_data,
            attempts=[self.sample_attempt],
            total_duration_ms=500.0,
        )

        metrics = response.get_metrics()

        assert metrics is not None
        assert metrics["api_latency_ms"] == 250.5
        assert metrics["total_duration_ms"] == 500.0
        assert metrics["attempts_made"] == 1
        assert metrics["successful_attempt_number"] == 1

    def test_get_metrics_no_response_data(self) -> None:
        """Test get_metrics when no response data available."""
        response = BedrockResponse(success=True, response_data=None)

        metrics = response.get_metrics()

        assert metrics is None

    def test_get_metrics_failed_response(self) -> None:
        """Test get_metrics on failed response."""
        response = BedrockResponse(success=False, response_data=self.sample_response_data)

        metrics = response.get_metrics()

        assert metrics is None

    def test_get_metrics_partial_data(self) -> None:
        """Test get_metrics with partial data available."""
        failed_attempt = RequestAttempt(
            model_id="test",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=Exception("Error"),
        )

        response = BedrockResponse(
            success=True,
            response_data={"dummy": "data"},  # Some response data but no metrics section
            attempts=[failed_attempt],
            total_duration_ms=300.0,
        )

        metrics = response.get_metrics()

        assert metrics is not None
        assert "api_latency_ms" not in metrics
        assert metrics["total_duration_ms"] == 300.0
        assert metrics["attempts_made"] == 1
        assert "successful_attempt_number" not in metrics

    def test_get_stop_reason_success(self) -> None:
        """Test getting stop reason from response."""
        response = BedrockResponse(success=True, response_data=self.sample_response_data)

        stop_reason = response.get_stop_reason()

        assert stop_reason == "end_turn"

    def test_get_stop_reason_no_response_data(self) -> None:
        """Test get_stop_reason when no response data available."""
        response = BedrockResponse(success=True, response_data=None)

        stop_reason = response.get_stop_reason()

        assert stop_reason is None

    def test_get_additional_model_response_fields_success(self) -> None:
        """Test getting additional model response fields."""
        response = BedrockResponse(success=True, response_data=self.sample_response_data)

        additional_fields = response.get_additional_model_response_fields()

        assert additional_fields == {"custom_field": "custom_value"}

    def test_get_additional_model_response_fields_no_response_data(self) -> None:
        """Test get_additional_model_response_fields when no response data available."""
        response = BedrockResponse(success=True, response_data=None)

        additional_fields = response.get_additional_model_response_fields()

        assert additional_fields is None

    def test_was_successful(self) -> None:
        """Test was_successful method."""
        successful_response = BedrockResponse(success=True)
        failed_response = BedrockResponse(success=False)

        assert successful_response.was_successful() is True
        assert failed_response.was_successful() is False

    def test_get_warnings(self) -> None:
        """Test getting warnings."""
        warnings = ["Warning 1", "Warning 2"]
        response = BedrockResponse(success=True, warnings=warnings)

        result_warnings = response.get_warnings()

        assert result_warnings == warnings
        assert result_warnings is not response.warnings  # Should be a copy

    def test_get_disabled_features(self) -> None:
        """Test getting disabled features."""
        disabled_features = ["feature1", "feature2"]
        response = BedrockResponse(success=True, features_disabled=disabled_features)

        result_features = response.get_disabled_features()

        assert result_features == disabled_features
        assert result_features is not response.features_disabled  # Should be a copy

    def test_get_last_error_success(self) -> None:
        """Test getting last error from failed attempts."""
        error1 = Exception("First error")
        error2 = Exception("Second error")

        failed_attempt1 = RequestAttempt(
            model_id="test1",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=error1,
        )

        failed_attempt2 = RequestAttempt(
            model_id="test2",
            region="us-west-2",
            access_method="cris",
            attempt_number=2,
            start_time=datetime.now(),
            success=False,
            error=error2,
        )

        response = BedrockResponse(success=False, attempts=[failed_attempt1, failed_attempt2])

        last_error = response.get_last_error()

        assert last_error == error2

    def test_get_last_error_no_errors(self) -> None:
        """Test getting last error when no errors exist."""
        successful_attempt = RequestAttempt(
            model_id="test",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=True,
            error=None,
        )

        response = BedrockResponse(success=True, attempts=[successful_attempt])

        last_error = response.get_last_error()

        assert last_error is None

    def test_get_all_errors(self) -> None:
        """Test getting all errors from failed attempts."""
        error1 = Exception("First error")
        error2 = Exception("Second error")

        failed_attempt1 = RequestAttempt(
            model_id="test1",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=error1,
        )

        successful_attempt = RequestAttempt(
            model_id="test2",
            region="us-west-2",
            access_method="direct",
            attempt_number=2,
            start_time=datetime.now(),
            success=True,
            error=None,
        )

        failed_attempt2 = RequestAttempt(
            model_id="test3",
            region="eu-west-1",
            access_method="cris",
            attempt_number=3,
            start_time=datetime.now(),
            success=False,
            error=error2,
        )

        response = BedrockResponse(
            success=False, attempts=[failed_attempt1, successful_attempt, failed_attempt2]
        )

        all_errors = response.get_all_errors()

        assert len(all_errors) == 2
        assert error1 in all_errors
        assert error2 in all_errors

    def test_get_attempt_count(self) -> None:
        """Test getting attempt count."""
        attempts = [self.sample_attempt, self.sample_attempt]
        response = BedrockResponse(success=True, attempts=attempts)

        count = response.get_attempt_count()

        assert count == 2

    def test_get_successful_attempt(self) -> None:
        """Test getting successful attempt."""
        failed_attempt = RequestAttempt(
            model_id="test1",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=Exception("Error"),
        )

        response = BedrockResponse(success=True, attempts=[failed_attempt, self.sample_attempt])

        successful_attempt = response.get_successful_attempt()

        assert successful_attempt == self.sample_attempt

    def test_get_successful_attempt_no_success(self) -> None:
        """Test getting successful attempt when no success exists."""
        failed_attempt = RequestAttempt(
            model_id="test1",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=datetime.now(),
            success=False,
            error=Exception("Error"),
        )

        response = BedrockResponse(success=False, attempts=[failed_attempt])

        successful_attempt = response.get_successful_attempt()

        assert successful_attempt is None

    def test_get_cached_tokens_info_with_cache(self) -> None:
        """Test getting cached tokens info when cache data is available."""
        response = BedrockResponse(success=True, response_data=self.sample_response_data)

        cache_info = response.get_cached_tokens_info()

        expected = {
            "cache_read_tokens": 5,
            "cache_write_tokens": 3,
            "cache_hit": True,
            "cache_write": True,
        }

        assert cache_info == expected

    def test_get_cached_tokens_info_no_cache(self) -> None:
        """Test getting cached tokens info when no cache data is available."""
        no_cache_data = {
            ConverseAPIFields.USAGE: {
                ConverseAPIFields.INPUT_TOKENS: 10,
                ConverseAPIFields.OUTPUT_TOKENS: 15,
                ConverseAPIFields.TOTAL_TOKENS: 25,
            }
        }

        response = BedrockResponse(success=True, response_data=no_cache_data)

        cache_info = response.get_cached_tokens_info()

        assert cache_info is None

    def test_get_cached_tokens_info_no_usage(self) -> None:
        """Test getting cached tokens info when no usage data is available."""
        response = BedrockResponse(success=True, response_data={})

        cache_info = response.get_cached_tokens_info()

        assert cache_info is None

    def test_had_validation_failures_true(self) -> None:
        """Test had_validation_failures when validation attempts exist."""
        validation_result = ValidationResult(
            success=False, error_message="Validation error", error_details={"detail": "error"}
        )

        validation_attempt = ValidationAttempt(
            attempt_number=1, validation_result=validation_result, failed_content="failed content"
        )

        response = BedrockResponse(success=True, validation_attempts=[validation_attempt])

        assert response.had_validation_failures() is True

    def test_had_validation_failures_false(self) -> None:
        """Test had_validation_failures when no validation attempts exist."""
        response = BedrockResponse(success=True)

        assert response.had_validation_failures() is False

    def test_get_validation_attempt_count(self) -> None:
        """Test getting validation attempt count."""
        validation_result1 = ValidationResult(success=True)
        validation_result2 = ValidationResult(success=False, error_message="Error")

        validation_attempt1 = ValidationAttempt(
            attempt_number=1, validation_result=validation_result1
        )
        validation_attempt2 = ValidationAttempt(
            attempt_number=2, validation_result=validation_result2
        )

        response = BedrockResponse(
            success=True, validation_attempts=[validation_attempt1, validation_attempt2]
        )

        count = response.get_validation_attempt_count()

        assert count == 2

    def test_get_validation_errors(self) -> None:
        """Test getting validation errors."""
        validation_errors = [{"error": "test_error_1"}, {"error": "test_error_2"}]
        response = BedrockResponse(success=True, validation_errors=validation_errors)

        result_errors = response.get_validation_errors()

        assert result_errors == validation_errors
        assert result_errors is not response.validation_errors  # Should be a copy

    def test_get_last_validation_error(self) -> None:
        """Test getting last validation error."""
        error1 = {"error": "first_error"}
        error2 = {"error": "second_error"}
        validation_errors = [error1, error2]

        response = BedrockResponse(success=True, validation_errors=validation_errors)

        last_error = response.get_last_validation_error()

        assert last_error == error2

    def test_get_last_validation_error_no_errors(self) -> None:
        """Test getting last validation error when no errors exist."""
        response = BedrockResponse(success=True)

        last_error = response.get_last_validation_error()

        assert last_error is None

    def test_get_validation_metrics_with_success(self) -> None:
        """Test getting validation metrics with successful validation."""
        successful_validation_result = ValidationResult(
            success=True, error_message=None, error_details=None
        )

        validation_attempt = ValidationAttempt(
            attempt_number=2, validation_result=successful_validation_result, failed_content=None
        )

        response = BedrockResponse(
            success=True,
            validation_attempts=[validation_attempt],
            validation_errors=[{"error": "test"}],
        )

        metrics = response.get_validation_metrics()

        expected = {
            "validation_attempts": 1,
            "validation_errors": 1,
            "had_validation_failures": True,
            "successful_validation_attempt": 2,
        }

        assert metrics == expected

    def test_get_validation_metrics_no_success(self) -> None:
        """Test getting validation metrics with no successful validation."""
        failed_validation_result = ValidationResult(
            success=False, error_message="Validation failed", error_details={"error": "details"}
        )

        validation_attempt = ValidationAttempt(
            attempt_number=1, validation_result=failed_validation_result, failed_content="failed"
        )

        response = BedrockResponse(success=True, validation_attempts=[validation_attempt])

        metrics = response.get_validation_metrics()

        expected = {
            "validation_attempts": 1,
            "validation_errors": 0,
            "had_validation_failures": True,
        }

        assert metrics == expected

    def test_to_dict(self) -> None:
        """Test converting response to dictionary."""
        start_time = datetime.now()
        end_time = datetime.now()

        attempt = RequestAttempt(
            model_id="test_model",
            region="us-east-1",
            access_method="direct",
            attempt_number=1,
            start_time=start_time,
            end_time=end_time,
            success=True,
            error=None,
        )

        validation_result = ValidationResult(success=True, error_message=None, error_details=None)

        validation_attempt = ValidationAttempt(
            attempt_number=1, validation_result=validation_result, failed_content=None
        )

        response = BedrockResponse(
            success=True,
            response_data={"test": "data"},
            model_used="test_model",
            region_used="us-east-1",
            access_method_used="direct",
            attempts=[attempt],
            total_duration_ms=500.0,
            api_latency_ms=250.0,
            warnings=["warning"],
            features_disabled=["feature"],
            validation_attempts=[validation_attempt],
            validation_errors=[{"error": "test"}],
        )

        result_dict = response.to_dict()

        assert result_dict["success"] is True
        assert result_dict["response_data"] == {"test": "data"}
        assert result_dict["model_used"] == "test_model"
        assert result_dict["region_used"] == "us-east-1"
        assert result_dict["access_method_used"] == "direct"
        assert result_dict["total_duration_ms"] == 500.0
        assert result_dict["api_latency_ms"] == 250.0
        assert result_dict["warnings"] == ["warning"]
        assert result_dict["features_disabled"] == ["feature"]
        assert len(result_dict["attempts"]) == 1
        assert len(result_dict["validation_attempts"]) == 1
        assert result_dict["validation_errors"] == [{"error": "test"}]

    def test_to_json(self) -> None:
        """Test converting response to JSON string."""
        response = BedrockResponse(success=True, model_used="test_model")

        json_str = response.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["model_used"] == "test_model"

    def test_to_json_with_indent(self) -> None:
        """Test converting response to formatted JSON string."""
        response = BedrockResponse(success=True, model_used="test_model")

        json_str = response.to_json(indent=2)

        # Should be valid JSON with formatting
        assert "\n" in json_str
        parsed = json.loads(json_str)
        assert parsed["success"] is True

    def test_from_dict(self) -> None:
        """Test creating response from dictionary."""
        start_time = datetime.now()
        end_time = datetime.now()

        data = {
            "success": True,
            "response_data": {"test": "data"},
            "model_used": "test_model",
            "region_used": "us-east-1",
            "access_method_used": "direct",
            "total_duration_ms": 500.0,
            "api_latency_ms": 250.0,
            "warnings": ["warning"],
            "features_disabled": ["feature"],
            "attempts": [
                {
                    "model_id": "test_model",
                    "region": "us-east-1",
                    "access_method": "direct",
                    "attempt_number": 1,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_ms": 100.0,
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
                    "failed_content": None,
                }
            ],
            "validation_errors": [{"error": "test"}],
        }

        response = BedrockResponse.from_dict(data=data)

        assert response.success is True
        assert response.response_data == {"test": "data"}
        assert response.model_used == "test_model"
        assert response.region_used == "us-east-1"
        assert response.access_method_used == "direct"
        assert response.total_duration_ms == 500.0
        assert response.api_latency_ms == 250.0
        assert response.warnings == ["warning"]
        assert response.features_disabled == ["feature"]
        assert len(response.attempts) == 1
        assert len(response.validation_attempts) == 1
        assert response.validation_errors == [{"error": "test"}]

    def test_from_dict_with_error_attempt(self) -> None:
        """Test creating response from dictionary with error attempt."""
        start_time = datetime.now()

        data = {
            "success": False,
            "attempts": [
                {
                    "model_id": "test_model",
                    "region": "us-east-1",
                    "access_method": "direct",
                    "attempt_number": 1,
                    "start_time": start_time.isoformat(),
                    "end_time": None,
                    "duration_ms": None,
                    "success": False,
                    "error": "Test error message",
                }
            ],
        }

        response = BedrockResponse.from_dict(data=data)

        assert response.success is False
        assert len(response.attempts) == 1
        assert response.attempts[0].success is False
        assert str(response.attempts[0].error) == "Test error message"

    def test_repr(self) -> None:
        """Test string representation of BedrockResponse."""
        response = BedrockResponse(
            success=True,
            model_used="test_model",
            region_used="us-east-1",
            attempts=[self.sample_attempt],
        )

        repr_str = repr(response)

        assert "SUCCESS" in repr_str
        assert "test_model" in repr_str
        assert "us-east-1" in repr_str
        assert "attempts=1" in repr_str

    def test_repr_failed(self) -> None:
        """Test string representation of failed BedrockResponse."""
        response = BedrockResponse(success=False, attempts=[])

        repr_str = repr(response)

        assert "FAILED" in repr_str
        assert "attempts=0" in repr_str


class TestStreamingResponse:
    """Test cases for StreamingResponse class."""

    def test_successful_streaming_response_creation(self) -> None:
        """Test creation of successful StreamingResponse."""
        final_response = BedrockResponse(success=True)

        response = StreamingResponse(
            success=True,
            content_parts=["Hello", " world"],
            final_response=final_response,
            stream_errors=[],
            stream_position=11,
        )

        assert response.success is True
        assert response.content_parts == ["Hello", " world"]
        assert response.final_response == final_response
        assert len(response.stream_errors) == 0
        assert response.stream_position == 11

    def test_failed_streaming_response_creation(self) -> None:
        """Test creation of failed StreamingResponse."""
        stream_error = Exception("Streaming error")

        response = StreamingResponse(success=False, stream_errors=[stream_error])

        assert response.success is False
        assert len(response.content_parts) == 0
        assert response.final_response is None
        assert len(response.stream_errors) == 1
        assert response.stream_position == 0

    def test_get_full_content(self) -> None:
        """Test getting full content from streaming parts."""
        response = StreamingResponse(success=True, content_parts=["Hello", " ", "world", "!"])

        full_content = response.get_full_content()

        assert full_content == "Hello world!"

    def test_get_full_content_empty(self) -> None:
        """Test getting full content when no parts exist."""
        response = StreamingResponse(success=True, content_parts=[])

        full_content = response.get_full_content()

        assert full_content == ""

    def test_get_content_parts(self) -> None:
        """Test getting content parts."""
        parts = ["Hello", " world"]
        response = StreamingResponse(success=True, content_parts=parts)

        result_parts = response.get_content_parts()

        assert result_parts == parts
        assert result_parts is not response.content_parts  # Should be a copy

    def test_add_content_part(self) -> None:
        """Test adding content part to streaming response."""
        response = StreamingResponse(success=True)

        response.add_content_part("Hello")
        response.add_content_part(" world")

        assert response.content_parts == ["Hello", " world"]
        assert response.stream_position == 11

    def test_add_stream_error(self) -> None:
        """Test adding stream error."""
        response = StreamingResponse(success=True)
        error = Exception("Stream error")

        response.add_stream_error(error)

        assert len(response.stream_errors) == 1
        assert response.stream_errors[0] == error

    def test_get_stream_errors(self) -> None:
        """Test getting stream errors."""
        error1 = Exception("Error 1")
        error2 = Exception("Error 2")
        errors = [error1, error2]

        response = StreamingResponse(success=False, stream_errors=errors)

        result_errors = response.get_stream_errors()

        assert result_errors == errors
        assert result_errors is not response.stream_errors  # Should be a copy

    def test_streaming_response_repr_success(self) -> None:
        """Test string representation of successful StreamingResponse."""
        response = StreamingResponse(
            success=True, content_parts=["Hello", " world"], stream_position=11
        )
        # Mark streaming as completed to show final status
        response._stream_completed = True

        repr_str = repr(response)

        assert "SUCCESS" in repr_str
        assert "parts=2" in repr_str
        assert "position=11" in repr_str
        assert "errors=0" in repr_str

    def test_streaming_response_repr_failed(self) -> None:
        """Test string representation of failed StreamingResponse."""
        response = StreamingResponse(success=False, stream_errors=[Exception("Error")])
        # Mark streaming as completed to show final status
        response._stream_completed = True

        repr_str = repr(response)

        assert "FAILED" in repr_str
        assert "parts=0" in repr_str
        assert "position=0" in repr_str
        assert "errors=1" in repr_str

    def test_streaming_response_repr_streaming(self) -> None:
        """Test string representation of StreamingResponse while streaming is in progress."""
        response = StreamingResponse(success=False, content_parts=["Hello"], stream_position=5)
        # Don't mark as completed - should show "STREAMING" status

        repr_str = repr(response)

        assert "STREAMING" in repr_str
        assert "parts=1" in repr_str
        assert "position=5" in repr_str
        assert "errors=0" in repr_str
