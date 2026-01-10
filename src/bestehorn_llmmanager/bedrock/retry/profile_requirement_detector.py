"""
Profile requirement detection for AWS Bedrock models.

This module provides functionality to detect when AWS Bedrock models require
inference profile access based on ValidationException error messages.
"""

import logging
import re
from typing import Final, Optional

# Configure logger
logger = logging.getLogger(__name__)


class ProfileRequirementPatterns:
    """Constants for profile requirement error patterns following coding standards."""

    PATTERN_ON_DEMAND_THROUGHPUT: Final[str] = "on-demand throughput"
    PATTERN_RETRY_WITH_PROFILE: Final[str] = (
        "retry your request with the id or arn of an inference profile"
    )
    PATTERN_INFERENCE_PROFILE_CONTAINS: Final[str] = "inference profile that contains this model"
    PATTERN_MODEL_ID_NOT_SUPPORTED: Final[str] = "isn't supported"


class ProfileRequirementDetector:
    """
    Detects when AWS errors indicate inference profile requirement.

    Analyzes ValidationException messages to identify when a model
    requires profile-based access instead of direct model ID invocation.
    """

    # Error patterns indicating profile requirement
    PROFILE_REQUIREMENT_PATTERNS: Final[list] = [
        ProfileRequirementPatterns.PATTERN_ON_DEMAND_THROUGHPUT,
        ProfileRequirementPatterns.PATTERN_RETRY_WITH_PROFILE,
        ProfileRequirementPatterns.PATTERN_INFERENCE_PROFILE_CONTAINS,
        ProfileRequirementPatterns.PATTERN_MODEL_ID_NOT_SUPPORTED,
    ]

    @classmethod
    def is_profile_requirement_error(cls, error: Exception) -> bool:
        """
        Check if error indicates profile requirement.

        Args:
            error: Exception to analyze

        Returns:
            True if error indicates profile is required, False otherwise
        """
        if error is None:
            return False

        # Get error message
        error_message = str(error).lower()

        # Check if error message is empty
        if not error_message or not error_message.strip():
            return False

        # Normalize apostrophes - replace Unicode apostrophes with regular ones
        # This handles cases where AWS returns "isn't" with Unicode apostrophe
        error_message = error_message.replace("'", "'").replace("'", "'")

        # Normalize whitespace - replace multiple spaces/newlines with single space
        error_message = " ".join(error_message.split())

        # Check for profile requirement patterns
        for pattern in cls.PROFILE_REQUIREMENT_PATTERNS:
            pattern_normalized = pattern.lower().replace("'", "'").replace("'", "'")
            pattern_normalized = " ".join(pattern_normalized.split())
            if pattern_normalized in error_message:
                logger.debug(
                    f"Profile requirement detected. Pattern matched: '{pattern}' "
                    f"in error message: '{error_message[:200]}'"
                )
                return True

        return False

    @classmethod
    def extract_model_id_from_error(cls, error: Exception) -> Optional[str]:
        """
        Extract model ID from profile requirement error message.

        Attempts to extract the model ID from error messages that indicate
        a profile requirement. Looks for patterns like:
        - "Invocation of model ID <model-id> with on-demand throughput..."
        - "model ID <model-id> isn't supported"

        Args:
            error: Profile requirement error

        Returns:
            Model ID if found, None otherwise
        """
        if error is None:
            return None

        error_message = str(error)

        # Check if error message is empty
        if not error_message or not error_message.strip():
            return None

        # Pattern 1: "Invocation of model ID <model-id> with on-demand throughput"
        pattern1 = r"invocation of model id\s+([^\s]+)\s+with on-demand throughput"
        match = re.search(pattern=pattern1, string=error_message, flags=re.IGNORECASE)
        if match:
            model_id = match.group(1)
            logger.debug(f"Extracted model ID from error: '{model_id}'")
            return model_id

        # Pattern 2: "model ID <model-id> isn't supported"
        pattern2 = r"model id\s+([^\s]+)\s+isn't supported"
        match = re.search(pattern=pattern2, string=error_message, flags=re.IGNORECASE)
        if match:
            model_id = match.group(1)
            logger.debug(f"Extracted model ID from error: '{model_id}'")
            return model_id

        # Pattern 3: Generic model ID extraction - look for model ID patterns
        # AWS model IDs typically follow patterns like:
        # - anthropic.claude-3-sonnet-20240229-v1:0
        # - amazon.titan-text-express-v1
        pattern3 = r"([a-z0-9]+\.[a-z0-9\-]+(?:-v\d+)?(?::\d+)?)"
        matches = re.findall(pattern=pattern3, string=error_message, flags=re.IGNORECASE)
        if matches:
            # Return the first match that looks like a model ID
            for potential_model_id in matches:
                # Filter out common false positives
                if "." in potential_model_id and len(potential_model_id) > 10:
                    logger.debug(f"Extracted model ID from error (generic): '{potential_model_id}'")
                    return potential_model_id

        logger.debug("Could not extract model ID from error message")
        return None
