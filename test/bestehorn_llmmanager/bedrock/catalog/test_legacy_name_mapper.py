"""
Unit tests for LegacyNameMapper.

This module contains unit tests that validate specific examples and edge cases
for the legacy name mapping system.

**Validates: Requirements 1.4, 4.1, 4.2, 4.3, 4.4**
"""

from bestehorn_llmmanager.bedrock.catalog.legacy_name_mapper import LegacyNameMapper


class TestLegacyNameMapperBasicFunctionality:
    """Test basic functionality of LegacyNameMapper."""

    def test_resolve_known_legacy_name_claude_3_haiku(self) -> None:
        """
        Test resolving a known legacy name (Claude 3 Haiku).

        **Validates: Requirements 1.4, 4.1, 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="Claude 3 Haiku")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_resolve_known_legacy_name_titan_text_lite(self) -> None:
        """
        Test resolving a known legacy name (Titan Text G1 - Lite).

        **Validates: Requirements 1.4, 4.1, 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="Titan Text G1 - Lite")

        assert result is not None
        assert result == "amazon.titan-text-lite-v1"

    def test_resolve_known_legacy_name_llama_3_8b(self) -> None:
        """
        Test resolving a known legacy name (Llama 3 8B Instruct).

        **Validates: Requirements 1.4, 4.1, 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="Llama 3 8B Instruct")

        assert result is not None
        assert result == "meta.llama3-8b-instruct-v1:0"

    def test_resolve_unknown_legacy_name(self) -> None:
        """
        Test resolving an unknown legacy name returns None.

        **Validates: Requirements 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="Unknown Model Name")

        assert result is None

    def test_resolve_empty_string(self) -> None:
        """
        Test resolving an empty string returns None.

        **Validates: Requirements 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="")

        assert result is None


class TestLegacyNameMapperCaseInsensitivity:
    """Test case-insensitive name resolution."""

    def test_resolve_lowercase_legacy_name(self) -> None:
        """
        Test resolving a legacy name in lowercase.

        **Validates: Requirements 2.1, 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="claude 3 haiku")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_resolve_uppercase_legacy_name(self) -> None:
        """
        Test resolving a legacy name in uppercase.

        **Validates: Requirements 2.1, 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="CLAUDE 3 HAIKU")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_resolve_mixed_case_legacy_name(self) -> None:
        """
        Test resolving a legacy name in mixed case.

        **Validates: Requirements 2.1, 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="ClAuDe 3 HaIkU")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"


class TestLegacyNameMapperRegionalPrefixes:
    """Test resolution of regional prefixed model names."""

    def test_resolve_apac_prefixed_name(self) -> None:
        """
        Test resolving APAC prefixed legacy name.

        **Validates: Requirements 1.4, 4.1, 4.3**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="APAC Claude 3 Haiku")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_resolve_apac_anthropic_prefixed_name(self) -> None:
        """
        Test resolving APAC Anthropic prefixed legacy name.

        **Validates: Requirements 1.4, 4.1, 4.3**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="APAC Anthropic Claude 3 Haiku")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_resolve_eu_prefixed_name(self) -> None:
        """
        Test resolving EU prefixed legacy name.

        **Validates: Requirements 1.4, 4.1, 4.3**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="EU Claude 3 Haiku")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_resolve_us_prefixed_name(self) -> None:
        """
        Test resolving US prefixed legacy name.

        **Validates: Requirements 1.4, 4.1, 4.3**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="US Claude 3 Haiku")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"


class TestLegacyNameMapperRecognition:
    """Test legacy name recognition."""

    def test_is_legacy_name_known_name(self) -> None:
        """
        Test that known legacy names are recognized.

        **Validates: Requirements 1.4, 4.1**
        """
        mapper = LegacyNameMapper()

        assert mapper.is_legacy_name(user_name="Claude 3 Haiku")
        assert mapper.is_legacy_name(user_name="Titan Text G1 - Lite")
        assert mapper.is_legacy_name(user_name="Llama 3 8B Instruct")

    def test_is_legacy_name_unknown_name(self) -> None:
        """
        Test that unknown names are not recognized as legacy.

        **Validates: Requirements 4.1**
        """
        mapper = LegacyNameMapper()

        assert not mapper.is_legacy_name(user_name="Unknown Model")
        assert not mapper.is_legacy_name(user_name="")

    def test_is_legacy_name_case_insensitive(self) -> None:
        """
        Test that legacy name recognition is case-insensitive.

        **Validates: Requirements 2.1, 4.1**
        """
        mapper = LegacyNameMapper()

        assert mapper.is_legacy_name(user_name="claude 3 haiku")
        assert mapper.is_legacy_name(user_name="CLAUDE 3 HAIKU")
        assert mapper.is_legacy_name(user_name="ClAuDe 3 HaIkU")


class TestLegacyNameMapperDeprecation:
    """Test deprecated model handling."""

    def test_is_deprecated_active_model(self) -> None:
        """
        Test that active models are not marked as deprecated.

        **Validates: Requirements 4.4**
        """
        mapper = LegacyNameMapper()

        assert not mapper.is_deprecated(user_name="Claude 3 Haiku")
        assert not mapper.is_deprecated(user_name="Titan Text G1 - Lite")
        assert not mapper.is_deprecated(user_name="Llama 3 8B Instruct")

    def test_is_deprecated_deprecated_model(self) -> None:
        """
        Test that deprecated models are marked as deprecated.

        **Validates: Requirements 4.4**
        """
        mapper = LegacyNameMapper()

        assert mapper.is_deprecated(user_name="Claude v1")
        assert mapper.is_deprecated(user_name="Claude v1.3")
        assert mapper.is_deprecated(user_name="Titan Text G1")

    def test_get_deprecation_info_active_model(self) -> None:
        """
        Test that active models have no deprecation info.

        **Validates: Requirements 4.4**
        """
        mapper = LegacyNameMapper()

        assert mapper.get_deprecation_info(user_name="Claude 3 Haiku") is None
        assert mapper.get_deprecation_info(user_name="Titan Text G1 - Lite") is None

    def test_get_deprecation_info_deprecated_model(self) -> None:
        """
        Test that deprecated models have deprecation info.

        **Validates: Requirements 4.4**
        """
        mapper = LegacyNameMapper()

        info = mapper.get_deprecation_info(user_name="Claude v1")
        assert info is not None
        assert "Replaced by" in info

        info = mapper.get_deprecation_info(user_name="Titan Text G1")
        assert info is not None
        assert "Replaced by" in info


class TestLegacyNameMapperListMethods:
    """Test methods that return lists of legacy names."""

    def test_get_all_legacy_names(self) -> None:
        """
        Test getting all legacy names.

        **Validates: Requirements 4.1**
        """
        mapper = LegacyNameMapper()

        legacy_names = mapper.get_all_legacy_names()

        assert isinstance(legacy_names, list)
        assert len(legacy_names) > 0
        assert "Claude 3 Haiku" in legacy_names
        assert "Titan Text G1 - Lite" in legacy_names
        assert "Llama 3 8B Instruct" in legacy_names

    def test_get_all_deprecated_names(self) -> None:
        """
        Test getting all deprecated names.

        **Validates: Requirements 4.4**
        """
        mapper = LegacyNameMapper()

        deprecated_names = mapper.get_all_deprecated_names()

        assert isinstance(deprecated_names, list)
        assert len(deprecated_names) > 0
        assert "Claude v1" in deprecated_names
        assert "Claude v1.3" in deprecated_names
        assert "Titan Text G1" in deprecated_names


class TestLegacyNameMapperEdgeCases:
    """Test edge cases and special scenarios."""

    def test_resolve_name_with_extra_whitespace(self) -> None:
        """
        Test resolving a name with extra whitespace.

        **Validates: Requirements 2.1, 4.2**
        """
        mapper = LegacyNameMapper()

        result = mapper.resolve_legacy_name(user_name="  Claude  3  Haiku  ")

        assert result is not None
        assert result == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_resolve_name_with_special_characters(self) -> None:
        """
        Test resolving a name with special characters (hyphens).

        **Validates: Requirements 2.1, 4.2**
        """
        mapper = LegacyNameMapper()

        # The actual legacy name has hyphens
        result = mapper.resolve_legacy_name(user_name="Titan Text G1 - Lite")

        assert result is not None
        assert result == "amazon.titan-text-lite-v1"

    def test_multiple_mapper_instances_consistent(self) -> None:
        """
        Test that multiple mapper instances produce consistent results.

        **Validates: Requirements 4.2**
        """
        mapper1 = LegacyNameMapper()
        mapper2 = LegacyNameMapper()

        result1 = mapper1.resolve_legacy_name(user_name="Claude 3 Haiku")
        result2 = mapper2.resolve_legacy_name(user_name="Claude 3 Haiku")

        assert result1 == result2
        assert result1 == "anthropic.claude-3-haiku-20240307-v1:0"
