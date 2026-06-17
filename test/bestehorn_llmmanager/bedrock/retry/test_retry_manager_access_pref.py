"""Tests for CR-2 (RetryManager layer): caller access-method preference + interleave.

The RetryManager turns the RetryConfig's access_method_preference / global_cris_fraction
into a per-call caller preference passed to AccessMethodSelector.select_access_method.
A fixed preference applies to every call; an interleave fraction routes approximately
that share of calls to global CRIS (deterministic round-robin) and the rest to the
default order. With neither set, no caller preference is passed (today's behavior).
"""

from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig
from bestehorn_llmmanager.bedrock.retry.access_method_structures import AccessMethodNames
from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager


def _all_methods_info(region: str = "us-east-1") -> ModelAccessInfo:
    return ModelAccessInfo(
        region=region,
        has_direct_access=True,
        has_regional_cris=True,
        has_global_cris=True,
        model_id="anthropic.claude-opus-4-8",
        regional_cris_profile_id=f"arn:aws:bedrock:{region}::inference-profile/regional",
        global_cris_profile_id="global.anthropic.claude-opus-4-8",
    )


def _select(manager: RetryManager, info: ModelAccessInfo) -> tuple[str, str]:
    """Call the private selection helper the converse path uses."""
    return manager._select_model_id_for_request(
        access_info=info, model_name="Claude Opus 4 8", region=info.region
    )


class TestFixedPreferencePlumbing:
    """P4 — a fixed access_method_preference routes every call to that method."""

    def test_global_cris_preference(self) -> None:
        mgr = RetryManager(
            retry_config=RetryConfig(access_method_preference=AccessMethodNames.GLOBAL_CRIS)
        )
        info = _all_methods_info()
        model_id, method = _select(mgr, info)
        assert method == AccessMethodNames.GLOBAL_CRIS
        assert model_id == info.global_cris_profile_id


class TestInterleaveFraction:
    """P5 — global_cris_fraction routes ~fraction of calls to global CRIS."""

    def test_fraction_half_splits_calls(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(global_cris_fraction=0.5))
        info = _all_methods_info()
        methods = [_select(mgr, info)[1] for _ in range(20)]
        global_count = methods.count(AccessMethodNames.GLOBAL_CRIS)
        # ~half on global, the rest on the default order (direct).
        assert 8 <= global_count <= 12, f"expected ~10 global of 20, got {global_count}"
        assert AccessMethodNames.DIRECT in methods

    def test_fraction_zero_never_global(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(global_cris_fraction=0.0))
        info = _all_methods_info()
        methods = [_select(mgr, info)[1] for _ in range(10)]
        assert AccessMethodNames.GLOBAL_CRIS not in methods

    def test_fraction_one_always_global(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(global_cris_fraction=1.0))
        info = _all_methods_info()
        methods = [_select(mgr, info)[1] for _ in range(10)]
        assert all(m == AccessMethodNames.GLOBAL_CRIS for m in methods)


class TestBackwardCompat:
    """P6 — neither option set -> default selection (direct first), unchanged."""

    def test_no_preference_default_order(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig())
        info = _all_methods_info()
        model_id, method = _select(mgr, info)
        assert method == AccessMethodNames.DIRECT
        assert model_id == info.model_id


class TestConfigValidation:
    """The new RetryConfig fields are validated."""

    def test_invalid_preference_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            RetryConfig(access_method_preference="not-a-method")

    def test_out_of_range_fraction_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            RetryConfig(global_cris_fraction=1.5)
        with pytest.raises(ValueError):
            RetryConfig(global_cris_fraction=-0.1)
