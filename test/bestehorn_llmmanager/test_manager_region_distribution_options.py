"""Tests that the CR-1/CR-2 options are exposed on the public manager constructors and
folded into the RetryConfig the managers use (issue #16).

These verify the public API plumbing: the new constructor parameters
(region_order, access_method_preference, global_cris_fraction) reach the
RetryManager's config, and omitting them reproduces today's defaults.
"""

from unittest.mock import Mock, patch

from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RegionOrder,
    RetryConfig,
)
from bestehorn_llmmanager.bedrock.retry.access_method_structures import AccessMethodNames
from bestehorn_llmmanager.llm_manager import LLMManager
from bestehorn_llmmanager.parallel_llm_manager import ParallelLLMManager


def _mock_catalog() -> Mock:
    mock_catalog = Mock()
    mock_catalog.ensure_catalog_available.return_value = Mock()
    mock_catalog.get_model_info.return_value = Mock(
        model_id="test-model-id",
        has_direct_access=True,
        has_regional_cris=False,
        has_global_cris=False,
        regional_cris_profile_id=None,
        global_cris_profile_id=None,
    )
    mock_catalog.is_model_available.return_value = True
    return mock_catalog


def _make_llm_manager(**kwargs) -> LLMManager:
    with patch(
        "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
        return_value=_mock_catalog(),
    ):
        return LLMManager(
            models=["Claude Opus 4 8"],
            regions=["us-east-1", "us-west-2", "eu-west-1"],
            **kwargs,
        )


def _make_parallel_manager(**kwargs) -> ParallelLLMManager:
    with patch(
        "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
        return_value=_mock_catalog(),
    ):
        return ParallelLLMManager(
            models=["Claude Opus 4 8"],
            regions=["us-east-1", "us-west-2", "eu-west-1"],
            **kwargs,
        )


class TestLLMManagerOptions:
    def test_region_order_reaches_retry_config(self) -> None:
        mgr = _make_llm_manager(region_order=RegionOrder.ROTATE)
        assert mgr._retry_manager._config.region_order == RegionOrder.ROTATE

    def test_access_method_preference_reaches_retry_config(self) -> None:
        mgr = _make_llm_manager(access_method_preference=AccessMethodNames.GLOBAL_CRIS)
        assert mgr._retry_manager._config.access_method_preference == AccessMethodNames.GLOBAL_CRIS

    def test_global_cris_fraction_reaches_retry_config(self) -> None:
        mgr = _make_llm_manager(global_cris_fraction=0.7)
        assert mgr._retry_manager._config.global_cris_fraction == 0.7

    def test_defaults_unchanged(self) -> None:
        mgr = _make_llm_manager()
        cfg = mgr._retry_manager._config
        assert cfg.region_order == RegionOrder.FIXED
        assert cfg.access_method_preference is None
        assert cfg.global_cris_fraction is None

    def test_new_options_merge_into_explicit_retry_config(self) -> None:
        """Caller-passed new options override a provided retry_config's fields."""
        mgr = _make_llm_manager(
            retry_config=RetryConfig(max_retries=7),
            region_order=RegionOrder.ROTATE,
        )
        cfg = mgr._retry_manager._config
        assert cfg.max_retries == 7  # preserved from the provided config
        assert cfg.region_order == RegionOrder.ROTATE  # applied from the new option


class TestParallelLLMManagerOptions:
    def test_options_propagate_to_inner_llm_manager(self) -> None:
        mgr = _make_parallel_manager(
            region_order=RegionOrder.ROTATE,
            access_method_preference=AccessMethodNames.GLOBAL_CRIS,
            global_cris_fraction=0.3,
        )
        inner_cfg = mgr._llm_manager._retry_manager._config
        assert inner_cfg.region_order == RegionOrder.ROTATE
        assert inner_cfg.access_method_preference == AccessMethodNames.GLOBAL_CRIS
        assert inner_cfg.global_cris_fraction == 0.3

    def test_defaults_unchanged(self) -> None:
        mgr = _make_parallel_manager()
        inner_cfg = mgr._llm_manager._retry_manager._config
        assert inner_cfg.region_order == RegionOrder.FIXED
        assert inner_cfg.access_method_preference is None
        assert inner_cfg.global_cris_fraction is None
