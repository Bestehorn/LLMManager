"""End-to-end test for issue #21 + #16 CR-2: a correlated model carrying a global CRIS
profile is selectable via AccessMethodSelector(caller_preference="global_cris").

This ties the fix to its purpose: once the correlator retains the global profile
(issue #21), the existing access-method selection (issue #16 CR-2) can actually resolve
the global profile id instead of always falling back to regional/direct.
"""

from datetime import datetime

from bestehorn_llmmanager.bedrock.correlators.model_cris_correlator import ModelCRISCorrelator
from bestehorn_llmmanager.bedrock.models.cris_structures import (
    CRISCatalog,
    CRISInferenceProfile,
    CRISModelInfo,
)
from bestehorn_llmmanager.bedrock.models.data_structures import BedrockModelInfo, ModelCatalog
from bestehorn_llmmanager.bedrock.retry.access_method_selector import AccessMethodSelector
from bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
    AccessMethodPreference,
)
from bestehorn_llmmanager.bedrock.tracking.access_method_tracker import AccessMethodTracker

REGIONAL_PROFILE = "us.anthropic.claude-opus-4-8"
GLOBAL_PROFILE = "global.anthropic.claude-opus-4-8"


def _correlated_region_access():
    model = BedrockModelInfo(
        provider="Anthropic",
        model_id="anthropic.claude-opus-4-8",
        regions_supported=["us-east-1*"],  # CRIS-only region
        input_modalities=["Text"],
        output_modalities=["Text"],
        streaming_supported=True,
        inference_parameters_link="https://example.com/params",
        hyperparameters_link="https://example.com/hyper",
    )
    model_catalog = ModelCatalog(
        retrieval_timestamp=datetime.now(), models={"Claude Opus 4 8": model}
    )
    cris_model = CRISModelInfo(
        model_name="anthropic.claude-opus-4-8",
        inference_profiles={
            REGIONAL_PROFILE: CRISInferenceProfile(
                inference_profile_id=REGIONAL_PROFILE,
                region_mappings={"us-east-1": ["us-east-1", "us-west-2"]},
                is_global=False,
            ),
            GLOBAL_PROFILE: CRISInferenceProfile(
                inference_profile_id=GLOBAL_PROFILE,
                region_mappings={"us-east-1": ["us-east-1", "eu-west-1"]},
                is_global=True,
            ),
        },
    )
    cris_catalog = CRISCatalog(
        retrieval_timestamp=datetime.now(),
        cris_models={"anthropic.claude-opus-4-8": cris_model},
    )
    result = ModelCRISCorrelator(enable_fuzzy_matching=False).correlate_catalogs(
        model_catalog=model_catalog, cris_catalog=cris_catalog
    )
    unified = next(iter(result.unified_models.values()))
    return unified.region_access


class TestGlobalCrisSelectableEndToEnd:
    """P5 — caller_preference='global_cris' resolves the global id for a correlated model."""

    def test_selector_resolves_global_profile_from_correlated_catalog(self) -> None:
        access = _correlated_region_access()
        info = access["us-east-1"]
        # Precondition (issue #21 fix): the correlated model carries the global profile.
        assert info.has_global_cris is True
        assert info.global_cris_profile_id == GLOBAL_PROFILE

        selector = AccessMethodSelector(access_method_tracker=AccessMethodTracker.get_instance())
        caller = AccessMethodPreference.from_method_name(AccessMethodNames.GLOBAL_CRIS)
        model_id, method = selector.select_access_method(access_info=info, caller_preference=caller)
        assert method == AccessMethodNames.GLOBAL_CRIS
        assert model_id == GLOBAL_PROFILE

    def test_default_selection_still_prefers_regional_when_no_preference(self) -> None:
        """Backward-compat: with no caller preference, default order is unchanged."""
        access = _correlated_region_access()
        info = access["us-east-1"]
        selector = AccessMethodSelector(access_method_tracker=AccessMethodTracker.get_instance())
        _model_id, method = selector.select_access_method(access_info=info)
        # No direct access on this CRIS-only region; default order picks regional CRIS.
        assert method == AccessMethodNames.REGIONAL_CRIS
