"""
Data transformer for AWS Bedrock catalog data.

This module provides the CatalogTransformer class which transforms raw API
response data into unified catalog structures, correlating model and CRIS data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..correlators.model_cris_correlator import ModelCRISCorrelator
from ..models.catalog_constants import (
    CatalogAPIResponseFields,
    CatalogErrorMessages,
    CatalogLogMessages,
)
from ..models.catalog_structures import CatalogMetadata, CatalogSource, UnifiedCatalog
from ..models.cris_structures import CRISCatalog, CRISInferenceProfile, CRISModelInfo
from ..models.data_structures import BedrockModelInfo, ModelCatalog
from .api_fetcher import RawCatalogData


class CatalogTransformer:
    """
    Transforms raw API data into unified catalog structures.

    This class handles the transformation of AWS Bedrock API responses into
    structured data models and correlates model and CRIS data using the
    existing ModelCRISCorrelator.
    """

    def __init__(
        self,
        enable_fuzzy_matching: Optional[bool] = None,
    ) -> None:
        """
        Initialize the catalog transformer.

        Args:
            enable_fuzzy_matching: Whether to enable fuzzy matching in correlation.
                                  If None, uses default from ModelCRISCorrelator.
        """
        self._logger = logging.getLogger(__name__)
        self._correlator = ModelCRISCorrelator(enable_fuzzy_matching=enable_fuzzy_matching)

        self._logger.debug(
            f"CatalogTransformer initialized with fuzzy_matching={enable_fuzzy_matching}"
        )

    def transform_api_data(
        self,
        raw_data: RawCatalogData,
        retrieval_timestamp: Optional[datetime] = None,
    ) -> UnifiedCatalog:
        """
        Transform raw API responses into unified catalog.

        This method orchestrates the complete transformation process:
        1. Transform foundation models data
        2. Transform inference profiles data
        3. Correlate the two datasets
        4. Create unified catalog with metadata

        Args:
            raw_data: Raw API responses from fetcher
            retrieval_timestamp: Timestamp of data retrieval. If None, uses current time.

        Returns:
            UnifiedCatalog with correlated data

        Raises:
            ValueError: If transformation fails
        """
        self._logger.info(CatalogLogMessages.TRANSFORMATION_STARTED)

        if not raw_data.has_data:
            raise ValueError(CatalogErrorMessages.TRANSFORMATION_NO_DATA)

        # Use provided timestamp or current time
        timestamp = retrieval_timestamp or datetime.now()

        try:
            # Transform foundation models
            model_catalog = self._transform_models(
                raw_data=raw_data,
                retrieval_timestamp=timestamp,
            )

            self._logger.info(
                CatalogLogMessages.TRANSFORMATION_MODELS_COMPLETED.format(
                    count=model_catalog.model_count
                )
            )

            # Transform CRIS data
            cris_catalog = self._transform_cris(
                raw_data=raw_data,
                retrieval_timestamp=timestamp,
            )

            self._logger.info(
                CatalogLogMessages.TRANSFORMATION_CRIS_COMPLETED.format(
                    count=cris_catalog.model_count
                )
            )

            # Correlate data
            unified_catalog_data = self._correlate_data(
                model_catalog=model_catalog,
                cris_catalog=cris_catalog,
            )

            # Create metadata
            metadata = CatalogMetadata(
                source=CatalogSource.API,
                retrieval_timestamp=timestamp,
                api_regions_queried=raw_data.successful_regions,
                bundled_data_version=None,
                cache_file_path=None,
            )

            # Create final unified catalog
            unified_catalog = UnifiedCatalog(
                models=unified_catalog_data.unified_models,
                metadata=metadata,
            )

            self._logger.info(
                CatalogLogMessages.TRANSFORMATION_COMPLETED.format(
                    count=unified_catalog.model_count
                )
            )

            return unified_catalog

        except Exception as e:
            error_msg = CatalogErrorMessages.TRANSFORMATION_FAILED.format(error=str(e))
            self._logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _transform_models(
        self,
        raw_data: RawCatalogData,
        retrieval_timestamp: datetime,
    ) -> ModelCatalog:
        """
        Transform foundation models API data.

        Processes raw API responses and creates BedrockModelInfo structures
        for each model, handling missing or malformed data gracefully.

        Args:
            raw_data: Raw API responses
            retrieval_timestamp: Timestamp for the catalog

        Returns:
            ModelCatalog with transformed model data
        """
        models: Dict[str, BedrockModelInfo] = {}

        # Process models from all regions
        for region, model_summaries in raw_data.foundation_models.items():
            for model_summary in model_summaries:
                try:
                    # Extract model information from API response
                    model_info = self._extract_model_info(
                        model_summary=model_summary,
                        source_region=region,
                    )

                    if model_info:
                        # Use model name as key (extract from model_id)
                        model_name = self._extract_model_name(model_info.model_id)

                        # Merge with existing model if already processed from another region
                        if model_name in models:
                            models[model_name] = self._merge_model_info(
                                existing=models[model_name],
                                new=model_info,
                            )
                        else:
                            models[model_name] = model_info

                except Exception as e:
                    self._logger.warning(
                        f"Failed to process model summary from region {region}: {str(e)}"
                    )
                    continue

        return ModelCatalog(
            retrieval_timestamp=retrieval_timestamp,
            models=models,
        )

    def _transform_cris(
        self,
        raw_data: RawCatalogData,
        retrieval_timestamp: datetime,
    ) -> CRISCatalog:
        """
        Transform CRIS inference profiles API data.

        Processes raw API responses and creates CRISModelInfo structures,
        identifying global vs regional profiles and building region mappings.

        Args:
            raw_data: Raw API responses
            retrieval_timestamp: Timestamp for the catalog

        Returns:
            CRISCatalog with transformed CRIS data
        """
        # Group profiles by model
        model_profiles: Dict[str, Dict[str, CRISInferenceProfile]] = {}

        # Process inference profiles from all regions
        for region, profile_summaries in raw_data.inference_profiles.items():
            for profile_summary in profile_summaries:
                try:
                    # Extract profile information
                    profile_info = self._extract_profile_info(
                        profile_summary=profile_summary,
                        source_region=region,
                    )

                    if profile_info:
                        # Extract model name from profile
                        model_name = self._extract_model_name_from_profile(
                            profile_info.inference_profile_id
                        )

                        # Add to model's profile collection
                        if model_name not in model_profiles:
                            model_profiles[model_name] = {}

                        profile_id = profile_info.inference_profile_id
                        if profile_id not in model_profiles[model_name]:
                            model_profiles[model_name][profile_id] = profile_info
                        else:
                            # Merge region mappings if profile already exists
                            existing = model_profiles[model_name][profile_id]
                            merged_mappings = self._merge_region_mappings(
                                existing.region_mappings,
                                profile_info.region_mappings,
                            )
                            model_profiles[model_name][profile_id] = CRISInferenceProfile(
                                inference_profile_id=profile_id,
                                region_mappings=merged_mappings,
                                is_global=existing.is_global,
                            )

                except Exception as e:
                    self._logger.warning(
                        f"Failed to process inference profile from region {region}: {str(e)}"
                    )
                    continue

        # Create CRISModelInfo objects
        cris_models: Dict[str, CRISModelInfo] = {}
        for model_name, profiles in model_profiles.items():
            try:
                cris_models[model_name] = CRISModelInfo(
                    model_name=model_name,
                    inference_profiles=profiles,
                )
            except Exception as e:
                self._logger.warning(f"Failed to create CRISModelInfo for {model_name}: {str(e)}")
                continue

        return CRISCatalog(
            retrieval_timestamp=retrieval_timestamp,
            cris_models=cris_models,
        )

    def _correlate_data(
        self,
        model_catalog: ModelCatalog,
        cris_catalog: CRISCatalog,
    ) -> Any:  # Returns UnifiedModelCatalog from correlator
        """
        Correlate models with CRIS profiles using existing ModelCRISCorrelator.

        This method delegates to the existing correlation logic which handles:
        - Matching models with CRIS profiles
        - Building unified access information
        - Handling models without CRIS profiles
        - Handling CRIS profiles without matching models

        Args:
            model_catalog: Transformed model catalog
            cris_catalog: Transformed CRIS catalog

        Returns:
            UnifiedModelCatalog with correlated data
        """
        self._logger.info("Starting model-CRIS correlation")

        try:
            unified_catalog = self._correlator.correlate_catalogs(
                model_catalog=model_catalog,
                cris_catalog=cris_catalog,
            )

            # Log correlation statistics
            stats = self._correlator.get_correlation_stats()
            self._logger.info(
                f"Correlation completed: {stats['matched_models']} matched, "
                f"{stats['fuzzy_matched_models']} fuzzy matched, "
                f"{stats['cris_only_models']} CRIS-only, "
                f"{stats['unmatched_regular_models']} unmatched regular models"
            )

            return unified_catalog

        except Exception as e:
            error_msg = f"Correlation failed: {str(e)}"
            self._logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _extract_model_info(
        self,
        model_summary: Dict[str, Any],
        source_region: str,
    ) -> Optional[BedrockModelInfo]:
        """
        Extract BedrockModelInfo from API model summary.

        Handles missing or malformed data gracefully by using defaults
        and logging warnings for incomplete data.

        Args:
            model_summary: Model summary from API response
            source_region: Region where this data came from

        Returns:
            BedrockModelInfo if extraction successful, None otherwise
        """
        try:
            # Extract required fields
            model_id = model_summary.get(CatalogAPIResponseFields.MODEL_ID)
            if not model_id:
                self._logger.warning(
                    f"Model summary missing MODEL_ID in region {source_region}, skipping"
                )
                return None

            provider = model_summary.get(CatalogAPIResponseFields.PROVIDER_NAME, "Unknown")

            # Extract modalities with defaults
            input_modalities = model_summary.get(CatalogAPIResponseFields.INPUT_MODALITIES, [])
            if not isinstance(input_modalities, list):
                self._logger.warning(
                    f"Invalid INPUT_MODALITIES for {model_id}, using default ['Text']"
                )
                input_modalities = ["Text"]

            output_modalities = model_summary.get(CatalogAPIResponseFields.OUTPUT_MODALITIES, [])
            if not isinstance(output_modalities, list):
                self._logger.warning(
                    f"Invalid OUTPUT_MODALITIES for {model_id}, using default ['Text']"
                )
                output_modalities = ["Text"]

            # Extract streaming support
            streaming_supported = model_summary.get(
                CatalogAPIResponseFields.RESPONSE_STREAMING_SUPPORTED, False
            )
            if not isinstance(streaming_supported, bool):
                self._logger.warning(
                    f"Invalid RESPONSE_STREAMING_SUPPORTED for {model_id}, using False"
                )
                streaming_supported = False

            # Region is the source region where we found this model
            regions_supported = [source_region]

            # Extract inference types supported (new field for determining direct access)
            inference_types_supported = model_summary.get(
                CatalogAPIResponseFields.INFERENCE_TYPES_SUPPORTED
            )
            if inference_types_supported is not None:
                if not isinstance(inference_types_supported, list):
                    self._logger.warning(
                        f"Invalid INFERENCE_TYPES_SUPPORTED for {model_id}, using None"
                    )
                    inference_types_supported = None
            # If None, it means the field wasn't in the API response (backward compatibility)

            # Extract optional documentation links
            # Note: These may not be in the API response, so we use None as default
            inference_parameters_link = None
            hyperparameters_link = None

            return BedrockModelInfo(
                provider=provider,
                model_id=model_id,
                regions_supported=regions_supported,
                input_modalities=input_modalities,
                output_modalities=output_modalities,
                streaming_supported=streaming_supported,
                inference_parameters_link=inference_parameters_link,
                hyperparameters_link=hyperparameters_link,
                inference_types_supported=inference_types_supported,
            )

        except Exception as e:
            self._logger.warning(
                f"Failed to extract model info from summary in region {source_region}: {str(e)}"
            )
            return None

    def _extract_profile_info(
        self,
        profile_summary: Dict[str, Any],
        source_region: str,
    ) -> Optional[CRISInferenceProfile]:
        """
        Extract CRISInferenceProfile from API profile summary.

        Identifies global vs regional profiles and builds region mappings
        from the API response structure.

        Args:
            profile_summary: Profile summary from API response
            source_region: Region where this data came from

        Returns:
            CRISInferenceProfile if extraction successful, None otherwise
        """
        try:
            # Extract inference profile ID
            profile_id = profile_summary.get(CatalogAPIResponseFields.INFERENCE_PROFILE_ID)
            if not profile_id:
                self._logger.warning(
                    f"Profile summary missing INFERENCE_PROFILE_ID in region {source_region}, skipping"
                )
                return None

            # Determine if this is a global profile
            is_global = profile_id.startswith("global.")

            # Extract models array to build region mappings
            models = profile_summary.get(CatalogAPIResponseFields.MODELS, [])
            if not isinstance(models, list):
                self._logger.warning(
                    f"Invalid MODELS field for profile {profile_id}, using empty list"
                )
                models = []

            # Build region mappings from models array
            # The API returns models with modelArn that contains region information
            region_mappings = self._build_region_mappings_from_models(
                models=models,
                source_region=source_region,
                profile_id=profile_id,
            )

            # If no region mappings could be built, use source region as default
            if not region_mappings:
                self._logger.debug(
                    f"No region mappings found for profile {profile_id}, "
                    f"using source region {source_region} as default"
                )
                region_mappings = {source_region: [source_region]}

            return CRISInferenceProfile(
                inference_profile_id=profile_id,
                region_mappings=region_mappings,
                is_global=is_global,
            )

        except Exception as e:
            self._logger.debug(
                f"Failed to extract profile info from summary in region {source_region}: {str(e)}"
            )
            return None

    def _build_region_mappings_from_models(
        self,
        models: List[Dict[str, Any]],
        source_region: str,
        profile_id: str,
    ) -> Dict[str, List[str]]:
        """
        Build region mappings from models array in inference profile.

        The models array contains information about which models are available
        and their ARNs, which include region information.

        Args:
            models: Models array from inference profile summary
            source_region: Source region where profile was found
            profile_id: Inference profile ID for logging

        Returns:
            Dictionary mapping source regions to destination regions
        """
        region_mappings: Dict[str, List[str]] = {}

        # For each model in the profile, extract region information
        for model in models:
            if not isinstance(model, dict):
                continue

            # Extract model ARN which contains region info
            # Format: arn:aws:bedrock:region:account:foundation-model/model-id
            model_arn = model.get("modelArn", "")

            if model_arn:
                # Extract region from ARN
                # Format: arn:aws:bedrock:region:account:foundation-model/model-id
                # Issue #21: global inference profiles carry a region-less model ARN
                # (arn:aws:bedrock:::foundation-model/...), so arn_parts[3] is an EMPTY
                # string. Skipping empty regions prevents an invalid empty destination
                # region from being recorded (which previously caused CRISInferenceProfile
                # validation to reject the whole global profile, dropping it entirely).
                # With no explicit mapping, the caller falls back to
                # {source_region: [source_region]}, keeping the global profile available
                # from the region it was listed in.
                arn_parts = model_arn.split(":")
                if len(arn_parts) >= 4:
                    model_region = arn_parts[3]

                    if model_region:
                        # Add mapping: source_region -> model_region
                        if source_region not in region_mappings:
                            region_mappings[source_region] = []

                        if model_region not in region_mappings[source_region]:
                            region_mappings[source_region].append(model_region)

        # If we found mappings, sort them for consistency
        if region_mappings:
            for source in region_mappings:
                region_mappings[source] = sorted(region_mappings[source])

        return region_mappings

    def _extract_model_name(self, model_id: str) -> str:
        """
        Extract clean model name from model ID.

        Converts model IDs to human-readable names by:
        1. Removing provider prefix (e.g., "anthropic.")
        2. Converting hyphens to spaces
        3. Capitalizing words
        4. Removing version suffixes

        Examples:
            "anthropic.claude-3-5-haiku-20241022-v1:0" -> "Claude 3 5 Haiku 20241022"
            "amazon.titan-text-express-v1" -> "Titan Text Express"
            "meta.llama3-70b-instruct-v1:0" -> "Llama3 70b Instruct"

        Args:
            model_id: Full model ID

        Returns:
            Clean model name
        """
        # Remove provider prefix (everything before first dot)
        if "." in model_id:
            name_part = model_id.split(".", 1)[1]
        else:
            name_part = model_id

        # Remove version suffix (everything after last colon)
        if ":" in name_part:
            name_part = name_part.rsplit(":", 1)[0]

        # Remove common version patterns at the end
        # e.g., "-v1", "-v2", "-v1.0"
        import re

        name_part = re.sub(r"-v\d+(\.\d+)?$", "", name_part)

        # Convert hyphens to spaces and capitalize
        words = name_part.split("-")
        capitalized_words = [word.capitalize() for word in words if word]

        return " ".join(capitalized_words)

    def _extract_model_name_from_profile(self, profile_id: str) -> str:
        """
        Extract model name from inference profile ID.

        The region/geo prefix (global., us., eu., apac., jp., au., …) is stripped so that
        ALL profiles for the same foundation model — regional AND global — map to the SAME
        model name and are grouped into a single CRISModelInfo (issue #21). This lets a
        model carry both its geographic CRIS profiles and its global CRIS profile, which the
        correlator then exposes per region so callers can choose between them (geographic for
        data residency vs. global for cost/throughput — see AWS cross-Region inference docs).

        Note: previously a "global." profile was prefixed with "Global " to form a separate
        CRIS model. That caused the global profile to either be dropped (no matching base
        model) or to REPLACE the regional profiles via global-priority matching. Grouping by
        the prefix-stripped name avoids both.

        Examples:
            "global.anthropic.claude-3-5-haiku-20241022-v1:0" -> "Anthropic Claude 3 5 Haiku 20241022"
            "us.anthropic.claude-3-5-haiku-20241022-v1:0"     -> "Anthropic Claude 3 5 Haiku 20241022"
            "eu.amazon.titan-text-express-v1"                 -> "Amazon Titan Text Express"

        Args:
            profile_id: Inference profile ID

        Returns:
            Model name (provider + model), without any region/geo prefix
        """
        # Remove regional/global prefix (global., us., eu., apac., jp., au., etc.)
        parts = profile_id.split(".", 2)  # Split into at most 3 parts
        if len(parts) >= 3:
            # Format: region.provider.model-id
            provider = parts[1].capitalize()
            model_part = parts[2]
        elif len(parts) == 2:
            # Format: provider.model-id (no region prefix)
            provider = parts[0].capitalize()
            model_part = parts[1]
        else:
            # Fallback: use the whole ID
            return self._extract_model_name(model_id=profile_id)

        # Remove version suffix
        if ":" in model_part:
            model_part = model_part.rsplit(":", 1)[0]

        # Remove common version patterns
        import re

        model_part = re.sub(r"-v\d+(\.\d+)?$", "", model_part)

        # Convert hyphens to spaces and capitalize
        words = model_part.split("-")
        capitalized_words = [word.capitalize() for word in words if word]
        model_name = " ".join(capitalized_words)

        # Construct full name with provider (no "Global " prefix — see docstring)
        return f"{provider} {model_name}"

    def _merge_model_info(
        self,
        existing: BedrockModelInfo,
        new: BedrockModelInfo,
    ) -> BedrockModelInfo:
        """
        Merge model information from multiple regions.

        Args:
            existing: Existing model info
            new: New model info to merge

        Returns:
            Merged BedrockModelInfo
        """
        # Merge regions
        merged_regions = list(set(existing.regions_supported + new.regions_supported))

        # Merge modalities
        merged_input = list(set(existing.input_modalities + new.input_modalities))
        merged_output = list(set(existing.output_modalities + new.output_modalities))

        # Merge inference types supported
        # If either is None, use the non-None value; if both have values, combine them
        merged_inference_types = None
        if (
            existing.inference_types_supported is not None
            and new.inference_types_supported is not None
        ):
            merged_inference_types = sorted(
                list(set(existing.inference_types_supported + new.inference_types_supported))
            )
        elif existing.inference_types_supported is not None:
            merged_inference_types = existing.inference_types_supported
        elif new.inference_types_supported is not None:
            merged_inference_types = new.inference_types_supported

        return BedrockModelInfo(
            provider=existing.provider,
            model_id=existing.model_id,
            regions_supported=sorted(merged_regions),
            input_modalities=sorted(merged_input),
            output_modalities=sorted(merged_output),
            streaming_supported=existing.streaming_supported or new.streaming_supported,
            inference_parameters_link=existing.inference_parameters_link
            or new.inference_parameters_link,
            hyperparameters_link=existing.hyperparameters_link or new.hyperparameters_link,
            inference_types_supported=merged_inference_types,
        )

    def _merge_region_mappings(
        self,
        existing: Dict[str, List[str]],
        new: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """
        Merge region mappings from multiple sources.

        Args:
            existing: Existing region mappings
            new: New region mappings to merge

        Returns:
            Merged region mappings
        """
        merged = existing.copy()

        for source_region, dest_regions in new.items():
            if source_region in merged:
                # Merge destination regions
                merged[source_region] = sorted(list(set(merged[source_region] + dest_regions)))
            else:
                merged[source_region] = dest_regions

        return merged
