"""Tests for issue #21: the correlator must retain global.* CRIS profiles.

Regression context: a region served by BOTH a regional CRIS profile (us./eu./jp./au.) and
a global CRIS profile (global.*) previously kept only the regional one — the correlator
took profiles[0] from get_profiles_for_source_region and discarded the rest, so
has_global_cris was never set for any model that also had a regional profile. This made
issue #16's CR-2 (access_method_preference="global_cris") unusable: no catalog model ever
carried a global_cris_profile_id.

These tests assert that a region with both profile kinds records BOTH on its
ModelAccessInfo, that a global-only region sets has_global_cris, and that regional-only
behavior is unchanged.
"""

from datetime import datetime

import pytest

from bestehorn_llmmanager.bedrock.correlators.model_cris_correlator import ModelCRISCorrelator
from bestehorn_llmmanager.bedrock.models.cris_structures import (
    CRISCatalog,
    CRISInferenceProfile,
    CRISModelInfo,
)
from bestehorn_llmmanager.bedrock.models.data_structures import BedrockModelInfo, ModelCatalog

MODEL_ID = "anthropic.claude-opus-4-8"
REGIONAL_PROFILE = "us.anthropic.claude-opus-4-8"
GLOBAL_PROFILE = "global.anthropic.claude-opus-4-8"


@pytest.fixture
def correlator() -> ModelCRISCorrelator:
    return ModelCRISCorrelator(enable_fuzzy_matching=False)


def _model_catalog(regions) -> ModelCatalog:
    """A bedrock model marked CRIS-only (regions suffixed with *) so access comes from
    inference profiles, mirroring how Opus 4.8 appears in the real catalog."""
    model = BedrockModelInfo(
        provider="Anthropic",
        model_id=MODEL_ID,
        regions_supported=[f"{r}*" for r in regions],  # '*' marks CRIS-only regions
        input_modalities=["Text"],
        output_modalities=["Text"],
        streaming_supported=True,
        inference_parameters_link="https://example.com/params",
        hyperparameters_link="https://example.com/hyper",
    )
    return ModelCatalog(retrieval_timestamp=datetime.now(), models={"Claude Opus 4 8": model})


def _cris_catalog(profiles) -> CRISCatalog:
    cris_model = CRISModelInfo(
        model_name="anthropic.claude-opus-4-8",
        inference_profiles={p.inference_profile_id: p for p in profiles},
    )
    return CRISCatalog(
        retrieval_timestamp=datetime.now(),
        cris_models={"anthropic.claude-opus-4-8": cris_model},
    )


def _region_access(correlator, regions, profiles):
    result = correlator.correlate_catalogs(
        model_catalog=_model_catalog(regions),
        cris_catalog=_cris_catalog(profiles),
    )
    # The correlator keys the unified model by a normalized name; this test exercises a
    # single model, so fetch it without assuming the exact key.
    assert len(result.unified_models) == 1, (
        f"expected 1 unified model, got {list(result.unified_models)}"
    )
    unified = next(iter(result.unified_models.values()))
    return unified.region_access


class TestRegionWithRegionalAndGlobal:
    """P1 — a region covered by both regional and global profiles records BOTH."""

    def test_region_has_both_regional_and_global_cris(self, correlator) -> None:
        regional = CRISInferenceProfile(
            inference_profile_id=REGIONAL_PROFILE,
            region_mappings={"us-east-1": ["us-east-1", "us-west-2"]},
            is_global=False,
        )
        glob = CRISInferenceProfile(
            inference_profile_id=GLOBAL_PROFILE,
            region_mappings={"us-east-1": ["us-east-1", "eu-west-1", "ap-south-1"]},
            is_global=True,
        )
        access = _region_access(correlator, ["us-east-1"], [regional, glob])

        assert "us-east-1" in access
        info = access["us-east-1"]
        assert info.has_regional_cris is True, "regional CRIS must be retained"
        assert info.regional_cris_profile_id == REGIONAL_PROFILE
        assert info.has_global_cris is True, "global CRIS must also be recorded (issue #21)"
        assert info.global_cris_profile_id == GLOBAL_PROFILE


class TestGlobalOnlyRegion:
    """P2 — a region covered only by a global profile sets has_global_cris."""

    def test_global_only_region(self, correlator) -> None:
        glob = CRISInferenceProfile(
            inference_profile_id=GLOBAL_PROFILE,
            region_mappings={"eu-west-1": ["eu-west-1", "us-east-1"]},
            is_global=True,
        )
        access = _region_access(correlator, ["eu-west-1"], [glob])

        assert "eu-west-1" in access
        info = access["eu-west-1"]
        assert info.has_global_cris is True
        assert info.global_cris_profile_id == GLOBAL_PROFILE
        assert info.has_regional_cris is False


class TestRegionalOnlyUnchanged:
    """P3 — a region covered only by a regional profile is unchanged (no global flag)."""

    def test_regional_only_region(self, correlator) -> None:
        regional = CRISInferenceProfile(
            inference_profile_id=REGIONAL_PROFILE,
            region_mappings={"us-east-1": ["us-east-1", "us-west-2"]},
            is_global=False,
        )
        access = _region_access(correlator, ["us-east-1"], [regional])

        assert "us-east-1" in access
        info = access["us-east-1"]
        assert info.has_regional_cris is True
        assert info.regional_cris_profile_id == REGIONAL_PROFILE
        assert info.has_global_cris is False
        assert info.global_cris_profile_id is None
