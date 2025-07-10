"""
Unit tests for streaming display utilities.

Tests the StreamingDisplayFormatter class and convenience functions for displaying
streaming responses with rich formatting and metadata.
"""

import logging
import sys
from io import StringIO
from unittest.mock import Mock, patch

from bestehorn_llmmanager.bedrock.models.bedrock_response import StreamingResponse
from bestehorn_llmmanager.util.streaming_display import (
    StreamingDisplayFormatter,
    display_recovery_information,
    display_streaming_response,
    display_streaming_summary,
)


class TestStreamingDisplayFormatter:
    """Test cases for StreamingDisplayFormatter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = StreamingDisplayFormatter()
        self.captured_output = StringIO()

    def teardown_method(self):
        """Clean up after tests."""
        self.captured_output.close()

    def _capture_print_output(self, func, *args, **kwargs):
        """Capture print output from a function call."""
        old_stdout = sys.stdout
        sys.stdout = self.captured_output
        try:
            func(*args, **kwargs)
            return self.captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_init_default_logger(self):
        """Test StreamingDisplayFormatter initialization with default logger."""
        formatter = StreamingDisplayFormatter()
        assert formatter._logger is not None
        assert isinstance(formatter._logger, logging.Logger)

    def test_init_custom_logger(self):
        """Test StreamingDisplayFormatter initialization with custom logger."""
        custom_logger = logging.getLogger("test_logger")
        formatter = StreamingDisplayFormatter(logger=custom_logger)
        assert formatter._logger is custom_logger

    def test_display_streaming_response_successful(self):
        """Test displaying a successful streaming response."""
        # Create mock successful streaming response
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Claude 3.5 Sonnet v2"
        streaming_response.region_used = "us-east-1"
        streaming_response.access_method_used = "direct"
        streaming_response.total_duration_ms = 1500.5
        streaming_response.api_latency_ms = 800.2
        streaming_response.content_parts = ["Hello", " world", "!"]
        streaming_response.stream_position = 12
        streaming_response.stop_reason = "end_turn"
        streaming_response.current_message_role = "assistant"
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = "Hello world!"
        streaming_response.get_usage.return_value = {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }
        streaming_response.get_metrics.return_value = {
            "time_to_first_token_ms": 500.1,
            "time_to_last_token_ms": 1400.3,
            "token_generation_duration_ms": 900.2,
        }

        output = self._capture_print_output(
            self.formatter.display_streaming_response,
            streaming_response=streaming_response,
            title="Test Streaming Response",
        )

        # Verify expected content in output
        assert "Test Streaming Response" in output
        assert "✅ Success: True" in output
        assert "🤖 Model: Claude 3.5 Sonnet v2" in output
        assert "🌍 Region: us-east-1" in output
        assert "🔗 Access Method: direct" in output
        assert "Total Duration: 1500.50ms" in output
        assert "API Latency: 800.20ms" in output
        assert "📦 Content Parts: 3" in output
        assert "📏 Stream Position: 12" in output
        assert "🛑 Stop Reason: end_turn" in output
        assert "🎭 Message Role: assistant" in output
        assert "Hello world!" in output
        assert "Input tokens: 10" in output
        assert "Output tokens: 20" in output
        assert "Total tokens: 30" in output
        assert "Time to First Token: 500.10ms" in output
        assert "Time to Last Token: 1400.30ms" in output
        assert "Token Generation Duration: 900.20ms" in output

    def test_display_streaming_response_failed(self):
        """Test displaying a failed streaming response."""
        # Create mock failed streaming response
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = False
        streaming_response.stream_errors = [Exception("Test error"), ValueError("Another error")]
        streaming_response.warnings = ["Test warning"]
        streaming_response.get_full_content.return_value = "Partial content"
        streaming_response.content_parts = ["Partial"]

        output = self._capture_print_output(
            self.formatter.display_streaming_response,
            streaming_response=streaming_response,
            title="Failed Response",
            show_errors=True,
        )

        # Verify expected content in output
        assert "Failed Response" in output
        assert "❌ Success: False" in output
        assert "🔄 Stream Errors: 2" in output
        assert "Exception: Test error" in output
        assert "ValueError: Another error" in output
        assert "📝 Partial content received: 15 characters" in output
        assert "📦 Content parts: 1" in output
        assert "⚠️ Warnings:" in output
        assert "Test warning" in output

    def test_display_streaming_response_with_none_values(self):
        """Test displaying a streaming response with None values."""
        # Create mock streaming response with None values
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = None
        streaming_response.region_used = None
        streaming_response.access_method_used = None
        streaming_response.total_duration_ms = None
        streaming_response.api_latency_ms = None
        streaming_response.content_parts = []
        streaming_response.stream_position = 0
        streaming_response.stop_reason = None
        streaming_response.current_message_role = None
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = ""
        streaming_response.get_usage.return_value = None
        streaming_response.get_metrics.return_value = None

        output = self._capture_print_output(
            self.formatter.display_streaming_response, streaming_response=streaming_response
        )

        # Verify None values are handled gracefully
        assert "🤖 Model: None" in output
        assert "🌍 Region: None" in output
        assert "🔗 Access Method: None" in output
        assert "🛑 Stop Reason: N/A" in output
        assert "🎭 Message Role: N/A" in output

    def test_display_streaming_summary(self):
        """Test displaying a streaming response summary."""
        # Create mock streaming response
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Claude 3 Haiku"
        streaming_response.region_used = "us-west-2"
        streaming_response.content_parts = ["Test", " content"]
        streaming_response.total_duration_ms = 2000.0
        streaming_response.get_full_content.return_value = "Test content"

        output = self._capture_print_output(
            self.formatter.display_streaming_summary,
            streaming_response=streaming_response,
            title="Test Summary",
        )

        # Verify expected content in output
        assert "Test Summary" in output
        assert "✅ Success: True" in output
        assert "🤖 Model: Claude 3 Haiku" in output
        assert "🌍 Region: us-west-2" in output
        assert "📝 Content: 12 characters, 2 parts" in output
        assert "⏱️ Duration: 2000.0ms" in output

    def test_display_recovery_information_enabled(self):
        """Test displaying recovery information when recovery is enabled."""
        # Create mock streaming response with recovery info
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.get_recovery_info.return_value = {
            "recovery_enabled": True,
            "total_exceptions": 2,
            "recovered_exceptions": 1,
            "target_switches": 1,
            "final_model": "Claude 3 Haiku",
            "final_region": "us-west-2",
        }
        streaming_response.get_mid_stream_exceptions.return_value = [
            {
                "error_type": "ThrottlingException",
                "position": 0,
                "model": "Claude 3.5 Sonnet v2",
                "region": "us-east-1",
                "recovered": True,
            },
            {
                "error_type": "ServiceException",
                "position": 100,
                "model": "Claude 3 Haiku",
                "region": "us-west-2",
                "recovered": False,
            },
        ]

        output = self._capture_print_output(
            self.formatter.display_recovery_information,
            streaming_response=streaming_response,
            title="Recovery Test",
        )

        # Verify expected content in output
        assert "Recovery Test" in output
        assert "Total exceptions: 2" in output
        assert "Recovered exceptions: 1" in output
        assert "Target switches: 1" in output
        assert "ThrottlingException at position 0" in output
        assert "✅ recovered" in output
        assert "ServiceException at position 100" in output
        assert "❌ failed" in output
        assert "🔄 Final target: Claude 3 Haiku in us-west-2" in output

    def test_display_recovery_information_disabled(self):
        """Test displaying recovery information when recovery is disabled."""
        # Create mock streaming response without recovery
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.get_recovery_info.return_value = {"recovery_enabled": False}

        output = self._capture_print_output(
            self.formatter.display_recovery_information, streaming_response=streaming_response
        )

        # Should not display anything when recovery is disabled
        assert output.strip() == ""

    def test_display_streaming_response_content_truncation(self):
        """Test content truncation in streaming response display."""
        # Create mock streaming response with long content
        long_content = "A" * 1000
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Test Model"
        streaming_response.region_used = "test-region"
        streaming_response.access_method_used = "direct"
        streaming_response.total_duration_ms = 1000.0
        streaming_response.api_latency_ms = None
        streaming_response.content_parts = ["A" * 1000]
        streaming_response.stream_position = 1000
        streaming_response.stop_reason = "end_turn"
        streaming_response.current_message_role = "assistant"
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = long_content
        streaming_response.get_usage.return_value = None
        streaming_response.get_metrics.return_value = None

        output = self._capture_print_output(
            self.formatter.display_streaming_response,
            streaming_response=streaming_response,
            content_preview_length=100,
        )

        # Verify content is truncated
        assert "A" * 100 + "..." in output
        assert "[Content truncated - showing first 100 of 1000 characters]" in output

    def test_display_streaming_response_selective_sections(self):
        """Test displaying streaming response with selective sections."""
        # Create mock streaming response
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Test Model"
        streaming_response.region_used = "test-region"
        streaming_response.access_method_used = "direct"
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = "Test content"
        streaming_response.get_usage.return_value = {"input_tokens": 10}
        streaming_response.get_metrics.return_value = {"total_duration_ms": 1000}

        output = self._capture_print_output(
            self.formatter.display_streaming_response,
            streaming_response=streaming_response,
            show_content=False,
            show_metadata=False,
            show_timing=False,
            show_usage=False,
        )

        # Should only show success status
        assert "✅ Success: True" in output
        assert "Test content" not in output
        assert "Test Model" not in output
        assert "input_tokens" not in output
        assert "total_duration_ms" not in output


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.captured_output = StringIO()

    def teardown_method(self):
        """Clean up after tests."""
        self.captured_output.close()

    def _capture_print_output(self, func, *args, **kwargs):
        """Capture print output from a function call."""
        old_stdout = sys.stdout
        sys.stdout = self.captured_output
        try:
            func(*args, **kwargs)
            return self.captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_display_streaming_response_convenience(self):
        """Test the display_streaming_response convenience function."""
        # Create mock streaming response
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Test Model"
        streaming_response.region_used = "test-region"
        streaming_response.access_method_used = "direct"
        streaming_response.total_duration_ms = 1000.0
        streaming_response.api_latency_ms = None
        streaming_response.content_parts = []
        streaming_response.stream_position = 0
        streaming_response.stop_reason = "end_turn"
        streaming_response.current_message_role = "assistant"
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = ""
        streaming_response.get_usage.return_value = None
        streaming_response.get_metrics.return_value = None

        output = self._capture_print_output(
            display_streaming_response,
            streaming_response=streaming_response,
            title="Convenience Test",
        )

        # Verify the function works
        assert "Convenience Test" in output
        assert "✅ Success: True" in output
        assert "🤖 Model: Test Model" in output

    def test_display_streaming_summary_convenience(self):
        """Test the display_streaming_summary convenience function."""
        # Create mock streaming response
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Test Model"
        streaming_response.region_used = "test-region"
        streaming_response.content_parts = ["Test"]
        streaming_response.total_duration_ms = 1000.0
        streaming_response.get_full_content.return_value = "Test"

        output = self._capture_print_output(
            display_streaming_summary, streaming_response=streaming_response, title="Summary Test"
        )

        # Verify the function works
        assert "Summary Test" in output
        assert "✅ Success: True" in output
        assert "🤖 Model: Test Model" in output
        assert "📝 Content: 4 characters, 1 parts" in output

    def test_display_recovery_information_convenience(self):
        """Test the display_recovery_information convenience function."""
        # Create mock streaming response
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.get_recovery_info.return_value = {
            "recovery_enabled": True,
            "total_exceptions": 1,
            "recovered_exceptions": 1,
            "target_switches": 1,
        }
        streaming_response.get_mid_stream_exceptions.return_value = []

        output = self._capture_print_output(
            display_recovery_information,
            streaming_response=streaming_response,
            title="Recovery Test",
        )

        # Verify the function works
        assert "Recovery Test" in output
        assert "Total exceptions: 1" in output
        assert "Recovered exceptions: 1" in output

    @patch("bestehorn_llmmanager.util.streaming_display.StreamingDisplayFormatter")
    def test_convenience_functions_use_formatter(self, mock_formatter_class):
        """Test that convenience functions create and use StreamingDisplayFormatter."""
        mock_formatter = Mock()
        mock_formatter_class.return_value = mock_formatter

        streaming_response = Mock(spec=StreamingResponse)

        # Test display_streaming_response
        display_streaming_response(streaming_response, title="Test")
        mock_formatter_class.assert_called_once()
        mock_formatter.display_streaming_response.assert_called_once_with(
            streaming_response=streaming_response, title="Test"
        )

        # Reset mocks
        mock_formatter_class.reset_mock()
        mock_formatter.reset_mock()

        # Test display_streaming_summary
        display_streaming_summary(streaming_response, title="Summary Test")
        mock_formatter_class.assert_called_once()
        mock_formatter.display_streaming_summary.assert_called_once_with(
            streaming_response=streaming_response, title="Summary Test"
        )

        # Reset mocks
        mock_formatter_class.reset_mock()
        mock_formatter.reset_mock()

        # Test display_recovery_information
        display_recovery_information(streaming_response, title="Recovery Test")
        mock_formatter_class.assert_called_once()
        mock_formatter.display_recovery_information.assert_called_once_with(
            streaming_response=streaming_response, title="Recovery Test"
        )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = StreamingDisplayFormatter()
        self.captured_output = StringIO()

    def teardown_method(self):
        """Clean up after tests."""
        self.captured_output.close()

    def _capture_print_output(self, func, *args, **kwargs):
        """Capture print output from a function call."""
        old_stdout = sys.stdout
        sys.stdout = self.captured_output
        try:
            func(*args, **kwargs)
            return self.captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_empty_content_handling(self):
        """Test handling of empty content."""
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Test Model"
        streaming_response.region_used = "test-region"
        streaming_response.access_method_used = "direct"
        streaming_response.total_duration_ms = 1000.0
        streaming_response.api_latency_ms = None
        streaming_response.content_parts = []
        streaming_response.stream_position = 0
        streaming_response.stop_reason = "end_turn"
        streaming_response.current_message_role = "assistant"
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = ""
        streaming_response.get_usage.return_value = None
        streaming_response.get_metrics.return_value = None

        output = self._capture_print_output(
            self.formatter.display_streaming_response, streaming_response=streaming_response
        )

        # Should handle empty content gracefully
        assert "✅ Success: True" in output
        assert "📦 Content Parts: 0" in output
        # Content section should not appear for empty content
        assert "💬 Streamed Content" not in output

    def test_missing_usage_and_metrics(self):
        """Test handling when usage and metrics are not available."""
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Test Model"
        streaming_response.region_used = "test-region"
        streaming_response.access_method_used = "direct"
        streaming_response.total_duration_ms = None
        streaming_response.api_latency_ms = None
        streaming_response.content_parts = ["Test"]
        streaming_response.stream_position = 4
        streaming_response.stop_reason = "end_turn"
        streaming_response.current_message_role = "assistant"
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = "Test"
        streaming_response.get_usage.return_value = None
        streaming_response.get_metrics.return_value = None

        output = self._capture_print_output(
            self.formatter.display_streaming_response, streaming_response=streaming_response
        )

        # Should handle missing data gracefully
        assert "✅ Success: True" in output
        assert "📊 Token Usage:" not in output
        assert "⏱️ Performance Metrics:" not in output

    def test_cache_token_information(self):
        """Test display of cache token information."""
        streaming_response = Mock(spec=StreamingResponse)
        streaming_response.success = True
        streaming_response.model_used = "Test Model"
        streaming_response.region_used = "test-region"
        streaming_response.access_method_used = "direct"
        streaming_response.total_duration_ms = 1000.0
        streaming_response.api_latency_ms = None
        streaming_response.content_parts = ["Test"]
        streaming_response.stream_position = 4
        streaming_response.stop_reason = "end_turn"
        streaming_response.current_message_role = "assistant"
        streaming_response.warnings = []
        streaming_response.get_full_content.return_value = "Test"
        streaming_response.get_usage.return_value = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cache_read_tokens": 25,
            "cache_write_tokens": 10,
        }
        streaming_response.get_metrics.return_value = None

        output = self._capture_print_output(
            self.formatter.display_streaming_response, streaming_response=streaming_response
        )

        # Should display cache information
        assert "📊 Token Usage:" in output
        assert "Input tokens: 100" in output
        assert "Output tokens: 50" in output
        assert "Total tokens: 150" in output
        assert "Cache read tokens: 25" in output
        assert "Cache write tokens: 10" in output
