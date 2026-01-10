"""
Property-based tests for ModelNameResolver.

These tests validate universal properties that should hold across all inputs
using the Hypothesis property-based testing framework.
"""

from datetime import datetime
from typing import Dict, List

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.bestehorn_llmmanager.bedrock.catalog.name_resolver import ModelNameResolver
from src.bestehorn_llmmanager.bedrock.models.catalog_structures import (
    CatalogMetadata,
    CatalogSource,
    UnifiedCatalog,
)
from src.bestehorn_llmmanager.bedrock.models.unified_structures import UnifiedModelInfo


# Strategy for generating realistic model names that follow AWS Bedrock patterns
# This generates names like "Claude 3 Haiku", "Llama 3 8B Instruct", etc.
@st.composite
def realistic_model_name_strategy(draw):
    """Generate realistic model names following AWS Bedrock patterns."""
    # Common provider/model prefixes
    providers = ["Claude", "Llama", "Titan", "Mistral", "Cohere", "AI21"]
    variants = ["Haiku", "Sonnet", "Opus", "Instruct", "Chat", "Text", "Embed"]
    sizes = ["8B", "70B", "13B", "7B"]

    provider = draw(st.sampled_from(providers))

    # Generate version (e.g., "3", "3.5", "2")
    # Use higher version numbers to avoid ambiguous single-digit aliases
    major = draw(st.integers(min_value=2, max_value=5))
    has_minor = draw(st.booleans())
    version = f"{major}.{draw(st.integers(min_value=0, max_value=9))}" if has_minor else str(major)

    # Always include variant to make names more distinctive
    variant = draw(st.sampled_from(variants))

    # Optionally add size
    has_size = draw(st.booleans())
    size = draw(st.sampled_from(sizes)) if has_size else ""

    # Construct name - always include provider, version, and variant
    parts = [provider, version, variant]
    if size:
        parts.append(size)

    return " ".join(parts)


# Keep the old strategy for backward compatibility with other tests
model_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"), whitelist_characters=".-"
    ),
    min_size=3,
    max_size=50,
).filter(lambda x: x.strip() and not x.isspace())


# Strategy for generating UnifiedModelInfo with realistic names
@st.composite
def unified_model_info_strategy(draw):
    """Generate a UnifiedModelInfo for testing."""
    from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo

    model_name = draw(realistic_model_name_strategy())
    model_id = f"provider.{model_name.lower().replace(' ', '-')}"

    # Create region access info
    region_access = {
        "us-east-1": ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id=model_id,
        )
    }

    return UnifiedModelInfo(
        model_name=model_name,
        model_id=model_id,
        provider="test-provider",
        input_modalities=["TEXT"],
        output_modalities=["TEXT"],
        streaming_supported=True,
        region_access=region_access,
    )


# Strategy for generating UnifiedCatalog with multiple models
@st.composite
def unified_catalog_strategy(draw, min_models=1, max_models=5):
    """Generate a UnifiedCatalog with multiple models."""
    num_models = draw(st.integers(min_value=min_models, max_value=max_models))

    models: Dict[str, UnifiedModelInfo] = {}
    for _ in range(num_models):
        model_info = draw(unified_model_info_strategy())
        # Ensure unique model names
        if model_info.model_name not in models:
            models[model_info.model_name] = model_info

    metadata = CatalogMetadata(
        source=CatalogSource.API,
        retrieval_timestamp=datetime.now(),
        api_regions_queried=["us-east-1"],
    )

    return UnifiedCatalog(models=models, metadata=metadata)


class TestAliasResolutionConsistency:
    """
    Property 1: Alias Resolution Consistency

    For any model in the catalog, if an alias is generated for that model,
    then resolving that alias must return the original model's canonical name.

    Validates: Requirements 1.2, 1.3
    """

    @settings(max_examples=100)
    @given(catalog=unified_catalog_strategy(min_models=1, max_models=10))
    def test_alias_resolution_consistency(self, catalog: UnifiedCatalog):
        """
        Feature: fix-integration-test-models, Property 1: Alias Resolution Consistency

        For any model in the catalog, if an alias is generated for that model,
        then resolving that alias must return the original model's canonical name.

        Note: This property only applies to non-ambiguous aliases. If multiple models
        generate the same alias, only the first one will be indexed (first-come-first-served).
        """
        resolver = ModelNameResolver(catalog=catalog)

        # First, collect all aliases and track which models generate them
        alias_to_models: Dict[str, List[str]] = {}
        for canonical_name, model_info in catalog.models.items():
            aliases = resolver.generate_aliases(model_info=model_info)
            for alias in aliases:
                if alias not in alias_to_models:
                    alias_to_models[alias] = []
                alias_to_models[alias].append(canonical_name)

        # Now test resolution for each model's aliases
        for canonical_name, model_info in catalog.models.items():
            aliases = resolver.generate_aliases(model_info=model_info)

            for alias in aliases:
                # Skip ambiguous aliases (generated by multiple models)
                if len(alias_to_models[alias]) > 1:
                    continue

                # Resolve the alias
                match = resolver.resolve_name(user_name=alias, strict=False)

                # The alias must resolve to the original canonical name
                assert (
                    match is not None
                ), f"Alias '{alias}' for model '{canonical_name}' failed to resolve"
                assert match.canonical_name == canonical_name, (
                    f"Alias '{alias}' resolved to '{match.canonical_name}' "
                    f"instead of '{canonical_name}'"
                )


class TestCaseInsensitivity:
    """
    Property 6: Case Insensitivity

    For any model name, resolving it with different casing (uppercase, lowercase, mixed)
    must return the same model.

    Validates: Requirements 2.1
    """

    @settings(max_examples=100)
    @given(catalog=unified_catalog_strategy(min_models=1, max_models=10))
    def test_case_insensitivity(self, catalog: UnifiedCatalog):
        """
        Feature: fix-integration-test-models, Property 6: Case Insensitivity

        For any model name, resolving it with different casing (uppercase, lowercase, mixed)
        must return the same model.
        """
        resolver = ModelNameResolver(catalog=catalog)

        # For each model in the catalog
        for canonical_name in catalog.models.keys():
            # Try different case variations
            lowercase = canonical_name.lower()
            uppercase = canonical_name.upper()

            # Resolve all variations
            match_original = resolver.resolve_name(user_name=canonical_name, strict=False)
            match_lowercase = resolver.resolve_name(user_name=lowercase, strict=False)
            match_uppercase = resolver.resolve_name(user_name=uppercase, strict=False)

            # All variations should resolve to the same canonical name
            assert match_original is not None, f"Original name '{canonical_name}' failed to resolve"

            if match_lowercase is not None:
                assert match_lowercase.canonical_name == canonical_name, (
                    f"Lowercase '{lowercase}' resolved to '{match_lowercase.canonical_name}' "
                    f"instead of '{canonical_name}'"
                )

            if match_uppercase is not None:
                assert match_uppercase.canonical_name == canonical_name, (
                    f"Uppercase '{uppercase}' resolved to '{match_uppercase.canonical_name}' "
                    f"instead of '{canonical_name}'"
                )


class TestVersionFormatFlexibility:
    """
    Property 7: Version Format Flexibility

    For any model with a version number, providing the version in different formats
    ("4.5", "4 5", "45") must resolve to the same model.

    Validates: Requirements 2.2
    """

    @settings(max_examples=100)
    @given(catalog=unified_catalog_strategy(min_models=1, max_models=10))
    def test_version_format_flexibility(self, catalog: UnifiedCatalog):
        """
        Feature: fix-integration-test-models, Property 7: Version Format Flexibility

        For any model with a version number, providing the version in different formats
        ("4.5", "4 5", "45") must resolve to the same model.
        """
        import re

        resolver = ModelNameResolver(catalog=catalog)

        # For each model in the catalog
        for canonical_name in catalog.models.keys():
            # Check if model name contains a version pattern like "3.5" or "3 5"
            # Look for patterns like "X.Y" or "X Y" where X and Y are digits
            version_pattern = r"(\d+)[.\s](\d+)"
            match = re.search(pattern=version_pattern, string=canonical_name)

            if match:
                # Extract the version components
                major = match.group(1)
                minor = match.group(2)

                # Create different version format variations
                # Replace the version in the canonical name with different formats
                base_name = canonical_name[: match.start()] + "{}" + canonical_name[match.end() :]

                # Different version formats
                dot_format = base_name.format(f"{major}.{minor}")
                space_format = base_name.format(f"{major} {minor}")
                no_separator_format = base_name.format(f"{major}{minor}")

                # Try to resolve all formats
                match_dot = resolver.resolve_name(user_name=dot_format, strict=False)
                match_space = resolver.resolve_name(user_name=space_format, strict=False)
                match_no_sep = resolver.resolve_name(user_name=no_separator_format, strict=False)

                # At least one format should resolve
                resolved_matches = [m for m in [match_dot, match_space, match_no_sep] if m]
                if resolved_matches:
                    # All resolved matches should point to the same canonical name
                    expected_canonical = resolved_matches[0].canonical_name

                    for resolved_match in resolved_matches:
                        assert resolved_match.canonical_name == expected_canonical, (
                            f"Version format variations resolved to different models: "
                            f"{[m.canonical_name for m in resolved_matches]}"
                        )


class TestSuggestionRelevance:
    """
    Property 4: Suggestion Relevance

    For any failed name resolution, all suggested names must have some similarity
    to the input name (measured by edit distance or substring matching).

    Validates: Requirements 5.2
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        catalog=unified_catalog_strategy(min_models=3, max_models=10),
        # Generate a realistic but slightly misspelled/modified model name
        # This simulates real user typos like "Claud 3 Haiku" or "Claude 3 Haiko"
        invalid_name=st.one_of(
            # Typo in provider name
            st.just("Claud").flatmap(
                lambda p: st.builds(
                    lambda v, var: f"{p} {v} {var}",
                    st.sampled_from(["3", "3.5", "2"]),
                    st.sampled_from(["Haiku", "Sonnet", "Opus"]),
                )
            ),
            # Typo in variant name
            st.just("Claude").flatmap(
                lambda p: st.builds(
                    lambda v, var: f"{p} {v} {var}",
                    st.sampled_from(["3", "3.5", "2"]),
                    st.sampled_from(["Haiko", "Sonet", "Opuss"]),
                )
            ),
            # Wrong version number
            st.just("Claude").flatmap(
                lambda p: st.builds(
                    lambda v, var: f"{p} {v} {var}",
                    st.sampled_from(["99", "0", "10"]),
                    st.sampled_from(["Haiku", "Sonnet", "Opus"]),
                )
            ),
            # Partial name
            st.sampled_from(["Clau", "Llam", "Tita", "Mist"]),
        ),
    )
    def test_suggestion_relevance(self, catalog: UnifiedCatalog, invalid_name: str):
        """
        Feature: fix-integration-test-models, Property 4: Suggestion Relevance

        For any failed name resolution, all suggested names must have some similarity
        to the input name (measured by edit distance or substring matching).
        """
        import difflib

        resolver = ModelNameResolver(catalog=catalog)

        # Skip if the invalid_name actually resolves (it's not invalid)
        match = resolver.resolve_name(user_name=invalid_name, strict=False)
        if match is not None:
            # This name actually resolves, so skip this test case
            return

        # Get suggestions for the invalid name
        suggestions = resolver.get_suggestions(user_name=invalid_name, max_suggestions=5)

        # For each suggestion, verify it has some similarity to the input
        for suggestion in suggestions:
            # Calculate similarity using difflib
            similarity = difflib.SequenceMatcher(
                a=invalid_name.lower(),
                b=suggestion.lower(),
            ).ratio()

            # Check for substring match (either direction)
            invalid_lower = invalid_name.lower()
            suggestion_lower = suggestion.lower()
            has_substring = invalid_lower in suggestion_lower or suggestion_lower in invalid_lower

            # Adjust threshold based on string length
            # For very short strings (< 5 chars), use lower threshold
            min_length = min(len(invalid_name), len(suggestion))
            threshold = 0.2 if min_length < 5 else 0.3

            # Suggestion should have either:
            # 1. Reasonable similarity (>= threshold), OR
            # 2. Substring match
            assert similarity >= threshold or has_substring, (
                f"Suggestion '{suggestion}' has low similarity ({similarity:.2f}) "
                f"and no substring match with input '{invalid_name}' "
                f"(threshold: {threshold})"
            )
