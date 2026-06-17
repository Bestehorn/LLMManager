"""
Access method data structures for inference profile support.

This module provides data structures for tracking and managing access method
preferences for AWS Bedrock models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final


class AccessMethodNames:
    """Constants for access method names following coding standards."""

    DIRECT: Final[str] = "direct"
    REGIONAL_CRIS: Final[str] = "regional_cris"
    GLOBAL_CRIS: Final[str] = "global_cris"
    UNKNOWN: Final[str] = "unknown"


@dataclass
class AccessMethodPreference:
    """
    Learned preference for accessing a model in a region.

    This dataclass stores information about which access method (direct, regional CRIS,
    or global CRIS) is preferred for a specific model/region combination. Preferences
    can be learned from successful requests or from error detection.

    Attributes:
        prefer_direct: Prefer direct model ID access
        prefer_regional_cris: Prefer regional CRIS profile
        prefer_global_cris: Prefer global CRIS profile
        learned_from_error: Whether preference was learned from error
        last_updated: When preference was last updated
    """

    prefer_direct: bool = True
    prefer_regional_cris: bool = False
    prefer_global_cris: bool = False
    learned_from_error: bool = False
    last_updated: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_method_name(cls, name: str) -> "AccessMethodPreference":
        """
        Build a caller preference from an access-method name (issue #16).

        Creates an AccessMethodPreference whose flags select exactly the named method,
        with learned_from_error=False (this is a caller hint, not a learned hard
        requirement).

        Args:
            name: One of AccessMethodNames.{DIRECT, REGIONAL_CRIS, GLOBAL_CRIS}

        Returns:
            An AccessMethodPreference preferring the named method.

        Raises:
            ValueError: If name is not a recognized access-method name.
        """
        if name == AccessMethodNames.DIRECT:
            return cls(prefer_direct=True, prefer_regional_cris=False, prefer_global_cris=False)
        if name == AccessMethodNames.REGIONAL_CRIS:
            return cls(prefer_direct=False, prefer_regional_cris=True, prefer_global_cris=False)
        if name == AccessMethodNames.GLOBAL_CRIS:
            return cls(prefer_direct=False, prefer_regional_cris=False, prefer_global_cris=True)
        raise ValueError(
            f"Unknown access method name: {name!r}. Expected one of "
            f"{AccessMethodNames.DIRECT!r}, {AccessMethodNames.REGIONAL_CRIS!r}, "
            f"{AccessMethodNames.GLOBAL_CRIS!r}."
        )

    def get_preferred_method(self) -> str:
        """
        Get the preferred access method name.

        Returns the name of the preferred access method based on the preference flags.
        Preference order: direct → regional_cris → global_cris → unknown

        Returns:
            Access method name (direct, regional_cris, global_cris, or unknown)
        """
        if self.prefer_direct:
            return AccessMethodNames.DIRECT
        elif self.prefer_regional_cris:
            return AccessMethodNames.REGIONAL_CRIS
        elif self.prefer_global_cris:
            return AccessMethodNames.GLOBAL_CRIS
        return AccessMethodNames.UNKNOWN
