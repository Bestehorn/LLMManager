"""
Access method tracking for inference profile support.

This module provides functionality to track and learn successful access methods
for AWS Bedrock models across different regions.
"""

import logging
import threading
from typing import Any, Dict, Optional, Tuple

from ..retry.access_method_structures import AccessMethodPreference

# Configure logger
logger = logging.getLogger(__name__)


class AccessMethodTracker:
    """
    Tracks successful access methods for model/region combinations.

    Maintains a process-wide cache of learned access method preferences
    to optimize future requests. Uses singleton pattern to ensure a single
    instance across the process.

    Thread-safe for concurrent access from multiple threads.
    """

    _instance: Optional["AccessMethodTracker"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> "AccessMethodTracker":
        """
        Create or return singleton instance.

        Returns:
            Singleton AccessMethodTracker instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super(AccessMethodTracker, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Initialize tracker with empty preference cache.

        Only initializes once due to singleton pattern.
        """
        # Prevent re-initialization
        if self._initialized:
            return

        self._preferences: Dict[Tuple[str, str], AccessMethodPreference] = {}
        self._preference_lock: threading.Lock = threading.Lock()
        self._initialized = True

        logger.debug("AccessMethodTracker initialized")

    @classmethod
    def get_instance(cls) -> "AccessMethodTracker":
        """
        Get singleton instance (process-wide).

        Returns:
            Singleton AccessMethodTracker instance
        """
        return cls()

    def record_success(
        self,
        model_id: str,
        region: str,
        access_method: str,
        model_id_used: str,
    ) -> None:
        """
        Record successful access method.

        Updates the preference cache to indicate that a specific access method
        successfully worked for a model/region combination.

        Args:
            model_id: Base model ID (e.g., "anthropic.claude-3-haiku-20240307-v1:0")
            region: AWS region
            access_method: Access method used ("direct", "regional_cris", "global_cris")
            model_id_used: Actual ID used in request (model ID or profile ARN)
        """
        from datetime import datetime

        from ..retry.access_method_structures import AccessMethodNames

        key = (model_id, region)

        with self._preference_lock:
            # Create or update preference
            preference = AccessMethodPreference(
                prefer_direct=(access_method == AccessMethodNames.DIRECT),
                prefer_regional_cris=(access_method == AccessMethodNames.REGIONAL_CRIS),
                prefer_global_cris=(access_method == AccessMethodNames.GLOBAL_CRIS),
                learned_from_error=False,
                last_updated=datetime.now(),
            )

            self._preferences[key] = preference

            logger.debug(
                f"Recorded successful access method '{access_method}' for "
                f"model '{model_id}' in region '{region}'"
            )

    def record_profile_requirement(self, model_id: str, region: str) -> None:
        """
        Record that a model requires profile-based access.

        Updates the preference cache to indicate that a model does not support
        direct access and requires profile-based access (regional or global CRIS).

        Args:
            model_id: Model ID that requires profile
            region: AWS region
        """
        from datetime import datetime

        key = (model_id, region)

        with self._preference_lock:
            # Create preference indicating profile requirement
            # Prefer regional CRIS over global CRIS
            preference = AccessMethodPreference(
                prefer_direct=False,
                prefer_regional_cris=True,
                prefer_global_cris=False,
                learned_from_error=True,
                last_updated=datetime.now(),
            )

            self._preferences[key] = preference

            logger.debug(
                f"Recorded profile requirement for model '{model_id}' in region '{region}'"
            )

    def get_preference(self, model_id: str, region: str) -> Optional[AccessMethodPreference]:
        """
        Get learned preference for model/region.

        Retrieves the learned access method preference for a specific model/region
        combination if one has been recorded.

        Args:
            model_id: Model ID
            region: AWS region

        Returns:
            Learned preference if available, None otherwise
        """
        key = (model_id, region)

        with self._preference_lock:
            preference = self._preferences.get(key)

            if preference:
                logger.debug(
                    f"Retrieved preference for model '{model_id}' in region '{region}': "
                    f"{preference.get_preferred_method()}"
                )
            else:
                logger.debug(f"No preference found for model '{model_id}' in region '{region}'")

            return preference

    def requires_profile(self, model_id: str, region: str) -> bool:
        """
        Check if model is known to require profile access.

        Checks if a model/region combination is known to require profile-based
        access (i.e., does not support direct access).

        Args:
            model_id: Model ID
            region: AWS region

        Returns:
            True if model is known to require profile, False otherwise
        """
        preference = self.get_preference(model_id=model_id, region=region)

        if preference is None:
            return False

        # Model requires profile if it doesn't prefer direct access
        # and was learned from an error
        return not preference.prefer_direct and preference.learned_from_error

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tracked access methods.

        Returns:
            Dictionary with tracking statistics including:
            - total_tracked: Total number of tracked model/region combinations
            - profile_required_count: Number of combinations requiring profiles
            - direct_access_count: Number of combinations using direct access
            - regional_cris_count: Number using regional CRIS
            - global_cris_count: Number using global CRIS
            - learned_from_error_count: Number learned from errors
        """
        with self._preference_lock:
            total_tracked = len(self._preferences)
            profile_required_count = 0
            direct_access_count = 0
            regional_cris_count = 0
            global_cris_count = 0
            learned_from_error_count = 0

            for preference in self._preferences.values():
                if preference.prefer_direct:
                    direct_access_count += 1
                elif preference.prefer_regional_cris:
                    regional_cris_count += 1
                elif preference.prefer_global_cris:
                    global_cris_count += 1

                if not preference.prefer_direct and preference.learned_from_error:
                    profile_required_count += 1

                if preference.learned_from_error:
                    learned_from_error_count += 1

            statistics = {
                "total_tracked": total_tracked,
                "profile_required_count": profile_required_count,
                "direct_access_count": direct_access_count,
                "regional_cris_count": regional_cris_count,
                "global_cris_count": global_cris_count,
                "learned_from_error_count": learned_from_error_count,
            }

            logger.debug(f"Access method statistics: {statistics}")

            return statistics

    @classmethod
    def reset_for_testing(cls) -> None:
        """
        Reset singleton state for testing purposes.

        WARNING: This method should ONLY be called from test code.
        DO NOT call this method in production code as it will clear all
        learned preferences and reset the singleton instance.

        This method is provided to ensure test isolation by clearing the
        singleton state between test runs. It uses thread-safe operations
        to prevent race conditions during reset.

        Thread-safe: Uses class-level lock to ensure atomic reset.
        """
        with cls._lock:
            if cls._instance is not None:
                # Clear all learned preferences
                with cls._instance._preference_lock:
                    cls._instance._preferences.clear()

                # Reset initialization flag
                cls._instance._initialized = False

            # Reset singleton instance
            cls._instance = None

            logger.debug("AccessMethodTracker reset for testing")
