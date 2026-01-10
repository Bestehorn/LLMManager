"""
Legacy name mapper for backward compatibility with UnifiedModelManager.

This module provides the LegacyNameMapper class that handles resolution of
legacy model names from UnifiedModelManager to BedrockModelCatalog names.
"""

from typing import Optional

from .legacy_name_mappings import (
    DEPRECATED_MODELS,
    LEGACY_NAME_MAPPINGS,
    get_deprecation_reason,
    get_legacy_mapping,
    is_deprecated_model,
)
from .name_normalizer import normalize_model_name


class LegacyNameMapper:
    """
    Maps legacy UnifiedModelManager names to BedrockModelCatalog names.

    This class provides methods for resolving legacy model names and handling
    deprecated models. It supports both exact matching and normalized matching
    for flexible name resolution.

    Attributes:
        _normalized_legacy_index: Index mapping normalized legacy names to catalog names
    """

    def __init__(self) -> None:
        """Initialize the legacy name mapper with normalized index."""
        self._normalized_legacy_index = self._build_normalized_index()

    def _build_normalized_index(self) -> dict[str, str]:
        """
        Build normalized index for legacy names.

        Creates a mapping from normalized legacy names to catalog names
        to support flexible matching with spacing/punctuation variations.

        Returns:
            Dictionary mapping normalized legacy names to catalog names
        """
        normalized_index: dict[str, str] = {}

        for legacy_name, catalog_name in LEGACY_NAME_MAPPINGS.items():
            normalized = normalize_model_name(name=legacy_name)
            if normalized:
                normalized_index[normalized] = catalog_name

        return normalized_index

    def resolve_legacy_name(self, user_name: str) -> Optional[str]:
        """
        Resolve a legacy model name to a catalog name.

        Tries exact match first, then normalized match for flexibility.

        Args:
            user_name: User-provided model name (potentially legacy)

        Returns:
            Catalog model name if legacy mapping exists, None otherwise
        """
        # Try exact match first
        catalog_name = get_legacy_mapping(legacy_name=user_name)
        if catalog_name:
            return catalog_name

        # Try normalized match
        normalized = normalize_model_name(name=user_name)
        if normalized and normalized in self._normalized_legacy_index:
            return self._normalized_legacy_index[normalized]

        return None

    def is_legacy_name(self, user_name: str) -> bool:
        """
        Check if a name is a known legacy model name.

        Args:
            user_name: User-provided model name

        Returns:
            True if this is a known legacy name (active or deprecated)
        """
        # Check exact match
        if user_name in LEGACY_NAME_MAPPINGS or user_name in DEPRECATED_MODELS:
            return True

        # Check normalized match
        normalized = normalize_model_name(name=user_name)
        if normalized:
            return normalized in self._normalized_legacy_index

        return False

    def is_deprecated(self, user_name: str) -> bool:
        """
        Check if a legacy name refers to a deprecated model.

        Args:
            user_name: User-provided model name

        Returns:
            True if the model is deprecated
        """
        return is_deprecated_model(legacy_name=user_name)

    def get_deprecation_info(self, user_name: str) -> Optional[str]:
        """
        Get deprecation information for a legacy model name.

        Args:
            user_name: User-provided model name

        Returns:
            Deprecation reason if model is deprecated, None otherwise
        """
        return get_deprecation_reason(legacy_name=user_name)

    def get_all_legacy_names(self) -> list[str]:
        """
        Get all known legacy model names (active mappings only).

        Returns:
            List of all legacy model names that have active mappings
        """
        return list(LEGACY_NAME_MAPPINGS.keys())

    def get_all_deprecated_names(self) -> list[str]:
        """
        Get all deprecated model names.

        Returns:
            List of all deprecated model names
        """
        return list(DEPRECATED_MODELS.keys())
