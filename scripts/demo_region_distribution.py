"""Demonstration: per-request region distribution + global-CRIS selection (issue #16).

This script PROVES the three change requests from issue #16 work, using the REAL
production classes (RetryManager, RegionDistributionManager, AccessMethodSelector,
RetryConfig). The ONLY thing stubbed is the model-catalog lookup
(`get_model_access_info`) — that is the external data source, not the distribution logic
under test — so the demo needs no AWS credentials and is fully reproducible.

It reproduces the change request's scenario: 14 regions, a wide fan-out of independent
maxTokens=10 classification calls. The CR documented that today every request's first
attempt lands on regions[0] (us-east-1), causing a single-region RPM throttle burst.
We show that:

  CR-1  region_order="rotate"/"shuffle" spreads first attempts across all 14 regions
        (and "fixed" reproduces the old all-on-regions[0] behavior, byte-for-byte).
  CR-2  access_method_preference="global_cris" resolves to the global CRIS profile id,
        and global_cris_fraction interleaves global vs. the default order.
  CR-3  the parallel RegionDistributionManager round-robin cursor now rotates the
        first assigned region even when the full region set is assigned per request.

Run:  venv\\Scripts\\activate & python scripts/demo_region_distribution.py
"""

from __future__ import annotations

from collections import Counter
from typing import List, Optional
from unittest.mock import Mock

from bestehorn_llmmanager.bedrock.distributors.region_distribution_manager import (
    RegionDistributionManager,
)
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RegionOrder,
    RetryConfig,
)
from bestehorn_llmmanager.bedrock.models.parallel_structures import LoadBalancingStrategy
from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager

# The 14 regions from the change request's GenerateMultiTrendDocument fan-out.
REGIONS: List[str] = [
    "us-east-1",
    "us-east-2",
    "us-west-2",
    "eu-west-1",
    "eu-west-3",
    "eu-central-1",
    "eu-north-1",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-northeast-3",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ca-central-1",
]
MODELS = ["Claude Opus 4 8"]
FANOUT = 280  # M >> N: a wide fan-out of independent classification calls.


def _bar(count: int, total: int, width: int = 28) -> str:
    filled = round(width * count / total) if total else 0
    return "#" * filled + "." * (width - filled)


def _model_catalog_stub() -> Mock:
    """A UnifiedModelManager whose get_model_access_info returns, per region, an access
    info exposing direct + regional CRIS + global CRIS (so every access method is a real
    option the selector can choose)."""
    umm = Mock()

    def _info(model_name: str, region: str) -> ModelAccessInfo:
        return ModelAccessInfo(
            region=region,
            has_direct_access=True,
            has_regional_cris=True,
            has_global_cris=True,
            model_id=f"anthropic.claude-opus-4-8::{region}",
            regional_cris_profile_id=f"arn:aws:bedrock:{region}::inference-profile/regional",
            global_cris_profile_id="global.anthropic.claude-opus-4-8",
        )

    umm.get_model_access_info.side_effect = _info
    return umm


def _first_attempt_regions(region_order: str) -> List[str]:
    """Return the first-attempted region for each of FANOUT independent converse calls,
    using the REAL RetryManager.generate_retry_targets with the given region_order."""
    mgr = RetryManager(retry_config=RetryConfig(region_order=region_order))
    umm = _model_catalog_stub()
    firsts: List[str] = []
    for _ in range(FANOUT):
        targets = mgr.generate_retry_targets(
            models=MODELS, regions=REGIONS, unified_model_manager=umm
        )
        # targets is an ordered list of (model, region, access_info); [0] is the first attempt.
        firsts.append(targets[0][1])
    return firsts


def _print_distribution(title: str, firsts: List[str]) -> None:
    counts = Counter(firsts)
    print(f"\n{title}")
    print(
        f"  {len(firsts)} requests, first attempt landed on {len(counts)}/{len(REGIONS)} regions:"
    )
    for region in REGIONS:
        c = counts.get(region, 0)
        print(f"    {region:<16} {_bar(c, len(firsts))} {c:>4}")


def demo_cr1_region_rotation() -> bool:
    print("=" * 78)
    print("CR-1 — single-call region order (RetryManager.generate_retry_targets)")
    print("=" * 78)

    fixed = _first_attempt_regions(RegionOrder.FIXED)
    rotate = _first_attempt_regions(RegionOrder.ROTATE)
    shuffle = _first_attempt_regions(RegionOrder.SHUFFLE)

    _print_distribution("region_order='fixed'  (today's behavior — the throttle burst):", fixed)
    _print_distribution("region_order='rotate' (CR-1: deterministic even spread):", rotate)
    _print_distribution("region_order='shuffle' (CR-1: randomized spread):", shuffle)

    fixed_ok = set(fixed) == {REGIONS[0]}  # all first attempts on regions[0]
    rotate_ok = set(rotate) == set(REGIONS)  # every region used as a first attempt
    shuffle_ok = set(shuffle) == set(REGIONS)
    # Failover depth preserved: a single rotate call still cascades through ALL regions.
    mgr = RetryManager(retry_config=RetryConfig(region_order=RegionOrder.ROTATE))
    one_call = mgr.generate_retry_targets(
        models=MODELS, regions=REGIONS, unified_model_manager=_model_catalog_stub()
    )
    failover_ok = sorted({r for _m, r, _i in one_call}) == sorted(REGIONS)

    print("\n  RESULT:")
    print(f"    fixed   -> all {len(fixed)} first attempts on '{REGIONS[0]}' only: {fixed_ok}")
    print(f"    rotate  -> first attempts cover all {len(REGIONS)} regions:        {rotate_ok}")
    print(f"    shuffle -> first attempts cover all {len(REGIONS)} regions:        {shuffle_ok}")
    print(f"    failover depth preserved (one rotate call hits all regions):  {failover_ok}")
    return fixed_ok and rotate_ok and shuffle_ok and failover_ok


def demo_cr2_global_cris() -> bool:
    print("\n" + "=" * 78)
    print("CR-2 — caller-selectable global-CRIS preference + interleave")
    print("=" * 78)

    def selected_method(pref: Optional[str], fraction: Optional[float], calls: int) -> List[str]:
        mgr = RetryManager(
            retry_config=RetryConfig(access_method_preference=pref, global_cris_fraction=fraction)
        )
        info = _model_catalog_stub().get_model_access_info(model_name=MODELS[0], region="us-east-1")
        out = []
        for _ in range(calls):
            model_id, method = mgr._select_model_id_for_request(
                access_info=info, model_name=MODELS[0], region="us-east-1"
            )
            out.append((method, model_id))
        return out

    # Default (no preference) -> direct, today's behavior.
    default = selected_method(None, None, 1)[0]
    # Explicit global_cris -> the global profile id.
    glob = selected_method("global_cris", None, 1)[0]
    # Interleave 0.7 -> ~70% of calls on global, the rest on the default (direct).
    interleaved = selected_method(None, 0.7, 100)
    global_share = sum(1 for m, _ in interleaved if m == "global_cris") / len(interleaved)

    print(f"\n  access_method_preference=None    -> ({default[0]}, {default[1]})")
    print(f"  access_method_preference='global_cris' -> ({glob[0]}, {glob[1]})")
    print(f"  global_cris_fraction=0.7 over 100 calls -> {global_share:.0%} routed to global CRIS")

    default_ok = default[0] == "direct"
    global_ok = glob[0] == "global_cris" and glob[1] == "global.anthropic.claude-opus-4-8"
    interleave_ok = 0.65 <= global_share <= 0.75

    print("\n  RESULT:")
    print(f"    default selects 'direct' (unchanged):                {default_ok}")
    print(f"    'global_cris' resolves to the global profile id:     {global_ok}")
    print(f"    fraction=0.7 yields ~70% global (got {global_share:.0%}):          {interleave_ok}")
    return default_ok and global_ok and interleave_ok


def demo_cr3_round_robin_cursor() -> bool:
    print("\n" + "=" * 78)
    print("CR-3 — parallel RegionDistributionManager round-robin cursor")
    print("=" * 78)

    mgr = RegionDistributionManager(LoadBalancingStrategy.ROUND_ROBIN)
    mgr._initialize_region_tracking(REGIONS)
    n = len(REGIONS)
    # Assign the FULL region set to each request (target_count == len(regions)),
    # the exact case the CR identified as stuck-at-regions[0].
    first_assigned = []
    for _ in range(FANOUT):
        assigned = mgr._assign_regions_round_robin(REGIONS, n)
        first_assigned.append(assigned[0])

    _print_distribution(
        "target_regions_per_request = 14 (full set) — first assigned region per request:",
        first_assigned,
    )
    rotates_ok = set(first_assigned) == set(REGIONS)
    # And the full set is always returned (failover preserved).
    full_set_ok = sorted(mgr._assign_regions_round_robin(REGIONS, n)) == sorted(REGIONS)

    print("\n  RESULT:")
    print(f"    first assigned region rotates across all {n} regions:  {rotates_ok}")
    print(f"    full region set still returned each call (failover):  {full_set_ok}")
    return rotates_ok and full_set_ok


def main() -> int:
    print("\nIssue #16 demonstration — real production classes, catalog lookup stubbed.\n")
    results = {
        "CR-1 region rotation": demo_cr1_region_rotation(),
        "CR-2 global-CRIS preference + interleave": demo_cr2_global_cris(),
        "CR-3 round-robin cursor": demo_cr3_round_robin_cursor(),
    }
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for name, ok in results.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    all_ok = all(results.values())
    print(f"\n{'ALL DEMONSTRATIONS PASSED' if all_ok else 'SOME DEMONSTRATIONS FAILED'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
