"""
Data structures for model name resolution and alias generation.

This module contains the core data structures used by the ModelNameResolver
for resolving user-provided model names to canonical model names.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class MatchType(Enum):
    """
    Type of name match during model name resolution.

    Attributes:
        EXACT: Exact match to canonical model name
        ALIAS: Matched via generated alias
        LEGACY: Matched via legacy UnifiedModelManager name mapping
        NORMALIZED: Matched via normalization (spacing/punctuation variations)
        FUZZY: Matched via fuzzy search (partial name matching)
    """

    EXACT = "exact"
    ALIAS = "alias"
    LEGACY = "legacy"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"


@dataclass(frozen=True)
class ModelNameMatch:
    """
    Result of model name resolution with metadata.

    This dataclass represents a successful name resolution, including
    information about how the match was found and the confidence level.

    Attributes:
        canonical_name: The actual model name in the catalog
        match_type: How the match was found (exact, alias, legacy, etc.)
        confidence: Match confidence score (0.0-1.0)
        user_input: Original user input that was resolved
    """

    canonical_name: str
    match_type: MatchType
    confidence: float
    user_input: str

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass(frozen=True)
class AliasGenerationConfig:
    """
    Configuration for alias generation behavior.

    This dataclass controls how aliases are generated for models,
    allowing customization of the alias generation strategies.

    Attributes:
        generate_version_variants: Generate version variants (e.g., "4.5" and "4")
        generate_no_prefix_variants: Remove region prefixes (e.g., "APAC")
        generate_spacing_variants: Generate spacing variants (e.g., "Claude3" and "Claude 3")
        include_legacy_mappings: Include UnifiedModelManager legacy names
        max_aliases_per_model: Maximum number of aliases per model to prevent explosion
    """

    generate_version_variants: bool = True
    generate_no_prefix_variants: bool = True
    generate_spacing_variants: bool = True
    include_legacy_mappings: bool = True
    max_aliases_per_model: int = 10

    def __post_init__(self) -> None:
        """Validate max_aliases_per_model is positive."""
        if self.max_aliases_per_model <= 0:
            raise ValueError(
                f"max_aliases_per_model must be positive, got {self.max_aliases_per_model}"
            )


class ErrorType(Enum):
    """
    Type of error during model name resolution.

    Attributes:
        NOT_FOUND: Model name not found in catalog
        AMBIGUOUS: Model name matches multiple models
        DEPRECATED: Legacy model name no longer available
        INVALID_INPUT: Invalid input (empty, malformed, etc.)
    """

    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    DEPRECATED = "deprecated"
    INVALID_INPUT = "invalid_input"


@dataclass(frozen=True)
class ModelResolutionError:
    """
    Detailed error information for failed model name resolution.

    This dataclass provides comprehensive error information to help users
    understand why a model name couldn't be resolved and what alternatives
    are available.

    Attributes:
        user_input: The model name that failed to resolve
        error_type: Type of error that occurred
        suggestions: List of suggested model names
        legacy_name_found: Whether this was a legacy UnifiedModelManager name
        similar_models: List of (model_name, similarity_score) tuples
    """

    user_input: str
    error_type: ErrorType
    suggestions: List[str]
    legacy_name_found: bool
    similar_models: List[Tuple[str, float]]

    def __post_init__(self) -> None:
        """Validate similarity scores are in valid range."""
        for model_name, score in self.similar_models:
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"Similarity score for {model_name} must be between 0.0 and 1.0, got {score}"
                )

    def format_error_message(self) -> str:
        """
        Format a user-friendly error message.

        Returns:
            Formatted error message with suggestions
        """
        if self.error_type == ErrorType.NOT_FOUND:
            msg = f"Model '{self.user_input}' not found."
            if self.suggestions:
                msg += f" Did you mean: {', '.join(self.suggestions[:3])}?"
            if self.legacy_name_found:
                msg += " (This was a legacy UnifiedModelManager name)"
            return msg

        if self.error_type == ErrorType.AMBIGUOUS:
            msg = f"Ambiguous model name '{self.user_input}'."
            if self.suggestions:
                msg += f" Could refer to: {', '.join(self.suggestions)}"
            return msg

        if self.error_type == ErrorType.DEPRECATED:
            msg = f"Model '{self.user_input}' is no longer available."
            if self.suggestions:
                msg += f" Similar models: {', '.join(self.suggestions[:3])}"
            return msg

        # ErrorType.INVALID_INPUT
        return f"Invalid model name: '{self.user_input}'"
