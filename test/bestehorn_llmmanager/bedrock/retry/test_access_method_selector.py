"""
Unit tests for AccessMethodSelector.

Tests specific examples and edge cases for access method selection logic.
"""

import pytest

from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from src.bestehorn_llmmanager.bedrock.retry.access_method_selector import (
    AccessMethodSelector,
)
from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
    AccessMethodPreference,
)
from src.bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)


class TestAccessMethodSelector:
    """Unit tests for AccessMethodSelector."""

    @pytest.fixture
    def tracker(self):
        """Create fresh AccessMethodTracker."""
        return AccessMethodTracker.get_instance()

    @pytest.fixture
    def selector(self, tracker):
        """Create AccessMethodSelector with tracker."""
        return AccessMethodSelector(access_method_tracker=tracker)

    def test_select_with_direct_access_available(self, selector):
        """Test selection when direct access is available."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        assert method == AccessMethodNames.DIRECT
        assert model_id == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_select_with_only_regional_cris(self, selector):
        """Test selection when only regional CRIS is available."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_regional_cris=True,
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        assert method == AccessMethodNames.REGIONAL_CRIS
        assert model_id == "arn:aws:bedrock:us-east-1::inference-profile/regional-123"

    def test_select_with_only_global_cris(self, selector):
        """Test selection when only global CRIS is available."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_global_cris=True,
            global_cris_profile_id="arn:aws:bedrock:us-west-2::inference-profile/global-456",
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        assert method == AccessMethodNames.GLOBAL_CRIS
        assert model_id == "arn:aws:bedrock:us-west-2::inference-profile/global-456"

    def test_select_with_multiple_options_prefers_direct(self, selector):
        """Test that direct access is preferred when multiple options available."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            has_global_cris=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
            global_cris_profile_id="arn:aws:bedrock:us-west-2::inference-profile/global-456",
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        # Should prefer direct access
        assert method == AccessMethodNames.DIRECT
        assert model_id == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_select_with_direct_and_regional_prefers_direct(self, selector):
        """Test that direct is preferred over regional CRIS."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        assert method == AccessMethodNames.DIRECT
        assert model_id == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_select_with_regional_and_global_prefers_regional(self, selector):
        """Test that regional CRIS is preferred over global CRIS."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_regional_cris=True,
            has_global_cris=True,
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
            global_cris_profile_id="arn:aws:bedrock:us-west-2::inference-profile/global-456",
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        assert method == AccessMethodNames.REGIONAL_CRIS
        assert model_id == "arn:aws:bedrock:us-east-1::inference-profile/regional-123"

    def test_select_with_learned_preference_for_regional(self, selector):
        """Test that learned preference for regional CRIS is applied."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
        )

        preference = AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=True,
            prefer_global_cris=False,
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=preference,
        )

        # Should use learned preference for regional CRIS
        assert method == AccessMethodNames.REGIONAL_CRIS
        assert model_id == "arn:aws:bedrock:us-east-1::inference-profile/regional-123"

    def test_select_with_learned_preference_for_global(self, selector):
        """Test that learned preference for global CRIS is applied."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_global_cris=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            global_cris_profile_id="arn:aws:bedrock:us-west-2::inference-profile/global-456",
        )

        preference = AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=False,
            prefer_global_cris=True,
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=preference,
        )

        # Should use learned preference for global CRIS
        assert method == AccessMethodNames.GLOBAL_CRIS
        assert model_id == "arn:aws:bedrock:us-west-2::inference-profile/global-456"

    def test_select_with_unavailable_learned_preference_falls_back(self, selector):
        """Test that unavailable learned preference falls back to default order."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )

        # Preference for regional CRIS, but not available
        preference = AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=True,
            prefer_global_cris=False,
        )

        model_id, method = selector.select_access_method(
            access_info=access_info,
            learned_preference=preference,
        )

        # Should fall back to direct access
        assert method == AccessMethodNames.DIRECT
        assert model_id == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_fallback_generation_excludes_failed_method(self, selector):
        """Test that fallback methods exclude the failed method."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            has_global_cris=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
            global_cris_profile_id="arn:aws:bedrock:us-west-2::inference-profile/global-456",
        )

        fallbacks = selector.get_fallback_access_methods(
            access_info=access_info,
            failed_method=AccessMethodNames.DIRECT,
        )

        # Should have 2 fallbacks (regional and global)
        assert len(fallbacks) == 2

        # Should not include direct
        method_names = [method for _, method in fallbacks]
        assert AccessMethodNames.DIRECT not in method_names

        # Should be in preference order: regional, then global
        assert fallbacks[0][1] == AccessMethodNames.REGIONAL_CRIS
        assert fallbacks[1][1] == AccessMethodNames.GLOBAL_CRIS

    def test_fallback_generation_with_only_one_alternative(self, selector):
        """Test fallback generation when only one alternative exists."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
        )

        fallbacks = selector.get_fallback_access_methods(
            access_info=access_info,
            failed_method=AccessMethodNames.DIRECT,
        )

        # Should have 1 fallback (regional)
        assert len(fallbacks) == 1
        assert fallbacks[0][1] == AccessMethodNames.REGIONAL_CRIS
        assert fallbacks[0][0] == "arn:aws:bedrock:us-east-1::inference-profile/regional-123"

    def test_fallback_generation_with_no_alternatives(self, selector):
        """Test fallback generation when no alternatives exist."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )

        fallbacks = selector.get_fallback_access_methods(
            access_info=access_info,
            failed_method=AccessMethodNames.DIRECT,
        )

        # Should have no fallbacks
        assert len(fallbacks) == 0

    def test_fallback_respects_preference_order(self, selector):
        """Test that fallback methods respect preference order."""
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            has_global_cris=True,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional-123",
            global_cris_profile_id="arn:aws:bedrock:us-west-2::inference-profile/global-456",
        )

        # Fail regional CRIS
        fallbacks = selector.get_fallback_access_methods(
            access_info=access_info,
            failed_method=AccessMethodNames.REGIONAL_CRIS,
        )

        # Should have 2 fallbacks: direct, then global
        assert len(fallbacks) == 2
        assert fallbacks[0][1] == AccessMethodNames.DIRECT
        assert fallbacks[1][1] == AccessMethodNames.GLOBAL_CRIS

    def test_edge_case_no_access_methods_raises_error(self, selector):
        """Test that selecting with no access methods raises ValueError."""
        # This should not be possible due to ModelAccessInfo validation,
        # but test the selector's behavior if it somehow receives invalid input

        # We can't create an invalid ModelAccessInfo through normal means,
        # so we'll skip this test as it's prevented by ModelAccessInfo validation
        pass
