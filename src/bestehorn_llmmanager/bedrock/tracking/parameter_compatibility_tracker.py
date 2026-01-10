"""
Parameter compatibility tracker for AWS Bedrock model/region combinations.

This module provides a singleton tracker that records which additionalModelRequestFields
work with which model/region combinations, enabling intelligent retry optimization.
"""

import hashlib
import json
import logging
import threading
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ParameterCompatibilityTracker:
    """
    Tracks parameter compatibility across model/region combinations.

    Implemented as a process-level singleton with thread-safe access.
    Records successful and failed parameter usage to optimize future requests.

    Thread-safe singleton pattern ensures all LLMManager instances within
    the same process share compatibility information.
    """

    _instance: Optional["ParameterCompatibilityTracker"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        """
        Initialize the compatibility tracker.

        Note: Use get_instance() instead of direct instantiation to ensure singleton.
        """
        self._compatible: Dict[Tuple[str, str, str], bool] = {}
        # Key: (model_id, region, parameter_hash)
        # Value: True if compatible, False if incompatible

        self._parameter_hashes: Dict[str, str] = {}
        # Maps parameter dict JSON to hash for efficient lookup

        self._data_lock: threading.Lock = threading.Lock()
        # Separate lock for data access (not class instantiation)

    @classmethod
    def get_instance(cls) -> "ParameterCompatibilityTracker":
        """
        Get or create the singleton instance.

        Thread-safe singleton pattern using double-checked locking.

        Returns:
            The singleton ParameterCompatibilityTracker instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check pattern: verify again after acquiring lock
                if cls._instance is None:
                    cls._instance = cls()
                    logger.debug("Created new ParameterCompatibilityTracker singleton instance")
        return cls._instance

    def record_success(self, model_id: str, region: str, parameters: Dict[str, Any]) -> None:
        """
        Record successful parameter usage for a model/region combination.

        Args:
            model_id: The AWS Bedrock model ID
            region: The AWS region
            parameters: The additionalModelRequestFields that succeeded
        """
        param_hash = self._hash_parameters(parameters=parameters)
        key = (model_id, region, param_hash)

        with self._data_lock:
            self._compatible[key] = True

        logger.debug(
            f"Recorded successful parameter usage: "
            f"model={model_id}, region={region}, param_hash={param_hash[:8]}..."
        )

    def record_failure(
        self, model_id: str, region: str, parameters: Dict[str, Any], error: Exception
    ) -> None:
        """
        Record parameter incompatibility for a model/region combination.

        Args:
            model_id: The AWS Bedrock model ID
            region: The AWS region
            parameters: The additionalModelRequestFields that failed
            error: The exception that occurred
        """
        param_hash = self._hash_parameters(parameters=parameters)
        key = (model_id, region, param_hash)

        with self._data_lock:
            self._compatible[key] = False

        logger.debug(
            f"Recorded parameter incompatibility: "
            f"model={model_id}, region={region}, param_hash={param_hash[:8]}..., "
            f"error={type(error).__name__}"
        )

    def is_known_incompatible(self, model_id: str, region: str, parameters: Dict[str, Any]) -> bool:
        """
        Check if a model/region/parameter combination is known to be incompatible.

        Args:
            model_id: The AWS Bedrock model ID
            region: The AWS region
            parameters: The additionalModelRequestFields to check

        Returns:
            True if the combination is known to be incompatible, False otherwise
        """
        param_hash = self._hash_parameters(parameters=parameters)
        key = (model_id, region, param_hash)

        with self._data_lock:
            # Return True only if explicitly marked as incompatible (False)
            # Unknown combinations return False (not known to be incompatible)
            return self._compatible.get(key, None) is False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get compatibility tracking statistics for observability.

        Returns:
            Dictionary containing:
            - total_combinations: Total tracked combinations
            - compatible_count: Number of compatible combinations
            - incompatible_count: Number of incompatible combinations
            - models_tracked: Set of model IDs tracked
            - regions_tracked: Set of regions tracked
        """
        with self._data_lock:
            compatible_count = sum(1 for v in self._compatible.values() if v is True)
            incompatible_count = sum(1 for v in self._compatible.values() if v is False)

            models_tracked = set()
            regions_tracked = set()

            for model_id, region, _ in self._compatible.keys():
                models_tracked.add(model_id)
                regions_tracked.add(region)

            return {
                "total_combinations": len(self._compatible),
                "compatible_count": compatible_count,
                "incompatible_count": incompatible_count,
                "models_tracked": sorted(list(models_tracked)),
                "regions_tracked": sorted(list(regions_tracked)),
            }

    def _hash_parameters(self, parameters: Dict[str, Any]) -> str:
        """
        Create a stable hash of a parameter dictionary.

        Uses JSON serialization with sorted keys to ensure consistent hashing
        regardless of dictionary insertion order.

        Args:
            parameters: The additionalModelRequestFields dictionary

        Returns:
            SHA256 hash of the parameters as a hexadecimal string
        """
        # Convert to JSON with sorted keys for stable hashing
        json_str = json.dumps(parameters, sort_keys=True, separators=(",", ":"))

        # Check cache first
        if json_str in self._parameter_hashes:
            return self._parameter_hashes[json_str]

        # Compute hash
        hash_obj = hashlib.sha256(json_str.encode("utf-8"))
        param_hash = hash_obj.hexdigest()

        # Cache for future lookups
        with self._data_lock:
            self._parameter_hashes[json_str] = param_hash

        return param_hash
