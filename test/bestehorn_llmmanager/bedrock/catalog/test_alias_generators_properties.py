"""
Property-based tests for alias generators.

Tests universal properties that should hold for all alias generation strategies.
"""

from typing import Dict, List

from hypothesis import given, settings
from hypothesis import strategies as st

from src.bestehorn_llmmanager.bedrock.catalog.alias_generators import (
    AliasGenerator,
    ClaudeAliasGenerator,
    PrefixedModelAliasGenerator,
    VersionedModelAliasGenerator,
)
from src.bestehorn_llmmanager.bedrock.catalog.name_normalizer import normalize_model_name
from src.bestehorn_llmmanager.bedrock.catalog.name_resolution_structures import (
    AliasGenerationConfig,
)
from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from src.bestehorn_llmmanager.bedrock.models.unified_structures import UnifiedModelInfo


# Strategy for generating test model names
@st.composite
def model_name_strategy(draw: st.DrawFn) -> str:
    """Generate realistic model names for testing."""
    providers = ["Claude", "Llama", "Titan", "Mistral", "Cohere"]
    variants = ["Haiku", "Sonnet", "Opus", "Instruct", "Express", "Lite"]
    prefixes = ["", "APAC ", "EU ", "US ", "Anthropic ", "Amazon ", "Meta "]

    provider = draw(st.sampled_from(providers))
    version_major = draw(st.integers(min_value=1, max_value=5))
    version_minor = draw(st.integers(min_value=0, max_value=9))
    variant = draw(st.sampled_from(variants))
    prefix = draw(st.sampled_from(prefixes))

    # Generate different name patterns
    pattern = draw(st.integers(min_value=0, max_value=3))

    if pattern == 0:
        # Pattern: "Claude 3 Haiku"
        return f"{prefix}{provider} {version_major} {variant}"
    elif pattern == 1:
        # Pattern: "Claude Haiku 3 5"
        return f"{prefix}{provider} {variant} {version_major} {version_minor}"
    elif pattern == 2:
        # Pattern: "Llama 3 8B Instruct"
        size = draw(st.sampled_from(["8B", "13B", "70B", ""]))
        return f"{prefix}{provider} {version_major} {size} {variant}".strip()
    else:
        # Pattern: "Claude 3.5 Sonnet"
        return f"{prefix}{provider} {version_major}.{version_minor} {variant}"


@st.composite
def unified_model_info_strategy(draw: st.DrawFn) -> UnifiedModelInfo:
    """Generate UnifiedModelInfo instances for testing."""
    provider = draw(st.sampled_from(["Anthropic", "Amazon", "Meta", "Cohere", "AI21", "Mistral"]))

    # Generate model name that includes provider-specific patterns
    # This ensures models from different providers have different names
    if provider == "Anthropic":
        base_name = "Claude"
    elif provider == "Amazon":
        base_name = "Titan"
    elif provider == "Meta":
        base_name = "Llama"
    elif provider == "Cohere":
        base_name = "Command"
    elif provider == "AI21":
        base_name = "Jurassic"
    else:  # Mistral
        base_name = "Mistral"

    version_major = draw(st.integers(min_value=1, max_value=5))
    version_minor = draw(st.integers(min_value=0, max_value=9))
    variant = draw(st.sampled_from(["Haiku", "Sonnet", "Opus", "Instruct", "Express", "Lite"]))
    prefix = draw(st.sampled_from(["", "APAC ", "EU ", "US "]))

    # Generate model name with provider-specific base
    pattern = draw(st.integers(min_value=0, max_value=2))
    if pattern == 0:
        model_name = f"{prefix}{base_name} {version_major} {variant}"
    elif pattern == 1:
        model_name = f"{prefix}{base_name} {variant} {version_major} {version_minor}"
    else:
        model_name = f"{prefix}{base_name} {version_major}.{version_minor} {variant}"

    region = draw(st.sampled_from(["us-east-1", "us-west-2", "eu-west-1"]))
    model_id_base = model_name.lower().replace(" ", "-")
    model_id = f"{provider.lower()}.{model_id_base}"

    return UnifiedModelInfo(
        model_name=model_name,
        provider=provider,
        model_id=model_id,
        input_modalities=["TEXT"],
        output_modalities=["TEXT"],
        streaming_supported=True,
        region_access={
            region: ModelAccessInfo(
                region=region,
                has_direct_access=True,
                model_id=model_id,
            )
        },
    )


@st.composite
def model_list_strategy(
    draw: st.DrawFn, min_size: int = 2, max_size: int = 10
) -> List[UnifiedModelInfo]:
    """Generate a list of UnifiedModelInfo instances."""
    return draw(st.lists(unified_model_info_strategy(), min_size=min_size, max_size=max_size))


class TestAliasUniquenessProperty:
    """
    Property tests for alias uniqueness.

    **Property 5: No Ambiguous Aliases**
    **Validates: Requirements 2.4**
    """

    @given(models=model_list_strategy(min_size=2, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_no_ambiguous_aliases_across_models(self, models: List[UnifiedModelInfo]) -> None:
        """
        Property: For any two different models in the catalog, their generated aliases
        must not overlap (no alias maps to multiple models).

        **Feature: fix-integration-test-models, Property 5: No Ambiguous Aliases**

        This test verifies that the alias generation system never creates ambiguous
        aliases that could map to multiple different models.

        Note: Models with the same model_id but different names (e.g., regional variants)
        are considered the same model and can share aliases.
        """
        config = AliasGenerationConfig()
        generators: List[AliasGenerator] = [
            ClaudeAliasGenerator(config=config),
            VersionedModelAliasGenerator(config=config),
            PrefixedModelAliasGenerator(config=config),
        ]

        # Build alias mapping: normalized_alias -> list of (model_name, model_id) tuples
        alias_to_models: Dict[str, List[tuple[str, str]]] = {}

        for model in models:
            # Generate aliases using all applicable generators
            all_aliases: List[str] = []
            for generator in generators:
                if generator.can_generate(model_info=model):
                    aliases = generator.generate(model_info=model)
                    all_aliases.extend(aliases)

            # Track which models each normalized alias maps to
            for alias in all_aliases:
                normalized_alias = normalize_model_name(name=alias)
                if normalized_alias:
                    if normalized_alias not in alias_to_models:
                        alias_to_models[normalized_alias] = []
                    alias_to_models[normalized_alias].append((model.model_name, model.model_id))

        # Check for ambiguous aliases (aliases that map to multiple different model_ids)
        ambiguous_aliases = []
        for alias, model_tuples in alias_to_models.items():
            # Get unique model_ids (not just names)
            unique_model_ids = list(set(model_id for _, model_id in model_tuples))
            if len(unique_model_ids) > 1:
                # Get the model names for these different model_ids
                model_names = [name for name, _ in model_tuples]
                unique_names = list(set(model_names))
                ambiguous_aliases.append((alias, unique_names, unique_model_ids))

        # Assert no ambiguous aliases exist
        assert not ambiguous_aliases, (
            f"Found ambiguous aliases that map to multiple different models: "
            f"{[(alias, names, ids) for alias, names, ids in ambiguous_aliases]}"
        )

    @given(model=unified_model_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_aliases_are_unique_per_model(self, model: UnifiedModelInfo) -> None:
        """
        Property: For any model, all generated aliases must be unique
        (no duplicate aliases for the same model).

        **Feature: fix-integration-test-models, Property 5: No Ambiguous Aliases**

        This test verifies that each generator produces unique aliases without
        duplicates for a single model.
        """
        config = AliasGenerationConfig()
        generators: List[AliasGenerator] = [
            ClaudeAliasGenerator(config=config),
            VersionedModelAliasGenerator(config=config),
            PrefixedModelAliasGenerator(config=config),
        ]

        for generator in generators:
            if generator.can_generate(model_info=model):
                aliases = generator.generate(model_info=model)

                # Normalize all aliases for comparison
                normalized_aliases = [normalize_model_name(name=alias) for alias in aliases]
                normalized_aliases = [a for a in normalized_aliases if a]  # Remove empty

                # Check for duplicates
                unique_normalized = list(set(normalized_aliases))

                assert len(normalized_aliases) == len(unique_normalized), (
                    f"Generator {generator.__class__.__name__} produced duplicate aliases "
                    f"for model '{model.model_name}': {aliases}"
                )

    @given(model=unified_model_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_alias_limit_enforced(self, model: UnifiedModelInfo) -> None:
        """
        Property: For any model, the number of generated aliases must not exceed
        the configured maximum.

        **Feature: fix-integration-test-models, Property 5: No Ambiguous Aliases**

        This test verifies that the alias limit configuration is respected.
        """
        max_aliases = 5
        config = AliasGenerationConfig(max_aliases_per_model=max_aliases)
        generators: List[AliasGenerator] = [
            ClaudeAliasGenerator(config=config),
            VersionedModelAliasGenerator(config=config),
            PrefixedModelAliasGenerator(config=config),
        ]

        for generator in generators:
            if generator.can_generate(model_info=model):
                aliases = generator.generate(model_info=model)

                assert len(aliases) <= max_aliases, (
                    f"Generator {generator.__class__.__name__} produced {len(aliases)} aliases "
                    f"for model '{model.model_name}', exceeding limit of {max_aliases}"
                )
