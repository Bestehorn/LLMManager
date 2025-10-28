"""
Access method enumeration and related structures for Bedrock model access.
Defines how models can be accessed in different regions using orthogonal access flags.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .deprecation import DeprecatedEnumValueWarning, emit_deprecation_warning


class ModelAccessMethod(Enum):
    """
    Enumeration of model access methods in AWS Bedrock.

    DIRECT: Model is available directly with regular model ID
    REGIONAL_CRIS: Model is available through Regional Cross-Region Inference Service
    GLOBAL_CRIS: Model is available through Global Cross-Region Inference Service
    
    Deprecated values (maintained for backward compatibility):
    CRIS_ONLY: Use REGIONAL_CRIS or GLOBAL_CRIS instead
    BOTH: Use orthogonal access flags in ModelAccessInfo instead
    """

    DIRECT = "direct"
    REGIONAL_CRIS = "regional_cris"
    GLOBAL_CRIS = "global_cris"
    
    # Deprecated enum values (maintained for backward compatibility)
    CRIS_ONLY = "cris_only"  # Deprecated in v3.0.0
    BOTH = "both"  # Deprecated in v3.0.0

    @classmethod
    def _emit_deprecation_if_needed(cls, value: "ModelAccessMethod") -> None:
        """Emit deprecation warning for deprecated enum values."""
        if value == cls.CRIS_ONLY:
            emit_deprecation_warning(
                feature="ModelAccessMethod.CRIS_ONLY",
                since="3.0.0",
                removal="4.0.0",
                alternative="ModelAccessMethod.REGIONAL_CRIS or ModelAccessMethod.GLOBAL_CRIS",
                category=DeprecatedEnumValueWarning,
                stacklevel=4,
            )
        elif value == cls.BOTH:
            emit_deprecation_warning(
                feature="ModelAccessMethod.BOTH",
                since="3.0.0",
                removal="4.0.0",
                alternative="orthogonal access flags in ModelAccessInfo",
                category=DeprecatedEnumValueWarning,
                stacklevel=4,
            )


@dataclass(frozen=True)
class ModelAccessInfo:
    """
    Information about how to access a model in a specific region using orthogonal access flags.
    
    This class supports multiple simultaneous access methods through independent boolean flags.
    A model can have any combination of direct, regional CRIS, and global CRIS access.

    Attributes:
        region: The target region for access
        has_direct_access: Whether model is available directly with regular model ID
        has_regional_cris: Whether model is available through Regional CRIS
        has_global_cris: Whether model is available through Global CRIS
        model_id: Direct model ID (required if has_direct_access is True)
        regional_cris_profile_id: Regional CRIS inference profile ID (required if has_regional_cris is True)
        global_cris_profile_id: Global CRIS inference profile ID (required if has_global_cris is True)
        
    Deprecated attributes (maintained for backward compatibility):
        access_method: Use orthogonal flags instead
        inference_profile_id: Use regional_cris_profile_id or global_cris_profile_id instead
    """

    region: str
    has_direct_access: bool = False
    has_regional_cris: bool = False
    has_global_cris: bool = False
    model_id: Optional[str] = None
    regional_cris_profile_id: Optional[str] = None
    global_cris_profile_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate access info consistency."""
        # Validate that at least one access method is enabled
        if not (self.has_direct_access or self.has_regional_cris or self.has_global_cris):
            raise ValueError("At least one access method must be enabled")

        # Validate consistency between flags and IDs
        if self.has_direct_access and not self.model_id:
            raise ValueError("has_direct_access requires model_id")

        if self.has_regional_cris and not self.regional_cris_profile_id:
            raise ValueError("has_regional_cris requires regional_cris_profile_id")

        if self.has_global_cris and not self.global_cris_profile_id:
            raise ValueError("has_global_cris requires global_cris_profile_id")

        # Validate that IDs are not provided when corresponding flags are False
        if not self.has_direct_access and self.model_id:
            raise ValueError("model_id provided but has_direct_access is False")

        if not self.has_regional_cris and self.regional_cris_profile_id:
            raise ValueError("regional_cris_profile_id provided but has_regional_cris is False")

        if not self.has_global_cris and self.global_cris_profile_id:
            raise ValueError("global_cris_profile_id provided but has_global_cris is False")

    @property
    def access_method(self) -> ModelAccessMethod:
        """
        Deprecated property that maps orthogonal flags to legacy enum values.
        
        Returns:
            ModelAccessMethod enum value based on current flags
            
        Deprecated:
            Since v3.0.0. Use orthogonal access flags (has_direct_access, 
            has_regional_cris, has_global_cris) instead.
        """
        emit_deprecation_warning(
            feature="ModelAccessInfo.access_method property",
            since="3.0.0",
            removal="4.0.0",
            alternative="orthogonal access flags (has_direct_access, has_regional_cris, has_global_cris)",
            category=DeprecatedEnumValueWarning,
            stacklevel=2,
        )

        # Map to legacy enum values based on flags
        has_cris = self.has_regional_cris or self.has_global_cris
        
        if self.has_direct_access and has_cris:
            return ModelAccessMethod.BOTH
        elif has_cris:
            return ModelAccessMethod.CRIS_ONLY
        else:
            return ModelAccessMethod.DIRECT

    @property
    def inference_profile_id(self) -> Optional[str]:
        """
        Deprecated property that returns a CRIS profile ID.
        Prefers regional CRIS over global CRIS for backward compatibility.
        
        Returns:
            Regional or global CRIS profile ID, or None if no CRIS access
            
        Deprecated:
            Since v3.0.0. Use regional_cris_profile_id or global_cris_profile_id instead.
        """
        emit_deprecation_warning(
            feature="ModelAccessInfo.inference_profile_id property",
            since="3.0.0",
            removal="4.0.0",
            alternative="regional_cris_profile_id or global_cris_profile_id",
            category=DeprecatedEnumValueWarning,
            stacklevel=2,
        )

        # Prefer regional CRIS for backward compatibility
        if self.regional_cris_profile_id:
            return self.regional_cris_profile_id
        return self.global_cris_profile_id

    @classmethod
    def from_legacy(
        cls,
        access_method: ModelAccessMethod,
        region: str,
        model_id: Optional[str] = None,
        inference_profile_id: Optional[str] = None,
    ) -> "ModelAccessInfo":
        """
        Create ModelAccessInfo from legacy enum-based parameters.
        
        This factory method allows existing code using the old enum-based API
        to work with the new orthogonal flag system.
        
        Args:
            access_method: Legacy access method enum value
            region: The target region for access
            model_id: Direct model ID (if applicable)
            inference_profile_id: CRIS inference profile ID (if applicable)
            
        Returns:
            ModelAccessInfo with appropriate flags set
            
        Raises:
            ValueError: If parameters are inconsistent
        """
        ModelAccessMethod._emit_deprecation_if_needed(access_method)

        if access_method == ModelAccessMethod.DIRECT:
            return cls(
                region=region,
                has_direct_access=True,
                model_id=model_id,
            )
        elif access_method in (ModelAccessMethod.CRIS_ONLY, ModelAccessMethod.REGIONAL_CRIS):
            return cls(
                region=region,
                has_regional_cris=True,
                regional_cris_profile_id=inference_profile_id,
            )
        elif access_method == ModelAccessMethod.GLOBAL_CRIS:
            return cls(
                region=region,
                has_global_cris=True,
                global_cris_profile_id=inference_profile_id,
            )
        elif access_method == ModelAccessMethod.BOTH:
            # For BOTH, assume regional CRIS for backward compatibility
            return cls(
                region=region,
                has_direct_access=True,
                has_regional_cris=True,
                model_id=model_id,
                regional_cris_profile_id=inference_profile_id,
            )
        else:
            raise ValueError(f"Unknown access method: {access_method}")

    def get_access_summary(self) -> str:
        """
        Get a human-readable summary of available access methods.
        
        Returns:
            String describing available access methods
        """
        methods = []
        if self.has_direct_access:
            methods.append("DIRECT")
        if self.has_regional_cris:
            methods.append("REGIONAL_CRIS")
        if self.has_global_cris:
            methods.append("GLOBAL_CRIS")
        
        return " + ".join(methods)

    def has_any_cris_access(self) -> bool:
        """Check if model has any CRIS access (regional or global)."""
        return self.has_regional_cris or self.has_global_cris

    def get_cris_profile_ids(self) -> List[str]:
        """
        Get all available CRIS profile IDs.
        
        Returns:
            List of CRIS profile IDs (regional and/or global)
        """
        profile_ids = []
        if self.regional_cris_profile_id:
            profile_ids.append(self.regional_cris_profile_id)
        if self.global_cris_profile_id:
            profile_ids.append(self.global_cris_profile_id)
        return profile_ids


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
