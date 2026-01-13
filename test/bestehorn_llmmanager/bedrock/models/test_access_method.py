"""
Tests for access method enumeration and ModelAccessInfo with orthogonal flags.

INTENTIONAL DEPRECATION TESTS:
This test file contains tests that intentionally use deprecated APIs to verify
backward compatibility. Tests in the following classes use deprecated APIs:
- TestModelAccessMethod: Tests deprecated enum values (CRIS_ONLY, BOTH)
- TestModelAccessInfoDeprecatedProperties: Tests deprecated properties (access_method, inference_profile_id)
- TestModelAccessInfoFromLegacy: Tests from_legacy factory method with deprecated enums

The deprecation warnings from these specific tests are EXPECTED and should not be
counted as issues. These tests validate backward compatibility requirements.
"""

import warnings

import pytest

from bestehorn_llmmanager.bedrock.models.access_method import (
    AccessRecommendation,
    ModelAccessInfo,
    ModelAccessMethod,
)
from bestehorn_llmmanager.bedrock.models.deprecation import DeprecatedEnumValueWarning


class TestModelAccessMethod:
    """Test suite for ModelAccessMethod enum."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert ModelAccessMethod.DIRECT.value == "direct"
        assert ModelAccessMethod.REGIONAL_CRIS.value == "regional_cris"
        assert ModelAccessMethod.GLOBAL_CRIS.value == "global_cris"
        assert ModelAccessMethod.CRIS_ONLY.value == "cris_only"
        assert ModelAccessMethod.BOTH.value == "both"

    def test_deprecated_cris_only_warning(self):
        """Test that CRIS_ONLY emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ModelAccessMethod._emit_deprecation_if_needed(ModelAccessMethod.CRIS_ONLY)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)
            assert "CRIS_ONLY" in str(w[0].message)
            assert "3.0.0" in str(w[0].message)

    def test_deprecated_both_warning(self):
        """Test that BOTH emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ModelAccessMethod._emit_deprecation_if_needed(ModelAccessMethod.BOTH)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)
            assert "BOTH" in str(w[0].message)
            assert "orthogonal access flags" in str(w[0].message)

    def test_non_deprecated_no_warning(self):
        """Test that non-deprecated enum values don't emit warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ModelAccessMethod._emit_deprecation_if_needed(ModelAccessMethod.DIRECT)
            ModelAccessMethod._emit_deprecation_if_needed(ModelAccessMethod.REGIONAL_CRIS)
            ModelAccessMethod._emit_deprecation_if_needed(ModelAccessMethod.GLOBAL_CRIS)
            assert len(w) == 0


class TestModelAccessInfoCreation:
    """Test suite for ModelAccessInfo creation and validation."""

    def test_direct_access_only(self):
        """Test creating ModelAccessInfo with only direct access."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        )
        assert info.region == "us-east-1"
        assert info.has_direct_access is True
        assert info.has_regional_cris is False
        assert info.has_global_cris is False
        assert info.model_id == "anthropic.claude-3-5-sonnet-20240620-v1:0"
        assert info.regional_cris_profile_id is None
        assert info.global_cris_profile_id is None

    def test_regional_cris_only(self):
        """Test creating ModelAccessInfo with only regional CRIS."""
        info = ModelAccessInfo(
            region="us-west-2",
            has_regional_cris=True,
            regional_cris_profile_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        )
        assert info.region == "us-west-2"
        assert info.has_direct_access is False
        assert info.has_regional_cris is True
        assert info.has_global_cris is False
        assert info.model_id is None
        assert info.regional_cris_profile_id == "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
        assert info.global_cris_profile_id is None

    def test_global_cris_only(self):
        """Test creating ModelAccessInfo with only global CRIS."""
        info = ModelAccessInfo(
            region="eu-west-1",
            has_global_cris=True,
            global_cris_profile_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        )
        assert info.region == "eu-west-1"
        assert info.has_direct_access is False
        assert info.has_regional_cris is False
        assert info.has_global_cris is True
        assert info.model_id is None
        assert info.regional_cris_profile_id is None
        assert info.global_cris_profile_id == "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    def test_direct_and_regional_cris(self):
        """Test creating ModelAccessInfo with both direct and regional CRIS."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
            regional_cris_profile_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        )
        assert info.has_direct_access is True
        assert info.has_regional_cris is True
        assert info.has_global_cris is False
        assert info.model_id == "anthropic.claude-3-5-sonnet-20240620-v1:0"
        assert info.regional_cris_profile_id == "us.anthropic.claude-3-5-sonnet-20240620-v1:0"

    def test_all_three_access_methods(self):
        """Test creating ModelAccessInfo with all three access methods."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            has_global_cris=True,
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
            regional_cris_profile_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            global_cris_profile_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        )
        assert info.has_direct_access is True
        assert info.has_regional_cris is True
        assert info.has_global_cris is True
        assert info.model_id is not None
        assert info.regional_cris_profile_id is not None
        assert info.global_cris_profile_id is not None

    def test_no_access_methods_fails(self):
        """Test that creating ModelAccessInfo with no access methods fails."""
        with pytest.raises(ValueError, match="At least one access method must be enabled"):
            ModelAccessInfo(region="us-east-1")

    def test_direct_access_without_model_id_fails(self):
        """Test that direct access without model_id fails validation."""
        with pytest.raises(ValueError, match="has_direct_access requires model_id"):
            ModelAccessInfo(region="us-east-1", has_direct_access=True)

    def test_regional_cris_without_profile_id_fails(self):
        """Test that regional CRIS without profile ID fails validation."""
        with pytest.raises(ValueError, match="has_regional_cris requires regional_cris_profile_id"):
            ModelAccessInfo(region="us-east-1", has_regional_cris=True)

    def test_global_cris_without_profile_id_fails(self):
        """Test that global CRIS without profile ID fails validation."""
        with pytest.raises(ValueError, match="has_global_cris requires global_cris_profile_id"):
            ModelAccessInfo(region="us-east-1", has_global_cris=True)

    def test_model_id_without_direct_access_fails(self):
        """Test that providing model_id without direct access fails."""
        with pytest.raises(ValueError, match="model_id provided but has_direct_access is False"):
            ModelAccessInfo(
                region="us-east-1",
                has_regional_cris=True,
                regional_cris_profile_id="us.test",
                model_id="test-model",
            )

    def test_regional_profile_without_flag_fails(self):
        """Test that providing regional profile ID without flag fails."""
        with pytest.raises(
            ValueError, match="regional_cris_profile_id provided but has_regional_cris is False"
        ):
            ModelAccessInfo(
                region="us-east-1",
                has_direct_access=True,
                model_id="test-model",
                regional_cris_profile_id="us.test",
            )

    def test_global_profile_without_flag_fails(self):
        """Test that providing global profile ID without flag fails."""
        with pytest.raises(
            ValueError, match="global_cris_profile_id provided but has_global_cris is False"
        ):
            ModelAccessInfo(
                region="us-east-1",
                has_direct_access=True,
                model_id="test-model",
                global_cris_profile_id="global.test",
            )


class TestModelAccessInfoDeprecatedProperties:
    """Test suite for deprecated properties in ModelAccessInfo."""

    def test_access_method_property_direct(self):
        """Test deprecated access_method property for direct access."""
        info = ModelAccessInfo(region="us-east-1", has_direct_access=True, model_id="test-model")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            method = info.access_method
            assert method == ModelAccessMethod.DIRECT
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    def test_access_method_property_cris_only(self):
        """Test deprecated access_method property for CRIS-only access."""
        info = ModelAccessInfo(
            region="us-east-1", has_regional_cris=True, regional_cris_profile_id="us.test"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            method = info.access_method
            assert method == ModelAccessMethod.CRIS_ONLY
            assert len(w) == 1

    def test_access_method_property_both(self):
        """Test deprecated access_method property for both access types."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            model_id="test-model",
            regional_cris_profile_id="us.test",
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            method = info.access_method
            assert method == ModelAccessMethod.BOTH
            assert len(w) == 1

    def test_inference_profile_id_property_regional(self):
        """Test deprecated inference_profile_id property returns regional CRIS."""
        info = ModelAccessInfo(
            region="us-east-1", has_regional_cris=True, regional_cris_profile_id="us.test"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile_id = info.inference_profile_id
            assert profile_id == "us.test"
            assert len(w) == 1

    def test_inference_profile_id_property_global(self):
        """Test deprecated inference_profile_id property returns global CRIS."""
        info = ModelAccessInfo(
            region="us-east-1", has_global_cris=True, global_cris_profile_id="global.test"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile_id = info.inference_profile_id
            assert profile_id == "global.test"
            assert len(w) == 1

    def test_inference_profile_id_property_prefers_regional(self):
        """Test that inference_profile_id prefers regional over global."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_regional_cris=True,
            has_global_cris=True,
            regional_cris_profile_id="us.test",
            global_cris_profile_id="global.test",
        )
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            profile_id = info.inference_profile_id
            assert profile_id == "us.test"


class TestModelAccessInfoFromLegacy:
    """Test suite for from_legacy factory method."""

    def test_from_legacy_direct(self):
        """Test creating from legacy DIRECT enum."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            info = ModelAccessInfo.from_legacy(
                access_method=ModelAccessMethod.DIRECT,
                region="us-east-1",
                model_id="test-model",
            )
        assert info.has_direct_access is True
        assert info.has_regional_cris is False
        assert info.has_global_cris is False
        assert info.model_id == "test-model"

    def test_from_legacy_cris_only(self):
        """Test creating from legacy CRIS_ONLY enum."""
        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            info = ModelAccessInfo.from_legacy(
                access_method=ModelAccessMethod.CRIS_ONLY,
                region="us-east-1",
                inference_profile_id="us.test",
            )
        assert info.has_direct_access is False
        assert info.has_regional_cris is True
        assert info.has_global_cris is False
        assert info.regional_cris_profile_id == "us.test"
        # Should emit deprecation warning for CRIS_ONLY
        assert any(
            issubclass(warning.category, DeprecatedEnumValueWarning)
            for warning in captured_warnings
        )

    def test_from_legacy_regional_cris(self):
        """Test creating from REGIONAL_CRIS enum."""
        info = ModelAccessInfo.from_legacy(
            access_method=ModelAccessMethod.REGIONAL_CRIS,
            region="us-east-1",
            inference_profile_id="us.test",
        )
        assert info.has_regional_cris is True
        assert info.regional_cris_profile_id == "us.test"

    def test_from_legacy_global_cris(self):
        """Test creating from GLOBAL_CRIS enum."""
        info = ModelAccessInfo.from_legacy(
            access_method=ModelAccessMethod.GLOBAL_CRIS,
            region="us-east-1",
            inference_profile_id="global.test",
        )
        assert info.has_global_cris is True
        assert info.global_cris_profile_id == "global.test"

    def test_from_legacy_both(self):
        """Test creating from legacy BOTH enum."""
        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            info = ModelAccessInfo.from_legacy(
                access_method=ModelAccessMethod.BOTH,
                region="us-east-1",
                model_id="test-model",
                inference_profile_id="us.test",
            )
        assert info.has_direct_access is True
        assert info.has_regional_cris is True
        assert info.has_global_cris is False
        assert info.model_id == "test-model"
        assert info.regional_cris_profile_id == "us.test"
        # Should emit deprecation warning for BOTH
        assert any(
            issubclass(warning.category, DeprecatedEnumValueWarning)
            for warning in captured_warnings
        )


class TestModelAccessInfoMethods:
    """Test suite for ModelAccessInfo utility methods."""

    def test_get_access_summary_direct_only(self):
        """Test access summary for direct-only access."""
        info = ModelAccessInfo(region="us-east-1", has_direct_access=True, model_id="test-model")
        assert info.get_access_summary() == "DIRECT"

    def test_get_access_summary_regional_cris_only(self):
        """Test access summary for regional CRIS only."""
        info = ModelAccessInfo(
            region="us-east-1", has_regional_cris=True, regional_cris_profile_id="us.test"
        )
        assert info.get_access_summary() == "REGIONAL_CRIS"

    def test_get_access_summary_global_cris_only(self):
        """Test access summary for global CRIS only."""
        info = ModelAccessInfo(
            region="us-east-1", has_global_cris=True, global_cris_profile_id="global.test"
        )
        assert info.get_access_summary() == "GLOBAL_CRIS"

    def test_get_access_summary_multiple_methods(self):
        """Test access summary for multiple access methods."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            has_global_cris=True,
            model_id="test-model",
            regional_cris_profile_id="us.test",
            global_cris_profile_id="global.test",
        )
        summary = info.get_access_summary()
        assert "DIRECT" in summary
        assert "REGIONAL_CRIS" in summary
        assert "GLOBAL_CRIS" in summary

    def test_has_any_cris_access_true(self):
        """Test has_any_cris_access returns True when CRIS available."""
        info = ModelAccessInfo(
            region="us-east-1", has_regional_cris=True, regional_cris_profile_id="us.test"
        )
        assert info.has_any_cris_access() is True

    def test_has_any_cris_access_false(self):
        """Test has_any_cris_access returns False when no CRIS."""
        info = ModelAccessInfo(region="us-east-1", has_direct_access=True, model_id="test-model")
        assert info.has_any_cris_access() is False

    def test_get_cris_profile_ids_empty(self):
        """Test get_cris_profile_ids returns empty list when no CRIS."""
        info = ModelAccessInfo(region="us-east-1", has_direct_access=True, model_id="test-model")
        assert info.get_cris_profile_ids() == []

    def test_get_cris_profile_ids_regional_only(self):
        """Test get_cris_profile_ids with regional CRIS only."""
        info = ModelAccessInfo(
            region="us-east-1", has_regional_cris=True, regional_cris_profile_id="us.test"
        )
        assert info.get_cris_profile_ids() == ["us.test"]

    def test_get_cris_profile_ids_global_only(self):
        """Test get_cris_profile_ids with global CRIS only."""
        info = ModelAccessInfo(
            region="us-east-1", has_global_cris=True, global_cris_profile_id="global.test"
        )
        assert info.get_cris_profile_ids() == ["global.test"]

    def test_get_cris_profile_ids_both(self):
        """Test get_cris_profile_ids with both CRIS types."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_regional_cris=True,
            has_global_cris=True,
            regional_cris_profile_id="us.test",
            global_cris_profile_id="global.test",
        )
        profile_ids = info.get_cris_profile_ids()
        assert len(profile_ids) == 2
        assert "us.test" in profile_ids
        assert "global.test" in profile_ids


class TestAccessRecommendation:
    """Test suite for AccessRecommendation dataclass."""

    def test_create_recommendation(self):
        """Test creating an AccessRecommendation."""
        recommended = ModelAccessInfo(
            region="us-east-1", has_direct_access=True, model_id="test-model"
        )
        alternative = ModelAccessInfo(
            region="us-east-1", has_regional_cris=True, regional_cris_profile_id="us.test"
        )

        recommendation = AccessRecommendation(
            recommended_access=recommended,
            rationale="Direct access is faster",
            alternatives=[alternative],
        )

        assert recommendation.recommended_access == recommended
        assert recommendation.rationale == "Direct access is faster"
        assert len(recommendation.alternatives) == 1
        assert recommendation.alternatives[0] == alternative
