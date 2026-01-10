"""
Data structures for model-specific configuration and parameters.
Contains typed data classes for managing additionalModelRequestFields.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


# JSON field constants for serialization
class ModelSpecificFields:
    """JSON field name constants for ModelSpecificConfig."""

    ENABLE_EXTENDED_CONTEXT: str = "enable_extended_context"
    CUSTOM_FIELDS: str = "custom_fields"


@dataclass
class ModelSpecificConfig:
    """
    Configuration for model-specific request parameters.

    This class encapsulates the additionalModelRequestFields parameter
    and provides a structured way to manage model-specific features.

    Attributes:
        enable_extended_context: Flag to enable 1M token context window for compatible models
        custom_fields: Dictionary of custom additionalModelRequestFields
    """

    enable_extended_context: bool = False
    custom_fields: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """
        Validate field types after initialization.

        Raises:
            TypeError: If enable_extended_context is not a boolean
            TypeError: If custom_fields is not a dictionary or None
        """
        if not isinstance(self.enable_extended_context, bool):
            raise TypeError(
                f"enable_extended_context must be a boolean, "
                f"got {type(self.enable_extended_context).__name__}"
            )

        if self.custom_fields is not None and not isinstance(self.custom_fields, dict):
            raise TypeError(
                f"custom_fields must be a dictionary or None, "
                f"got {type(self.custom_fields).__name__}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for serialization.

        Returns:
            Dictionary representation using field constants
        """
        return {
            ModelSpecificFields.ENABLE_EXTENDED_CONTEXT: self.enable_extended_context,
            ModelSpecificFields.CUSTOM_FIELDS: self.custom_fields,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelSpecificConfig":
        """
        Create ModelSpecificConfig from dictionary.

        Args:
            data: Dictionary containing configuration data

        Returns:
            ModelSpecificConfig instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not isinstance(data, dict):
            raise ValueError(f"Data must be a dictionary, got {type(data).__name__}")

        enable_extended_context = data.get(ModelSpecificFields.ENABLE_EXTENDED_CONTEXT, False)
        custom_fields = data.get(ModelSpecificFields.CUSTOM_FIELDS)

        return cls(
            enable_extended_context=enable_extended_context,
            custom_fields=custom_fields,
        )
