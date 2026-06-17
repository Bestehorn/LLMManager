"""Tests for CR-1: per-call region-order rotation in generate_retry_targets.

Regression context (issue #16): under the default RetryStrategy.REGION_FIRST,
generate_retry_targets iterates the caller's region list in fixed order, so every
converse call starts its first attempt at regions[0]. For a wide fan-out this piles all
first attempts on one region and triggers single-region throttling. CR-1 adds an opt-in
region_order ("fixed" | "rotate" | "shuffle") on RetryConfig; "rotate"/"shuffle" spread
the first-attempted region across calls while preserving full failover depth (the list
is only reordered, never shrunk). Default "fixed" reproduces today's order exactly.
"""

from unittest.mock import Mock

from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RegionOrder,
    RetryConfig,
    RetryStrategy,
)
from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager

REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
MODELS = ["Claude Opus 4 8"]


def _umm() -> Mock:
    """A UnifiedModelManager mock whose get_model_access_info returns direct access."""
    umm = Mock()

    def _info(model_name: str, region: str) -> ModelAccessInfo:
        return ModelAccessInfo(
            region=region,
            has_direct_access=True,
            model_id=f"model-id-{region}",
        )

    umm.get_model_access_info.side_effect = _info
    return umm


def _first_regions(manager: RetryManager, umm: Mock, calls: int) -> list[str]:
    out = []
    for _ in range(calls):
        targets = manager.generate_retry_targets(
            models=MODELS, regions=REGIONS, unified_model_manager=umm
        )
        out.append(targets[0][1])  # (model, region, access_info) -> region
    return out


class TestRegionOrderRotate:
    """P1 — rotate spreads first attempts across all regions."""

    def test_rotate_spreads_first_region(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(region_order=RegionOrder.ROTATE))
        firsts = _first_regions(mgr, _umm(), calls=2 * len(REGIONS))
        # Every region must appear as the first attempt (uniform spread).
        assert set(firsts) == set(REGIONS)
        assert firsts[0] != firsts[1], "first region did not rotate between calls"

    def test_rotate_is_deterministic_left_rotation(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(region_order=RegionOrder.ROTATE))
        firsts = _first_regions(mgr, _umm(), calls=len(REGIONS))
        # call k starts at regions[k % n]
        assert firsts == REGIONS

    def test_rotate_preserves_all_regions_as_failover(self) -> None:
        """P3 — the full region set is still present every call (only reordered)."""
        mgr = RetryManager(retry_config=RetryConfig(region_order=RegionOrder.ROTATE))
        umm = _umm()
        for _ in range(len(REGIONS) + 1):
            targets = mgr.generate_retry_targets(
                models=MODELS, regions=REGIONS, unified_model_manager=umm
            )
            visited = [region for (_model, region, _info) in targets]
            assert sorted(visited) == sorted(REGIONS)


class TestRegionOrderShuffle:
    """P1 — shuffle also spreads, without reducing the region set."""

    def test_shuffle_preserves_all_regions(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(region_order=RegionOrder.SHUFFLE))
        umm = _umm()
        targets = mgr.generate_retry_targets(
            models=MODELS, regions=REGIONS, unified_model_manager=umm
        )
        visited = [region for (_model, region, _info) in targets]
        assert sorted(visited) == sorted(REGIONS)


class TestRegionOrderFixedBackwardCompat:
    """P2 — default 'fixed' is byte-identical to the pre-change order."""

    def test_default_is_fixed(self) -> None:
        assert RetryConfig().region_order == RegionOrder.FIXED

    def test_fixed_preserves_input_order(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(region_order=RegionOrder.FIXED))
        firsts = _first_regions(mgr, _umm(), calls=3)
        # Fixed: every call starts at regions[0], full order matches input.
        assert firsts == [REGIONS[0], REGIONS[0], REGIONS[0]]

    def test_fixed_full_order_matches_input(self) -> None:
        mgr = RetryManager(retry_config=RetryConfig(region_order=RegionOrder.FIXED))
        umm = _umm()
        targets = mgr.generate_retry_targets(
            models=MODELS, regions=REGIONS, unified_model_manager=umm
        )
        assert [region for (_m, region, _i) in targets] == REGIONS


class TestRegionOrderModelFirst:
    """Rotation also applies under MODEL_FIRST strategy."""

    def test_rotate_under_model_first(self) -> None:
        mgr = RetryManager(
            retry_config=RetryConfig(
                retry_strategy=RetryStrategy.MODEL_FIRST, region_order=RegionOrder.ROTATE
            )
        )
        firsts = _first_regions(mgr, _umm(), calls=len(REGIONS))
        assert set(firsts) == set(REGIONS)


class TestRegionOrderValidation:
    """Invalid region_order is rejected at config construction."""

    def test_invalid_region_order_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            RetryConfig(region_order="sideways")
