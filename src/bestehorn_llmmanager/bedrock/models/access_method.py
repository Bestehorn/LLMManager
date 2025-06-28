"""
Access method enumeration and related structures for Bedrock model access.
Defines how models can be accessed in different regions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class ModelAccessMethod(Enum):
    """
    Enumeration of model access methods in AWS Bedrock.

    DIRECT: Model is available directly with regular model ID
    CRIS_ONLY: Model is only available through Cross-Region Inference Service
    BOTH: Model is available via both direct access and CRIS
    """

    DIRECT = "direct"
    CRIS_ONLY = "cris_only"
    BOTH = "both"


@dataclass(frozen=True)
class ModelAccessInfo:
    """
    Information about how to access a model in a specific region.

    Attributes:
        access_method: How the model can be accessed
        model_id: Direct model ID (if direct access available)
        inference_profile_id: CRIS inference profile ID (if CRIS access available)
        region: The target region for access
    """

    access_method: ModelAccessMethod
    region: str
    model_id: Optional[str] = None
    inference_profile_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate access info consistency."""
        if self.access_method == ModelAccessMethod.DIRECT and not self.model_id:
            raise ValueError("Direct access requires model_id")

        if self.access_method == ModelAccessMethod.CRIS_ONLY and not self.inference_profile_id:
            raise ValueError("CRIS-only access requires inference_profile_id")

        if self.access_method == ModelAccessMethod.BOTH:
            if not self.model_id or not self.inference_profile_id:
                raise ValueError(
                    "Both access method requires both model_id and inference_profile_id"
                )


@dataclass(frozen=True)
class AccessRecommendation:
    """
    Recommendation for optimal model access method.

    Attributes:
        recommended_access: The recommended access information
        rationale: Explanation for the recommendation
        alternatives: Alternative access methods if any
    """

    recommended_access: ModelAccessInfo
    rationale: str
    alternatives: List[ModelAccessInfo]
