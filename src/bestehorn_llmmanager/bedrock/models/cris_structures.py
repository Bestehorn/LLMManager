"""
Data structures and type definitions for Amazon Bedrock CRIS (Cross-Region Inference) management.
Contains typed data classes and models for representing CRIS model information with proper inference profile separation.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union

from .cris_constants import CRISErrorMessages, CRISJSONFields, CRISValidationPatterns


@dataclass(frozen=True)
class CRISInferenceProfile:
    """
    Immutable data class representing a single inference profile with its region mappings.

    This class stores the region mappings specific to one inference profile ID,
    ensuring that each profile only contains regions relevant to its geographic deployment.

    Attributes:
        inference_profile_id: The inference profile ID (e.g., 'us.amazon.nova-lite-v1:0')
        region_mappings: Dictionary mapping source regions to lists of destination regions
                        for this specific inference profile
    """

    inference_profile_id: str
    region_mappings: Dict[str, List[str]]

    def __post_init__(self) -> None:
        """Validate the inference profile information after initialization."""
        self._validate_inference_profile_id()
        self._validate_region_mappings()

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

    def to_dict(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Convert the inference profile to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {CRISJSONFields.REGION_MAPPINGS: self.region_mappings}

    def get_source_regions(self) -> List[str]:
        """
        Get all source regions for this inference profile.

        Returns:
            List of source region identifiers
        """
        return list(self.region_mappings.keys())

    def get_destination_regions(self) -> List[str]:
        """
        Get all unique destination regions for this inference profile.

        Returns:
            List of unique destination region identifiers
        """
        all_destinations = set()
        for destinations in self.region_mappings.values():
            all_destinations.update(destinations)
        return sorted(list(all_destinations))

    def can_route_from_source(self, source_region: str) -> bool:
        """
        Check if this inference profile can be called from the specified source region.

        Args:
            source_region: The source region to check

        Returns:
            True if profile supports calls from this source region
        """
        return source_region in self.region_mappings

    def can_route_to_destination(self, destination_region: str) -> bool:
        """
        Check if this inference profile can route requests to the specified destination region.

        Args:
            destination_region: The destination region to check

        Returns:
            True if profile can route to this destination region
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
class CRISModelInfo:
    """
    Immutable data class representing information about a single CRIS model with multiple inference profiles.

    This enhanced model supports multiple regional inference profiles while maintaining
    backward compatibility with the original single-profile interface.

    Attributes:
        model_name: The clean model name (e.g., 'Nova Lite')
        inference_profiles: Dictionary mapping inference profile IDs to their profile data
    """

    model_name: str
    inference_profiles: Dict[str, CRISInferenceProfile]

    def __post_init__(self) -> None:
        """Validate the model information after initialization."""
        self._validate_model_name()
        self._validate_inference_profiles()

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

    def _validate_inference_profiles(self) -> None:
        """
        Validate the inference profiles collection.

        Raises:
            ValueError: If inference profiles collection is invalid
        """
        if not self.inference_profiles:
            raise ValueError(
                CRISErrorMessages.NO_INFERENCE_PROFILES.format(model_name=self.model_name)
            )

        # Validate that all profile IDs are consistent with their keys
        for profile_id, profile_info in self.inference_profiles.items():
            if profile_id != profile_info.inference_profile_id:
                raise ValueError(
                    f"Profile ID mismatch: key '{profile_id}' != profile ID '{profile_info.inference_profile_id}'"
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
        # Try to find a US profile first (preferred)
        for profile_id, profile_info in self.inference_profiles.items():
            if profile_id.startswith("us."):
                return profile_id

        # Fallback to EU profile
        for profile_id, profile_info in self.inference_profiles.items():
            if profile_id.startswith("eu."):
                return profile_id

        # Fallback to APAC profile
        for profile_id, profile_info in self.inference_profiles.items():
            if profile_id.startswith("apac.") or profile_id.startswith("ap."):
                return profile_id

        # If no regional preference found, return first available
        return next(iter(self.inference_profiles.keys()))

    @property
    def region_mappings(self) -> Dict[str, List[str]]:
        """
        Merged region mappings from all inference profiles for backward compatibility.

        Combines region mappings from all inference profiles into a single
        comprehensive mapping dictionary.

        Returns:
            Dictionary mapping source regions to lists of destination regions
        """
        merged_mappings: Dict[str, List[str]] = {}

        for profile_info in self.inference_profiles.values():
            for source_region, destination_regions in profile_info.region_mappings.items():
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

    def get_inference_profile(self, profile_id: str) -> Optional[CRISInferenceProfile]:
        """
        Get a specific inference profile by its ID.

        Args:
            profile_id: The inference profile ID to look up

        Returns:
            CRISInferenceProfile if found, None otherwise
        """
        return self.inference_profiles.get(profile_id)

    def get_all_inference_profile_ids(self) -> List[str]:
        """
        Get all inference profile IDs for this model.

        Returns:
            List of inference profile IDs
        """
        return list(self.inference_profiles.keys())

    def has_inference_profile(self, profile_id: str) -> bool:
        """
        Check if the model has a specific inference profile.

        Args:
            profile_id: The inference profile ID to check

        Returns:
            True if profile exists for this model
        """
        return profile_id in self.inference_profiles

    def get_source_regions(self) -> List[str]:
        """
        Get all source regions across all inference profiles.

        Returns:
            List of unique source region identifiers
        """
        all_sources = set()
        for profile_info in self.inference_profiles.values():
            all_sources.update(profile_info.get_source_regions())
        return sorted(list(all_sources))

    def get_destination_regions(self) -> List[str]:
        """
        Get all destination regions across all inference profiles.

        Returns:
            List of unique destination region identifiers
        """
        all_destinations = set()
        for profile_info in self.inference_profiles.values():
            all_destinations.update(profile_info.get_destination_regions())
        return sorted(list(all_destinations))

    def can_route_from_source(self, source_region: str) -> bool:
        """
        Check if any inference profile can be called from the specified source region.

        Args:
            source_region: The source region to check

        Returns:
            True if any profile supports calls from this source region
        """
        return any(
            profile_info.can_route_from_source(source_region=source_region)
            for profile_info in self.inference_profiles.values()
        )

    def can_route_to_destination(self, destination_region: str) -> bool:
        """
        Check if any inference profile can route requests to the specified destination region.

        Args:
            destination_region: The destination region to check

        Returns:
            True if any profile can route to this destination region
        """
        return any(
            profile_info.can_route_to_destination(destination_region=destination_region)
            for profile_info in self.inference_profiles.values()
        )

    def get_destinations_for_source(self, source_region: str) -> List[str]:
        """
        Get destination regions available from a specific source region across all profiles.

        Args:
            source_region: The source region to query

        Returns:
            List of unique destination regions, empty if source region not supported
        """
        all_destinations = set()
        for profile_info in self.inference_profiles.values():
            destinations = profile_info.get_destinations_for_source(source_region=source_region)
            all_destinations.update(destinations)
        return sorted(list(all_destinations))

    def get_profiles_for_source_region(self, source_region: str) -> List[str]:
        """
        Get inference profile IDs that can be called from a specific source region.

        Args:
            source_region: The source region to query

        Returns:
            List of inference profile IDs that support this source region
        """
        matching_profiles = []
        for profile_id, profile_info in self.inference_profiles.items():
            if profile_info.can_route_from_source(source_region=source_region):
                matching_profiles.append(profile_id)
        return matching_profiles

    def get_profiles_for_destination_region(self, destination_region: str) -> List[str]:
        """
        Get inference profile IDs that can route to a specific destination region.

        Args:
            destination_region: The destination region to query

        Returns:
            List of inference profile IDs that can route to this destination region
        """
        matching_profiles = []
        for profile_id, profile_info in self.inference_profiles.items():
            if profile_info.can_route_to_destination(destination_region=destination_region):
                matching_profiles.append(profile_id)
        return matching_profiles

    def to_dict(self) -> Dict[str, Union[str, Dict]]:
        """
        Convert the CRIS model info to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {
            CRISJSONFields.MODEL_NAME: self.model_name,
            CRISJSONFields.INFERENCE_PROFILES: {
                profile_id: profile_info.to_dict()
                for profile_id, profile_info in self.inference_profiles.items()
            },
            # Include backward compatibility field
            CRISJSONFields.INFERENCE_PROFILE_ID: self.inference_profile_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, Dict]]) -> "CRISModelInfo":
        """
        Create CRISModelInfo from dictionary data (for deserialization).

        Args:
            data: Dictionary containing model data

        Returns:
            CRISModelInfo instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            model_name = str(data[CRISJSONFields.MODEL_NAME])

            profiles_data = data[CRISJSONFields.INFERENCE_PROFILES]
            if not isinstance(profiles_data, dict):
                raise ValueError("Inference profiles must be a dictionary")

            inference_profiles = {}
            for profile_id, profile_data in profiles_data.items():
                if not isinstance(profile_data, dict):
                    raise ValueError(f"Profile data for {profile_id} must be a dictionary")

                region_mappings = profile_data[CRISJSONFields.REGION_MAPPINGS]
                if not isinstance(region_mappings, dict):
                    raise ValueError(f"Region mappings for {profile_id} must be a dictionary")

                inference_profiles[profile_id] = CRISInferenceProfile(
                    inference_profile_id=profile_id, region_mappings=region_mappings
                )

            return cls(model_name=model_name, inference_profiles=inference_profiles)

        except KeyError as e:
            raise ValueError(f"Missing required field in model data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid model data structure: {e}") from e


@dataclass(frozen=True)
class CRISCatalog:
    """
    Immutable data class representing the complete catalog of CRIS models.

    Attributes:
        retrieval_timestamp: ISO timestamp when the data was retrieved
        cris_models: Dictionary mapping model names to their CRIS information
    """

    retrieval_timestamp: datetime
    cris_models: Dict[str, CRISModelInfo]

    def to_dict(self) -> Dict[str, Union[str, Dict[str, Dict]]]:
        """
        Convert the CRIS catalog to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {
            CRISJSONFields.RETRIEVAL_TIMESTAMP: self.retrieval_timestamp.isoformat(),
            CRISJSONFields.CRIS: {
                model_name: model_info.to_dict()
                for model_name, model_info in self.cris_models.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, Dict]]) -> "CRISCatalog":
        """
        Create CRISCatalog from dictionary data (for deserialization).

        Args:
            data: Dictionary containing catalog data

        Returns:
            CRISCatalog instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            timestamp_str = data[CRISJSONFields.RETRIEVAL_TIMESTAMP]
            if isinstance(timestamp_str, str):
                retrieval_timestamp = datetime.fromisoformat(timestamp_str)
            else:
                raise ValueError("Invalid timestamp format")

            cris_data = data[CRISJSONFields.CRIS]
            if not isinstance(cris_data, dict):
                raise ValueError("CRIS data must be a dictionary")

            cris_models = {}
            for model_name, model_data in cris_data.items():
                if not isinstance(model_data, dict):
                    raise ValueError(f"Model data for {model_name} must be a dictionary")

                cris_models[model_name] = CRISModelInfo.from_dict(data=model_data)

            return cls(retrieval_timestamp=retrieval_timestamp, cris_models=cris_models)

        except KeyError as e:
            raise ValueError(f"Missing required field in catalog data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid catalog data structure: {e}") from e

    @property
    def model_count(self) -> int:
        """Get the total number of CRIS models in the catalog."""
        return len(self.cris_models)

    def get_models_by_source_region(self, source_region: str) -> Dict[str, CRISModelInfo]:
        """
        Get all models that can be called from a specific source region.

        Args:
            source_region: The source region to filter by

        Returns:
            Dictionary of model names to model info for the specified source region
        """
        return {
            name: info
            for name, info in self.cris_models.items()
            if info.can_route_from_source(source_region=source_region)
        }

    def get_models_by_destination_region(self, destination_region: str) -> Dict[str, CRISModelInfo]:
        """
        Get all models that can route requests to a specific destination region.

        Args:
            destination_region: The destination region to filter by

        Returns:
            Dictionary of model names to model info for the specified destination region
        """
        return {
            name: info
            for name, info in self.cris_models.items()
            if info.can_route_to_destination(destination_region=destination_region)
        }

    def get_inference_profile_for_model(self, model_name: str) -> Optional[str]:
        """
        Get the primary inference profile ID for a specific model.

        Args:
            model_name: The name of the model to look up

        Returns:
            Primary inference profile ID if model exists, None otherwise
        """
        model_info = self.cris_models.get(model_name)
        return model_info.inference_profile_id if model_info else None

    def get_all_source_regions(self) -> List[str]:
        """
        Get all unique source regions across all models.

        Returns:
            Sorted list of all source regions
        """
        all_sources = set()
        for model_info in self.cris_models.values():
            all_sources.update(model_info.get_source_regions())
        return sorted(list(all_sources))

    def get_all_destination_regions(self) -> List[str]:
        """
        Get all unique destination regions across all models.

        Returns:
            Sorted list of all destination regions
        """
        all_destinations = set()
        for model_info in self.cris_models.values():
            all_destinations.update(model_info.get_destination_regions())
        return sorted(list(all_destinations))

    def get_model_names(self) -> List[str]:
        """
        Get all model names in the catalog.

        Returns:
            Sorted list of model names
        """
        return sorted(list(self.cris_models.keys()))

    def has_model(self, model_name: str) -> bool:
        """
        Check if a model exists in the catalog.

        Args:
            model_name: The model name to check

        Returns:
            True if model exists in catalog
        """
        return model_name in self.cris_models


# Type aliases for better code readability
CRISModelName = str
CRISRegionName = str
CRISInferenceProfileId = str
CRISModelDict = Dict[str, Union[str, Dict[str, Dict[str, List[str]]]]]
CRISCatalogDict = Dict[str, Union[str, Dict[str, CRISModelDict]]]
RegionMappings = Dict[str, List[str]]
InferenceProfilesMap = Dict[str, CRISInferenceProfile]
