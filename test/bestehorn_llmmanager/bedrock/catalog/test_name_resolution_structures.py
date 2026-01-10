"""
Unit tests for name resolution data structures.

Tests dataclass initialization, validation, and serialization for:
- MatchType enum
- ModelNameMatch dataclass
- AliasGenerationConfig dataclass
- ErrorType enum
- ModelResolutionError dataclass
"""

import pytest

from bestehorn_llmmanager.bedrock.catalog.name_resolution_structures import (
    AliasGenerationConfig,
    ErrorType,
    MatchType,
    ModelNameMatch,
    ModelResolutionError,
)


class TestMatchType:
    """Test MatchType enum."""

    def test_match_type_values(self) -> None:
        """Test that MatchType has all expected values."""
        assert MatchType.EXACT.value == "exact"
        assert MatchType.ALIAS.value == "alias"
        assert MatchType.LEGACY.value == "legacy"
        assert MatchType.NORMALIZED.value == "normalized"
        assert MatchType.FUZZY.value == "fuzzy"

    def test_match_type_enum_members(self) -> None:
        """Test that MatchType has exactly the expected members."""
        expected_members = {"EXACT", "ALIAS", "LEGACY", "NORMALIZED", "FUZZY"}
        actual_members = {member.name for member in MatchType}
        assert actual_members == expected_members

    def test_match_type_from_value(self) -> None:
        """Test creating MatchType from string value."""
        assert MatchType("exact") == MatchType.EXACT
        assert MatchType("alias") == MatchType.ALIAS
        assert MatchType("legacy") == MatchType.LEGACY
        assert MatchType("normalized") == MatchType.NORMALIZED
        assert MatchType("fuzzy") == MatchType.FUZZY


class TestModelNameMatch:
    """Test ModelNameMatch dataclass."""

    def test_model_name_match_initialization(self) -> None:
        """Test basic initialization of ModelNameMatch."""
        match = ModelNameMatch(
            canonical_name="Claude 3 Haiku",
            match_type=MatchType.ALIAS,
            confidence=0.95,
            user_input="claude-3-haiku",
        )

        assert match.canonical_name == "Claude 3 Haiku"
        assert match.match_type == MatchType.ALIAS
        assert match.confidence == 0.95
        assert match.user_input == "claude-3-haiku"

    def test_model_name_match_confidence_validation_valid(self) -> None:
        """Test that valid confidence values are accepted."""
        # Test boundary values
        match_min = ModelNameMatch(
            canonical_name="Model",
            match_type=MatchType.EXACT,
            confidence=0.0,
            user_input="model",
        )
        assert match_min.confidence == 0.0

        match_max = ModelNameMatch(
            canonical_name="Model",
            match_type=MatchType.EXACT,
            confidence=1.0,
            user_input="model",
        )
        assert match_max.confidence == 1.0

        # Test mid-range value
        match_mid = ModelNameMatch(
            canonical_name="Model",
            match_type=MatchType.EXACT,
            confidence=0.5,
            user_input="model",
        )
        assert match_mid.confidence == 0.5

    def test_model_name_match_confidence_validation_invalid(self) -> None:
        """Test that invalid confidence values raise ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            ModelNameMatch(
                canonical_name="Model",
                match_type=MatchType.EXACT,
                confidence=1.5,
                user_input="model",
            )

        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            ModelNameMatch(
                canonical_name="Model",
                match_type=MatchType.EXACT,
                confidence=-0.1,
                user_input="model",
            )

    def test_model_name_match_frozen(self) -> None:
        """Test that ModelNameMatch is immutable (frozen)."""
        match = ModelNameMatch(
            canonical_name="Model",
            match_type=MatchType.EXACT,
            confidence=1.0,
            user_input="model",
        )

        with pytest.raises(AttributeError):
            match.canonical_name = "New Model"  # type: ignore

        with pytest.raises(AttributeError):
            match.confidence = 0.5  # type: ignore


class TestAliasGenerationConfig:
    """Test AliasGenerationConfig dataclass."""

    def test_alias_generation_config_defaults(self) -> None:
        """Test default values for AliasGenerationConfig."""
        config = AliasGenerationConfig()

        assert config.generate_version_variants is True
        assert config.generate_no_prefix_variants is True
        assert config.generate_spacing_variants is True
        assert config.include_legacy_mappings is True
        assert config.max_aliases_per_model == 10

    def test_alias_generation_config_custom_values(self) -> None:
        """Test custom values for AliasGenerationConfig."""
        config = AliasGenerationConfig(
            generate_version_variants=False,
            generate_no_prefix_variants=False,
            generate_spacing_variants=False,
            include_legacy_mappings=False,
            max_aliases_per_model=5,
        )

        assert config.generate_version_variants is False
        assert config.generate_no_prefix_variants is False
        assert config.generate_spacing_variants is False
        assert config.include_legacy_mappings is False
        assert config.max_aliases_per_model == 5

    def test_alias_generation_config_max_aliases_validation_valid(self) -> None:
        """Test that valid max_aliases_per_model values are accepted."""
        config = AliasGenerationConfig(max_aliases_per_model=1)
        assert config.max_aliases_per_model == 1

        config = AliasGenerationConfig(max_aliases_per_model=100)
        assert config.max_aliases_per_model == 100

    def test_alias_generation_config_max_aliases_validation_invalid(self) -> None:
        """Test that invalid max_aliases_per_model values raise ValueError."""
        with pytest.raises(ValueError, match="max_aliases_per_model must be positive"):
            AliasGenerationConfig(max_aliases_per_model=0)

        with pytest.raises(ValueError, match="max_aliases_per_model must be positive"):
            AliasGenerationConfig(max_aliases_per_model=-1)

    def test_alias_generation_config_frozen(self) -> None:
        """Test that AliasGenerationConfig is immutable (frozen)."""
        config = AliasGenerationConfig()

        with pytest.raises(AttributeError):
            config.generate_version_variants = False  # type: ignore

        with pytest.raises(AttributeError):
            config.max_aliases_per_model = 20  # type: ignore


class TestErrorType:
    """Test ErrorType enum."""

    def test_error_type_values(self) -> None:
        """Test that ErrorType has all expected values."""
        assert ErrorType.NOT_FOUND.value == "not_found"
        assert ErrorType.AMBIGUOUS.value == "ambiguous"
        assert ErrorType.DEPRECATED.value == "deprecated"
        assert ErrorType.INVALID_INPUT.value == "invalid_input"

    def test_error_type_enum_members(self) -> None:
        """Test that ErrorType has exactly the expected members."""
        expected_members = {"NOT_FOUND", "AMBIGUOUS", "DEPRECATED", "INVALID_INPUT"}
        actual_members = {member.name for member in ErrorType}
        assert actual_members == expected_members

    def test_error_type_from_value(self) -> None:
        """Test creating ErrorType from string value."""
        assert ErrorType("not_found") == ErrorType.NOT_FOUND
        assert ErrorType("ambiguous") == ErrorType.AMBIGUOUS
        assert ErrorType("deprecated") == ErrorType.DEPRECATED
        assert ErrorType("invalid_input") == ErrorType.INVALID_INPUT


class TestModelResolutionError:
    """Test ModelResolutionError dataclass."""

    def test_model_resolution_error_initialization(self) -> None:
        """Test basic initialization of ModelResolutionError."""
        error = ModelResolutionError(
            user_input="claude-3",
            error_type=ErrorType.NOT_FOUND,
            suggestions=["Claude 3 Haiku", "Claude 3 Sonnet"],
            legacy_name_found=False,
            similar_models=[("Claude 3 Haiku", 0.8), ("Claude 3 Sonnet", 0.75)],
        )

        assert error.user_input == "claude-3"
        assert error.error_type == ErrorType.NOT_FOUND
        assert error.suggestions == ["Claude 3 Haiku", "Claude 3 Sonnet"]
        assert error.legacy_name_found is False
        assert error.similar_models == [("Claude 3 Haiku", 0.8), ("Claude 3 Sonnet", 0.75)]

    def test_model_resolution_error_similarity_validation_valid(self) -> None:
        """Test that valid similarity scores are accepted."""
        error = ModelResolutionError(
            user_input="test",
            error_type=ErrorType.NOT_FOUND,
            suggestions=[],
            legacy_name_found=False,
            similar_models=[("Model1", 0.0), ("Model2", 1.0), ("Model3", 0.5)],
        )

        assert len(error.similar_models) == 3

    def test_model_resolution_error_similarity_validation_invalid(self) -> None:
        """Test that invalid similarity scores raise ValueError."""
        with pytest.raises(ValueError, match="Similarity score .* must be between 0.0 and 1.0"):
            ModelResolutionError(
                user_input="test",
                error_type=ErrorType.NOT_FOUND,
                suggestions=[],
                legacy_name_found=False,
                similar_models=[("Model", 1.5)],
            )

        with pytest.raises(ValueError, match="Similarity score .* must be between 0.0 and 1.0"):
            ModelResolutionError(
                user_input="test",
                error_type=ErrorType.NOT_FOUND,
                suggestions=[],
                legacy_name_found=False,
                similar_models=[("Model", -0.1)],
            )

    def test_model_resolution_error_frozen(self) -> None:
        """Test that ModelResolutionError is immutable (frozen)."""
        error = ModelResolutionError(
            user_input="test",
            error_type=ErrorType.NOT_FOUND,
            suggestions=[],
            legacy_name_found=False,
            similar_models=[],
        )

        with pytest.raises(AttributeError):
            error.user_input = "new_test"  # type: ignore

        with pytest.raises(AttributeError):
            error.error_type = ErrorType.AMBIGUOUS  # type: ignore

    def test_format_error_message_not_found(self) -> None:
        """Test error message formatting for NOT_FOUND errors."""
        error = ModelResolutionError(
            user_input="claude-3",
            error_type=ErrorType.NOT_FOUND,
            suggestions=["Claude 3 Haiku", "Claude 3 Sonnet", "Claude 3 Opus"],
            legacy_name_found=False,
            similar_models=[],
        )

        message = error.format_error_message()
        assert "Model 'claude-3' not found" in message
        assert "Did you mean: Claude 3 Haiku, Claude 3 Sonnet, Claude 3 Opus?" in message

    def test_format_error_message_not_found_with_legacy(self) -> None:
        """Test error message formatting for NOT_FOUND with legacy name."""
        error = ModelResolutionError(
            user_input="old-model",
            error_type=ErrorType.NOT_FOUND,
            suggestions=["New Model"],
            legacy_name_found=True,
            similar_models=[],
        )

        message = error.format_error_message()
        assert "Model 'old-model' not found" in message
        assert "Did you mean: New Model?" in message
        assert "(This was a legacy UnifiedModelManager name)" in message

    def test_format_error_message_ambiguous(self) -> None:
        """Test error message formatting for AMBIGUOUS errors."""
        error = ModelResolutionError(
            user_input="claude",
            error_type=ErrorType.AMBIGUOUS,
            suggestions=["Claude 3 Haiku", "Claude 3 Sonnet"],
            legacy_name_found=False,
            similar_models=[],
        )

        message = error.format_error_message()
        assert "Ambiguous model name 'claude'" in message
        assert "Could refer to: Claude 3 Haiku, Claude 3 Sonnet" in message

    def test_format_error_message_deprecated(self) -> None:
        """Test error message formatting for DEPRECATED errors."""
        error = ModelResolutionError(
            user_input="old-model",
            error_type=ErrorType.DEPRECATED,
            suggestions=["New Model 1", "New Model 2"],
            legacy_name_found=True,
            similar_models=[],
        )

        message = error.format_error_message()
        assert "Model 'old-model' is no longer available" in message
        assert "Similar models: New Model 1, New Model 2" in message

    def test_format_error_message_invalid_input(self) -> None:
        """Test error message formatting for INVALID_INPUT errors."""
        error = ModelResolutionError(
            user_input="",
            error_type=ErrorType.INVALID_INPUT,
            suggestions=[],
            legacy_name_found=False,
            similar_models=[],
        )

        message = error.format_error_message()
        assert "Invalid model name: ''" in message

    def test_format_error_message_no_suggestions(self) -> None:
        """Test error message formatting when no suggestions are available."""
        error = ModelResolutionError(
            user_input="unknown",
            error_type=ErrorType.NOT_FOUND,
            suggestions=[],
            legacy_name_found=False,
            similar_models=[],
        )

        message = error.format_error_message()
        assert "Model 'unknown' not found" in message
        assert "Did you mean" not in message
