"""
Regional variant data structures for Amazon Bedrock CRIS (Cross-Region Inference) management.
Contains typed data classes for handling models that exist in multiple regional deployments.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from .cris_constants import (
    CRISErrorMessages,
    CRISJSONFields,
    CRISRegionPrefixes,
    CRISValidationPatterns,
)


@dataclass(frozen=True)
class CRISRegionalVariant:
    """
    Immutable data class representing a regional deployment variant of a CRIS model.

    This represents a single regional deployment (e.g., US, EU, APAC) of a CRIS model
    with its specific inference profile ID and region mappings.

    Attributes:
        region_prefix: Regional identifier (e.g., 'US', 'EU', 'APAC')
        inference_profile_id: The region-specific inference profile ID
        region_mappings: Dictionary mapping source regions to lists of destination regions
    """

    region_prefix: str
    inference_profile_id: str
    region_mappings: Dict[str, List[str]]

    def __post_init__(self) -> None:
        """Validate the regional variant information after initialization."""
        self._validate_region_prefix()
        self._validate_inference_profile_id()
        self._validate_region_mappings()

    def _validate_region_prefix(self) -> None:
        """
        Validate the region prefix format.

        Raises:
            ValueError: If region prefix is invalid
        """
        if not self.region_prefix or not self.region_prefix.strip():
            raise ValueError(
                CRISErrorMessages.INVALID_REGION_PREFIX.format(region_prefix=self.region_prefix)
            )

        if not re.match(CRISValidationPatterns.REGION_PREFIX_PATTERN, self.region_prefix):
            raise ValueError(
                CRISErrorMessages.INVALID_REGION_PREFIX.format(region_prefix=self.region_prefix)
            )

    def _validate_inference_profile_id(self) -> None:
        """
        Validate the inference profile ID format.

        Raises:
            ValueError: If inference profile ID is invalid
        """
        if not self.inference_profile_id or not self.inference_profile_id.strip():
            raise ValueError("Inference profile ID cannot be empty")

        if not re.match(
            CRISValidationPatterns.INFERENCE_PROFILE_PATTERN, self.inference_profile_id
        ):
            raise ValueError(f"Invalid inference profile ID format: {self.inference_profile_id}")

    def _validate_region_mappings(self) -> None:
        """
        Validate the region mappings structure and content.

        Raises:
            ValueError: If region mappings are invalid
        """
        if not self.region_mappings:
            raise ValueError("Region mappings cannot be empty")

        for source_region, destination_regions in self.region_mappings.items():
            # Validate source region
            if not re.match(CRISValidationPatterns.AWS_REGION_PATTERN, source_region):
                raise ValueError(CRISErrorMessages.INVALID_REGION.format(region=source_region))

            # Validate destination regions
            if not destination_regions:
                raise ValueError(
                    f"Destination regions list cannot be empty for source region: {source_region}"
                )

            for dest_region in destination_regions:
                if not re.match(CRISValidationPatterns.AWS_REGION_PATTERN, dest_region):
                    raise ValueError(CRISErrorMessages.INVALID_REGION.format(region=dest_region))

    def to_dict(self) -> Dict[str, Union[str, Dict[str, List[str]]]]:
        """
        Convert the regional variant to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {
            CRISJSONFields.REGION_PREFIX: self.region_prefix,
            CRISJSONFields.INFERENCE_PROFILE_ID: self.inference_profile_id,
            CRISJSONFields.REGION_MAPPINGS: self.region_mappings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, Dict]]) -> "CRISRegionalVariant":
        """
        Create CRISRegionalVariant from dictionary data (for deserialization).

        Args:
            data: Dictionary containing variant data

        Returns:
            CRISRegionalVariant instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            return cls(
                region_prefix=str(data[CRISJSONFields.REGION_PREFIX]),
                inference_profile_id=str(data[CRISJSONFields.INFERENCE_PROFILE_ID]),
                region_mappings=dict(data[CRISJSONFields.REGION_MAPPINGS]),  # type: ignore
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in variant data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid variant data structure: {e}") from e

    def get_source_regions(self) -> List[str]:
        """
        Get all source regions for this variant.

        Returns:
            List of source region identifiers
        """
        return list(self.region_mappings.keys())

    def get_destination_regions(self) -> List[str]:
        """
        Get all unique destination regions for this variant.

        Returns:
            List of unique destination region identifiers
        """
        all_destinations = set()
        for destinations in self.region_mappings.values():
            all_destinations.update(destinations)
        return sorted(list(all_destinations))

    def can_route_from_source(self, source_region: str) -> bool:
        """
        Check if this variant can be called from the specified source region.

        Args:
            source_region: The source region to check

        Returns:
            True if variant supports calls from this source region
        """
        return source_region in self.region_mappings

    def can_route_to_destination(self, destination_region: str) -> bool:
        """
        Check if this variant can route requests to the specified destination region.

        Args:
            destination_region: The destination region to check

        Returns:
            True if variant can route to this destination region
        """
        return destination_region in self.get_destination_regions()

    def get_destinations_for_source(self, source_region: str) -> List[str]:
        """
        Get destination regions available from a specific source region.

        Args:
            source_region: The source region to query

        Returns:
            List of destination regions, empty if source region not supported
        """
        return self.region_mappings.get(source_region, [])


@dataclass(frozen=True)
class CRISMultiRegionalModel:
    """
    Immutable data class representing a CRIS model with multiple regional variants.

    This enhanced model supports multiple regional deployments while maintaining
    backward compatibility with the original single-variant interface.

    Attributes:
        model_name: The clean model name without regional prefix (e.g., 'Nova Micro')
        regional_variants: Dictionary mapping region prefixes to their deployment variants
    """

    model_name: str
    regional_variants: Dict[str, CRISRegionalVariant]

    def __post_init__(self) -> None:
        """Validate the multi-regional model information after initialization."""
        self._validate_model_name()
        self._validate_regional_variants()

    def _validate_model_name(self) -> None:
        """
        Validate the model name format.

        Raises:
            ValueError: If model name is invalid
        """
        if not self.model_name or not self.model_name.strip():
            raise ValueError(CRISErrorMessages.EMPTY_MODEL_NAME.format(header=self.model_name))

        if not re.match(CRISValidationPatterns.MODEL_NAME_PATTERN, self.model_name):
            raise ValueError(
                CRISErrorMessages.INVALID_MODEL_NAME.format(model_name=self.model_name)
            )

    def _validate_regional_variants(self) -> None:
        """
        Validate the regional variants collection.

        Raises:
            ValueError: If regional variants collection is invalid
        """
        if not self.regional_variants:
            raise ValueError(
                CRISErrorMessages.NO_REGIONAL_VARIANTS.format(model_name=self.model_name)
            )

        # Validate that all region prefixes are consistent
        for region_prefix, variant in self.regional_variants.items():
            if region_prefix != variant.region_prefix:
                raise ValueError(
                    f"Region prefix mismatch: key '{region_prefix}' != variant prefix '{variant.region_prefix}'"
                )

    @property
    def inference_profile_id(self) -> str:
        """
        Primary inference profile ID for backward compatibility.

        Returns the inference profile ID from the preferred regional variant
        based on the preference order defined in constants.

        Returns:
            Primary inference profile ID
        """
        # Use preference order to select primary variant
        for preferred_prefix in CRISRegionPrefixes.PRIMARY_PREFERENCE_ORDER:
            if preferred_prefix in self.regional_variants:
                return self.regional_variants[preferred_prefix].inference_profile_id

        # Fallback to first available variant if no preferred variant found
        return next(iter(self.regional_variants.values())).inference_profile_id

    @property
    def region_mappings(self) -> Dict[str, List[str]]:
        """
        Merged region mappings from all variants for backward compatibility.

        Combines region mappings from all regional variants into a single
        comprehensive mapping dictionary.

        Returns:
            Dictionary mapping source regions to lists of destination regions
        """
        merged_mappings: Dict[str, List[str]] = {}

        for variant in self.regional_variants.values():
            for source_region, destination_regions in variant.region_mappings.items():
                if source_region in merged_mappings:
                    # Merge destination regions, avoiding duplicates
                    existing_destinations = set(merged_mappings[source_region])
                    new_destinations = set(destination_regions)
                    merged_mappings[source_region] = sorted(
                        list(existing_destinations | new_destinations)
                    )
                else:
                    merged_mappings[source_region] = destination_regions.copy()

        return merged_mappings

    def get_variant_by_prefix(self, region_prefix: str) -> Optional[CRISRegionalVariant]:
        """
        Get a specific regional variant by its prefix.

        Args:
            region_prefix: The region prefix to look up (e.g., 'US', 'EU', 'APAC')

        Returns:
            CRISRegionalVariant if found, None otherwise
        """
        return self.regional_variants.get(region_prefix)

    def get_all_inference_profiles(self) -> Dict[str, str]:
        """
        Get all inference profile IDs mapped by their region prefix.

        Returns:
            Dictionary mapping region prefixes to inference profile IDs
        """
        return {
            prefix: variant.inference_profile_id
            for prefix, variant in self.regional_variants.items()
        }

    def get_regional_prefixes(self) -> List[str]:
        """
        Get all available regional prefixes for this model.

        Returns:
            Sorted list of regional prefixes
        """
        return sorted(list(self.regional_variants.keys()))

    def has_regional_variant(self, region_prefix: str) -> bool:
        """
        Check if the model has a variant for the specified region prefix.

        Args:
            region_prefix: The region prefix to check

        Returns:
            True if variant exists for the region prefix
        """
        return region_prefix in self.regional_variants

    def get_source_regions(self) -> List[str]:
        """
        Get all source regions across all variants.

        Returns:
            List of unique source region identifiers
        """
        all_sources = set()
        for variant in self.regional_variants.values():
            all_sources.update(variant.get_source_regions())
        return sorted(list(all_sources))

    def get_destination_regions(self) -> List[str]:
        """
        Get all destination regions across all variants.

        Returns:
            List of unique destination region identifiers
        """
        all_destinations = set()
        for variant in self.regional_variants.values():
            all_destinations.update(variant.get_destination_regions())
        return sorted(list(all_destinations))

    def can_route_from_source(self, source_region: str) -> bool:
        """
        Check if any variant can be called from the specified source region.

        Args:
            source_region: The source region to check

        Returns:
            True if any variant supports calls from this source region
        """
        return any(
            variant.can_route_from_source(source_region=source_region)
            for variant in self.regional_variants.values()
        )

    def can_route_to_destination(self, destination_region: str) -> bool:
        """
        Check if any variant can route requests to the specified destination region.

        Args:
            destination_region: The destination region to check

        Returns:
            True if any variant can route to this destination region
        """
        return any(
            variant.can_route_to_destination(destination_region=destination_region)
            for variant in self.regional_variants.values()
        )

    def get_destinations_for_source(self, source_region: str) -> List[str]:
        """
        Get destination regions available from a specific source region across all variants.

        Args:
            source_region: The source region to query

        Returns:
            List of unique destination regions, empty if source region not supported
        """
        all_destinations = set()
        for variant in self.regional_variants.values():
            destinations = variant.get_destinations_for_source(source_region=source_region)
            all_destinations.update(destinations)
        return sorted(list(all_destinations))

    def to_dict(self) -> Dict[str, Union[str, Dict]]:
        """
        Convert the multi-regional model to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {
            CRISJSONFields.MODEL_NAME: self.model_name,
            CRISJSONFields.REGIONAL_VARIANTS: {
                prefix: variant.to_dict() for prefix, variant in self.regional_variants.items()
            },
            # Include backward compatibility fields
            CRISJSONFields.INFERENCE_PROFILE_ID: self.inference_profile_id,
            CRISJSONFields.REGION_MAPPINGS: self.region_mappings,
            CRISJSONFields.ALL_INFERENCE_PROFILES: self.get_all_inference_profiles(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, Dict]]) -> "CRISMultiRegionalModel":
        """
        Create CRISMultiRegionalModel from dictionary data (for deserialization).

        Args:
            data: Dictionary containing model data

        Returns:
            CRISMultiRegionalModel instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            model_name = str(data[CRISJSONFields.MODEL_NAME])

            variants_data = data[CRISJSONFields.REGIONAL_VARIANTS]
            if not isinstance(variants_data, dict):
                raise ValueError("Regional variants must be a dictionary")

            regional_variants = {}
            for prefix, variant_data in variants_data.items():
                if not isinstance(variant_data, dict):
                    raise ValueError(f"Variant data for {prefix} must be a dictionary")
                regional_variants[prefix] = CRISRegionalVariant.from_dict(data=variant_data)

            return cls(model_name=model_name, regional_variants=regional_variants)

        except KeyError as e:
            raise ValueError(f"Missing required field in model data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid model data structure: {e}") from e


# Type aliases for improved code readability
CRISRegionPrefix = str
CRISRegionalVariantDict = Dict[str, Union[str, Dict[str, List[str]]]]
CRISMultiRegionalModelDict = Dict[str, Union[str, Dict[str, CRISRegionalVariantDict]]]
RegionalVariantsMap = Dict[str, CRISRegionalVariant]
