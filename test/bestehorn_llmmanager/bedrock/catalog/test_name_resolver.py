"""
Unit tests for ModelNameResolver.

These tests validate specific examples and edge cases for model name resolution.
"""

from datetime import datetime

import pytest

from src.bestehorn_llmmanager.bedrock.catalog.name_resolution_structures import (
    AliasGenerationConfig,
    MatchType,
)
from src.bestehorn_llmmanager.bedrock.catalog.name_resolver import ModelNameResolver
from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from src.bestehorn_llmmanager.bedrock.models.catalog_structures import (
    CatalogMetadata,
    CatalogSource,
    UnifiedCatalog,
)
from src.bestehorn_llmmanager.bedrock.models.unified_structures import UnifiedModelInfo


@pytest.fixture
def sample_catalog():
    """Create a sample catalog for testing."""
    models = {
        "Claude Haiku 4 5 20251001": UnifiedModelInfo(
            model_name="Claude Haiku 4 5 20251001",
            model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
            provider="Anthropic",
            input_modalities=["TEXT", "IMAGE"],
            output_modalities=["TEXT"],
            streaming_supported=True,
            region_access={
                "us-east-1": ModelAccessInfo(
                    region="us-east-1",
                    has_direct_access=True,
                    model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
                )
            },
        ),
        "Llama 3 8B Instruct": UnifiedModelInfo(
            model_name="Llama 3 8B Instruct",
            model_id="meta.llama3-8b-instruct-v1:0",
            provider="Meta",
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            streaming_supported=True,
            region_access={
                "us-west-2": ModelAccessInfo(
                    region="us-west-2",
                    has_direct_access=True,
                    model_id="meta.llama3-8b-instruct-v1:0",
                )
            },
        ),
        "APAC Anthropic Claude 3 Haiku": UnifiedModelInfo(
            model_name="APAC Anthropic Claude 3 Haiku",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            provider="Anthropic",
            input_modalities=["TEXT", "IMAGE"],
            output_modalities=["TEXT"],
            streaming_supported=True,
            region_access={
                "ap-southeast-1": ModelAccessInfo(
                    region="ap-southeast-1",
                    has_direct_access=True,
                    model_id="anthropic.claude-3-haiku-20240307-v1:0",
                )
            },
        ),
    }

    metadata = CatalogMetadata(
        source=CatalogSource.API,
        retrieval_timestamp=datetime.now(),
        api_regions_queried=["us-east-1", "us-west-2", "ap-southeast-1"],
    )

    return UnifiedCatalog(models=models, metadata=metadata)


class TestExactNameMatching:
    """Test exact name matching functionality."""

    def test_exact_match_canonical_name(self, sample_catalog):
        """Test exact match with canonical model name."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="Claude Haiku 4 5 20251001", strict=True)

        assert match is not None
        assert match.canonical_name == "Claude Haiku 4 5 20251001"
        assert match.match_type == MatchType.EXACT
        assert match.confidence == 1.0

    def test_exact_match_all_models(self, sample_catalog):
        """Test exact match works for all models in catalog."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        for model_name in sample_catalog.models.keys():
            match = resolver.resolve_name(user_name=model_name, strict=True)

            assert match is not None
            assert match.canonical_name == model_name
            assert match.match_type == MatchType.EXACT


class TestAliasMatching:
    """Test alias matching functionality."""

    def test_alias_match_claude_model(self, sample_catalog):
        """Test alias matching for Claude model."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        # Try a generated alias
        match = resolver.resolve_name(user_name="Claude 4.5 Haiku", strict=True)

        assert match is not None
        assert match.canonical_name == "Claude Haiku 4 5 20251001"
        assert match.match_type == MatchType.ALIAS
        assert match.confidence == 1.0

    def test_alias_match_prefixed_model(self, sample_catalog):
        """Test alias matching for prefixed model."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        # Try alias WITH prefix (regional prefixes are preserved to avoid ambiguity)
        match = resolver.resolve_name(user_name="APAC Claude 3 Haiku", strict=True)

        assert match is not None
        assert match.canonical_name == "APAC Anthropic Claude 3 Haiku"
        assert match.match_type == MatchType.ALIAS


class TestNormalizedMatching:
    """Test normalized matching functionality."""

    def test_normalized_match_case_insensitive(self, sample_catalog):
        """Test normalized matching with different case."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="llama 3 8b instruct", strict=False)

        assert match is not None
        assert match.canonical_name == "Llama 3 8B Instruct"
        assert match.match_type == MatchType.NORMALIZED
        assert match.confidence == 0.95

    def test_normalized_match_spacing_variations(self, sample_catalog):
        """Test normalized matching with spacing variations."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="Llama  3  8B  Instruct", strict=False)

        assert match is not None
        assert match.canonical_name == "Llama 3 8B Instruct"
        assert match.match_type == MatchType.NORMALIZED


class TestFuzzyMatching:
    """Test fuzzy matching functionality."""

    def test_fuzzy_match_substring(self, sample_catalog):
        """Test fuzzy matching with substring."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="Llama", strict=False)

        assert match is not None
        # Should match the Llama model
        assert "Llama" in match.canonical_name
        assert match.match_type == MatchType.FUZZY

    def test_fuzzy_match_similarity(self, sample_catalog):
        """Test fuzzy matching with similar name."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="Llama 3 8B Instrct", strict=False)

        assert match is not None
        assert match.canonical_name == "Llama 3 8B Instruct"
        assert match.match_type == MatchType.FUZZY

    def test_fuzzy_match_disabled_in_strict_mode(self, sample_catalog):
        """Test fuzzy matching is disabled in strict mode."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="Haiku", strict=True)

        # Should not match in strict mode
        assert match is None


class TestSuggestionGeneration:
    """Test suggestion generation functionality."""

    def test_suggestions_for_invalid_name(self, sample_catalog):
        """Test suggestions are generated for invalid name."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        # Use "Claude" which should match "Claude Haiku 4 5 20251001" with high similarity
        suggestions = resolver.get_suggestions(user_name="Claude", max_suggestions=5)

        assert len(suggestions) > 0
        # Should suggest Claude models
        assert any("Claude" in s for s in suggestions)

    def test_suggestions_limited_by_max(self, sample_catalog):
        """Test suggestions are limited by max_suggestions parameter."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        suggestions = resolver.get_suggestions(user_name="Model", max_suggestions=2)

        assert len(suggestions) <= 2

    def test_suggestions_ranked_by_relevance(self, sample_catalog):
        """Test suggestions are ranked by relevance."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        # Use "Llama 3" which should match "Llama 3 8B Instruct" with high similarity
        suggestions = resolver.get_suggestions(user_name="Llama 3", max_suggestions=5)

        # First suggestion should be most relevant
        assert "Llama" in suggestions[0]


class TestErrorScenarios:
    """Test error handling scenarios."""

    def test_empty_input(self, sample_catalog):
        """Test resolution with empty input."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="", strict=False)

        assert match is None

    def test_whitespace_only_input(self, sample_catalog):
        """Test resolution with whitespace-only input."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="   ", strict=False)

        assert match is None

    def test_none_input(self, sample_catalog):
        """Test resolution with None input."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name=None, strict=False)

        assert match is None

    def test_completely_invalid_name(self, sample_catalog):
        """Test resolution with completely invalid name."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        match = resolver.resolve_name(user_name="XYZ123InvalidModel", strict=False)

        # May or may not match depending on fuzzy matching
        # But should not crash
        assert match is None or match.match_type == MatchType.FUZZY


class TestAliasGeneration:
    """Test alias generation functionality."""

    def test_generate_aliases_for_claude_model(self, sample_catalog):
        """Test alias generation for Claude model."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        model_info = sample_catalog.models["Claude Haiku 4 5 20251001"]
        aliases = resolver.generate_aliases(model_info=model_info)

        assert len(aliases) > 0
        # Should include version variants
        assert any("4.5" in alias for alias in aliases)

    def test_generate_aliases_respects_limit(self, sample_catalog):
        """Test alias generation respects max_aliases_per_model limit."""
        config = AliasGenerationConfig(max_aliases_per_model=3)
        resolver = ModelNameResolver(catalog=sample_catalog, config=config)

        model_info = sample_catalog.models["Claude Haiku 4 5 20251001"]
        aliases = resolver.generate_aliases(model_info=model_info)

        assert len(aliases) <= 3

    def test_generate_aliases_deduplicates(self, sample_catalog):
        """Test alias generation removes duplicates."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        model_info = sample_catalog.models["Llama 3 8B Instruct"]
        aliases = resolver.generate_aliases(model_info=model_info)

        # Check no duplicates (case-insensitive)
        normalized_aliases = [alias.lower() for alias in aliases]
        assert len(normalized_aliases) == len(set(normalized_aliases))


class TestLazyIndexInitialization:
    """Test lazy index initialization."""

    def test_indexes_not_built_on_init(self, sample_catalog):
        """Test indexes are not built during initialization."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        # Indexes should not be built yet
        assert not resolver._indexes_built
        assert resolver._name_index is None
        assert resolver._normalized_index is None

    def test_indexes_built_on_first_query(self, sample_catalog):
        """Test indexes are built on first query."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        # Trigger index building
        resolver.resolve_name(user_name="Claude Haiku 4 5 20251001", strict=True)

        # Indexes should now be built
        assert resolver._indexes_built
        assert resolver._name_index is not None
        assert resolver._normalized_index is not None

    def test_indexes_built_only_once(self, sample_catalog):
        """Test indexes are built only once."""
        resolver = ModelNameResolver(catalog=sample_catalog)

        # First query
        resolver.resolve_name(user_name="Claude Haiku 4 5 20251001", strict=True)
        first_name_index = resolver._name_index

        # Second query
        resolver.resolve_name(user_name="Llama 3 8B Instruct", strict=True)
        second_name_index = resolver._name_index

        # Should be the same index object
        assert first_name_index is second_name_index
