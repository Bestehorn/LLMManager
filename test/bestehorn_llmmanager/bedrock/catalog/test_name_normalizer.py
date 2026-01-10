"""
Unit tests for name normalization functions.

This module contains unit tests for the normalize_model_name function,
focusing on edge cases and specific normalization behaviors.

**Feature: fix-integration-test-models**
"""

from bestehorn_llmmanager.bedrock.catalog.name_normalizer import normalize_model_name


class TestNormalizeModelName:
    """Unit tests for normalize_model_name function."""

    # ========================================================================
    # Empty String Tests
    # ========================================================================

    def test_normalize_none_returns_empty_string(self) -> None:
        """Test that None input returns empty string."""
        result = normalize_model_name(name=None)
        assert result == ""

    def test_normalize_empty_string_returns_empty_string(self) -> None:
        """Test that empty string returns empty string."""
        result = normalize_model_name(name="")
        assert result == ""

    def test_normalize_whitespace_only_returns_empty_string(self) -> None:
        """Test that whitespace-only strings return empty string."""
        assert normalize_model_name(name="   ") == ""
        assert normalize_model_name(name="\t") == ""
        assert normalize_model_name(name="\n") == ""
        assert normalize_model_name(name=" \t\n ") == ""

    # ========================================================================
    # Case Conversion Tests
    # ========================================================================

    def test_normalize_converts_to_lowercase(self) -> None:
        """Test that normalization converts to lowercase."""
        assert normalize_model_name(name="CLAUDE") == "claude"
        assert normalize_model_name(name="Claude") == "claude"
        assert normalize_model_name(name="ClAuDe") == "claude"

    def test_normalize_mixed_case_model_names(self) -> None:
        """Test normalization of mixed case model names."""
        assert normalize_model_name(name="Claude 3 Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="CLAUDE 3 HAIKU") == "claude 3 haiku"
        assert normalize_model_name(name="claude 3 haiku") == "claude 3 haiku"

    # ========================================================================
    # Special Character Tests
    # ========================================================================

    def test_normalize_removes_hyphens(self) -> None:
        """Test that hyphens are removed and replaced with spaces."""
        assert normalize_model_name(name="Claude-3-Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude-Haiku") == "claude haiku"

    def test_normalize_removes_underscores(self) -> None:
        """Test that underscores are removed and replaced with spaces."""
        assert normalize_model_name(name="Claude_3_Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude_Haiku") == "claude haiku"

    def test_normalize_removes_periods(self) -> None:
        """Test that periods are removed and replaced with spaces."""
        assert normalize_model_name(name="Claude.3.Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude.Haiku") == "claude haiku"

    def test_normalize_mixed_special_characters(self) -> None:
        """Test normalization with mixed special characters."""
        assert normalize_model_name(name="Claude-3_Haiku.v1") == "claude 3 haiku v1"
        assert normalize_model_name(name="APAC-Claude_3.Haiku") == "apac claude 3 haiku"

    # ========================================================================
    # Whitespace Tests
    # ========================================================================

    def test_normalize_collapses_multiple_spaces(self) -> None:
        """Test that multiple spaces are collapsed to single space."""
        assert normalize_model_name(name="Claude  3  Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude   3   Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude    Haiku") == "claude haiku"

    def test_normalize_trims_leading_whitespace(self) -> None:
        """Test that leading whitespace is trimmed."""
        assert normalize_model_name(name="  Claude 3 Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="   Claude") == "claude"

    def test_normalize_trims_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is trimmed."""
        assert normalize_model_name(name="Claude 3 Haiku  ") == "claude 3 haiku"
        assert normalize_model_name(name="Claude   ") == "claude"

    def test_normalize_trims_both_ends(self) -> None:
        """Test that whitespace is trimmed from both ends."""
        assert normalize_model_name(name="  Claude 3 Haiku  ") == "claude 3 haiku"
        assert normalize_model_name(name="   Claude   ") == "claude"

    # ========================================================================
    # Version Format Tests
    # ========================================================================

    def test_normalize_version_with_period(self) -> None:
        """Test normalization of version numbers with periods."""
        # Period is replaced with space, then adjacent digits are collapsed
        assert normalize_model_name(name="Claude 3.5 Sonnet") == "claude 35 sonnet"
        assert normalize_model_name(name="Claude 4.5 Haiku") == "claude 45 haiku"

    def test_normalize_version_with_spaces(self) -> None:
        """Test normalization of version numbers with spaces."""
        # Adjacent single digits separated by spaces are collapsed
        assert normalize_model_name(name="Claude 4 5 20251001") == "claude 45 20251001"
        assert normalize_model_name(name="Claude 3 5 Sonnet") == "claude 35 sonnet"

    def test_normalize_preserves_multi_digit_numbers(self) -> None:
        """Test that multi-digit numbers are preserved."""
        assert normalize_model_name(name="Claude 45 Haiku") == "claude 45 haiku"
        assert normalize_model_name(name="Llama 3 8B Instruct") == "llama 3 8b instruct"
        assert normalize_model_name(name="Claude 4 5 20251001") == "claude 45 20251001"

    def test_normalize_version_format_variations(self) -> None:
        """Test various version format variations."""
        # All should normalize to similar forms
        assert normalize_model_name(name="Claude 3.5") == "claude 35"
        assert normalize_model_name(name="Claude 3 5") == "claude 35"
        assert normalize_model_name(name="Claude-3-5") == "claude 35"
        assert normalize_model_name(name="Claude_3.5") == "claude 35"

    # ========================================================================
    # Real Model Name Tests
    # ========================================================================

    def test_normalize_claude_models(self) -> None:
        """Test normalization of Claude model names."""
        assert normalize_model_name(name="Claude 3 Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude 3 Sonnet") == "claude 3 sonnet"
        assert normalize_model_name(name="Claude 3 Opus") == "claude 3 opus"
        assert normalize_model_name(name="Claude 3.5 Sonnet") == "claude 35 sonnet"

    def test_normalize_titan_models(self) -> None:
        """Test normalization of Titan model names."""
        assert normalize_model_name(name="Titan Text G1 - Lite") == "titan text g1 lite"
        assert normalize_model_name(name="Titan-Text-G1-Lite") == "titan text g1 lite"

    def test_normalize_llama_models(self) -> None:
        """Test normalization of Llama model names."""
        assert normalize_model_name(name="Llama 3 8B Instruct") == "llama 3 8b instruct"
        assert normalize_model_name(name="Llama-3-8B-Instruct") == "llama 3 8b instruct"

    def test_normalize_prefixed_models(self) -> None:
        """Test normalization of region-prefixed model names."""
        assert (
            normalize_model_name(name="APAC Anthropic Claude 3 Haiku")
            == "apac anthropic claude 3 haiku"
        )
        assert normalize_model_name(name="EU Claude 3 Sonnet") == "eu claude 3 sonnet"

    # ========================================================================
    # Complex Edge Cases
    # ========================================================================

    def test_normalize_with_numbers_and_letters(self) -> None:
        """Test normalization with mixed numbers and letters."""
        assert normalize_model_name(name="GPT-4") == "gpt 4"
        assert normalize_model_name(name="GPT4") == "gpt4"
        # Period is replaced with space, then "3 5" becomes "35"
        assert normalize_model_name(name="Claude3.5") == "claude3 5"

    def test_normalize_consecutive_special_characters(self) -> None:
        """Test normalization with consecutive special characters."""
        assert normalize_model_name(name="Claude--3--Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude__3__Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude..3..Haiku") == "claude 3 haiku"
        assert normalize_model_name(name="Claude-_-3-_-Haiku") == "claude 3 haiku"

    def test_normalize_special_characters_at_boundaries(self) -> None:
        """Test normalization with special characters at string boundaries."""
        assert normalize_model_name(name="-Claude-") == "claude"
        assert normalize_model_name(name="_Claude_") == "claude"
        assert normalize_model_name(name=".Claude.") == "claude"
        assert normalize_model_name(name="-_Claude_-") == "claude"

    def test_normalize_only_special_characters(self) -> None:
        """Test normalization of strings with only special characters."""
        assert normalize_model_name(name="---") == ""
        assert normalize_model_name(name="___") == ""
        assert normalize_model_name(name="...") == ""
        assert normalize_model_name(name="-_.") == ""

    # ========================================================================
    # Idempotence Tests (Unit Test Verification)
    # ========================================================================

    def test_normalize_is_idempotent(self) -> None:
        """Test that normalization is idempotent (unit test verification)."""
        test_cases = [
            "Claude 3 Haiku",
            "Claude-3-Haiku",
            "CLAUDE 3 HAIKU",
            "  Claude  3  Haiku  ",
            "Claude 3.5 Sonnet",
            "Claude 4 5 20251001",
        ]

        for test_case in test_cases:
            normalized_once = normalize_model_name(name=test_case)
            normalized_twice = normalize_model_name(name=normalized_once)
            assert (
                normalized_once == normalized_twice
            ), f"Not idempotent for '{test_case}': '{normalized_once}' != '{normalized_twice}'"

    # ========================================================================
    # Unicode and Special Cases
    # ========================================================================

    def test_normalize_preserves_alphanumeric(self) -> None:
        """Test that alphanumeric characters are preserved."""
        assert normalize_model_name(name="abc123") == "abc123"
        assert normalize_model_name(name="ABC123") == "abc123"
        assert normalize_model_name(name="Model123") == "model123"

    def test_normalize_single_character(self) -> None:
        """Test normalization of single characters."""
        assert normalize_model_name(name="A") == "a"
        assert normalize_model_name(name="1") == "1"
        assert normalize_model_name(name="-") == ""
        assert normalize_model_name(name=" ") == ""
