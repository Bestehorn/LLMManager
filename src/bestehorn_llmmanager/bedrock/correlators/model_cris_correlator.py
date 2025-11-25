"""
Model-CRIS correlation logic for unified Bedrock model management.
Handles matching and merging data between regular model information and CRIS data.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from ..models.access_method import ModelAccessInfo
from ..models.cris_constants import CRISGlobalConstants
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
        self, model_catalog: ModelCatalog, cris_catalog: Optional[CRISCatalog]
    ) -> UnifiedModelCatalog:
        """
        Correlate and merge model and CRIS catalogs into a unified catalog.

        Args:
            model_catalog: Regular Bedrock model catalog
            cris_catalog: CRIS model catalog (optional, can be None if CRIS data unavailable)

        Returns:
            UnifiedModelCatalog containing merged data

        Raises:
            ModelCRISCorrelationError: If correlation process fails
        """
        self._logger.info(UnifiedLogMessages.CORRELATION_STARTED)

        try:
            # Reset correlation statistics
            self._reset_correlation_stats()

            # Handle None cris_catalog - create empty catalog for graceful processing
            if cris_catalog is None:
                self._logger.warning(
                    "CRIS catalog is None - proceeding with direct model access only"
                )
                cris_catalog = CRISCatalog(
                    retrieval_timestamp=model_catalog.retrieval_timestamp, cris_models={}
                )

            # Create model name mapping for correlation
            cris_to_standard_mapping = self._create_model_name_mapping(
                cris_models=cris_catalog.cris_models
            )

            # CRITICAL FIX: Create synthetic base models for CRIS-only models
            # This ensures models like Claude Haiku 4.5 have a base entry to correlate with
            model_catalog = self._add_synthetic_base_models(
                model_catalog=model_catalog,
                cris_catalog=cris_catalog,
                cris_to_standard_mapping=cris_to_standard_mapping,
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
        Normalize a model name by removing provider prefixes.

        Handles both naming conventions used in AWS Bedrock:
        - Dot-separated lowercase (model IDs): "anthropic.claude-3-5-haiku..."
        - Space-separated capitalized (CRIS names): "Anthropic Claude 3.5 Haiku"

        This normalization enables proper correlation between CRIS data and
        foundational model data despite different naming conventions.

        Examples:
            Dot-separated (model IDs):
            "anthropic.claude-3-5-haiku-20241022-v1:0" -> "claude-3-5-haiku-20241022-v1:0"
            "twelvelabs.marengo-embed-2-7-v1:0" -> "marengo-embed-2-7-v1:0"
            "cohere.embed-english-v3" -> "embed-english-v3"

            Space-separated (CRIS names):
            "Anthropic Claude Haiku 4.5" -> "Claude Haiku 4.5"
            "TwelveLabs Marengo Embed v2.7" -> "Marengo Embed v2.7"
            "Meta Llama 3.3 70B Instruct" -> "Llama 3.3 70B Instruct"

        Args:
            model_name: The model name to normalize

        Returns:
            Normalized model name with provider prefix removed
        """
        # Strip whitespace first to ensure prefix matching works correctly
        normalized = model_name.strip()

        # Use comprehensive provider prefix list from constants
        # Includes both dot-separated (model IDs) and space-separated (CRIS names)
        for prefix in ModelCorrelationConstants.ALL_PROVIDER_PREFIXES:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break

        return normalized.strip()

    def _find_matching_cris_model(
        self, model_name: str, cris_models: Dict[str, CRISModelInfo], name_mapping: Dict[str, str]
    ) -> Tuple[Optional[CRISModelInfo], str]:
        """
        Find a matching CRIS model for a regular model.

        IMPORTANT: Prioritizes Global CRIS variants over regional variants to ensure
        models like Claude Haiku 4.5 match with "Global Anthropic Claude Haiku 4.5"
        instead of "Anthropic Claude Haiku 4.5".

        Args:
            model_name: Name of the regular model
            cris_models: Dictionary of CRIS models
            name_mapping: CRIS name to standard name mapping

        Returns:
            Tuple of (Matching CRISModelInfo if found, match type)
            Match type can be "exact", "fuzzy", or None if no match
        """
        # Step 1: Check for Global variant first (PRIORITY FIX)
        # Look for "Global [model_name]" pattern in CRIS models
        for cris_name, standard_name in name_mapping.items():
            if standard_name == model_name and cris_name.startswith("Global "):
                self._logger.info(
                    f"Matched model '{model_name}' with Global CRIS variant '{cris_name}'"
                )
                return cris_models[cris_name], "exact"

        # Step 2: Direct match in explicit mappings (regional variants)
        for cris_name, standard_name in name_mapping.items():
            if standard_name == model_name:
                return cris_models[cris_name], "exact"

        # Step 3: Fuzzy matching (only if enabled and all other options exhausted)
        if self._fuzzy_matching_enabled:
            normalized_target = self._normalize_model_name(model_name=model_name).lower()

            # First try to match Global variants with fuzzy matching
            for cris_name, cris_model in cris_models.items():
                if cris_name.startswith("Global "):
                    normalized_cris = self._normalize_model_name(model_name=cris_name).lower()
                    if normalized_cris == normalized_target:
                        # Log fuzzy match warning
                        self._logger.warning(
                            UnifiedLogMessages.FUZZY_MATCH_APPLIED.format(
                                regular_model=model_name, cris_model=cris_name
                            )
                        )
                        return cris_model, "fuzzy"

            # Then try regional variants
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

                    # Determine if this is a global or regional profile
                    is_global = primary_profile.startswith("global.")

                    if is_global:
                        region_access[region] = ModelAccessInfo(
                            region=region,
                            has_global_cris=True,
                            global_cris_profile_id=primary_profile,
                        )
                    else:
                        region_access[region] = ModelAccessInfo(
                            region=region,
                            has_regional_cris=True,
                            regional_cris_profile_id=primary_profile,
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
                        # Determine if this is a global or regional profile
                        is_global = inference_profile.startswith("global.")

                        if is_global:
                            region_access[clean_region] = ModelAccessInfo(
                                region=clean_region,
                                has_global_cris=True,
                                global_cris_profile_id=inference_profile,
                            )
                        else:
                            region_access[clean_region] = ModelAccessInfo(
                                region=clean_region,
                                has_regional_cris=True,
                                regional_cris_profile_id=inference_profile,
                            )

                        self._logger.debug(
                            f"CRIS-only region '{clean_region}' for model '{model_info.model_id}' "
                            f"using profile '{inference_profile}'"
                        )
                    else:
                        # Log info about CRIS-only region without profile (expected behavior)
                        info_msg = (
                            f"Model '{model_info.model_id}' has CRIS-only region '{clean_region}' "
                            "but no CRIS inference profile found. This is expected for models "
                            "with limited CRIS coverage. Skipping region. "
                            f"Has CRIS data: {cris_model_info is not None}"
                        )
                        if cris_model_info:
                            info_msg += f", CRIS model: {cris_model_info.model_name}"
                        self._logger.info(info_msg)
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
                            # Determine if this is a global or regional profile
                            is_global = inference_profile.startswith("global.")

                            if is_global:
                                # Both direct and global CRIS
                                region_access[region] = ModelAccessInfo(
                                    region=region,
                                    has_direct_access=True,
                                    has_global_cris=True,
                                    model_id=model_info.model_id,
                                    global_cris_profile_id=inference_profile,
                                )
                            else:
                                # Both direct and regional CRIS
                                region_access[region] = ModelAccessInfo(
                                    region=region,
                                    has_direct_access=True,
                                    has_regional_cris=True,
                                    model_id=model_info.model_id,
                                    regional_cris_profile_id=inference_profile,
                                )
                        else:
                            # Fallback to direct access only if CRIS profile not available
                            region_access[region] = ModelAccessInfo(
                                region=region,
                                has_direct_access=True,
                                model_id=model_info.model_id,
                            )
                            self._logger.debug(
                                f"CRIS available for region '{region}' but no profile found, using direct access for model '{model_info.model_id}'"
                            )
                    else:
                        # Direct access only
                        region_access[region] = ModelAccessInfo(
                            region=region,
                            has_direct_access=True,
                            model_id=model_info.model_id,
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
                            # Determine if this is a global or regional profile
                            is_global = inference_profile.startswith("global.")

                            if is_global:
                                region_access[region] = ModelAccessInfo(
                                    region=region,
                                    has_global_cris=True,
                                    global_cris_profile_id=inference_profile,
                                )
                            else:
                                region_access[region] = ModelAccessInfo(
                                    region=region,
                                    has_regional_cris=True,
                                    regional_cris_profile_id=inference_profile,
                                )
                        else:
                            self._logger.info(
                                f"CRIS model '{cris_model_info.model_name}' has source region '{region}' "
                                "but no inference profile found for region. This is expected for models "
                                "with limited CRIS coverage. Skipping region."
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

    def _extract_clean_model_name_from_cris(self, cris_name: str) -> str:
        """
        Extract clean model name by removing regional prefixes.

        Args:
            cris_name: CRIS model name that may have prefix

        Returns:
            Clean model name without regional prefix
        """
        for prefix in ["Global ", "US ", "EU ", "APAC "]:
            if cris_name.startswith(prefix):
                return cris_name[len(prefix) :]
        return cris_name

    def _extract_provider_from_profile_id(self, profile_id: str) -> str:
        """
        Extract provider name from inference profile ID.

        Args:
            profile_id: Inference profile ID

        Returns:
            Provider name
        """
        # Format: global.anthropic.model or us.amazon.model
        parts = profile_id.split(".")
        if len(parts) >= 2:
            provider = parts[1]
            return provider.capitalize()
        return "Unknown"

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

    def _add_synthetic_base_models(
        self,
        model_catalog: ModelCatalog,
        cris_catalog: CRISCatalog,
        cris_to_standard_mapping: Dict[str, str],
    ) -> ModelCatalog:
        """
        Add synthetic base model entries for CRIS-only models.

        This critical fix enables models like Claude Haiku 4.5 to load by creating
        synthetic BedrockModelInfo entries for models that only exist in CRIS.

        Args:
            model_catalog: Original model catalog
            cris_catalog: CRIS catalog
            cris_to_standard_mapping: Mapping from CRIS names to standard names

        Returns:
            Updated model catalog with synthetic entries added
        """
        synthetic_models = {}

        for cris_name, cris_model_info in cris_catalog.cris_models.items():
            standard_name = cris_to_standard_mapping.get(cris_name, cris_name)

            # Check if this model already exists in the catalog
            if standard_name in model_catalog.models:
                continue

            # This is a CRIS-only model - create synthetic base entry
            try:
                synthetic_model = self._create_synthetic_base_model(cris_model_info)
                synthetic_models[standard_name] = synthetic_model
                self._logger.info(
                    f"Created synthetic base model for CRIS-only model '{standard_name}' "
                    f"(CRIS name: '{cris_name}', Profile: {cris_model_info.inference_profile_id})"
                )
            except Exception as e:
                self._logger.warning(
                    f"Failed to create synthetic base model for '{cris_name}': {str(e)}"
                )

        # Create new catalog with synthetic models added
        if synthetic_models:
            merged_models = {**model_catalog.models, **synthetic_models}
            return ModelCatalog(
                retrieval_timestamp=model_catalog.retrieval_timestamp, models=merged_models
            )

        return model_catalog

    def _create_synthetic_base_model(self, cris_model_info: CRISModelInfo) -> BedrockModelInfo:
        """
        Create synthetic base model entry for CRIS-only models.

        Args:
            cris_model_info: CRIS model info to create base entry from

        Returns:
            Synthetic BedrockModelInfo
        """
        # Use source regions as supported regions with * marker
        source_regions = cris_model_info.get_source_regions()
        regions_with_marker = [f"{region}*" for region in source_regions]

        # Extract provider from inference profile ID
        profile_id = cris_model_info.inference_profile_id
        provider = self._extract_provider_from_profile_id(profile_id)

        return BedrockModelInfo(
            provider=provider,
            model_id=profile_id,  # Use profile ID as model ID
            regions_supported=regions_with_marker,
            input_modalities=["Text"],  # Default assumption
            output_modalities=["Text"],
            streaming_supported=True,  # Default assumption
            inference_parameters_link=None,
            hyperparameters_link=None,
        )

    def _expand_marker_in_region_mappings(
        self, region_mappings: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Expand commercial regions marker in region mappings.

        This method replaces the COMMERCIAL_REGIONS_MARKER with the actual
        list of commercial AWS regions at runtime.

        Args:
            region_mappings: Region mappings that may contain markers

        Returns:
            Region mappings with markers expanded
        """
        expanded = {}
        for source, destinations in region_mappings.items():
            expanded_dests = []
            for dest in destinations:
                if dest == CRISGlobalConstants.COMMERCIAL_REGIONS_MARKER:
                    expanded_dests.extend(CRISGlobalConstants.COMMERCIAL_AWS_REGIONS)
                else:
                    expanded_dests.append(dest)
            expanded[source] = list(set(expanded_dests))  # Remove duplicates
        return expanded

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
