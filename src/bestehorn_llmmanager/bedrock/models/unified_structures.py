"""
Unified data structures for integrated Bedrock model and CRIS management.
Contains typed data classes that merge regular model information with CRIS data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union

from .access_method import ModelAccessInfo, ModelAccessMethod
from .unified_constants import UnifiedJSONFields


@dataclass(frozen=True)
class UnifiedModelInfo:
    """
    Unified data class representing complete information about a Bedrock model.

    Integrates regular model information with CRIS access options to provide
    a comprehensive view of model availability and access methods.

    Attributes:
        model_name: The canonical model name
        provider: The model provider (e.g., 'Amazon', 'Anthropic', 'Meta')
        model_id: The direct model identifier used for API calls (if available)
        input_modalities: List of supported input types
        output_modalities: List of supported output types
        streaming_supported: Whether the model supports streaming responses
        inference_parameters_link: Optional URL to inference parameters documentation
        hyperparameters_link: Optional URL to hyperparameters documentation
        region_access: Dictionary mapping regions to their access information
    """

    model_name: str
    provider: str
    model_id: Optional[str]
    input_modalities: List[str]
    output_modalities: List[str]
    streaming_supported: bool
    region_access: Dict[str, ModelAccessInfo]
    inference_parameters_link: Optional[str] = None
    hyperparameters_link: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate unified model information."""
        if not self.model_name or not self.model_name.strip():
            raise ValueError("Model name cannot be empty")

        if not self.provider or not self.provider.strip():
            raise ValueError("Provider cannot be empty")

        if not self.region_access:
            raise ValueError("Model must have at least one region access option")

    def get_supported_regions(self) -> List[str]:
        """
        Get all regions where this model is available.

        Returns:
            Sorted list of region identifiers
        """
        return sorted(list(self.region_access.keys()))

    def get_direct_access_regions(self) -> List[str]:
        """
        Get regions where direct model access is available.

        Returns:
            List of regions supporting direct access
        """
        return sorted(
            [
                region
                for region, access_info in self.region_access.items()
                if access_info.access_method in [ModelAccessMethod.DIRECT, ModelAccessMethod.BOTH]
            ]
        )

    def get_cris_only_regions(self) -> List[str]:
        """
        Get regions where only CRIS access is available.

        Returns:
            List of regions with CRIS-only access
        """
        return sorted(
            [
                region
                for region, access_info in self.region_access.items()
                if access_info.access_method == ModelAccessMethod.CRIS_ONLY
            ]
        )

    def get_cris_access_regions(self) -> List[str]:
        """
        Get regions where CRIS access is available (including both methods).

        Returns:
            List of regions supporting CRIS access
        """
        return sorted(
            [
                region
                for region, access_info in self.region_access.items()
                if access_info.access_method
                in [ModelAccessMethod.CRIS_ONLY, ModelAccessMethod.BOTH]
            ]
        )

    def get_access_info_for_region(self, region: str) -> Optional[ModelAccessInfo]:
        """
        Get access information for a specific region.

        Args:
            region: The region to query

        Returns:
            ModelAccessInfo if region is supported, None otherwise
        """
        return self.region_access.get(region)

    def is_available_in_region(self, region: str) -> bool:
        """
        Check if model is available in a specific region.

        Args:
            region: The region to check

        Returns:
            True if model is available in the region
        """
        return region in self.region_access

    def get_recommended_access_for_region(self, region: str) -> Optional[ModelAccessInfo]:
        """
        Get the recommended access method for a region.

        Prefers direct access over CRIS when both are available.

        Args:
            region: The region to get recommendation for

        Returns:
            Recommended ModelAccessInfo if region is supported
        """
        access_info = self.region_access.get(region)
        if not access_info:
            return None

        # If both methods available, return direct access as recommended
        if access_info.access_method == ModelAccessMethod.BOTH:
            return ModelAccessInfo(
                access_method=ModelAccessMethod.DIRECT,
                region=region,
                model_id=access_info.model_id,
                inference_profile_id=access_info.inference_profile_id,
            )

        return access_info

    def get_inference_profiles(self) -> List[str]:
        """
        Get all inference profile IDs available for this model.

        Returns:
            List of unique inference profile IDs
        """
        profiles = set()
        for access_info in self.region_access.values():
            if access_info.inference_profile_id:
                profiles.add(access_info.inference_profile_id)
        return sorted(list(profiles))

    def to_dict(self) -> Dict[str, Union[str, List[str], bool, Dict, None]]:
        """
        Convert the unified model info to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        region_access_dict = {}
        for region, access_info in self.region_access.items():
            region_access_dict[region] = {
                UnifiedJSONFields.ACCESS_METHOD: access_info.access_method.value,
                UnifiedJSONFields.REGION: access_info.region,
                UnifiedJSONFields.MODEL_ID: access_info.model_id,
                UnifiedJSONFields.INFERENCE_PROFILE_ID: access_info.inference_profile_id,
            }

        return {
            UnifiedJSONFields.MODEL_NAME: self.model_name,
            UnifiedJSONFields.PROVIDER: self.provider,
            UnifiedJSONFields.MODEL_ID: self.model_id,
            UnifiedJSONFields.INPUT_MODALITIES: self.input_modalities,
            UnifiedJSONFields.OUTPUT_MODALITIES: self.output_modalities,
            UnifiedJSONFields.STREAMING_SUPPORTED: self.streaming_supported,
            UnifiedJSONFields.INFERENCE_PARAMETERS_LINK: self.inference_parameters_link,
            UnifiedJSONFields.HYPERPARAMETERS_LINK: self.hyperparameters_link,
            UnifiedJSONFields.REGION_ACCESS: region_access_dict,
        }

    @classmethod
    def from_dict(
        cls, data: Dict[str, Union[str, List[str], bool, Dict, None]]
    ) -> "UnifiedModelInfo":
        """
        Create UnifiedModelInfo from dictionary data (for deserialization).

        Args:
            data: Dictionary containing unified model data

        Returns:
            UnifiedModelInfo instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            # Parse region access information
            region_access_data = data[UnifiedJSONFields.REGION_ACCESS]
            if not isinstance(region_access_data, dict):
                raise ValueError("Region access data must be a dictionary")

            region_access = {}
            for region, access_data in region_access_data.items():
                if not isinstance(access_data, dict):
                    raise ValueError(f"Access data for region {region} must be a dictionary")

                access_method = ModelAccessMethod(access_data[UnifiedJSONFields.ACCESS_METHOD])
                region_access[region] = ModelAccessInfo(
                    access_method=access_method,
                    region=access_data[UnifiedJSONFields.REGION],
                    model_id=access_data.get(UnifiedJSONFields.MODEL_ID),
                    inference_profile_id=access_data.get(UnifiedJSONFields.INFERENCE_PROFILE_ID),
                )

            # Extract and validate data with proper type conversion
            model_id_raw = data.get(UnifiedJSONFields.MODEL_ID)
            model_id = str(model_id_raw) if model_id_raw is not None else None

            input_modalities_raw = data[UnifiedJSONFields.INPUT_MODALITIES]
            if not isinstance(input_modalities_raw, list):
                raise ValueError("Input modalities must be a list")
            input_modalities = [str(item) for item in input_modalities_raw]

            output_modalities_raw = data[UnifiedJSONFields.OUTPUT_MODALITIES]
            if not isinstance(output_modalities_raw, list):
                raise ValueError("Output modalities must be a list")
            output_modalities = [str(item) for item in output_modalities_raw]

            inference_params_raw = data.get(UnifiedJSONFields.INFERENCE_PARAMETERS_LINK)
            inference_params_link = (
                str(inference_params_raw) if inference_params_raw is not None else None
            )

            hyperparams_raw = data.get(UnifiedJSONFields.HYPERPARAMETERS_LINK)
            hyperparams_link = str(hyperparams_raw) if hyperparams_raw is not None else None

            return cls(
                model_name=str(data[UnifiedJSONFields.MODEL_NAME]),
                provider=str(data[UnifiedJSONFields.PROVIDER]),
                model_id=model_id,
                input_modalities=input_modalities,
                output_modalities=output_modalities,
                streaming_supported=bool(data[UnifiedJSONFields.STREAMING_SUPPORTED]),
                inference_parameters_link=inference_params_link,
                hyperparameters_link=hyperparams_link,
                region_access=region_access,
            )

        except KeyError as e:
            raise ValueError(f"Missing required field in unified model data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid unified model data structure: {e}") from e


@dataclass(frozen=True)
class UnifiedModelCatalog:
    """
    Unified data class representing the complete catalog of integrated Bedrock models.

    Attributes:
        retrieval_timestamp: ISO timestamp when the data was retrieved
        unified_models: Dictionary mapping model names to their unified information
    """

    retrieval_timestamp: datetime
    unified_models: Dict[str, UnifiedModelInfo]

    def to_dict(self) -> Dict[str, Union[str, Dict[str, Dict]]]:
        """
        Convert the unified catalog to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {
            UnifiedJSONFields.RETRIEVAL_TIMESTAMP: self.retrieval_timestamp.isoformat(),
            UnifiedJSONFields.UNIFIED_MODELS: {
                model_name: model_info.to_dict()
                for model_name, model_info in self.unified_models.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, Dict]]) -> "UnifiedModelCatalog":
        """
        Create UnifiedModelCatalog from dictionary data (for deserialization).

        Args:
            data: Dictionary containing catalog data

        Returns:
            UnifiedModelCatalog instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            timestamp_str = data[UnifiedJSONFields.RETRIEVAL_TIMESTAMP]
            if isinstance(timestamp_str, str):
                retrieval_timestamp = datetime.fromisoformat(timestamp_str)
            else:
                raise ValueError("Invalid timestamp format")

            models_data = data[UnifiedJSONFields.UNIFIED_MODELS]
            if not isinstance(models_data, dict):
                raise ValueError("Unified models data must be a dictionary")

            unified_models = {}
            for model_name, model_data in models_data.items():
                if not isinstance(model_data, dict):
                    raise ValueError(f"Model data for {model_name} must be a dictionary")

                unified_models[model_name] = UnifiedModelInfo.from_dict(data=model_data)

            return cls(retrieval_timestamp=retrieval_timestamp, unified_models=unified_models)

        except KeyError as e:
            raise ValueError(f"Missing required field in catalog data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid catalog data structure: {e}") from e

    @property
    def model_count(self) -> int:
        """Get the total number of models in the unified catalog."""
        return len(self.unified_models)

    def get_model_names(self) -> List[str]:
        """
        Get all model names in the catalog.

        Returns:
            Sorted list of model names
        """
        return sorted(list(self.unified_models.keys()))

    def get_models_by_provider(self, provider: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get all models from a specific provider.

        Args:
            provider: The provider name to filter by

        Returns:
            Dictionary of model names to unified model info for the specified provider
        """
        return {
            name: info for name, info in self.unified_models.items() if info.provider == provider
        }

    def get_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get all models available in a specific region.

        Args:
            region: The AWS region to filter by

        Returns:
            Dictionary of model names to unified model info for the specified region
        """
        return {
            name: info
            for name, info in self.unified_models.items()
            if info.is_available_in_region(region=region)
        }

    def get_direct_access_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get models with direct access in a specific region.

        Args:
            region: The AWS region to filter by

        Returns:
            Dictionary of model names to unified model info with direct access
        """
        return {
            name: info
            for name, info in self.unified_models.items()
            if region in info.get_direct_access_regions()
        }

    def get_cris_only_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get models with CRIS-only access in a specific region.

        Args:
            region: The AWS region to filter by

        Returns:
            Dictionary of model names to unified model info with CRIS-only access
        """
        return {
            name: info
            for name, info in self.unified_models.items()
            if region in info.get_cris_only_regions()
        }

    def get_streaming_models(self) -> Dict[str, UnifiedModelInfo]:
        """
        Get all models that support streaming.

        Returns:
            Dictionary of model names to unified model info for streaming-enabled models
        """
        return {
            name: info for name, info in self.unified_models.items() if info.streaming_supported
        }

    def has_model(self, model_name: str) -> bool:
        """
        Check if a model exists in the catalog.

        Args:
            model_name: The model name to check

        Returns:
            True if model exists in catalog
        """
        return model_name in self.unified_models

    def get_all_supported_regions(self) -> List[str]:
        """
        Get all unique regions supported across all models.

        Returns:
            Sorted list of all supported regions
        """
        all_regions = set()
        for model_info in self.unified_models.values():
            all_regions.update(model_info.get_supported_regions())
        return sorted(list(all_regions))


# Type aliases for better code readability
UnifiedModelName = str
UnifiedModelDict = Dict[str, Union[str, List[str], bool, Dict, None]]
UnifiedCatalogDict = Dict[str, Union[str, Dict[str, UnifiedModelDict]]]
