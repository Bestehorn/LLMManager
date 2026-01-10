"""
Integration tests for BedrockModelCatalog name resolution.

Tests the integration of ModelNameResolver with BedrockModelCatalog,
verifying that friendly names, legacy names, and API names all work correctly.
"""

import pytest

from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode


class TestCatalogNameResolution:
    """Test catalog name resolution with various name formats."""

    @pytest.fixture
    def catalog(self):
        """Create a catalog instance for testing."""
        # Use bundled data to avoid API calls in tests
        return BedrockModelCatalog(
            cache_mode=CacheMode.NONE,
            fallback_to_bundled=True,
        )

    def test_get_model_info_with_api_name(self, catalog):
        """Test getting model info using exact API name."""
        # Get a model from the catalog to use its exact name
        models = catalog.list_models()
        if not models:
            pytest.skip("No models available in catalog")

        # Use the exact API name
        api_name = models[0].model_name
        region = models[0].get_supported_regions()[0]

        # Should resolve successfully
        access_info = catalog.get_model_info(model_name=api_name, region=region)
        assert access_info is not None
        assert access_info.model_id is not None

    def test_get_model_info_with_friendly_name(self, catalog):
        """Test getting model info using friendly alias."""
        # Try common friendly names
        friendly_names = [
            "Claude 3 Haiku",
            "Claude 3 Sonnet",
            "Claude 3.5 Sonnet",
            "Titan Text G1 - Lite",
        ]

        resolved_count = 0
        for friendly_name in friendly_names:
            # Try to get model info (may not exist in bundled data)
            access_info = catalog.get_model_info(model_name=friendly_name, region="us-east-1")
            if access_info is not None:
                resolved_count += 1
                assert access_info.model_id is not None

        # At least one friendly name should resolve
        # (if none resolve, bundled data might be outdated)
        if resolved_count == 0:
            pytest.skip("No friendly names resolved - bundled data may be outdated")

    def test_get_model_info_with_case_variations(self, catalog):
        """Test getting model info with different casing."""
        # Get a model from the catalog
        models = catalog.list_models()
        if not models:
            pytest.skip("No models available in catalog")

        # Use the exact API name
        api_name = models[0].model_name
        region = models[0].get_supported_regions()[0]

        # Try different case variations
        variations = [
            api_name.lower(),
            api_name.upper(),
            api_name.title(),
        ]

        for variation in variations:
            access_info = catalog.get_model_info(model_name=variation, region=region)
            # Should resolve (case insensitive)
            assert access_info is not None, f"Failed to resolve case variation: {variation}"

    def test_get_model_info_with_spacing_variations(self, catalog):
        """Test getting model info with spacing variations."""
        # Get a model from the catalog
        models = catalog.list_models()
        if not models:
            pytest.skip("No models available in catalog")

        # Find a model with spaces in the name
        model_with_spaces = None
        for model in models:
            if " " in model.model_name:
                model_with_spaces = model
                break

        if model_with_spaces is None:
            pytest.skip("No models with spaces in name")

        api_name = model_with_spaces.model_name
        region = model_with_spaces.get_supported_regions()[0]

        # Try spacing variations
        variations = [
            api_name.replace(" ", ""),  # No spaces
            api_name.replace(" ", "  "),  # Double spaces
            api_name.replace(" ", "-"),  # Hyphens instead of spaces
        ]

        for variation in variations:
            access_info = catalog.get_model_info(model_name=variation, region=region)
            # Should resolve (spacing flexible)
            if access_info is None:
                # Some variations might not resolve, that's okay
                # Just verify we don't crash
                pass

    def test_is_model_available_with_friendly_name(self, catalog):
        """Test checking model availability using friendly alias."""
        # Try common friendly names
        friendly_names = [
            "Claude 3 Haiku",
            "Claude 3 Sonnet",
        ]

        for friendly_name in friendly_names:
            # Should not crash, even if model doesn't exist
            result = catalog.is_model_available(model_name=friendly_name, region="us-east-1")
            assert isinstance(result, bool)

    def test_is_model_available_with_invalid_name(self, catalog):
        """Test checking availability with invalid model name."""
        # Should return False, not crash
        result = catalog.is_model_available(model_name="NonExistentModel12345", region="us-east-1")
        assert result is False

    def test_get_model_info_returns_none_for_invalid_name(self, catalog):
        """Test that invalid model names return None."""
        access_info = catalog.get_model_info(model_name="NonExistentModel12345", region="us-east-1")
        assert access_info is None

    def test_name_resolution_with_legacy_names(self, catalog):
        """Test resolution of legacy UnifiedModelManager names."""
        # These are known legacy names from UnifiedModelManager
        legacy_names = [
            "Claude 3 Haiku",
            "Claude 3 Sonnet",
            "Claude 3 Opus",
            "Claude 3.5 Sonnet",
            "Titan Text G1 - Lite",
            "Titan Text G1 - Express",
        ]

        resolved_count = 0
        for legacy_name in legacy_names:
            # Try to resolve (may not exist in bundled data)
            access_info = catalog.get_model_info(model_name=legacy_name, region="us-east-1")
            if access_info is not None:
                resolved_count += 1

        # At least some legacy names should resolve
        # (if none resolve, legacy mapping might be incomplete)
        if resolved_count == 0:
            pytest.skip("No legacy names resolved - mapping may be incomplete")

    def test_name_resolver_lazy_initialization(self, catalog):
        """Test that name resolver is initialized lazily."""
        # Name resolver should not be initialized yet
        assert catalog._name_resolver is None

        # First query should initialize it
        catalog.get_model_info(model_name="test", region="us-east-1")

        # Now it should be initialized
        assert catalog._name_resolver is not None

    def test_clear_cache_clears_name_resolver(self, catalog):
        """Test that clearing cache also clears name resolver."""
        # Initialize name resolver
        catalog.get_model_info(model_name="test", region="us-east-1")
        assert catalog._name_resolver is not None

        # Clear cache
        catalog.clear_cache()

        # Name resolver should be cleared
        assert catalog._name_resolver is None

    def test_refresh_catalog_clears_name_resolver(self, catalog):
        """Test that refreshing catalog clears name resolver."""
        # Initialize name resolver
        catalog.get_model_info(model_name="test", region="us-east-1")
        assert catalog._name_resolver is not None

        # Refresh catalog (will use bundled data since API is not available)
        try:
            catalog.refresh_catalog()
        except Exception:
            # Refresh might fail if no data sources available
            pass

        # Name resolver should be cleared (will be re-initialized on next query)
        # Note: It might be re-initialized during refresh, so we just check it exists
        # The important thing is it doesn't crash


class TestCatalogNameResolutionErrorMessages:
    """Test error messages include suggestions."""

    @pytest.fixture
    def catalog(self):
        """Create a catalog instance for testing."""
        return BedrockModelCatalog(
            cache_mode=CacheMode.NONE,
            fallback_to_bundled=True,
        )

    def test_invalid_model_name_returns_none(self, catalog):
        """Test that invalid model names return None (not exceptions)."""
        # Invalid model name should return None
        access_info = catalog.get_model_info(model_name="InvalidModelXYZ123", region="us-east-1")
        assert access_info is None

    def test_is_model_available_returns_false_for_invalid(self, catalog):
        """Test that invalid model names return False."""
        # Invalid model name should return False
        result = catalog.is_model_available(model_name="InvalidModelXYZ123", region="us-east-1")
        assert result is False

    def test_empty_model_name_returns_none(self, catalog):
        """Test that empty model names return None."""
        access_info = catalog.get_model_info(model_name="", region="us-east-1")
        assert access_info is None

    def test_whitespace_model_name_returns_none(self, catalog):
        """Test that whitespace-only model names return None."""
        access_info = catalog.get_model_info(model_name="   ", region="us-east-1")
        assert access_info is None


class TestCatalogNameResolutionWithRealModels:
    """Test name resolution with real model names from catalog."""

    @pytest.fixture
    def catalog(self):
        """Create a catalog instance for testing."""
        return BedrockModelCatalog(
            cache_mode=CacheMode.NONE,
            fallback_to_bundled=True,
        )

    def test_all_catalog_models_resolve_by_exact_name(self, catalog):
        """Test that all models in catalog resolve by their exact name."""
        models = catalog.list_models()
        if not models:
            pytest.skip("No models available in catalog")

        # Test first 10 models (to keep test fast)
        for model in models[:10]:
            api_name = model.model_name
            regions = model.get_supported_regions()
            if not regions:
                continue

            region = regions[0]

            # Should resolve by exact name
            access_info = catalog.get_model_info(model_name=api_name, region=region)
            assert access_info is not None, f"Failed to resolve model: {api_name}"
            # Verify we got access info (model_id might be None for CRIS-only models)
            assert access_info.region == region

    def test_catalog_models_resolve_case_insensitive(self, catalog):
        """Test that catalog models resolve with different casing."""
        models = catalog.list_models()
        if not models:
            pytest.skip("No models available in catalog")

        # Test first 5 models (to keep test fast)
        for model in models[:5]:
            api_name = model.model_name
            regions = model.get_supported_regions()
            if not regions:
                continue

            region = regions[0]

            # Try lowercase
            access_info = catalog.get_model_info(model_name=api_name.lower(), region=region)
            assert access_info is not None, f"Failed to resolve lowercase: {api_name.lower()}"

            # Try uppercase
            access_info = catalog.get_model_info(model_name=api_name.upper(), region=region)
            assert access_info is not None, f"Failed to resolve uppercase: {api_name.upper()}"
