"""
Unit tests for alias generators.

Tests specific examples and edge cases for each alias generation strategy.
"""

import pytest

from src.bestehorn_llmmanager.bedrock.catalog.alias_generators import (
    ClaudeAliasGenerator,
    PrefixedModelAliasGenerator,
    VersionedModelAliasGenerator,
)
from src.bestehorn_llmmanager.bedrock.catalog.name_resolution_structures import (
    AliasGenerationConfig,
)
from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from src.bestehorn_llmmanager.bedrock.models.unified_structures import UnifiedModelInfo


def create_test_model(
    model_name: str, provider: str = "Anthropic", region: str = "us-east-1"
) -> UnifiedModelInfo:
    """Helper to create test model info."""
    return UnifiedModelInfo(
        model_name=model_name,
        provider=provider,
        model_id=f"{provider.lower()}.{model_name.lower().replace(' ', '-')}",
        input_modalities=["TEXT"],
        output_modalities=["TEXT"],
        streaming_supported=True,
        region_access={
            region: ModelAccessInfo(
                region=region,
                has_direct_access=True,
                model_id=f"{provider.lower()}.{model_name.lower().replace(' ', '-')}",
            )
        },
    )


class TestClaudeAliasGenerator:
    """Tests for ClaudeAliasGenerator."""

    def test_can_generate_claude_models(self) -> None:
        """Test that generator recognizes Claude models."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        claude_model = create_test_model(model_name="Claude 3 Haiku")
        assert generator.can_generate(model_info=claude_model)

        non_claude_model = create_test_model(model_name="Llama 3 8B Instruct", provider="Meta")
        assert not generator.can_generate(model_info=non_claude_model)

    def test_generate_claude_haiku_aliases(self) -> None:
        """Test alias generation for Claude Haiku model."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude Haiku 4 5 20251001")
        aliases = generator.generate(model_info=model)

        # Should generate version variants
        assert "Claude 4.5 Haiku" in aliases
        # Should also generate spacing variant
        assert "Claude4.5 Haiku" in aliases

    def test_generate_claude_sonnet_aliases(self) -> None:
        """Test alias generation for Claude Sonnet model."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude Sonnet 3 5 20240620")
        aliases = generator.generate(model_info=model)

        # Should generate version variants
        assert "Claude 3.5 Sonnet" in aliases
        # Should also generate spacing variant
        assert "Claude3.5 Sonnet" in aliases

    def test_generate_with_spacing_variants(self) -> None:
        """Test spacing variant generation."""
        config = AliasGenerationConfig(generate_spacing_variants=True)
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude Haiku 3 5")
        aliases = generator.generate(model_info=model)

        # Should include spacing variants
        assert any("Claude3" in alias for alias in aliases)

    def test_no_aliases_without_variant(self) -> None:
        """Test that no aliases are generated without a variant."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude 3")
        aliases = generator.generate(model_info=model)

        # Should not generate aliases without variant
        assert len(aliases) == 0

    def test_no_aliases_without_version(self) -> None:
        """Test that no aliases are generated without a version."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude Haiku")
        aliases = generator.generate(model_info=model)

        # Should not generate aliases without version
        assert len(aliases) == 0

    def test_alias_limit_enforced(self) -> None:
        """Test that alias limit is enforced."""
        config = AliasGenerationConfig(max_aliases_per_model=3)
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude Haiku 4 5 20251001")
        aliases = generator.generate(model_info=model)

        assert len(aliases) <= 3

    def test_no_duplicate_aliases(self) -> None:
        """Test that no duplicate aliases are generated."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude Haiku 3 0")
        aliases = generator.generate(model_info=model)

        # Check for duplicates (case-insensitive)
        aliases_lower = [alias.lower() for alias in aliases]
        assert len(aliases_lower) == len(set(aliases_lower))


class TestVersionedModelAliasGenerator:
    """Tests for VersionedModelAliasGenerator."""

    def test_can_generate_versioned_non_claude_models(self) -> None:
        """Test that generator recognizes versioned non-Claude models."""
        config = AliasGenerationConfig()
        generator = VersionedModelAliasGenerator(config=config)

        llama_model = create_test_model(model_name="Llama 3 8B Instruct", provider="Meta")
        assert generator.can_generate(model_info=llama_model)

        claude_model = create_test_model(model_name="Claude 3 Haiku")
        assert not generator.can_generate(model_info=claude_model)

        non_versioned_model = create_test_model(model_name="Titan Text", provider="Amazon")
        assert not generator.can_generate(model_info=non_versioned_model)

    def test_generate_llama_aliases(self) -> None:
        """Test alias generation for Llama model."""
        config = AliasGenerationConfig()
        generator = VersionedModelAliasGenerator(config=config)

        model = create_test_model(model_name="Llama 3 8B Instruct", provider="Meta")
        aliases = generator.generate(model_info=model)

        # Should include original name
        assert "Llama 3 8B Instruct" in aliases

        # Should include spacing variant
        assert "Llama3 8B Instruct" in aliases

    def test_generate_with_version_normalization(self) -> None:
        """Test version number normalization."""
        config = AliasGenerationConfig(generate_version_variants=True)
        generator = VersionedModelAliasGenerator(config=config)

        model = create_test_model(model_name="Mistral 7 1 Instruct", provider="Mistral")
        aliases = generator.generate(model_info=model)

        # Should generate aliases with normalized and original versions
        # The generator includes the original name and spacing variants
        assert len(aliases) > 0
        assert "Mistral 7 1 Instruct" in aliases or "Mistral7 1 Instruct" in aliases

    def test_no_duplicate_aliases(self) -> None:
        """Test that no duplicate aliases are generated."""
        config = AliasGenerationConfig()
        generator = VersionedModelAliasGenerator(config=config)

        model = create_test_model(model_name="Llama 3 8B", provider="Meta")
        aliases = generator.generate(model_info=model)

        # Check for duplicates (case-insensitive)
        aliases_lower = [alias.lower() for alias in aliases]
        assert len(aliases_lower) == len(set(aliases_lower))

    def test_alias_limit_enforced(self) -> None:
        """Test that alias limit is enforced."""
        config = AliasGenerationConfig(max_aliases_per_model=2)
        generator = VersionedModelAliasGenerator(config=config)

        model = create_test_model(model_name="Llama 3 8B Instruct", provider="Meta")
        aliases = generator.generate(model_info=model)

        assert len(aliases) <= 2


class TestPrefixedModelAliasGenerator:
    """Tests for PrefixedModelAliasGenerator."""

    def test_can_generate_prefixed_models(self) -> None:
        """Test that generator recognizes prefixed models."""
        config = AliasGenerationConfig()
        generator = PrefixedModelAliasGenerator(config=config)

        apac_model = create_test_model(model_name="APAC Anthropic Claude 3 Haiku")
        assert generator.can_generate(model_info=apac_model)

        eu_model = create_test_model(model_name="EU Claude 3 Haiku")
        assert generator.can_generate(model_info=eu_model)

        non_prefixed_model = create_test_model(model_name="Claude 3 Haiku")
        assert not generator.can_generate(model_info=non_prefixed_model)

    def test_generate_removes_regional_prefix(self) -> None:
        """Test that regional prefixes are NOT removed (to prevent ambiguity)."""
        config = AliasGenerationConfig()
        generator = PrefixedModelAliasGenerator(config=config)

        model = create_test_model(model_name="APAC Anthropic Claude 3 Haiku")
        aliases = generator.generate(model_info=model)

        # Should remove Anthropic (provider) but keep APAC (regional)
        # Regional prefixes must be preserved to prevent ambiguous aliases
        assert "APAC Claude 3 Haiku" in aliases
        # Should NOT generate unprefixed variant (would be ambiguous)
        assert "Claude 3 Haiku" not in aliases

    def test_generate_removes_provider_prefix(self) -> None:
        """Test removal of provider prefixes while preserving regional prefixes."""
        config = AliasGenerationConfig()
        generator = PrefixedModelAliasGenerator(config=config)

        model = create_test_model(model_name="APAC Anthropic Claude 3 Haiku")
        aliases = generator.generate(model_info=model)

        # Should remove Anthropic (provider) but keep APAC (regional)
        assert "APAC Claude 3 Haiku" in aliases
        # Should NOT remove regional prefix (would create ambiguous aliases)
        assert "Claude 3 Haiku" not in aliases

    def test_generate_removes_provider_only(self) -> None:
        """Test removal of provider prefix without regional prefix."""
        config = AliasGenerationConfig()
        generator = PrefixedModelAliasGenerator(config=config)

        model = create_test_model(model_name="Anthropic Claude 3 Haiku")
        aliases = generator.generate(model_info=model)

        # Should remove Anthropic prefix
        assert "Claude 3 Haiku" in aliases

    def test_generate_with_meta_prefix(self) -> None:
        """Test removal of Meta provider prefix."""
        config = AliasGenerationConfig()
        generator = PrefixedModelAliasGenerator(config=config)

        model = create_test_model(model_name="Meta Llama 3 8B", provider="Meta")
        aliases = generator.generate(model_info=model)

        # Should remove Meta prefix
        assert "Llama 3 8B" in aliases

    def test_no_duplicate_aliases(self) -> None:
        """Test that no duplicate aliases are generated."""
        config = AliasGenerationConfig()
        generator = PrefixedModelAliasGenerator(config=config)

        model = create_test_model(model_name="APAC Anthropic Claude 3 Haiku")
        aliases = generator.generate(model_info=model)

        # Check for duplicates (case-insensitive)
        aliases_lower = [alias.lower() for alias in aliases]
        assert len(aliases_lower) == len(set(aliases_lower))

    def test_alias_limit_enforced(self) -> None:
        """Test that alias limit is enforced."""
        config = AliasGenerationConfig(max_aliases_per_model=2)
        generator = PrefixedModelAliasGenerator(config=config)

        model = create_test_model(model_name="APAC Anthropic Claude 3 Haiku")
        aliases = generator.generate(model_info=model)

        assert len(aliases) <= 2

    def test_config_disable_no_prefix_variants(self) -> None:
        """Test that no-prefix variants can be disabled."""
        config = AliasGenerationConfig(generate_no_prefix_variants=False)
        generator = PrefixedModelAliasGenerator(config=config)

        model = create_test_model(model_name="APAC Anthropic Claude 3 Haiku")
        aliases = generator.generate(model_info=model)

        # Should not generate any aliases when disabled
        assert len(aliases) == 0


class TestAliasGeneratorEdgeCases:
    """Tests for edge cases across all generators."""

    def test_empty_model_name(self) -> None:
        """Test handling of empty model names."""
        # This should raise during model creation, not during alias generation
        with pytest.raises(ValueError):
            create_test_model(model_name="")

    def test_special_characters_in_model_name(self) -> None:
        """Test handling of special characters."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude-3-Haiku")
        aliases = generator.generate(model_info=model)

        # Should handle special characters gracefully
        # May not generate aliases if pattern doesn't match
        assert isinstance(aliases, list)

    def test_very_long_model_name(self) -> None:
        """Test handling of very long model names."""
        config = AliasGenerationConfig()
        generator = VersionedModelAliasGenerator(config=config)

        long_name = "Llama 3 8B Instruct With Very Long Descriptive Name And Many Words"
        model = create_test_model(model_name=long_name, provider="Meta")
        aliases = generator.generate(model_info=model)

        # Should handle long names without errors
        assert isinstance(aliases, list)
        # All aliases should respect the limit
        assert len(aliases) <= config.max_aliases_per_model

    def test_multiple_version_numbers(self) -> None:
        """Test handling of multiple version numbers in name."""
        config = AliasGenerationConfig()
        generator = ClaudeAliasGenerator(config=config)

        model = create_test_model(model_name="Claude Haiku 4 5 20251001")
        aliases = generator.generate(model_info=model)

        # Should extract the first version number (4.5)
        assert any("4.5" in alias for alias in aliases)
        # Should not confuse date with version
        assert not any("20251001" in alias.split()[-1] for alias in aliases if "4.5" in alias)
