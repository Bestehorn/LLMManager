"""
Exception classes for parallel processing functionality in LLM Manager system.
Provides specialized exceptions for parallel execution errors and validation failures.
"""

from typing import Any, Dict, List, Optional

from ..models.parallel_structures import BedrockConverseRequest
from .llm_manager_exceptions import LLMManagerError


class ParallelProcessingError(LLMManagerError):
    """Base exception for parallel processing errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)


class RequestIdCollisionError(ParallelProcessingError):
    """
    Exception raised when request ID collisions are detected.

    This exception contains detailed information about which request IDs
    collided and the associated request objects for debugging.
    """

    def __init__(
        self,
        duplicated_ids: Dict[str, List[BedrockConverseRequest]],
        details: Optional[Dict[str, Any]] = None,
    ):
        self.duplicated_ids = duplicated_ids

        # Create summary of collisions for error message
        collision_summary = []
        for req_id, requests in duplicated_ids.items():
            collision_summary.append(f"ID '{req_id}': {len(requests)} requests")

        message = f"Request ID collisions detected: {', '.join(collision_summary)}"

        # Add collision details if not provided
        if details is None and duplicated_ids:
            details = {
                "collision_count": len(duplicated_ids),
                "total_colliding_requests": sum(len(reqs) for reqs in duplicated_ids.values()),
                "collision_ids": list(duplicated_ids.keys()),
            }

        super().__init__(message=message, details=details)

    def get_duplicated_ids(self) -> Dict[str, List[BedrockConverseRequest]]:
        """
        Get dictionary of duplicated IDs and their associated requests.

        Returns:
            Dictionary mapping request_id to list of requests with that ID
        """
        return self.duplicated_ids.copy()

    def get_collision_count(self) -> int:
        """
        Get total number of ID collisions.

        Returns:
            Number of unique IDs that had collisions
        """
        return len(self.duplicated_ids)

    def get_total_colliding_requests(self) -> int:
        """
        Get total number of requests involved in collisions.

        Returns:
            Total count of requests with duplicate IDs
        """
        return sum(len(reqs) for reqs in self.duplicated_ids.values())


class ParallelExecutionError(ParallelProcessingError):
    """
    Exception raised when parallel execution fails.

    Contains information about failed requests and execution statistics.
    """

    def __init__(
        self,
        message: str,
        failed_requests: List[str],
        total_requests: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.failed_requests = failed_requests
        self.total_requests = total_requests

        # Add execution details if not provided
        if details is None:
            details = {
                "failed_request_count": len(failed_requests),
                "total_request_count": total_requests,
                "success_rate": (
                    ((total_requests - len(failed_requests)) / total_requests * 100)
                    if total_requests > 0
                    else 0.0
                ),
                "failed_request_ids": failed_requests,
            }

        super().__init__(message=message, details=details)

    def get_failed_requests(self) -> List[str]:
        """
        Get list of failed request IDs.

        Returns:
            List of request IDs that failed
        """
        return self.failed_requests.copy()

    def get_failure_rate(self) -> float:
        """
        Get failure rate as percentage.

        Returns:
            Failure rate (0.0-100.0)
        """
        if self.total_requests == 0:
            return 0.0
        return (len(self.failed_requests) / self.total_requests) * 100.0

    def get_success_rate(self) -> float:
        """
        Get success rate as percentage.

        Returns:
            Success rate (0.0-100.0)
        """
        return 100.0 - self.get_failure_rate()


class RegionDistributionError(ParallelProcessingError):
    """
    Exception raised when region distribution fails.

    This can occur when there are insufficient regions available
    or when region assignment constraints cannot be satisfied.
    """

    def __init__(
        self,
        message: str,
        requested_regions: int,
        available_regions: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.requested_regions = requested_regions
        self.available_regions = available_regions

        # Add distribution details if not provided
        if details is None:
            details = {
                "requested_regions": requested_regions,
                "available_regions": available_regions,
                "shortage": max(0, requested_regions - available_regions),
            }

        super().__init__(message=message, details=details)

    def get_shortage(self) -> int:
        """
        Get the shortage of regions.

        Returns:
            Number of additional regions needed (0 if sufficient)
        """
        return max(0, self.requested_regions - self.available_regions)


class ParallelConfigurationError(ParallelProcessingError):
    """
    Exception raised when parallel processing configuration is invalid.

    This includes issues with concurrency limits, timeout values,
    and other configuration parameters.
    """

    def __init__(
        self,
        message: str,
        invalid_parameter: Optional[str] = None,
        provided_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.invalid_parameter = invalid_parameter
        self.provided_value = provided_value

        # Add configuration details if not provided
        if details is None and invalid_parameter is not None:
            details = {"invalid_parameter": invalid_parameter, "provided_value": provided_value}

        super().__init__(message=message, details=details)

    def get_invalid_parameter(self) -> Optional[str]:
        """
        Get the name of the invalid parameter.

        Returns:
            Parameter name that caused the error, None if not specified
        """
        return self.invalid_parameter

    def get_provided_value(self) -> Optional[Any]:
        """
        Get the invalid value that was provided.

        Returns:
            The value that caused the error, None if not specified
        """
        return self.provided_value


class RequestTimeoutError(ParallelProcessingError):
    """
    Exception raised when a request times out during parallel execution.

    Contains information about the timed-out request and duration.
    """

    def __init__(
        self,
        message: str,
        request_id: str,
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.request_id = request_id
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds

        # Add timeout details if not provided
        if details is None:
            details = {
                "request_id": request_id,
                "timeout_seconds": timeout_seconds,
                "elapsed_seconds": elapsed_seconds,
            }

        super().__init__(message=message, details=details)

    def get_request_id(self) -> str:
        """
        Get the ID of the timed-out request.

        Returns:
            Request ID
        """
        return self.request_id

    def get_timeout_duration(self) -> float:
        """
        Get the configured timeout duration.

        Returns:
            Timeout duration in seconds
        """
        return self.timeout_seconds

    def get_elapsed_time(self) -> Optional[float]:
        """
        Get the actual elapsed time before timeout.

        Returns:
            Elapsed time in seconds, None if not available
        """
        return self.elapsed_seconds


class RequestValidationError(ParallelProcessingError):
    """
    Exception raised when request validation fails.

    This can occur during request structure validation or
    when checking request parameters before parallel execution.
    """

    def __init__(
        self,
        message: str,
        request_id: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.request_id = request_id
        self.validation_errors = validation_errors or []

        # Add validation details if not provided
        if details is None:
            details = {
                "request_id": request_id,
                "validation_error_count": len(self.validation_errors),
                "validation_errors": self.validation_errors,
            }

        super().__init__(message=message, details=details)

    def get_request_id(self) -> Optional[str]:
        """
        Get the ID of the request that failed validation.

        Returns:
            Request ID, None if not specified
        """
        return self.request_id

    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation error messages.

        Returns:
            List of validation error descriptions
        """
        return self.validation_errors.copy()

    def get_validation_error_count(self) -> int:
        """
        Get count of validation errors.

        Returns:
            Number of validation errors
        """
        return len(self.validation_errors)
