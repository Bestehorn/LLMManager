"""
API fetcher for AWS Bedrock model and CRIS data.

This module provides the BedrockAPIFetcher class which retrieves model and
inference profile data from AWS Bedrock APIs using parallel execution across
multiple regions.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import BotoCoreError, ClientError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..auth.auth_manager import AuthManager
from ..exceptions.llm_manager_exceptions import APIFetchError
from ..models.aws_regions import get_commercial_regions
from ..models.catalog_constants import (
    CatalogAPIParameters,
    CatalogAPIResponseFields,
    CatalogDefaults,
    CatalogErrorMessages,
    CatalogLogMessages,
)


class RawCatalogData:
    """
    Container for raw API response data from AWS Bedrock.

    Attributes:
        foundation_models: Dictionary mapping region to list of foundation model summaries
        inference_profiles: Dictionary mapping region to list of inference profile summaries
        successful_regions: List of regions that were successfully queried
        failed_regions: Dictionary mapping failed regions to their error messages
    """

    def __init__(self) -> None:
        """Initialize empty raw catalog data container."""
        self.foundation_models: Dict[str, List[Dict[str, Any]]] = {}
        self.inference_profiles: Dict[str, List[Dict[str, Any]]] = {}
        self.successful_regions: List[str] = []
        self.failed_regions: Dict[str, str] = {}

    def add_region_data(
        self,
        region: str,
        models: List[Dict[str, Any]],
        profiles: List[Dict[str, Any]],
    ) -> None:
        """
        Add data for a successfully queried region.

        Args:
            region: AWS region identifier
            models: List of foundation model summaries
            profiles: List of inference profile summaries
        """
        self.foundation_models[region] = models
        self.inference_profiles[region] = profiles
        self.successful_regions.append(region)

    def add_region_failure(self, region: str, error: str) -> None:
        """
        Record a failed region query.

        Args:
            region: AWS region identifier
            error: Error message describing the failure
        """
        self.failed_regions[region] = error

    @property
    def has_data(self) -> bool:
        """Check if any data was successfully retrieved."""
        return len(self.successful_regions) > 0

    @property
    def total_models(self) -> int:
        """Get total number of model summaries across all regions."""
        return sum(len(models) for models in self.foundation_models.values())

    @property
    def total_profiles(self) -> int:
        """Get total number of inference profiles across all regions."""
        return sum(len(profiles) for profiles in self.inference_profiles.values())


class BedrockAPIFetcher:
    """
    Fetches model and CRIS data from AWS Bedrock APIs.

    This class handles parallel API calls across multiple regions with retry logic
    and graceful error handling for per-region failures.
    """

    def __init__(
        self,
        auth_manager: AuthManager,
        timeout: int = CatalogDefaults.DEFAULT_API_TIMEOUT_SECONDS,
        max_workers: int = CatalogDefaults.DEFAULT_MAX_WORKERS,
        max_retries: int = CatalogDefaults.DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Initialize the Bedrock API fetcher.

        Args:
            auth_manager: Configured AuthManager for AWS authentication
            timeout: API call timeout in seconds
            max_workers: Maximum number of parallel workers for multi-region queries
            max_retries: Maximum number of retry attempts for failed API calls
        """
        self._logger = logging.getLogger(__name__)
        self._auth_manager = auth_manager
        self._timeout = timeout
        self._max_workers = max_workers
        self._max_retries = max_retries

        self._logger.debug(
            f"BedrockAPIFetcher initialized: timeout={timeout}s, "
            f"max_workers={max_workers}, max_retries={max_retries}"
        )

    def fetch_all_data(
        self,
        regions: Optional[List[str]] = None,
    ) -> RawCatalogData:
        """
        Fetch both model and CRIS data from all regions in parallel.

        This method queries multiple AWS regions concurrently using a thread pool.
        Per-region failures are handled gracefully - the method continues processing
        other regions and returns partial results.

        Args:
            regions: List of AWS regions to query. If None, uses default commercial regions.

        Returns:
            RawCatalogData containing API responses from all successful regions

        Raises:
            APIFetchError: If all regions fail or no data could be retrieved
        """
        import time

        target_regions = regions or get_commercial_regions()

        self._logger.info(CatalogLogMessages.API_FETCH_STARTED.format(regions=len(target_regions)))

        start_time = time.time()
        raw_data = RawCatalogData()

        # Use ThreadPoolExecutor for parallel region queries
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit all region queries
            future_to_region = {
                executor.submit(self._fetch_region_data, region): region
                for region in target_regions
            }

            # Collect results as they complete
            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    models, profiles = future.result()
                    raw_data.add_region_data(region=region, models=models, profiles=profiles)

                    self._logger.debug(
                        CatalogLogMessages.API_FETCH_REGION_COMPLETED.format(
                            region=region, models=len(models), profiles=len(profiles)
                        )
                    )

                except Exception as e:
                    error_msg = str(e)
                    raw_data.add_region_failure(region=region, error=error_msg)

                    self._logger.warning(
                        CatalogLogMessages.API_FETCH_REGION_FAILED.format(
                            region=region, error=error_msg
                        )
                    )

        # Check if we got any data
        if not raw_data.has_data:
            last_error = (
                list(raw_data.failed_regions.values())[0]
                if raw_data.failed_regions
                else "Unknown error"
            )
            raise APIFetchError(
                message=CatalogErrorMessages.API_FETCH_ALL_REGIONS_FAILED.format(
                    count=len(target_regions), error=last_error
                ),
                region="all",
            )

        duration = time.time() - start_time
        self._logger.info(
            CatalogLogMessages.API_FETCH_COMPLETED.format(
                success=len(raw_data.successful_regions),
                total=len(target_regions),
                duration=duration,
            )
        )

        return raw_data

    def _fetch_region_data(self, region: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch both foundation models and inference profiles for a single region.

        Args:
            region: AWS region identifier

        Returns:
            Tuple of (foundation_models, inference_profiles)

        Raises:
            Exception: If fetching fails for this region
        """
        self._logger.debug(CatalogLogMessages.API_FETCH_REGION_STARTED.format(region=region))

        # Fetch both types of data
        models = self._fetch_foundation_models(region=region)
        profiles = self._fetch_inference_profiles(region=region)

        return models, profiles

    @retry(
        stop=stop_after_attempt(CatalogDefaults.DEFAULT_MAX_RETRIES),
        wait=wait_exponential(
            multiplier=CatalogDefaults.DEFAULT_RETRY_MULTIPLIER,
            min=CatalogDefaults.DEFAULT_RETRY_MIN_WAIT_SECONDS,
            max=CatalogDefaults.DEFAULT_RETRY_MAX_WAIT_SECONDS,
        ),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        reraise=True,
    )
    def _fetch_foundation_models(self, region: str) -> List[Dict[str, Any]]:
        """
        Fetch foundation models from a single region with retry logic.

        Uses the AWS Bedrock list-foundation-models API with exponential backoff
        retry for transient errors.

        Args:
            region: AWS region identifier

        Returns:
            List of foundation model summaries

        Raises:
            ClientError: If API call fails after retries
            BotoCoreError: If boto3 client error occurs
        """
        try:
            # Get Bedrock control plane client for this region
            client = self._auth_manager.get_bedrock_control_client(region=region)

            # Call list-foundation-models API
            response = client.list_foundation_models()

            # Extract model summaries from response
            model_summaries = response.get(CatalogAPIResponseFields.MODEL_SUMMARIES, [])

            if not isinstance(model_summaries, list):
                raise APIFetchError(
                    message=CatalogErrorMessages.API_FETCH_INVALID_RESPONSE.format(
                        error="MODEL_SUMMARIES is not a list"
                    ),
                    region=region,
                )

            return model_summaries

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            # Handle specific error cases
            if error_code == "AccessDeniedException":
                raise APIFetchError(
                    message=CatalogErrorMessages.API_FETCH_AUTH_ERROR.format(error=str(e)),
                    region=region,
                ) from e
            elif error_code == "ThrottlingException":
                raise APIFetchError(
                    message=CatalogErrorMessages.API_FETCH_THROTTLED.format(error=str(e)),
                    region=region,
                ) from e
            else:
                # Re-raise for retry logic to handle
                raise

        except BotoCoreError:
            # Re-raise for retry logic to handle
            raise

        except Exception as e:
            raise APIFetchError(
                message=f"Unexpected error fetching foundation models: {str(e)}",
                region=region,
            ) from e

    @retry(
        stop=stop_after_attempt(CatalogDefaults.DEFAULT_MAX_RETRIES),
        wait=wait_exponential(
            multiplier=CatalogDefaults.DEFAULT_RETRY_MULTIPLIER,
            min=CatalogDefaults.DEFAULT_RETRY_MIN_WAIT_SECONDS,
            max=CatalogDefaults.DEFAULT_RETRY_MAX_WAIT_SECONDS,
        ),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        reraise=True,
    )
    def _fetch_inference_profiles(self, region: str) -> List[Dict[str, Any]]:
        """
        Fetch inference profiles from a single region with retry logic.

        Uses the AWS Bedrock list-inference-profiles API with exponential backoff
        retry for transient errors. Filters for SYSTEM_DEFINED profiles only.

        Args:
            region: AWS region identifier

        Returns:
            List of inference profile summaries (SYSTEM_DEFINED only)

        Raises:
            ClientError: If API call fails after retries
            BotoCoreError: If boto3 client error occurs
        """
        try:
            # Get Bedrock control plane client for this region
            client = self._auth_manager.get_bedrock_control_client(region=region)

            # Call list-inference-profiles API with SYSTEM_DEFINED filter
            response = client.list_inference_profiles(
                **{CatalogAPIParameters.PROFILE_TYPE_EQUALS: CatalogAPIParameters.SYSTEM_DEFINED}
            )

            # Extract inference profile summaries from response
            profile_summaries = response.get(
                CatalogAPIResponseFields.INFERENCE_PROFILE_SUMMARIES, []
            )

            if not isinstance(profile_summaries, list):
                raise APIFetchError(
                    message=CatalogErrorMessages.API_FETCH_INVALID_RESPONSE.format(
                        error="INFERENCE_PROFILE_SUMMARIES is not a list"
                    ),
                    region=region,
                )

            return profile_summaries

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            # Handle specific error cases
            if error_code == "AccessDeniedException":
                raise APIFetchError(
                    message=CatalogErrorMessages.API_FETCH_AUTH_ERROR.format(error=str(e)),
                    region=region,
                ) from e
            elif error_code == "ThrottlingException":
                raise APIFetchError(
                    message=CatalogErrorMessages.API_FETCH_THROTTLED.format(error=str(e)),
                    region=region,
                ) from e
            else:
                # Re-raise for retry logic to handle
                raise

        except BotoCoreError:
            # Re-raise for retry logic to handle
            raise

        except Exception as e:
            raise APIFetchError(
                message=f"Unexpected error fetching inference profiles: {str(e)}",
                region=region,
            ) from e
