"""Tests for CR-3: round-robin cursor advances when all regions are assigned.

Regression context (issue #16): when target_count == len(available_regions), the cursor
advance `(_last_assigned_region_index + regions_needed) % n` evaluated to +0, so every
request received the identical ordered list starting at regions[0]. The fix advances the
cursor by 1 in that case so the starting region rotates across calls, while the partial
(target_count < n) behavior — and its existing pinned test — stay byte-identical.
"""

from bestehorn_llmmanager.bedrock.distributors.region_distribution_manager import (
    RegionDistributionManager,
)
from bestehorn_llmmanager.bedrock.models.parallel_structures import LoadBalancingStrategy


class TestRoundRobinFullSetRotation:
    """CR-3 — assigned_regions[0] must rotate when the full region set is assigned."""

    def setup_method(self) -> None:
        self.regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
        self.manager = RegionDistributionManager(LoadBalancingStrategy.ROUND_ROBIN)
        self.manager._initialize_region_tracking(self.regions)

    def test_full_set_assignment_rotates_first_region(self) -> None:
        """P8: with target_count == len(regions), the first region cycles across calls."""
        n = len(self.regions)
        first_regions = []
        for _ in range(2 * n):
            assigned = self.manager._assign_regions_round_robin(self.regions, n)
            # The full set is always returned (failover depth preserved)...
            assert sorted(assigned) == sorted(self.regions)
            first_regions.append(assigned[0])

        # ...but the STARTING region must not be constant; over 2n calls every region
        # must appear as the first-attempted region at least once (uniform spread).
        assert (
            len(set(first_regions)) == n
        ), f"expected all {n} regions to appear as first attempt, got {set(first_regions)}"
        assert first_regions[0] != first_regions[1], "first region did not rotate between calls"

    def test_full_set_first_region_sequence_is_rotation(self) -> None:
        """The first region advances by exactly one position per call (deterministic)."""
        n = len(self.regions)
        seq = [self.manager._assign_regions_round_robin(self.regions, n)[0] for _ in range(n)]
        # Starting from regions[0], a +1 rotation yields regions[0], regions[1], ...
        assert seq == self.regions
