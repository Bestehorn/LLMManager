"""
AWS Bedrock Region Discovery with caching.

This module provides dynamic discovery of Bedrock-enabled AWS regions,
with file-based caching to minimize AWS API calls.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class RegionDiscoveryError(Exception):
    """Exception raised for region discovery errors."""

    pass


class BedrockRegionDiscovery:
    """
    Discovers AWS Bedrock-enabled regions dynamically.

    This class provides dynamic discovery of AWS regions that support
    Amazon Bedrock, with file-based caching to reduce API calls.

    Features:
    - Dynamic region discovery via boto3
    - File-based caching with configurable TTL
    - Thread-safe implementation
    - Automatic cache invalidation

    Example:
        >>> discovery = BedrockRegionDiscovery()
        >>> regions = discovery.get_bedrock_regions()
        >>> print(f"Found {len(regions)} Bedrock regions")
        Found 15 Bedrock regions
    """

    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl_hours: int = 24) -> None:
        """
        Initialize the region discovery service.

        Args:
            cache_dir: Directory to store cache files. Defaults to docs/ directory.
            cache_ttl_hours: Time-to-live for cached data in hours. Defaults to 24.
        """
        self._logger = logging.getLogger(__name__)
        self._cache_ttl_hours = cache_ttl_hours
        self._lock = Lock()  # Thread-safe operations

        # Set cache directory and file path
        if cache_dir is None:
            # Default to docs directory relative to project root
            self._cache_dir = Path(__file__).parent.parent.parent.parent.parent / "docs"
        else:
            self._cache_dir = cache_dir

        self._cache_file = self._cache_dir / "bedrock_regions.json"

        # Create cache directory if it doesn't exist
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get_bedrock_regions(self, force_refresh: bool = False) -> List[str]:
        """
        Get list of Bedrock-enabled AWS regions.

        This method returns a list of AWS regions that support Amazon Bedrock.
        Results are cached to minimize AWS API calls.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data from AWS.

        Returns:
            Sorted list of region identifiers (e.g., ['us-east-1', 'us-west-2', ...])

        Raises:
            RegionDiscoveryError: If region discovery fails
        """
        with self._lock:
            # Try to load from cache if not forcing refresh
            if not force_refresh:
                cached_regions = self._load_cached_regions()
                if cached_regions is not None:
                    self._logger.debug(f"Loaded {len(cached_regions)} regions from cache")
                    return cached_regions

            # Fetch fresh data from AWS
            try:
                regions = self._fetch_regions_from_aws()
                self._save_cached_regions(regions)
                self._logger.info(f"Discovered {len(regions)} Bedrock regions from AWS")
                return regions
            except Exception as e:
                error_msg = f"Failed to discover Bedrock regions: {str(e)}"
                self._logger.error(error_msg)
                raise RegionDiscoveryError(error_msg) from e

    def _fetch_regions_from_aws(self) -> List[str]:
        """
        Fetch list of Bedrock-enabled regions from AWS.

        Uses boto3 to dynamically discover regions that support the
        Amazon Bedrock service.

        Returns:
            Sorted list of region identifiers

        Raises:
            RegionDiscoveryError: If AWS API call fails
        """
        try:
            # Create a session (uses default credentials)
            session = boto3.Session()

            # Get all regions that support the 'bedrock' service
            regions = session.get_available_regions("bedrock")

            if not regions:
                raise RegionDiscoveryError(
                    "No Bedrock regions found. This may indicate a boto3 version issue "
                    "or AWS API changes."
                )

            # Return sorted list for consistency
            return sorted(regions)

        except (BotoCoreError, ClientError) as e:
            raise RegionDiscoveryError(f"AWS API error during region discovery: {str(e)}") from e
        except Exception as e:
            raise RegionDiscoveryError(f"Unexpected error during region discovery: {str(e)}") from e

    def _load_cached_regions(self) -> Optional[List[str]]:
        """
        Load cached region data from file.

        Returns:
            List of regions if cache is valid, None otherwise
        """
        if not self._cache_file.exists():
            self._logger.debug("Cache file does not exist")
            return None

        try:
            # Read cache file
            with open(self._cache_file, "r") as f:
                cache_data = json.load(f)

            # Validate cache structure
            if not isinstance(cache_data, dict):
                self._logger.warning("Invalid cache structure, ignoring cache")
                return None

            if "retrieval_timestamp" not in cache_data or "regions" not in cache_data:
                self._logger.warning("Missing required fields in cache, ignoring cache")
                return None

            # Check if cache is still valid
            if not self._is_cache_valid(cache_data["retrieval_timestamp"]):
                self._logger.debug("Cache has expired")
                return None

            regions = cache_data["regions"]
            if not isinstance(regions, list):
                self._logger.warning("Invalid regions format in cache")
                return None

            return regions

        except json.JSONDecodeError as e:
            self._logger.warning(f"Failed to parse cache file: {e}")
            return None
        except Exception as e:
            self._logger.warning(f"Error loading cache: {e}")
            return None

    def _save_cached_regions(self, regions: List[str]) -> None:
        """
        Save region data to cache file.

        Args:
            regions: List of region identifiers to cache
        """
        try:
            cache_data = {
                "retrieval_timestamp": datetime.now().isoformat(),
                "regions": regions,
            }

            with open(self._cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            self._logger.debug(f"Saved {len(regions)} regions to cache")

        except Exception as e:
            # Log warning but don't fail - caching is optional
            self._logger.warning(f"Failed to save cache: {e}")

    def _is_cache_valid(self, timestamp_str: str) -> bool:
        """
        Check if cached data is still valid based on TTL.

        Args:
            timestamp_str: ISO format timestamp string from cache

        Returns:
            True if cache is still valid, False otherwise
        """
        try:
            cache_time = datetime.fromisoformat(timestamp_str)
            current_time = datetime.now()
            age = current_time - cache_time

            is_valid = age < timedelta(hours=self._cache_ttl_hours)

            if not is_valid:
                self._logger.debug(
                    f"Cache age {age.total_seconds() / 3600:.1f}h exceeds TTL "
                    f"{self._cache_ttl_hours}h"
                )

            return is_valid

        except ValueError as e:
            self._logger.warning(f"Invalid timestamp in cache: {e}")
            return False

    def clear_cache(self) -> None:
        """
        Clear the cached region data.

        This forces the next get_bedrock_regions() call to fetch fresh data from AWS.
        """
        with self._lock:
            if self._cache_file.exists():
                try:
                    self._cache_file.unlink()
                    self._logger.info("Region cache cleared")
                except Exception as e:
                    self._logger.warning(f"Failed to clear cache: {e}")
            else:
                self._logger.debug("Cache file does not exist, nothing to clear")

    def get_cache_info(self) -> dict:
        """
        Get information about the current cache state.

        Returns:
            Dictionary with cache information including path, validity, and age
        """
        with self._lock:
            info = {
                "cache_file": str(self._cache_file),
                "cache_exists": self._cache_file.exists(),
                "cache_ttl_hours": self._cache_ttl_hours,
            }

            if self._cache_file.exists():
                try:
                    with open(self._cache_file, "r") as f:
                        cache_data = json.load(f)

                    timestamp_str = cache_data.get("retrieval_timestamp")
                    if timestamp_str:
                        cache_time = datetime.fromisoformat(timestamp_str)
                        age = datetime.now() - cache_time
                        info["cache_age_hours"] = age.total_seconds() / 3600
                        info["cache_valid"] = self._is_cache_valid(timestamp_str)
                        info["cached_region_count"] = len(cache_data.get("regions", []))
                except Exception:
                    info["cache_error"] = "Failed to read cache details"

            return info

    def __repr__(self) -> str:
        """Return string representation of the discovery service."""
        return (
            f"BedrockRegionDiscovery(cache_dir='{self._cache_dir}', "
            f"cache_ttl_hours={self._cache_ttl_hours})"
        )
