"""
Custom exceptions for LLM Manager system.
Provides a hierarchy of exceptions for different error conditions.
"""

from typing import Any, Dict, Final, List, Optional


class ExceptionDetailFields:
    """Constants for exception detail field names following coding standards."""

    INVALID_CONFIG: Final[str] = "invalid_config"
    AUTH_TYPE: Final[str] = "auth_type"
    REGION: Final[str] = "region"
    MODEL_ID: Final[str] = "model_id"
    ACCESS_METHOD: Final[str] = "access_method"
    ATTEMPTS_MADE: Final[str] = "attempts_made"
    LAST_ERRORS: Final[str] = "last_errors"
    MODELS_TRIED: Final[str] = "models_tried"
    REGIONS_TRIED: Final[str] = "regions_tried"
    VALIDATION_ERRORS: Final[str] = "validation_errors"
    INVALID_FIELDS: Final[str] = "invalid_fields"
    STREAM_POSITION: Final[str] = "stream_position"
    PARTIAL_CONTENT: Final[str] = "partial_content"
    CONTENT_TYPE: Final[str] = "content_type"
    CONTENT_SIZE: Final[str] = "content_size"
    MAX_ALLOWED_SIZE: Final[str] = "max_allowed_size"


class LLMManagerError(Exception):
    """Base exception for all LLM Manager operations."""

    message: str
    details: Optional[Dict[str, Any]]

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize LLM Manager error.

        Args:
            message: Error message
            details: Optional additional error details (None when no details available)
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def _has_details(self) -> bool:
        """
        Helper method to check if details are present.

        Returns:
            True if details are available, False otherwise
        """
        return self.details is not None

    def __repr__(self) -> str:
        """Return repr string for the error."""
        return f"{self.__class__.__name__}(message='{self.message}', details={self.details})"

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self._has_details():
            return f"{self.message}. Details: {self.details}"
        return self.message


class ConfigurationError(LLMManagerError):
    """Raised when LLM Manager configuration is invalid."""

    invalid_config: Optional[Dict[str, Any]]

    def __init__(self, message: str, invalid_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize configuration error.

        Args:
            message: Error message
            invalid_config: The invalid configuration that caused the error
        """
        details = self._build_configuration_details(invalid_config=invalid_config)
        super().__init__(message=message, details=details)
        self.invalid_config = invalid_config

    def _build_configuration_details(
        self, invalid_config: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Build details dictionary for configuration errors.

        Args:
            invalid_config: The invalid configuration data

        Returns:
            Details dictionary if meaningful data available, None otherwise
        """
        if invalid_config is not None:
            return {ExceptionDetailFields.INVALID_CONFIG: invalid_config}
        return None


class AuthenticationError(LLMManagerError):
    """Raised when authentication fails."""

    auth_type: Optional[str]
    region: Optional[str]

    def __init__(
        self, message: str, auth_type: Optional[str] = None, region: Optional[str] = None
    ) -> None:
        """
        Initialize authentication error.

        Args:
            message: Error message
            auth_type: Type of authentication that failed
            region: AWS region where authentication failed
        """
        details = self._build_authentication_details(auth_type=auth_type, region=region)
        super().__init__(message=message, details=details)
        self.auth_type = auth_type
        self.region = region

    def _build_authentication_details(
        self, auth_type: Optional[str], region: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Build details dictionary for authentication errors.

        Args:
            auth_type: Type of authentication that failed
            region: AWS region where authentication failed

        Returns:
            Details dictionary if meaningful data available, None otherwise
        """
        if auth_type or region:
            details: Dict[str, Any] = {}
            if auth_type:
                details[ExceptionDetailFields.AUTH_TYPE] = auth_type
            if region:
                details[ExceptionDetailFields.REGION] = region
            return details
        return None


class ModelAccessError(LLMManagerError):
    """Raised when model access fails."""

    model_id: Optional[str]
    region: Optional[str]
    access_method: Optional[str]

    def __init__(
        self,
        message: str,
        model_id: Optional[str] = None,
        region: Optional[str] = None,
        access_method: Optional[str] = None,
    ) -> None:
        """
        Initialize model access error.

        Args:
            message: Error message
            model_id: Model ID that failed to access
            region: AWS region where access failed
            access_method: Access method that was attempted (direct/cris)
        """
        details = self._build_model_access_details(
            model_id=model_id, region=region, access_method=access_method
        )
        super().__init__(message=message, details=details)
        self.model_id = model_id
        self.region = region
        self.access_method = access_method

    def _build_model_access_details(
        self, model_id: Optional[str], region: Optional[str], access_method: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Build details dictionary for model access errors.

        Args:
            model_id: Model ID that failed to access
            region: AWS region where access failed
            access_method: Access method that was attempted

        Returns:
            Details dictionary if meaningful data available, None otherwise
        """
        if model_id or region or access_method:
            details: Dict[str, Any] = {}
            if model_id:
                details[ExceptionDetailFields.MODEL_ID] = model_id
            if region:
                details[ExceptionDetailFields.REGION] = region
            if access_method:
                details[ExceptionDetailFields.ACCESS_METHOD] = access_method
            return details
        return None


class RetryExhaustedError(LLMManagerError):
    """Raised when all retry attempts have been exhausted."""

    attempts_made: Optional[int]
    last_errors: List[Exception]
    models_tried: List[str]
    regions_tried: List[str]

    def __init__(
        self,
        message: str,
        attempts_made: Optional[int] = None,
        last_errors: Optional[List[Exception]] = None,
        models_tried: Optional[List[str]] = None,
        regions_tried: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize retry exhausted error.

        Args:
            message: Error message
            attempts_made: Number of attempts made
            last_errors: List of the last errors encountered
            models_tried: List of models that were tried
            regions_tried: List of regions that were tried
        """
        details = self._build_retry_details(
            attempts_made=attempts_made,
            last_errors=last_errors,
            models_tried=models_tried,
            regions_tried=regions_tried,
        )
        super().__init__(message=message, details=details)
        self.attempts_made = attempts_made
        self.last_errors = last_errors or []
        self.models_tried = models_tried or []
        self.regions_tried = regions_tried or []

    def _build_retry_details(
        self,
        attempts_made: Optional[int],
        last_errors: Optional[List[Exception]],
        models_tried: Optional[List[str]],
        regions_tried: Optional[List[str]],
    ) -> Optional[Dict[str, Any]]:
        """
        Build details dictionary for retry exhausted errors.

        Args:
            attempts_made: Number of attempts made
            last_errors: List of the last errors encountered
            models_tried: List of models that were tried
            regions_tried: List of regions that were tried

        Returns:
            Details dictionary if meaningful data available, None otherwise
        """
        if attempts_made is not None or last_errors or models_tried or regions_tried:
            details: Dict[str, Any] = {}
            if attempts_made is not None:
                details[ExceptionDetailFields.ATTEMPTS_MADE] = attempts_made
            if last_errors:
                details[ExceptionDetailFields.LAST_ERRORS] = [str(error) for error in last_errors]
            if models_tried:
                details[ExceptionDetailFields.MODELS_TRIED] = models_tried
            if regions_tried:
                details[ExceptionDetailFields.REGIONS_TRIED] = regions_tried
            return details
        return None


class RequestValidationError(LLMManagerError):
    """Raised when request validation fails."""

    validation_errors: List[str]
    invalid_fields: List[str]

    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None,
        invalid_fields: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize request validation error.

        Args:
            message: Error message
            validation_errors: List of validation error messages
            invalid_fields: List of field names that failed validation
        """
        details = self._build_validation_details(
            validation_errors=validation_errors, invalid_fields=invalid_fields
        )
        super().__init__(message=message, details=details)
        self.validation_errors = validation_errors or []
        self.invalid_fields = invalid_fields or []

    def _build_validation_details(
        self, validation_errors: Optional[List[str]], invalid_fields: Optional[List[str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Build details dictionary for request validation errors.

        Args:
            validation_errors: List of validation error messages
            invalid_fields: List of field names that failed validation

        Returns:
            Details dictionary if meaningful data available, None otherwise
        """
        if validation_errors or invalid_fields:
            details: Dict[str, Any] = {}
            if validation_errors:
                details[ExceptionDetailFields.VALIDATION_ERRORS] = validation_errors
            if invalid_fields:
                details[ExceptionDetailFields.INVALID_FIELDS] = invalid_fields
            return details
        return None


class StreamingError(LLMManagerError):
    """Raised when streaming operations fail."""

    stream_position: Optional[int]
    partial_content: Optional[str]

    def __init__(
        self,
        message: str,
        stream_position: Optional[int] = None,
        partial_content: Optional[str] = None,
    ) -> None:
        """
        Initialize streaming error.

        Args:
            message: Error message
            stream_position: Position in stream where error occurred
            partial_content: Partial content received before error
        """
        details = self._build_streaming_details(
            stream_position=stream_position, partial_content=partial_content
        )
        super().__init__(message=message, details=details)
        self.stream_position = stream_position
        self.partial_content = partial_content

    def _build_streaming_details(
        self, stream_position: Optional[int], partial_content: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Build details dictionary for streaming errors.

        Args:
            stream_position: Position in stream where error occurred
            partial_content: Partial content received before error

        Returns:
            Details dictionary if meaningful data available, None otherwise
        """
        if stream_position is not None or partial_content:
            details: Dict[str, Any] = {}
            if stream_position is not None:
                details[ExceptionDetailFields.STREAM_POSITION] = stream_position
            if partial_content:
                details[ExceptionDetailFields.PARTIAL_CONTENT] = partial_content
            return details
        return None


class ContentError(LLMManagerError):
    """Raised when content validation or processing fails."""

    content_type: Optional[str]
    content_size: Optional[int]
    max_allowed_size: Optional[int]

    def __init__(
        self,
        message: str,
        content_type: Optional[str] = None,
        content_size: Optional[int] = None,
        max_allowed_size: Optional[int] = None,
    ) -> None:
        """
        Initialize content error.

        Args:
            message: Error message
            content_type: Type of content that caused the error
            content_size: Size of the problematic content
            max_allowed_size: Maximum allowed size for the content type
        """
        details = self._build_content_details(
            content_type=content_type, content_size=content_size, max_allowed_size=max_allowed_size
        )
        super().__init__(message=message, details=details)
        self.content_type = content_type
        self.content_size = content_size
        self.max_allowed_size = max_allowed_size

    def _build_content_details(
        self,
        content_type: Optional[str],
        content_size: Optional[int],
        max_allowed_size: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """
        Build details dictionary for content errors.

        Args:
            content_type: Type of content that caused the error
            content_size: Size of the problematic content
            max_allowed_size: Maximum allowed size for the content type

        Returns:
            Details dictionary if meaningful data available, None otherwise
        """
        if content_type or content_size is not None or max_allowed_size is not None:
            details: Dict[str, Any] = {}
            if content_type:
                details[ExceptionDetailFields.CONTENT_TYPE] = content_type
            if content_size is not None:
                details[ExceptionDetailFields.CONTENT_SIZE] = content_size
            if max_allowed_size is not None:
                details[ExceptionDetailFields.MAX_ALLOWED_SIZE] = max_allowed_size
            return details
        return None
