"""
Data structures and type definitions for Amazon Bedrock model management.
Contains typed data classes and models for representing Bedrock model information.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union

from .constants import JSONFields


@dataclass(frozen=True)
class BedrockModelInfo:
    """
    Immutable data class representing information about a single Bedrock model.

    Attributes:
        provider: The model provider (e.g., 'Amazon', 'Anthropic', 'Meta')
        model_id: The unique model identifier used for API calls
        regions_supported: List of AWS regions where the model is available
        input_modalities: List of supported input types (e.g., 'Text', 'Image')
        output_modalities: List of supported output types (e.g., 'Text', 'Image')
        streaming_supported: Whether the model supports streaming responses
        inference_parameters_link: Optional URL to inference parameters documentation
        hyperparameters_link: Optional URL to hyperparameters documentation
    """

    provider: str
    model_id: str
    regions_supported: List[str]
    input_modalities: List[str]
    output_modalities: List[str]
    streaming_supported: bool
    inference_parameters_link: Optional[str] = None
    hyperparameters_link: Optional[str] = None

    def to_dict(self) -> Dict[str, Union[str, List[str], bool, None]]:
        """
        Convert the model info to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {
            JSONFields.PROVIDER: self.provider,
            JSONFields.MODEL_ID: self.model_id,
            JSONFields.REGIONS_SUPPORTED: self.regions_supported,
            JSONFields.INPUT_MODALITIES: self.input_modalities,
            JSONFields.OUTPUT_MODALITIES: self.output_modalities,
            JSONFields.STREAMING_SUPPORTED: self.streaming_supported,
            JSONFields.INFERENCE_PARAMETERS_LINK: self.inference_parameters_link,
            JSONFields.HYPERPARAMETERS_LINK: self.hyperparameters_link,
        }


@dataclass(frozen=True)
class ModelCatalog:
    """
    Immutable data class representing the complete catalog of Bedrock models.

    Attributes:
        retrieval_timestamp: ISO timestamp when the data was retrieved
        models: Dictionary mapping model names to their information
    """

    retrieval_timestamp: datetime
    models: Dict[str, BedrockModelInfo]

    def to_dict(self) -> Dict[str, Union[str, Dict[str, Dict]]]:
        """
        Convert the model catalog to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation using JSON field constants
        """
        return {
            JSONFields.RETRIEVAL_TIMESTAMP: self.retrieval_timestamp.isoformat(),
            JSONFields.MODELS: {
                model_name: model_info.to_dict() for model_name, model_info in self.models.items()
            },
        }

    @property
    def model_count(self) -> int:
        """Get the total number of models in the catalog."""
        return len(self.models)

    def get_models_by_provider(self, provider: str) -> Dict[str, BedrockModelInfo]:
        """
        Get all models from a specific provider.

        Args:
            provider: The provider name to filter by

        Returns:
            Dictionary of model names to model info for the specified provider
        """
        return {name: info for name, info in self.models.items() if info.provider == provider}

    def get_models_by_region(self, region: str) -> Dict[str, BedrockModelInfo]:
        """
        Get all models available in a specific region.

        Args:
            region: The AWS region to filter by

        Returns:
            Dictionary of model names to model info for the specified region
        """
        return {
            name: info for name, info in self.models.items() if region in info.regions_supported
        }

    def get_streaming_models(self) -> Dict[str, BedrockModelInfo]:
        """
        Get all models that support streaming.

        Returns:
            Dictionary of model names to model info for streaming-enabled models
        """
        return {name: info for name, info in self.models.items() if info.streaming_supported}


# Type aliases for better code readability
ModelName = str
RegionName = str
ProviderName = str
ModelDict = Dict[str, Union[str, List[str], bool, None]]
CatalogDict = Dict[str, Union[str, Dict[str, ModelDict]]]
