"""
Custom exceptions for LLM Manager system.
Provides a hierarchy of exceptions for different error conditions.
"""

from typing import Any, Dict, List, Optional


class LLMManagerError(Exception):
    """Base exception for all LLM Manager operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize LLM Manager error.
        
        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __repr__(self) -> str:
        """Return repr string for the error."""
        return f"{self.__class__.__name__}(message='{self.message}', details={self.details})"
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class ConfigurationError(LLMManagerError):
    """Raised when LLM Manager configuration is invalid."""
    
    def __init__(self, message: str, invalid_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            invalid_config: The invalid configuration that caused the error
        """
        details = {"invalid_config": invalid_config}
        super().__init__(message=message, details=details)
        self.invalid_config = invalid_config


class AuthenticationError(LLMManagerError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, auth_type: Optional[str] = None, region: Optional[str] = None) -> None:
        """
        Initialize authentication error.
        
        Args:
            message: Error message
            auth_type: Type of authentication that failed
            region: AWS region where authentication failed
        """
        details = None
        if auth_type or region:
            details = {}
            if auth_type:
                details["auth_type"] = auth_type
            if region:
                details["region"] = region
        
        super().__init__(message=message, details=details)
        self.auth_type = auth_type
        self.region = region


class ModelAccessError(LLMManagerError):
    """Raised when model access fails."""
    
    def __init__(
        self, 
        message: str, 
        model_id: Optional[str] = None, 
        region: Optional[str] = None,
        access_method: Optional[str] = None
    ) -> None:
        """
        Initialize model access error.
        
        Args:
            message: Error message
            model_id: Model ID that failed to access
            region: AWS region where access failed
            access_method: Access method that was attempted (direct/cris)
        """
        details = None
        if model_id or region or access_method:
            details = {}
            if model_id:
                details["model_id"] = model_id
            if region:
                details["region"] = region
            if access_method:
                details["access_method"] = access_method
        
        super().__init__(message=message, details=details)
        self.model_id = model_id
        self.region = region
        self.access_method = access_method


class RetryExhaustedError(LLMManagerError):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(
        self, 
        message: str, 
        attempts_made: Optional[int] = None,
        last_errors: Optional[List[Exception]] = None,
        models_tried: Optional[List[str]] = None,
        regions_tried: Optional[List[str]] = None
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
        details = None
        if attempts_made is not None or last_errors or models_tried or regions_tried:
            details = {}
            if attempts_made is not None:
                details["attempts_made"] = attempts_made
            if last_errors:
                details["last_errors"] = [str(error) for error in last_errors]
            if models_tried:
                details["models_tried"] = models_tried
            if regions_tried:
                details["regions_tried"] = regions_tried
        
        super().__init__(message=message, details=details)
        self.attempts_made = attempts_made
        self.last_errors = last_errors or []
        self.models_tried = models_tried or []
        self.regions_tried = regions_tried or []


class RequestValidationError(LLMManagerError):
    """Raised when request validation fails."""
    
    def __init__(
        self, 
        message: str, 
        validation_errors: Optional[List[str]] = None,
        invalid_fields: Optional[List[str]] = None
    ) -> None:
        """
        Initialize request validation error.
        
        Args:
            message: Error message
            validation_errors: List of validation error messages
            invalid_fields: List of field names that failed validation
        """
        details = None
        if validation_errors or invalid_fields:
            details = {}
            if validation_errors:
                details["validation_errors"] = validation_errors
            if invalid_fields:
                details["invalid_fields"] = invalid_fields
        
        super().__init__(message=message, details=details)
        self.validation_errors = validation_errors or []
        self.invalid_fields = invalid_fields or []


class StreamingError(LLMManagerError):
    """Raised when streaming operations fail."""
    
    def __init__(
        self, 
        message: str, 
        stream_position: Optional[int] = None,
        partial_content: Optional[str] = None
    ) -> None:
        """
        Initialize streaming error.
        
        Args:
            message: Error message
            stream_position: Position in stream where error occurred
            partial_content: Partial content received before error
        """
        details = None
        if stream_position is not None or partial_content:
            details = {}
            if stream_position is not None:
                details["stream_position"] = stream_position
            if partial_content:
                details["partial_content"] = partial_content
        
        super().__init__(message=message, details=details)
        self.stream_position = stream_position
        self.partial_content = partial_content


class ContentError(LLMManagerError):
    """Raised when content validation or processing fails."""
    
    def __init__(
        self, 
        message: str, 
        content_type: Optional[str] = None,
        content_size: Optional[int] = None,
        max_allowed_size: Optional[int] = None
    ) -> None:
        """
        Initialize content error.
        
        Args:
            message: Error message
            content_type: Type of content that caused the error
            content_size: Size of the problematic content
            max_allowed_size: Maximum allowed size for the content type
        """
        details = None
        if content_type or content_size is not None or max_allowed_size is not None:
            details = {}
            if content_type:
                details["content_type"] = content_type
            if content_size is not None:
                details["content_size"] = content_size
            if max_allowed_size is not None:
                details["max_allowed_size"] = max_allowed_size
        
        super().__init__(message=message, details=details)
        self.content_type = content_type
        self.content_size = content_size
        self.max_allowed_size = max_allowed_size
