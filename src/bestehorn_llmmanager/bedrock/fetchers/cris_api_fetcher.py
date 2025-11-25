"""
CRIS API Fetcher for retrieving inference profile data from AWS Bedrock API.

This module provides functionality to fetch Cross-Region Inference Service (CRIS)
data from AWS Bedrock APIs across multiple regions in parallel.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from botocore.exceptions import BotoCoreError, ClientError

from ..auth.auth_manager import AuthManager
from ..models.cris_structures import CRISInferenceProfile, CRISModelInfo


class CRISAPIFetcherError(Exception):
    """Exception raised for CRIS API fetching errors."""

    pass


class CRISAPIFetcher:
    """
    Fetches CRIS data from AWS Bedrock API across multiple regions.

    This class queries the ListInferenceProfiles API in parallel across
    all Bedrock-enabled regions to build a comprehensive catalog of
    Cross-Region Inference models and their region mappings.

    Features:
    - Parallel execution across regions using ThreadPoolExecutor
    - Graceful per-region error handling
    - Automatic data transformation to CRISModelInfo structures
    - Region mapping extraction from model ARNs

    Example:
        >>> auth = AuthManager()
        >>> fetcher = CRISAPIFetcher(auth_manager=auth)
        >>> models = fetcher.fetch_cris_data(['us-east-1', 'us-west-2'])
        >>> print(f"Found {len(models)} CRIS models")
    """

    def __init__(self, auth_manager: AuthManager, max_workers: int = 10) -> None:
        """
        Initialize the CRIS API fetcher.

        Args:
            auth_manager: AuthManager instance for AWS authentication
            max_workers: Maximum number of parallel workers for region queries
        """
        self._auth_manager = auth_manager
        self._max_workers = max_workers
        self._logger = logging.getLogger(__name__)

    def fetch_cris_data(self, regions: List[str]) -> Dict[str, CRISModelInfo]:
        """
        Fetch CRIS data from all specified regions in parallel.

        This method queries the ListInferenceProfiles API in each region
        simultaneously, then merges the results into a unified catalog.

        Args:
            regions: List of AWS region identifiers to query

        Returns:
            Dictionary mapping model names to CRISModelInfo objects

        Raises:
            CRISAPIFetcherError: If all regions fail or no data is retrieved
        """
        if not regions:
            raise CRISAPIFetcherError("No regions provided for CRIS data fetch")

        self._logger.info(f"Fetching CRIS data from {len(regions)} regions in parallel")

        # Collect all inference profiles from all regions
        all_profiles = []
        failed_regions = []

        # Use ThreadPoolExecutor for parallel region queries
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit tasks for each region
            future_to_region = {
                executor.submit(self._fetch_region_profiles, region): region for region in regions
            }

            # Collect results as they complete
            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    profiles = future.result()
                    if profiles:
                        all_profiles.extend(profiles)
                        self._logger.debug(f"Retrieved {len(profiles)} profiles from {region}")
                    else:
                        self._logger.debug(f"No profiles found in {region}")
                except Exception as e:
                    failed_regions.append(region)
                    self._logger.warning(f"Failed to fetch from {region}: {str(e)}")

        # Log summary
        success_count = len(regions) - len(failed_regions)
        self._logger.info(
            f"Successfully queried {success_count}/{len(regions)} regions, "
            f"found {len(all_profiles)} total profiles"
        )

        if not all_profiles:
            if failed_regions:
                raise CRISAPIFetcherError(
                    f"Failed to retrieve CRIS data from any region. "
                    f"Failed regions: {', '.join(failed_regions)}"
                )
            else:
                self._logger.warning("No CRIS profiles found in any region")
                return {}

        # Transform profiles to CRISModelInfo structures
        try:
            models_dict = self._parse_profiles_to_models(all_profiles)
            self._logger.info(f"Transformed data into {len(models_dict)} CRIS models")
            return models_dict
        except Exception as e:
            raise CRISAPIFetcherError(
                f"Failed to transform API data to model structures: {str(e)}"
            ) from e

    def _fetch_region_profiles(self, region: str) -> List[Dict[str, Any]]:
        """
        Fetch inference profiles from a single region.

        Args:
            region: AWS region identifier

        Returns:
            List of inference profile dictionaries from API response

        Raises:
            Exception: If API call fails for this region
        """
        try:
            # Get bedrock control plane client for this region
            client = self._auth_manager.get_bedrock_control_client(region)

            # Call ListInferenceProfiles API
            response = client.list_inference_profiles()

            # Extract profiles from response
            profiles = response.get("inferenceProfileSummaries", [])

            # Tag each profile with its source region
            for profile in profiles:
                profile["_source_region"] = region

            return profiles  # type: ignore[no-any-return]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied to Bedrock in {region}. "
                    "Ensure proper IAM permissions for bedrock:ListInferenceProfiles"
                ) from e
            raise Exception(f"AWS API error in {region}: {str(e)}") from e
        except BotoCoreError as e:
            raise Exception(f"Boto3 error in {region}: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Unexpected error in {region}: {str(e)}") from e

    def _parse_profiles_to_models(self, profiles: List[Dict]) -> Dict[str, CRISModelInfo]:
        """
        Transform API profile data into CRISModelInfo structures.

        This method groups profiles by model name and builds region mappings
        by extracting regions from model ARNs.

        Args:
            profiles: List of inference profile dictionaries from API

        Returns:
            Dictionary mapping model names to CRISModelInfo objects
        """
        # Group profiles by base model name
        model_profiles: Dict[str, Dict[str, CRISInferenceProfile]] = {}

        for profile in profiles:
            try:
                # Extract key information
                profile_id = profile.get("inferenceProfileId", "")
                profile_name = profile.get("inferenceProfileName", "")
                models = profile.get("models", [])
                source_region = profile.get("_source_region", "unknown")

                if not profile_id or not models:
                    self._logger.debug(f"Skipping profile with missing data: {profile_id}")
                    continue

                # Extract model name (use profile name as base)
                model_name = self._extract_model_name(profile_name, profile_id)

                # Extract destination regions from model ARNs
                destination_regions = self._extract_regions_from_models(models)

                if not destination_regions:
                    self._logger.debug(f"No destination regions found for profile {profile_id}")
                    continue

                # Build region mapping for this profile
                # The source region is where this profile can be called from
                # The destination regions are where it can route requests to
                region_mappings = {source_region: destination_regions}

                # Check if this is a global profile (starts with "global.")
                is_global = profile_id.startswith("global.")

                # Create CRISInferenceProfile object
                cris_profile = CRISInferenceProfile(
                    inference_profile_id=profile_id,
                    region_mappings=region_mappings,
                    is_global=is_global,
                )

                # Add to model profiles dictionary
                if model_name not in model_profiles:
                    model_profiles[model_name] = {}

                model_profiles[model_name][profile_id] = cris_profile

            except Exception as e:
                self._logger.warning(
                    f"Error processing profile {profile.get('inferenceProfileId', 'unknown')}: {e}"
                )
                continue

        # Convert to CRISModelInfo objects
        models_dict = {}
        for model_name, profiles_map in model_profiles.items():
            try:
                model_info = CRISModelInfo(model_name=model_name, inference_profiles=profiles_map)
                models_dict[model_name] = model_info
            except Exception as e:
                self._logger.warning(f"Error creating CRISModelInfo for {model_name}: {e}")
                continue

        return models_dict

    def _extract_model_name(self, profile_name: str, profile_id: str) -> str:
        """
        Extract clean model name from profile information.

        Args:
            profile_name: Human-readable profile name from API
            profile_id: Profile identifier (e.g., 'us.amazon.nova-lite-v1:0')

        Returns:
            Cleaned model name suitable for use as a key
        """
        if profile_name:
            # Use profile name, cleaned up
            return profile_name.strip()

        # Fallback: extract from profile ID
        # Pattern: region.vendor.model-version
        # Example: us.amazon.nova-lite-v1:0 -> Nova Lite
        match = re.match(r"^(?:[\w-]+\.)?(.+?)(?:-v\d+)?:\d+$", profile_id)
        if match:
            model_part = match.group(1)
            # Convert kebab-case to Title Case
            return " ".join(word.capitalize() for word in model_part.split("-"))

        # Ultimate fallback: use profile ID as-is
        return profile_id

    def _extract_regions_from_models(self, models: List[Dict]) -> List[str]:
        """
        Extract region identifiers from model ARN list.

        Model ARNs have format:
        arn:aws:bedrock:REGION::foundation-model/MODEL_ID

        Args:
            models: List of model dictionaries with 'modelArn' field

        Returns:
            List of unique region identifiers extracted from ARNs
        """
        regions = set()

        for model in models:
            model_arn = model.get("modelArn", "")
            if not model_arn:
                continue

            # Parse ARN to extract region
            # Format: arn:aws:bedrock:REGION::foundation-model/MODEL_ID
            arn_parts = model_arn.split(":")
            if len(arn_parts) >= 4:
                region = arn_parts[3]
                if region:  # Ensure region is not empty
                    regions.add(region)

        return sorted(list(regions))

    def __repr__(self) -> str:
        """Return string representation of the fetcher."""
        return f"CRISAPIFetcher(max_workers={self._max_workers})"
