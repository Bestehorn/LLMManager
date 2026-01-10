"""
Access method selection for inference profile support.

This module provides functionality to select the optimal access method for
AWS Bedrock models based on available access methods and learned preferences.
"""

import logging
from typing import List, Optional, Tuple

from ..models.access_method import ModelAccessInfo
from ..tracking.access_method_tracker import AccessMethodTracker
from .access_method_structures import AccessMethodNames, AccessMethodPreference

# Configure logger
logger = logging.getLogger(__name__)


class AccessMethodSelector:
    """
    Selects optimal access method for model/region combinations.

    Uses learned preferences and ModelAccessInfo to choose the best
    access method. Preference order: Direct → Regional CRIS → Global CRIS

    This class implements intelligent access method selection by:
    1. Applying learned preferences when available
    2. Falling back to default preference order
    3. Generating fallback methods when primary method fails
    """

    # Default preference order constants
    DEFAULT_PREFERENCE_ORDER: Tuple[str, str, str] = (
        AccessMethodNames.DIRECT,
        AccessMethodNames.REGIONAL_CRIS,
        AccessMethodNames.GLOBAL_CRIS,
    )

    def __init__(self, access_method_tracker: AccessMethodTracker) -> None:
        """
        Initialize selector with access method tracker.

        Args:
            access_method_tracker: Tracker instance for querying learned preferences
        """
        self._tracker = access_method_tracker
        logger.debug("AccessMethodSelector initialized")

    def select_access_method(
        self,
        access_info: ModelAccessInfo,
        learned_preference: Optional[AccessMethodPreference] = None,
    ) -> Tuple[str, str]:
        """
        Select optimal access method and return model ID to use.

        This method selects the best access method based on:
        1. Learned preferences (if provided)
        2. Available access methods in ModelAccessInfo
        3. Default preference order (direct → regional CRIS → global CRIS)

        Args:
            access_info: Model access information from catalog
            learned_preference: Previously learned preference (if any)

        Returns:
            Tuple of (model_id_to_use, access_method_name)

        Examples:
            - ("anthropic.claude-3-haiku-20240307-v1:0", "direct")
            - ("arn:aws:bedrock:us-east-1::inference-profile/...", "regional_cris")

        Raises:
            ValueError: If no access methods are available
        """
        logger.debug(
            f"Selecting access method for region '{access_info.region}' "
            f"with learned preference: {learned_preference.get_preferred_method() if learned_preference else 'None'}"
        )

        # If learned preference provided, try to use it
        if learned_preference is not None:
            preferred_method = learned_preference.get_preferred_method()

            # If preference was learned from error (profile requirement), skip direct access
            if (
                learned_preference.learned_from_error
                and preferred_method != AccessMethodNames.DIRECT
            ):
                # Skip direct access and go straight to CRIS options
                logger.debug(
                    f"Skipping direct access due to learned profile requirement for region '{access_info.region}'"
                )

                # Try regional CRIS first, then global CRIS
                if access_info.has_regional_cris:
                    logger.debug("Using regional CRIS (learned from error)")
                    assert access_info.regional_cris_profile_id is not None
                    return (
                        access_info.regional_cris_profile_id,
                        AccessMethodNames.REGIONAL_CRIS,
                    )
                elif access_info.has_global_cris:
                    logger.debug("Using global CRIS (learned from error)")
                    assert access_info.global_cris_profile_id is not None
                    return (
                        access_info.global_cris_profile_id,
                        AccessMethodNames.GLOBAL_CRIS,
                    )
                # If no CRIS available but direct is, we have to use it
                elif access_info.has_direct_access:
                    logger.warning(
                        "Profile requirement learned but no CRIS available, using direct access"
                    )
                    assert access_info.model_id is not None
                    return (access_info.model_id, AccessMethodNames.DIRECT)

            # Try to use the preferred method if available (normal learned preference)
            if preferred_method == AccessMethodNames.DIRECT and access_info.has_direct_access:
                logger.debug(f"Using learned preference: {AccessMethodNames.DIRECT}")
                assert access_info.model_id is not None  # Guaranteed by ModelAccessInfo validation
                return (access_info.model_id, AccessMethodNames.DIRECT)

            elif (
                preferred_method == AccessMethodNames.REGIONAL_CRIS
                and access_info.has_regional_cris
            ):
                logger.debug(f"Using learned preference: {AccessMethodNames.REGIONAL_CRIS}")
                assert (
                    access_info.regional_cris_profile_id is not None
                )  # Guaranteed by ModelAccessInfo validation
                return (
                    access_info.regional_cris_profile_id,
                    AccessMethodNames.REGIONAL_CRIS,
                )

            elif preferred_method == AccessMethodNames.GLOBAL_CRIS and access_info.has_global_cris:
                logger.debug(f"Using learned preference: {AccessMethodNames.GLOBAL_CRIS}")
                assert (
                    access_info.global_cris_profile_id is not None
                )  # Guaranteed by ModelAccessInfo validation
                return (
                    access_info.global_cris_profile_id,
                    AccessMethodNames.GLOBAL_CRIS,
                )

            # Learned preference not available, fall through to default order
            logger.debug(
                f"Learned preference '{preferred_method}' not available, "
                f"falling back to default order"
            )

        # Use default preference order
        for method in self.DEFAULT_PREFERENCE_ORDER:
            if method == AccessMethodNames.DIRECT and access_info.has_direct_access:
                logger.debug(f"Selected default method: {AccessMethodNames.DIRECT}")
                assert access_info.model_id is not None  # Guaranteed by ModelAccessInfo validation
                return (access_info.model_id, AccessMethodNames.DIRECT)

            elif method == AccessMethodNames.REGIONAL_CRIS and access_info.has_regional_cris:
                logger.debug(f"Selected default method: {AccessMethodNames.REGIONAL_CRIS}")
                assert (
                    access_info.regional_cris_profile_id is not None
                )  # Guaranteed by ModelAccessInfo validation
                return (
                    access_info.regional_cris_profile_id,
                    AccessMethodNames.REGIONAL_CRIS,
                )

            elif method == AccessMethodNames.GLOBAL_CRIS and access_info.has_global_cris:
                logger.debug(f"Selected default method: {AccessMethodNames.GLOBAL_CRIS}")
                assert (
                    access_info.global_cris_profile_id is not None
                )  # Guaranteed by ModelAccessInfo validation
                return (
                    access_info.global_cris_profile_id,
                    AccessMethodNames.GLOBAL_CRIS,
                )

        # No access methods available - this should not happen due to ModelAccessInfo validation
        error_msg = f"No access methods available for region '{access_info.region}'"
        logger.error(error_msg)
        raise ValueError(error_msg)

    def get_fallback_access_methods(
        self,
        access_info: ModelAccessInfo,
        failed_method: str,
    ) -> List[Tuple[str, str]]:
        """
        Get fallback access methods after a failure.

        Generates an ordered list of fallback methods to try after the primary
        method fails. The list follows the default preference order but excludes
        the failed method.

        Args:
            access_info: Model access information
            failed_method: Access method that failed

        Returns:
            List of (model_id, access_method_name) tuples to try

        Examples:
            If direct access failed, returns:
            [
                ("arn:aws:bedrock:us-east-1::inference-profile/...", "regional_cris"),
                ("arn:aws:bedrock:us-west-2::inference-profile/...", "global_cris")
            ]
        """
        logger.debug(
            f"Generating fallback methods for region '{access_info.region}' "
            f"after '{failed_method}' failed"
        )

        fallback_methods: List[Tuple[str, str]] = []

        # Generate fallbacks in preference order, excluding failed method
        for method in self.DEFAULT_PREFERENCE_ORDER:
            # Skip the failed method
            if method == failed_method:
                continue

            # Add method if available
            if method == AccessMethodNames.DIRECT and access_info.has_direct_access:
                assert access_info.model_id is not None  # Guaranteed by ModelAccessInfo validation
                fallback_methods.append((access_info.model_id, AccessMethodNames.DIRECT))

            elif method == AccessMethodNames.REGIONAL_CRIS and access_info.has_regional_cris:
                assert (
                    access_info.regional_cris_profile_id is not None
                )  # Guaranteed by ModelAccessInfo validation
                fallback_methods.append(
                    (
                        access_info.regional_cris_profile_id,
                        AccessMethodNames.REGIONAL_CRIS,
                    )
                )

            elif method == AccessMethodNames.GLOBAL_CRIS and access_info.has_global_cris:
                assert (
                    access_info.global_cris_profile_id is not None
                )  # Guaranteed by ModelAccessInfo validation
                fallback_methods.append(
                    (
                        access_info.global_cris_profile_id,
                        AccessMethodNames.GLOBAL_CRIS,
                    )
                )

        logger.debug(f"Generated {len(fallback_methods)} fallback methods")
        return fallback_methods
