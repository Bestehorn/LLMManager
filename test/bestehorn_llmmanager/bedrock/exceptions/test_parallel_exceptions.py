"""
Unit tests for parallel exception classes.
"""

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import LLMManagerError
from bestehorn_llmmanager.bedrock.exceptions.parallel_exceptions import (
    ParallelConfigurationError,
    ParallelExecutionError,
    ParallelProcessingError,
    RegionDistributionError,
    RequestIdCollisionError,
    RequestTimeoutError,
    RequestValidationError,
)
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest


class TestParallelProcessingError:
    """Test cases for ParallelProcessingError."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = ParallelProcessingError(message="Test error")
        assert str(error) == "Test error"
        assert error.details is None

    def test_init_with_message_and_details(self):
        """Test initialization with message and details."""
        details = {"key": "value", "count": 42}
        error = ParallelProcessingError(message="Test error", details=details)
        assert "Test error" in str(error)
        assert error.details == details

    def test_inheritance(self):
        """Test that ParallelProcessingError inherits from LLMManagerError."""
        error = ParallelProcessingError(message="Test error")
        assert isinstance(error, LLMManagerError)


class TestRequestIdCollisionError:
    """Test cases for RequestIdCollisionError."""

    def setup_method(self):
        """Set up test fixtures."""
        self.request1 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "request1"}]}], request_id="duplicate"
        )
        self.request2 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "request2"}]}], request_id="duplicate"
        )
        self.request3 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "request3"}]}],
            request_id="another-duplicate",
        )

        self.duplicated_ids = {
            "duplicate": [self.request1, self.request2],
            "another-duplicate": [self.request3],
        }

    def test_init_with_duplicated_ids(self):
        """Test initialization with duplicated IDs."""
        error = RequestIdCollisionError(duplicated_ids=self.duplicated_ids)

        assert "Request ID collisions detected" in str(error)
        assert "duplicate" in str(error)
        assert "another-duplicate" in str(error)
        assert error.duplicated_ids == self.duplicated_ids

    def test_init_with_custom_details(self):
        """Test initialization with custom details."""
        custom_details = {"custom_field": "custom_value"}
        error = RequestIdCollisionError(duplicated_ids=self.duplicated_ids, details=custom_details)

        assert error.details == custom_details

    def test_init_with_auto_generated_details(self):
        """Test initialization with auto-generated details."""
        error = RequestIdCollisionError(duplicated_ids=self.duplicated_ids)

        assert error.details is not None
        assert error.details["collision_count"] == 2
        assert error.details["total_colliding_requests"] == 3
        assert set(error.details["collision_ids"]) == {"duplicate", "another-duplicate"}

    def test_init_with_empty_duplicated_ids(self):
        """Test initialization with empty duplicated IDs."""
        error = RequestIdCollisionError(duplicated_ids={})

        assert "Request ID collisions detected:" in str(error)
        assert error.duplicated_ids == {}

    def test_get_duplicated_ids(self):
        """Test getting duplicated IDs."""
        error = RequestIdCollisionError(duplicated_ids=self.duplicated_ids)

        result = error.get_duplicated_ids()
        assert result == self.duplicated_ids

        # Should return a copy, not the original
        result["new_key"] = [self.request1]
        assert "new_key" not in error.duplicated_ids

    def test_get_collision_count(self):
        """Test getting collision count."""
        error = RequestIdCollisionError(duplicated_ids=self.duplicated_ids)
        assert error.get_collision_count() == 2

    def test_get_collision_count_empty(self):
        """Test getting collision count with empty duplicates."""
        error = RequestIdCollisionError(duplicated_ids={})
        assert error.get_collision_count() == 0

    def test_get_total_colliding_requests(self):
        """Test getting total colliding requests count."""
        error = RequestIdCollisionError(duplicated_ids=self.duplicated_ids)
        assert error.get_total_colliding_requests() == 3

    def test_get_total_colliding_requests_empty(self):
        """Test getting total colliding requests with empty duplicates."""
        error = RequestIdCollisionError(duplicated_ids={})
        assert error.get_total_colliding_requests() == 0

    def test_inheritance(self):
        """Test that RequestIdCollisionError inherits from ParallelProcessingError."""
        error = RequestIdCollisionError(duplicated_ids=self.duplicated_ids)
        assert isinstance(error, ParallelProcessingError)


class TestParallelExecutionError:
    """Test cases for ParallelExecutionError."""

    def test_init_with_basic_parameters(self):
        """Test initialization with basic parameters."""
        failed_requests = ["req-1", "req-2"]
        error = ParallelExecutionError(
            message="Execution failed", failed_requests=failed_requests, total_requests=5
        )

        assert "Execution failed" in str(error)
        assert error.failed_requests == failed_requests
        assert error.total_requests == 5

    def test_init_with_auto_generated_details(self):
        """Test initialization with auto-generated details."""
        failed_requests = ["req-1", "req-2"]
        error = ParallelExecutionError(
            message="Execution failed", failed_requests=failed_requests, total_requests=5
        )

        assert error.details is not None
        assert error.details["failed_request_count"] == 2
        assert error.details["total_request_count"] == 5
        assert error.details["success_rate"] == 60.0
        assert error.details["failed_request_ids"] == failed_requests

    def test_init_with_custom_details(self):
        """Test initialization with custom details."""
        custom_details = {"custom_field": "custom_value"}
        error = ParallelExecutionError(
            message="Execution failed",
            failed_requests=["req-1"],
            total_requests=3,
            details=custom_details,
        )

        assert error.details == custom_details

    def test_init_with_zero_total_requests(self):
        """Test initialization with zero total requests."""
        error = ParallelExecutionError(message="No requests", failed_requests=[], total_requests=0)

        assert error.details is not None
        assert error.details["success_rate"] == 0.0

    def test_get_failed_requests(self):
        """Test getting failed requests."""
        failed_requests = ["req-1", "req-2"]
        error = ParallelExecutionError(
            message="Execution failed", failed_requests=failed_requests, total_requests=5
        )

        result = error.get_failed_requests()
        assert result == failed_requests

        # Should return a copy, not the original
        result.append("req-3")
        assert "req-3" not in error.failed_requests

    def test_get_failure_rate(self):
        """Test getting failure rate."""
        error = ParallelExecutionError(
            message="Execution failed", failed_requests=["req-1", "req-2"], total_requests=5
        )

        assert error.get_failure_rate() == 40.0

    def test_get_failure_rate_zero_total(self):
        """Test getting failure rate with zero total requests."""
        error = ParallelExecutionError(message="No requests", failed_requests=[], total_requests=0)

        assert error.get_failure_rate() == 0.0

    def test_get_success_rate(self):
        """Test getting success rate."""
        error = ParallelExecutionError(
            message="Execution failed", failed_requests=["req-1", "req-2"], total_requests=5
        )

        assert error.get_success_rate() == 60.0

    def test_get_success_rate_all_failed(self):
        """Test getting success rate when all requests failed."""
        error = ParallelExecutionError(
            message="All failed", failed_requests=["req-1", "req-2"], total_requests=2
        )

        assert error.get_success_rate() == 0.0

    def test_inheritance(self):
        """Test that ParallelExecutionError inherits from ParallelProcessingError."""
        error = ParallelExecutionError(
            message="Execution failed", failed_requests=["req-1"], total_requests=2
        )
        assert isinstance(error, ParallelProcessingError)


class TestRegionDistributionError:
    """Test cases for RegionDistributionError."""

    def test_init_with_basic_parameters(self):
        """Test initialization with basic parameters."""
        error = RegionDistributionError(
            message="Insufficient regions", requested_regions=5, available_regions=3
        )

        assert "Insufficient regions" in str(error)
        assert error.requested_regions == 5
        assert error.available_regions == 3

    def test_init_with_auto_generated_details(self):
        """Test initialization with auto-generated details."""
        error = RegionDistributionError(
            message="Insufficient regions", requested_regions=5, available_regions=3
        )

        assert error.details is not None
        assert error.details["requested_regions"] == 5
        assert error.details["available_regions"] == 3
        assert error.details["shortage"] == 2

    def test_init_with_custom_details(self):
        """Test initialization with custom details."""
        custom_details = {"custom_field": "custom_value"}
        error = RegionDistributionError(
            message="Insufficient regions",
            requested_regions=5,
            available_regions=3,
            details=custom_details,
        )

        assert error.details == custom_details

    def test_init_with_sufficient_regions(self):
        """Test initialization when there are sufficient regions."""
        error = RegionDistributionError(
            message="Region error", requested_regions=3, available_regions=5
        )

        assert error.details is not None
        assert error.details["shortage"] == 0

    def test_get_shortage(self):
        """Test getting region shortage."""
        error = RegionDistributionError(
            message="Insufficient regions", requested_regions=5, available_regions=3
        )

        assert error.get_shortage() == 2

    def test_get_shortage_sufficient_regions(self):
        """Test getting shortage when there are sufficient regions."""
        error = RegionDistributionError(
            message="Region error", requested_regions=3, available_regions=5
        )

        assert error.get_shortage() == 0

    def test_inheritance(self):
        """Test that RegionDistributionError inherits from ParallelProcessingError."""
        error = RegionDistributionError(
            message="Region error", requested_regions=3, available_regions=2
        )
        assert isinstance(error, ParallelProcessingError)


class TestParallelConfigurationError:
    """Test cases for ParallelConfigurationError."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = ParallelConfigurationError(message="Config error")

        assert str(error) == "Config error"
        assert error.invalid_parameter is None
        assert error.provided_value is None
        assert error.details is None

    def test_init_with_parameter_info(self):
        """Test initialization with parameter information."""
        error = ParallelConfigurationError(
            message="Invalid parameter",
            invalid_parameter="max_concurrent_requests",
            provided_value=-1,
        )

        assert error.invalid_parameter == "max_concurrent_requests"
        assert error.provided_value == -1

    def test_init_with_auto_generated_details(self):
        """Test initialization with auto-generated details."""
        error = ParallelConfigurationError(
            message="Invalid parameter", invalid_parameter="timeout", provided_value=0
        )

        assert error.details is not None
        assert error.details["invalid_parameter"] == "timeout"
        assert error.details["provided_value"] == 0

    def test_init_with_custom_details(self):
        """Test initialization with custom details."""
        custom_details = {"custom_field": "custom_value"}
        error = ParallelConfigurationError(
            message="Config error",
            invalid_parameter="param",
            provided_value="value",
            details=custom_details,
        )

        assert error.details == custom_details

    def test_init_with_none_parameter_no_details_generation(self):
        """Test initialization with None parameter doesn't generate details."""
        error = ParallelConfigurationError(
            message="Config error", invalid_parameter=None, provided_value="value"
        )

        assert error.details is None

    def test_get_invalid_parameter(self):
        """Test getting invalid parameter."""
        error = ParallelConfigurationError(
            message="Invalid parameter", invalid_parameter="max_retries", provided_value=-5
        )

        assert error.get_invalid_parameter() == "max_retries"

    def test_get_invalid_parameter_none(self):
        """Test getting invalid parameter when None."""
        error = ParallelConfigurationError(message="Config error")
        assert error.get_invalid_parameter() is None

    def test_get_provided_value(self):
        """Test getting provided value."""
        error = ParallelConfigurationError(
            message="Invalid parameter", invalid_parameter="timeout", provided_value=0.5
        )

        assert error.get_provided_value() == 0.5

    def test_get_provided_value_none(self):
        """Test getting provided value when None."""
        error = ParallelConfigurationError(message="Config error")
        assert error.get_provided_value() is None

    def test_inheritance(self):
        """Test that ParallelConfigurationError inherits from ParallelProcessingError."""
        error = ParallelConfigurationError(message="Config error")
        assert isinstance(error, ParallelProcessingError)


class TestRequestTimeoutError:
    """Test cases for RequestTimeoutError."""

    def test_init_with_basic_parameters(self):
        """Test initialization with basic parameters."""
        error = RequestTimeoutError(
            message="Request timed out", request_id="req-123", timeout_seconds=30.0
        )

        assert "Request timed out" in str(error)
        assert error.request_id == "req-123"
        assert error.timeout_seconds == 30.0
        assert error.elapsed_seconds is None

    def test_init_with_elapsed_time(self):
        """Test initialization with elapsed time."""
        error = RequestTimeoutError(
            message="Request timed out",
            request_id="req-123",
            timeout_seconds=30.0,
            elapsed_seconds=35.5,
        )

        assert error.elapsed_seconds == 35.5

    def test_init_with_auto_generated_details(self):
        """Test initialization with auto-generated details."""
        error = RequestTimeoutError(
            message="Request timed out",
            request_id="req-123",
            timeout_seconds=30.0,
            elapsed_seconds=32.1,
        )

        assert error.details is not None
        assert error.details["request_id"] == "req-123"
        assert error.details["timeout_seconds"] == 30.0
        assert error.details["elapsed_seconds"] == 32.1

    def test_init_with_custom_details(self):
        """Test initialization with custom details."""
        custom_details = {"custom_field": "custom_value"}
        error = RequestTimeoutError(
            message="Request timed out",
            request_id="req-123",
            timeout_seconds=30.0,
            details=custom_details,
        )

        assert error.details == custom_details

    def test_get_request_id(self):
        """Test getting request ID."""
        error = RequestTimeoutError(
            message="Request timed out", request_id="req-456", timeout_seconds=15.0
        )

        assert error.get_request_id() == "req-456"

    def test_get_timeout_duration(self):
        """Test getting timeout duration."""
        error = RequestTimeoutError(
            message="Request timed out", request_id="req-123", timeout_seconds=45.5
        )

        assert error.get_timeout_duration() == 45.5

    def test_get_elapsed_time(self):
        """Test getting elapsed time."""
        error = RequestTimeoutError(
            message="Request timed out",
            request_id="req-123",
            timeout_seconds=30.0,
            elapsed_seconds=28.7,
        )

        assert error.get_elapsed_time() == 28.7

    def test_get_elapsed_time_none(self):
        """Test getting elapsed time when None."""
        error = RequestTimeoutError(
            message="Request timed out", request_id="req-123", timeout_seconds=30.0
        )

        assert error.get_elapsed_time() is None

    def test_inheritance(self):
        """Test that RequestTimeoutError inherits from ParallelProcessingError."""
        error = RequestTimeoutError(
            message="Request timed out", request_id="req-123", timeout_seconds=30.0
        )
        assert isinstance(error, ParallelProcessingError)


class TestRequestValidationError:
    """Test cases for RequestValidationError."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = RequestValidationError(message="Validation failed")

        assert "Validation failed" in str(error)
        assert error.request_id is None
        assert error.validation_errors == []

    def test_init_with_request_id(self):
        """Test initialization with request ID."""
        error = RequestValidationError(message="Validation failed", request_id="req-789")

        assert error.request_id == "req-789"

    def test_init_with_validation_errors(self):
        """Test initialization with validation errors."""
        validation_errors = ["Missing required field", "Invalid format"]
        error = RequestValidationError(
            message="Validation failed", validation_errors=validation_errors
        )

        assert error.validation_errors == validation_errors

    def test_init_with_auto_generated_details(self):
        """Test initialization with auto-generated details."""
        validation_errors = ["Error 1", "Error 2"]
        error = RequestValidationError(
            message="Validation failed", request_id="req-789", validation_errors=validation_errors
        )

        assert error.details is not None
        assert error.details["request_id"] == "req-789"
        assert error.details["validation_error_count"] == 2
        assert error.details["validation_errors"] == validation_errors

    def test_init_with_custom_details(self):
        """Test initialization with custom details."""
        custom_details = {"custom_field": "custom_value"}
        error = RequestValidationError(
            message="Validation failed", request_id="req-789", details=custom_details
        )

        assert error.details == custom_details

    def test_init_with_none_validation_errors(self):
        """Test initialization with None validation errors."""
        error = RequestValidationError(message="Validation failed", validation_errors=None)

        assert error.validation_errors == []

    def test_get_request_id(self):
        """Test getting request ID."""
        error = RequestValidationError(message="Validation failed", request_id="req-abc")

        assert error.get_request_id() == "req-abc"

    def test_get_request_id_none(self):
        """Test getting request ID when None."""
        error = RequestValidationError(message="Validation failed")
        assert error.get_request_id() is None

    def test_get_validation_errors(self):
        """Test getting validation errors."""
        validation_errors = ["Error A", "Error B", "Error C"]
        error = RequestValidationError(
            message="Validation failed", validation_errors=validation_errors
        )

        result = error.get_validation_errors()
        assert result == validation_errors

        # Should return a copy, not the original
        result.append("Error D")
        assert "Error D" not in error.validation_errors

    def test_get_validation_errors_empty(self):
        """Test getting validation errors when empty."""
        error = RequestValidationError(message="Validation failed")
        assert error.get_validation_errors() == []

    def test_get_validation_error_count(self):
        """Test getting validation error count."""
        validation_errors = ["Error 1", "Error 2"]
        error = RequestValidationError(
            message="Validation failed", validation_errors=validation_errors
        )

        assert error.get_validation_error_count() == 2

    def test_get_validation_error_count_empty(self):
        """Test getting validation error count when empty."""
        error = RequestValidationError(message="Validation failed")
        assert error.get_validation_error_count() == 0

    def test_inheritance(self):
        """Test that RequestValidationError inherits from ParallelProcessingError."""
        error = RequestValidationError(message="Validation failed")
        assert isinstance(error, ParallelProcessingError)
