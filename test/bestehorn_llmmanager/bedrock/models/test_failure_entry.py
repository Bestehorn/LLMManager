"""
Unit tests for FailureEntry dataclass.
"""

from datetime import datetime

from bestehorn_llmmanager.bedrock.models.parallel_structures import FailureEntry


class TestFailureEntry:
    """Test suite for FailureEntry dataclass."""

    def test_failure_entry_creation(self):
        """Test basic FailureEntry creation with all fields."""
        exception = ValueError("Test error message")
        timestamp = datetime.now()

        entry = FailureEntry(
            attempt_number=1,
            timestamp=timestamp,
            exception=exception,
            exception_type="ValueError",
            error_message="Test error message",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
        )

        assert entry.attempt_number == 1
        assert entry.timestamp == timestamp
        assert entry.exception is exception
        assert entry.exception_type == "ValueError"
        assert entry.error_message == "Test error message"
        assert entry.model == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert entry.region == "us-east-1"

    def test_failure_entry_optional_fields(self):
        """Test FailureEntry creation with optional fields as None."""
        exception = RuntimeError("Test error")
        timestamp = datetime.now()

        entry = FailureEntry(
            attempt_number=2,
            timestamp=timestamp,
            exception=exception,
            exception_type="RuntimeError",
            error_message="Test error",
        )

        assert entry.attempt_number == 2
        assert entry.model is None
        assert entry.region is None

    def test_to_dict_excludes_exception(self):
        """Test that to_dict() excludes the exception instance."""
        exception = ValueError("Test error message")
        timestamp = datetime(2025, 10, 21, 13, 45, 30, 123456)

        entry = FailureEntry(
            attempt_number=3,
            timestamp=timestamp,
            exception=exception,
            exception_type="ValueError",
            error_message="Test error message",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-west-2",
        )

        result = entry.to_dict()

        # Verify exception is not included
        assert "exception" not in result

        # Verify other fields are included
        assert result["attempt_number"] == 3
        assert result["timestamp"] == "2025-10-21T13:45:30.123456"
        assert result["exception_type"] == "ValueError"
        assert result["error_message"] == "Test error message"
        assert result["model"] == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert result["region"] == "us-west-2"

    def test_to_dict_with_none_fields(self):
        """Test to_dict() with None optional fields."""
        exception = RuntimeError("Error")
        timestamp = datetime.now()

        entry = FailureEntry(
            attempt_number=1,
            timestamp=timestamp,
            exception=exception,
            exception_type="RuntimeError",
            error_message="Error",
        )

        result = entry.to_dict()

        assert result["model"] is None
        assert result["region"] is None

    def test_repr_format(self):
        """Test __repr__() string representation."""
        exception = ValueError(
            "This is a very long error message that should be truncated in the repr"
        )
        timestamp = datetime.now()

        entry = FailureEntry(
            attempt_number=5,
            timestamp=timestamp,
            exception=exception,
            exception_type="ValueError",
            error_message="This is a very long error message that should be truncated in the repr",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="eu-west-1",
        )

        repr_str = repr(entry)

        # Verify format
        assert "FailureEntry(" in repr_str
        assert "attempt=5" in repr_str
        assert "type=ValueError" in repr_str
        assert "model=anthropic.claude-3-sonnet-20240229-v1:0" in repr_str
        assert "region=eu-west-1" in repr_str

        # Verify message is truncated to 50 chars
        assert "..." in repr_str

    def test_repr_short_message(self):
        """Test __repr__() with a short error message."""
        exception = ValueError("Short error")
        timestamp = datetime.now()

        entry = FailureEntry(
            attempt_number=1,
            timestamp=timestamp,
            exception=exception,
            exception_type="ValueError",
            error_message="Short error",
            model="model-1",
            region="us-east-1",
        )

        repr_str = repr(entry)

        assert "message='Short error...'" in repr_str

    def test_different_exception_types(self):
        """Test FailureEntry with various exception types."""
        exception_types = [
            (ValueError("value error"), "ValueError"),
            (RuntimeError("runtime error"), "RuntimeError"),
            (TimeoutError("timeout"), "TimeoutError"),
            (ConnectionError("connection failed"), "ConnectionError"),
        ]

        for exception, exc_type in exception_types:
            entry = FailureEntry(
                attempt_number=1,
                timestamp=datetime.now(),
                exception=exception,
                exception_type=exc_type,
                error_message=str(exception),
            )

            assert entry.exception_type == exc_type
            assert entry.exception is exception

    def test_multiple_attempts_tracking(self):
        """Test that attempt numbers can be tracked correctly."""
        exception = ValueError("Test")
        timestamp = datetime.now()

        # Simulate multiple retry attempts
        attempts = []
        for i in range(1, 6):
            entry = FailureEntry(
                attempt_number=i,
                timestamp=timestamp,
                exception=exception,
                exception_type="ValueError",
                error_message=f"Attempt {i} failed",
            )
            attempts.append(entry)

        # Verify each attempt has correct number
        for i, entry in enumerate(attempts, start=1):
            assert entry.attempt_number == i
            assert entry.error_message == f"Attempt {i} failed"

    def test_timestamp_serialization(self):
        """Test that timestamp is properly serialized to ISO format."""
        exception = ValueError("Test")
        timestamp = datetime(2025, 10, 21, 10, 30, 45, 123456)

        entry = FailureEntry(
            attempt_number=1,
            timestamp=timestamp,
            exception=exception,
            exception_type="ValueError",
            error_message="Test",
        )

        result = entry.to_dict()

        # Verify ISO format
        assert result["timestamp"] == "2025-10-21T10:30:45.123456"
        assert isinstance(result["timestamp"], str)
