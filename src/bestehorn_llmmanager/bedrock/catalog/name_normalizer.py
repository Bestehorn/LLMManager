"""
Name normalization functions for model name resolution.

This module provides functions for normalizing model names to enable
flexible matching with variations in spacing, punctuation, and version formats.
"""

import re
from typing import Optional


def normalize_model_name(name: Optional[str]) -> str:
    """
    Normalize a model name for flexible matching.

    This function converts model names to a normalized form by:
    1. Converting to lowercase
    2. Removing special characters (-, _, .)
    3. Collapsing multiple spaces to single space
    4. Trimming whitespace
    5. Normalizing version numbers (e.g., "4.5" → "45", "4 5" → "45")

    Args:
        name: Model name to normalize (can be None)

    Returns:
        Normalized model name (empty string if input is None or empty)

    Examples:
        >>> normalize_model_name("Claude-3-Haiku")
        'claude 3 haiku'

        >>> normalize_model_name("Claude  3  Haiku")
        'claude 3 haiku'

        >>> normalize_model_name("Claude 3.5 Sonnet")
        'claude 35 sonnet'

        >>> normalize_model_name("Claude 4 5 20251001")
        'claude 45 20251001'

        >>> normalize_model_name(None)
        ''

        >>> normalize_model_name("  ")
        ''
    """
    # Handle None or empty input
    if not name:
        return ""

    # Convert to lowercase
    normalized = name.lower()

    # Remove special characters (-, _, .)
    # Keep spaces and alphanumeric characters
    normalized = re.sub(r"[-_.]", " ", normalized)

    # Normalize version numbers: collapse adjacent digits separated by spaces
    # This handles patterns like "4 5" → "45" and "3 5" → "35"
    # But preserves "Claude 3 Haiku" as "claude 3 haiku"
    # We look for patterns of single digits separated by single spaces
    normalized = re.sub(r"\b(\d)\s+(\d)\b", r"\1\2", normalized)

    # Collapse multiple spaces to single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Trim whitespace
    normalized = normalized.strip()

    return normalized
