"""
Model-CRIS correlation logic for unified Bedrock model management.
Handles matching and merging data between regular model information and CRIS data.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from ..models.access_method import ModelAccessInfo, ModelAccessMethod
from ..models.cris_structures import CRISCatalog, CRISModelInfo
from ..models.data_structures import BedrockModelInfo, ModelCatalog
from ..models.unified_constants import (
    ModelCorrelationConfig,
    ModelCorrelationConstants,
    RegionMarkers,
    UnifiedLogMessages,
)
from ..models.unified_structures import UnifiedModelCatalog, UnifiedModelInfo


class ModelCRISCorrelationError(Exception):
    """Exception raised when model-CRIS correlation fails."""

    pass


class ModelCRISCorrelator:
    """
    Correlates and merges regular Bedrock model data with CRIS data.

    This class handles the complex logic of matching models between the two
    systems, resolving naming differences, and creating unified model objects
    that represent all available access methods.
    """

    def __init__(self, enable_fuzzy_matching: Optional[bool] = None) -> None:
        """
        Initialize the correlator with logging and configuration.

        Args:
            enable_fuzzy_matching: Whether to enable fuzzy matching. If None, uses default
        """
        self._logger = logging.getLogger(__name__)
        self._correlation_stats = {
            "matched_models": 0,
            "unmatched_regular_models": 0,
            "unmatched_cris_models": 0,
            "cris_only_models": 0,
            "fuzzy_matched_models": 0,
        }

        # Configure fuzzy matching
        self._fuzzy_matching_enabled = (
            enable_fuzzy_matching
            if enable_fuzzy_matching is not None
            else ModelCorrelationConfig.ENABLE_FUZZY_MATCHING_DEFAULT
        )

        self._logger.info(
            UnifiedLogMessages.CORRELATION_CONFIG_LOADED.format(
                fuzzy_enabled=self._fuzzy_matching_enabled
            )
        )

    def correlate_catalogs(
        self, model_catalog: ModelCatalog, cris_catalog: CRISCatalog
    ) -> UnifiedModelCatalog:
        """
        Correlate and merge model and CRIS catalogs into a unified catalog.

        Args:
            model_catalog: Regular Bedrock model catalog
            cris_catalog: CRIS model catalog

        Returns:
            UnifiedModelCatalog containing merged data

        Raises:
            ModelCRISCorrelationError: If correlation process fails
        """
        self._logger.info(UnifiedLogMessages.CORRELATION_STARTED)

        try:
            # Reset correlation statistics
            self._reset_correlation_stats()

            # Create model name mapping for correlation
            cris_to_standard_mapping = self._create_model_name_mapping(
                cris_models=cris_catalog.cris_models
            )

            # Track processed models to avoid duplicates
            processed_models: Set[str] = set()
            unified_models: Dict[str, UnifiedModelInfo] = {}

            # Process regular models and correlate with CRIS data
            failed_models = []
            for model_name, model_info in model_catalog.models.items():
                if model_name in processed_models:
                    continue

                matching_cris_model = None
                try:
                    # Find matching CRIS model
                    matching_cris_model, match_type = self._find_matching_cris_model(
                        model_name=model_name,
                        cris_models=cris_catalog.cris_models,
                        name_mapping=cris_to_standard_mapping,
                    )

                    # Create unified model
                    unified_model = self._create_unified_model(
                        model_info=model_info,
                        cris_model_info=matching_cris_model,
                        canonical_name=model_name,
                    )

                    unified_models[model_name] = unified_model
                    processed_models.add(model_name)

                    if matching_cris_model:
                        if match_type == "exact":
                            self._correlation_stats["matched_models"] += 1
                        elif match_type == "fuzzy":
                            self._correlation_stats["fuzzy_matched_models"] += 1
                    else:
                        self._correlation_stats["unmatched_regular_models"] += 1

                except Exception as e:
                    error_context = (
                        f"Failed to process model '{model_name}' "
                        f"(Model ID: {model_info.model_id}, Provider: {model_info.provider}). "
                        f"Supported regions: {model_info.regions_supported}. "
                        f"Has matching CRIS model: {matching_cris_model is not None}. "
                        f"Error details: {str(e)}"
                    )
                    self._logger.warning(
                        f"Skipping problematic model '{model_name}': {error_context}"
                    )
                    failed_models.append(model_name)
                    continue  # Skip this model and continue with others

            # Process CRIS-only models (models that don't have regular counterparts)
            for cris_model_name, cris_model_info in cris_catalog.cris_models.items():
                standard_name = cris_to_standard_mapping.get(cris_model_name, cris_model_name)
                # Ensure standard_name is never None (it shouldn't be based on logic, but for type safety)
                if not standard_name:
                    standard_name = cris_model_name

                try:
                    # Check if this CRIS model was already processed
                    if standard_name in processed_models:
                        continue

                    # This is a CRIS-only model
                    unified_model = self._create_cris_only_unified_model(
                        cris_model_info=cris_model_info, canonical_name=standard_name
                    )

                    unified_models[standard_name] = unified_model
                    processed_models.add(standard_name)
                    self._correlation_stats["cris_only_models"] += 1

                except Exception as e:
                    error_context = (
                        f"Failed to process CRIS-only model '{cris_model_name}' "
                        f"(Standard name: {standard_name}, "
                        f"Primary inference profile: {cris_model_info.inference_profile_id}). "
                        f"Available source regions: {cris_model_info.get_source_regions()}. "
                        f"Available inference profiles: {list(cris_model_info.inference_profiles.keys())}. "
                        f"Error details: {str(e)}"
                    )
                    self._logger.error(f"CRIS model correlation error: {error_context}")
                    raise ModelCRISCorrelationError(
                        f"CRIS model correlation failed for '{cris_model_name}': {error_context}"
                    ) from e

            # Log correlation results
            self._log_correlation_results(
                unmatched_regular_models=self._get_unmatched_regular_models(
                    model_catalog=model_catalog, processed_models=processed_models
                ),
                unmatched_cris_models=self._get_unmatched_cris_models(
                    cris_catalog=cris_catalog,
                    cris_to_standard_mapping=cris_to_standard_mapping,
                    processed_models=processed_models,
                ),
            )

            # Create unified catalog
            unified_catalog = UnifiedModelCatalog(
                retrieval_timestamp=model_catalog.retrieval_timestamp, unified_models=unified_models
            )

            self._logger.info(
                UnifiedLogMessages.UNIFIED_CATALOG_CREATED.format(
                    model_count=unified_catalog.model_count
                )
            )

            return unified_catalog

        except Exception as e:
            error_msg = f"Correlation process failed: {str(e)}"
            self._logger.error(error_msg)
            raise ModelCRISCorrelationError(error_msg) from e

    def _create_model_name_mapping(self, cris_models: Dict[str, CRISModelInfo]) -> Dict[str, str]:
        """
        Create mapping from CRIS model names to standardized names.

        Args:
            cris_models: Dictionary of CRIS models

        Returns:
            Mapping from CRIS name to standard name
        """
        mapping = {}

        for cris_name in cris_models.keys():
            # Use explicit mapping if available
            if cris_name in ModelCorrelationConstants.MODEL_NAME_MAPPINGS:
                mapping[cris_name] = ModelCorrelationConstants.MODEL_NAME_MAPPINGS[cris_name]
            else:
                # Apply automatic normalization rules
                normalized_name = self._normalize_model_name(model_name=cris_name)
                mapping[cris_name] = normalized_name

        return mapping

    def _normalize_model_name(self, model_name: str) -> str:
        """
        Normalize a model name by removing common prefixes.

        Args:
            model_name: The model name to normalize

        Returns:
            Normalized model name
        """
        normalized = model_name

        # Remove common prefixes
        prefixes = [
            ModelCorrelationConstants.ANTHROPIC_PREFIX,
            ModelCorrelationConstants.META_PREFIX,
            ModelCorrelationConstants.AMAZON_PREFIX,
            ModelCorrelationConstants.MISTRAL_PREFIX,
        ]

        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break

        return normalized.strip()

    def _find_matching_cris_model(
        self, model_name: str, cris_models: Dict[str, CRISModelInfo], name_mapping: Dict[str, str]
    ) -> Tuple[Optional[CRISModelInfo], str]:
        """
        Find a matching CRIS model for a regular model.

        Args:
            model_name: Name of the regular model
            cris_models: Dictionary of CRIS models
            name_mapping: CRIS name to standard name mapping

        Returns:
            Tuple of (Matching CRISModelInfo if found, match type)
            Match type can be "exact", "fuzzy", or None if no match
        """
        # Step 1: Direct match in explicit mappings
        for cris_name, standard_name in name_mapping.items():
            if standard_name == model_name:
                return cris_models[cris_name], "exact"

        # Step 2: Fuzzy matching (only if enabled and all other options exhausted)
        if self._fuzzy_matching_enabled:
            normalized_target = self._normalize_model_name(model_name=model_name).lower()

            for cris_name, cris_model in cris_models.items():
                normalized_cris = self._normalize_model_name(model_name=cris_name).lower()
                if normalized_cris == normalized_target:
                    # Log fuzzy match warning
                    self._logger.warning(
                        UnifiedLogMessages.FUZZY_MATCH_APPLIED.format(
                            regular_model=model_name, cris_model=cris_name
                        )
                    )
                    return cris_model, "fuzzy"
        else:
            # Log that fuzzy matching is disabled
            self._logger.debug(
                UnifiedLogMessages.FUZZY_MATCHING_DISABLED.format(model_name=model_name)
            )

        return None, "none"

    def _create_unified_model(
        self,
        model_info: BedrockModelInfo,
        cris_model_info: Optional[CRISModelInfo],
        canonical_name: str,
    ) -> UnifiedModelInfo:
        """
        Create a unified model from regular and CRIS model information.

        Args:
            model_info: Regular Bedrock model information
            cris_model_info: CRIS model information (if available)
            canonical_name: The canonical name to use for the unified model

        Returns:
            UnifiedModelInfo instance
        """
        try:
            # Build region access information
            region_access = self._build_region_access_info(
                model_info=model_info, cris_model_info=cris_model_info
            )

            return UnifiedModelInfo(
                model_name=canonical_name,
                provider=model_info.provider,
                model_id=model_info.model_id,
                input_modalities=model_info.input_modalities.copy(),
                output_modalities=model_info.output_modalities.copy(),
                streaming_supported=model_info.streaming_supported,
                inference_parameters_link=model_info.inference_parameters_link,
                hyperparameters_link=model_info.hyperparameters_link,
                region_access=region_access,
            )
        except Exception as e:
            error_context = (
                f"Failed to create unified model for '{canonical_name}'. "
                f"Model ID: {model_info.model_id}, "
                f"Provider: {model_info.provider}, "
                f"Original regions: {model_info.regions_supported}, "
                f"Has CRIS data: {cris_model_info is not None}"
            )
            if cris_model_info:
                error_context += (
                    f", CRIS model name: {cris_model_info.model_name}, "
                    f"CRIS primary profile: {cris_model_info.inference_profile_id}, "
                    f"CRIS source regions: {cris_model_info.get_source_regions()}"
                )

            raise ModelCRISCorrelationError(f"{error_context}. Error details: {str(e)}") from e

    def _create_cris_only_unified_model(
        self, cris_model_info: CRISModelInfo, canonical_name: str
    ) -> UnifiedModelInfo:
        """
        Create a unified model for CRIS-only models.

        Args:
            cris_model_info: CRIS model information
            canonical_name: The canonical name to use

        Returns:
            UnifiedModelInfo instance
        """
        try:
            # Extract provider from model name or inference profile
            provider = self._extract_provider_from_cris_model(cris_model_info=cris_model_info)

            # Build CRIS-only region access information
            region_access = {}
            for region in cris_model_info.get_source_regions():
                try:
                    # Get appropriate inference profile for this region
                    inference_profiles = cris_model_info.get_profiles_for_source_region(
                        source_region=region
                    )
                    primary_profile = (
                        inference_profiles[0]
                        if inference_profiles
                        else cris_model_info.inference_profile_id
                    )

                    if not primary_profile:
                        self._logger.warning(
                            f"No inference profile found for CRIS model '{canonical_name}' in region '{region}'. "
                            f"Available profiles for region: {inference_profiles}, "
                            f"Primary model profile: {cris_model_info.inference_profile_id}. Skipping region."
                        )
                        continue

                    region_access[region] = ModelAccessInfo(
                        access_method=ModelAccessMethod.CRIS_ONLY,
                        region=region,
                        model_id=None,
                        inference_profile_id=primary_profile,
                    )
                except Exception as e:
                    self._logger.warning(
                        f"Failed to create region access for CRIS model '{canonical_name}' in region '{region}': {str(e)}. Skipping region."
                    )
                    continue

            if not region_access:
                raise ValueError(
                    f"No valid region access found for CRIS model '{canonical_name}'. "
                    f"Source regions: {cris_model_info.get_source_regions()}, "
                    f"Available profiles: {list(cris_model_info.inference_profiles.keys())}"
                )

            return UnifiedModelInfo(
                model_name=canonical_name,
                provider=provider,
                model_id=None,  # CRIS-only models don't have direct model IDs
                input_modalities=["Text"],  # Default assumption
                output_modalities=["Text"],  # Default assumption
                streaming_supported=False,  # Default assumption
                inference_parameters_link=None,
                hyperparameters_link=None,
                region_access=region_access,
            )
        except Exception as e:
            error_context = (
                f"Failed to create CRIS-only unified model for '{canonical_name}'. "
                f"CRIS model name: {cris_model_info.model_name}, "
                f"Primary inference profile: {cris_model_info.inference_profile_id}, "
                f"Available source regions: {cris_model_info.get_source_regions()}, "
                f"Available inference profiles: {list(cris_model_info.inference_profiles.keys())}"
            )
            raise ModelCRISCorrelationError(f"{error_context}. Error details: {str(e)}") from e

    def _build_region_access_info(
        self, model_info: BedrockModelInfo, cris_model_info: Optional[CRISModelInfo]
    ) -> Dict[str, ModelAccessInfo]:
        """
        Build comprehensive region access information.

        Args:
            model_info: Regular Bedrock model information
            cris_model_info: CRIS model information (if available)

        Returns:
            Dictionary mapping regions to access information
        """
        region_access: Dict[str, ModelAccessInfo] = {}
        skipped_regions = []

        # Process regions from regular model
        for region in model_info.regions_supported:
            try:
                # Check if region is marked as CRIS-only (contains *)
                if region.endswith(RegionMarkers.CRIS_ONLY_MARKER):
                    clean_region = region.rstrip(RegionMarkers.CRIS_ONLY_MARKER)
                    # This region is CRIS-only
                    inference_profile = (
                        self._get_inference_profile_for_region(
                            cris_model_info=cris_model_info, region=clean_region
                        )
                        if cris_model_info
                        else None
                    )

                    # Only create CRIS-only access if we have an inference profile
                    if inference_profile:
                        region_access[clean_region] = ModelAccessInfo(
                            access_method=ModelAccessMethod.CRIS_ONLY,
                            region=clean_region,
                            model_id=None,
                            inference_profile_id=inference_profile,
                        )

                        self._logger.debug(
                            f"CRIS-only region '{clean_region}' for model '{model_info.model_id}' "
                            f"using profile '{inference_profile}'"
                        )
                    else:
                        # Log warning and skip this region instead of failing
                        warning_msg = (
                            f"Model '{model_info.model_id}' has CRIS-only region '{clean_region}' "
                            "but no CRIS inference profile found. Skipping region. "
                            f"Has CRIS data: {cris_model_info is not None}"
                        )
                        if cris_model_info:
                            warning_msg += f", CRIS model: {cris_model_info.model_name}"
                        self._logger.warning(warning_msg)
                        skipped_regions.append(f"{clean_region} (CRIS-only, no profile)")
                else:
                    # Check if CRIS is also available for this region
                    cris_available = cris_model_info and cris_model_info.can_route_from_source(
                        source_region=region
                    )

                    if cris_available:
                        inference_profile = self._get_inference_profile_for_region(
                            cris_model_info=cris_model_info, region=region
                        )

                        if inference_profile:
                            region_access[region] = ModelAccessInfo(
                                access_method=ModelAccessMethod.BOTH,
                                region=region,
                                model_id=model_info.model_id,
                                inference_profile_id=inference_profile,
                            )
                        else:
                            # Fallback to direct access if CRIS profile not available
                            region_access[region] = ModelAccessInfo(
                                access_method=ModelAccessMethod.DIRECT,
                                region=region,
                                model_id=model_info.model_id,
                                inference_profile_id=None,
                            )
                            self._logger.debug(
                                f"CRIS available for region '{region}' but no profile found, using direct access for model '{model_info.model_id}'"
                            )
                    else:
                        region_access[region] = ModelAccessInfo(
                            access_method=ModelAccessMethod.DIRECT,
                            region=region,
                            model_id=model_info.model_id,
                            inference_profile_id=None,
                        )
            except Exception as e:
                error_context = (
                    f"Failed to process region '{region}' for model '{model_info.model_id}'. "
                    f"Is CRIS-only: {region.endswith(RegionMarkers.CRIS_ONLY_MARKER)}, "
                    f"Has CRIS data: {cris_model_info is not None}"
                )
                if cris_model_info:
                    error_context += f", CRIS model: {cris_model_info.model_name}"

                raise ModelCRISCorrelationError(f"{error_context}. Error details: {str(e)}") from e

        # Add CRIS-only regions that weren't in the regular model
        if cris_model_info:
            for region in cris_model_info.get_source_regions():
                if region not in region_access:
                    try:
                        inference_profile = self._get_inference_profile_for_region(
                            cris_model_info=cris_model_info, region=region
                        )

                        if inference_profile:
                            region_access[region] = ModelAccessInfo(
                                access_method=ModelAccessMethod.CRIS_ONLY,
                                region=region,
                                model_id=None,
                                inference_profile_id=inference_profile,
                            )
                        else:
                            self._logger.warning(
                                f"CRIS model '{cris_model_info.model_name}' has source region '{region}' "
                                "but no inference profile found for region. Skipping region."
                            )
                            skipped_regions.append(f"{region} (CRIS additional, no profile)")
                    except Exception as e:
                        self._logger.warning(
                            f"Failed to add CRIS-only region '{region}' for model '{model_info.model_id}': {str(e)}"
                        )
                        skipped_regions.append(f"{region} (CRIS additional, error)")

        if not region_access:
            error_msg = (
                f"No valid region access information could be built for model '{model_info.model_id}'. "
                f"Original regions: {model_info.regions_supported}, "
                f"Has CRIS data: {cris_model_info is not None}, "
                f"Skipped regions: {skipped_regions}"
            )
            if cris_model_info:
                error_msg += f", CRIS source regions: {cris_model_info.get_source_regions()}"
            raise ValueError(error_msg)

        if skipped_regions:
            self._logger.info(
                f"Model '{model_info.model_id}' had {len(skipped_regions)} skipped regions: {skipped_regions}"
            )

        return region_access

    def _get_inference_profile_for_region(
        self, cris_model_info: Optional[CRISModelInfo], region: str
    ) -> Optional[str]:
        """
        Get the appropriate inference profile for a region.

        Args:
            cris_model_info: CRIS model information
            region: The region to get profile for

        Returns:
            Inference profile ID if available
        """
        if not cris_model_info:
            return None

        # Get profiles that support this source region
        profiles = cris_model_info.get_profiles_for_source_region(source_region=region)
        if profiles:
            return profiles[0]  # Return first available profile

        # Fallback to primary profile if it can route from this region
        if cris_model_info.can_route_from_source(source_region=region):
            return cris_model_info.inference_profile_id

        return None

    def _extract_provider_from_cris_model(self, cris_model_info: CRISModelInfo) -> str:
        """
        Extract provider name from CRIS model information.

        Args:
            cris_model_info: CRIS model information

        Returns:
            Provider name
        """
        model_name = cris_model_info.model_name

        # Check for known prefixes
        if model_name.startswith(ModelCorrelationConstants.ANTHROPIC_PREFIX):
            return "Anthropic"
        elif model_name.startswith(ModelCorrelationConstants.META_PREFIX):
            return "Meta"
        elif model_name.startswith(ModelCorrelationConstants.AMAZON_PREFIX):
            return "Amazon"
        elif model_name.startswith(ModelCorrelationConstants.MISTRAL_PREFIX):
            return "Mistral AI"

        # Extract from inference profile ID
        profile_id = cris_model_info.inference_profile_id
        if "anthropic" in profile_id.lower():
            return "Anthropic"
        elif "meta" in profile_id.lower():
            return "Meta"
        elif "amazon" in profile_id.lower():
            return "Amazon"
        elif "mistral" in profile_id.lower():
            return "Mistral AI"
        elif "deepseek" in profile_id.lower():
            return "DeepSeek"
        elif "writer" in profile_id.lower():
            return "Writer"

        return "Unknown"

    def _get_unmatched_regular_models(
        self, model_catalog: ModelCatalog, processed_models: Set[str]
    ) -> List[str]:
        """Get list of regular models that weren't matched with CRIS data."""
        return [
            model_name
            for model_name in model_catalog.models.keys()
            if model_name not in processed_models
        ]

    def _get_unmatched_cris_models(
        self,
        cris_catalog: CRISCatalog,
        cris_to_standard_mapping: Dict[str, str],
        processed_models: Set[str],
    ) -> List[str]:
        """Get list of CRIS models that weren't matched with regular models."""
        unmatched = []
        for cris_name in cris_catalog.cris_models.keys():
            standard_name = cris_to_standard_mapping.get(cris_name, cris_name)
            if standard_name not in processed_models:
                unmatched.append(cris_name)
        return unmatched

    def _log_correlation_results(
        self, unmatched_regular_models: List[str], unmatched_cris_models: List[str]
    ) -> None:
        """Log the results of the correlation process."""
        total_matched = (
            self._correlation_stats["matched_models"]
            + self._correlation_stats["fuzzy_matched_models"]
        )

        self._logger.info(
            UnifiedLogMessages.CORRELATION_COMPLETED.format(matched_count=total_matched)
        )

        # Log fuzzy matching statistics if any occurred
        if self._correlation_stats["fuzzy_matched_models"] > 0:
            self._logger.info(
                f"Fuzzy matching applied to {self._correlation_stats['fuzzy_matched_models']} models"
            )

        if unmatched_regular_models:
            self._logger.warning(
                UnifiedLogMessages.UNMATCHED_MODELS.format(
                    count=len(unmatched_regular_models), models=", ".join(unmatched_regular_models)
                )
            )

        if unmatched_cris_models:
            self._logger.warning(
                UnifiedLogMessages.UNMATCHED_CRIS.format(
                    count=len(unmatched_cris_models), models=", ".join(unmatched_cris_models)
                )
            )

    def _reset_correlation_stats(self) -> None:
        """Reset correlation statistics."""
        self._correlation_stats = {
            "matched_models": 0,
            "unmatched_regular_models": 0,
            "unmatched_cris_models": 0,
            "cris_only_models": 0,
            "fuzzy_matched_models": 0,
        }

    def get_correlation_stats(self) -> Dict[str, int]:
        """
        Get correlation statistics from the last correlation run.

        Returns:
            Dictionary with correlation statistics
        """
        return self._correlation_stats.copy()

    def is_fuzzy_matching_enabled(self) -> bool:
        """
        Check if fuzzy matching is currently enabled.

        Returns:
            True if fuzzy matching is enabled
        """
        return self._fuzzy_matching_enabled

    def set_fuzzy_matching_enabled(self, enabled: bool) -> None:
        """
        Enable or disable fuzzy matching.

        Args:
            enabled: Whether to enable fuzzy matching
        """
        self._fuzzy_matching_enabled = enabled
        self._logger.info(f"Fuzzy matching {'enabled' if enabled else 'disabled'}")
