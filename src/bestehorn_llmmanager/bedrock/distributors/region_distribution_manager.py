"""
Region distribution functionality for parallel processing in LLM Manager system.
Handles intelligent assignment of requests to regions for optimal parallel execution.
"""

import logging
import random
from typing import Dict, List

from typing_extensions import assert_never

from ..exceptions.parallel_exceptions import ParallelConfigurationError, RegionDistributionError
from ..models.parallel_constants import ParallelErrorMessages, ParallelLogMessages
from ..models.parallel_structures import (
    BedrockConverseRequest,
    LoadBalancingStrategy,
    RegionAssignment,
)


class RegionDistributionManager:
    """
    Manages distribution of requests across AWS regions for parallel processing.

    Provides functionality for:
    - Intelligent region assignment based on load balancing strategies
    - Request prioritization and region optimization
    - Load balancing across regions to avoid hotspots
    """

    def __init__(
        self, load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    ) -> None:
        """
        Initialize the region distribution manager.

        Args:
            load_balancing_strategy: Strategy to use for distributing requests
        """
        self._logger = logging.getLogger(__name__)
        self._load_balancing_strategy = load_balancing_strategy

        # Track region assignments for load balancing
        self._region_assignment_counter: Dict[str, int] = {}
        self._last_assigned_region_index = 0

    def distribute_requests(
        self,
        requests: List[BedrockConverseRequest],
        available_regions: List[str],
        target_regions_per_request: int,
    ) -> List[RegionAssignment]:
        """
        Distribute requests across available regions.

        Args:
            requests: List of requests to distribute
            available_regions: List of available AWS regions
            target_regions_per_request: Target number of regions per request

        Returns:
            List of RegionAssignment objects

        Raises:
            ParallelConfigurationError: If configuration parameters are invalid
            RegionDistributionError: If region distribution fails
        """
        self._validate_distribution_parameters(
            requests=requests,
            available_regions=available_regions,
            target_regions_per_request=target_regions_per_request,
        )

        # Initialize region tracking
        self._initialize_region_tracking(available_regions=available_regions)

        # Create assignments based on strategy
        assignments = self._create_region_assignments(
            requests=requests,
            available_regions=available_regions,
            target_regions_per_request=target_regions_per_request,
        )

        # Log distribution statistics
        self._log_distribution_stats(assignments=assignments, available_regions=available_regions)

        return assignments

    def _validate_distribution_parameters(
        self,
        requests: List[BedrockConverseRequest],
        available_regions: List[str],
        target_regions_per_request: int,
    ) -> None:
        """
        Validate parameters for region distribution.

        Args:
            requests: List of requests to validate
            available_regions: List of available regions to validate
            target_regions_per_request: Target regions per request to validate

        Raises:
            ParallelConfigurationError: If parameters are invalid
            RegionDistributionError: If insufficient regions available
        """
        if not requests:
            raise ParallelConfigurationError(
                message="Request list cannot be empty",
                invalid_parameter="requests",
                provided_value=len(requests),
            )

        if not available_regions:
            raise ParallelConfigurationError(
                message="Available regions list cannot be empty",
                invalid_parameter="available_regions",
                provided_value=len(available_regions),
            )

        if target_regions_per_request <= 0:
            raise ParallelConfigurationError(
                message=ParallelErrorMessages.INVALID_TARGET_REGIONS.format(
                    value=target_regions_per_request
                ),
                invalid_parameter="target_regions_per_request",
                provided_value=target_regions_per_request,
            )

        if target_regions_per_request > len(available_regions):
            raise RegionDistributionError(
                message=ParallelErrorMessages.INSUFFICIENT_REGIONS.format(
                    requested=target_regions_per_request, available=len(available_regions)
                ),
                requested_regions=target_regions_per_request,
                available_regions=len(available_regions),
            )

    def _initialize_region_tracking(self, available_regions: List[str]) -> None:
        """
        Initialize region tracking for load balancing.

        Args:
            available_regions: List of available regions
        """
        self._region_assignment_counter.clear()
        for region in available_regions:
            self._region_assignment_counter[region] = 0
        self._last_assigned_region_index = 0

    def _create_region_assignments(
        self,
        requests: List[BedrockConverseRequest],
        available_regions: List[str],
        target_regions_per_request: int,
    ) -> List[RegionAssignment]:
        """
        Create region assignments for all requests.

        Args:
            requests: List of requests to assign
            available_regions: List of available regions
            target_regions_per_request: Target number of regions per request

        Returns:
            List of RegionAssignment objects
        """
        assignments = []

        for request in requests:
            assigned_regions = self._assign_regions_for_request(
                request=request,
                available_regions=available_regions,
                target_regions_per_request=target_regions_per_request,
            )

            assignment = RegionAssignment(
                request_id=request.request_id or "unknown",
                assigned_regions=assigned_regions,
                priority=0,  # Default priority, can be enhanced later
            )
            assignments.append(assignment)

        return assignments

    def _assign_regions_for_request(
        self,
        request: BedrockConverseRequest,
        available_regions: List[str],
        target_regions_per_request: int,
    ) -> List[str]:
        """
        Assign regions to a single request based on load balancing strategy.

        Args:
            request: Request to assign regions to
            available_regions: List of available regions
            target_regions_per_request: Number of regions to assign

        Returns:
            List of assigned region names
        """
        if self._load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._assign_regions_round_robin(
                available_regions=available_regions, target_count=target_regions_per_request
            )
        elif self._load_balancing_strategy == LoadBalancingStrategy.RANDOM:
            return self._assign_regions_random(
                available_regions=available_regions, target_count=target_regions_per_request
            )
        elif self._load_balancing_strategy == LoadBalancingStrategy.LEAST_LOADED:
            return self._assign_regions_least_loaded(
                available_regions=available_regions, target_count=target_regions_per_request
            )
        assert_never(self._load_balancing_strategy)

    def _assign_regions_round_robin(
        self, available_regions: List[str], target_count: int
    ) -> List[str]:
        """
        Assign regions using round-robin strategy.

        Args:
            available_regions: List of available regions
            target_count: Number of regions to assign

        Returns:
            List of assigned region names
        """
        assigned_regions = []
        regions_needed = min(target_count, len(available_regions))

        for i in range(regions_needed):
            region_index = (self._last_assigned_region_index + i) % len(available_regions)
            region = available_regions[region_index]
            assigned_regions.append(region)
            self._region_assignment_counter[region] += 1

        # Update the starting index for next assignment
        self._last_assigned_region_index = (
            self._last_assigned_region_index + regions_needed
        ) % len(available_regions)

        return assigned_regions

    def _assign_regions_random(self, available_regions: List[str], target_count: int) -> List[str]:
        """
        Assign regions using random selection strategy.

        Args:
            available_regions: List of available regions
            target_count: Number of regions to assign

        Returns:
            List of assigned region names
        """
        regions_needed = min(target_count, len(available_regions))
        assigned_regions = random.sample(available_regions, regions_needed)

        # Update assignment counters
        for region in assigned_regions:
            self._region_assignment_counter[region] += 1

        return assigned_regions

    def _assign_regions_least_loaded(
        self, available_regions: List[str], target_count: int
    ) -> List[str]:
        """
        Assign regions using least-loaded strategy.

        Args:
            available_regions: List of available regions
            target_count: Number of regions to assign

        Returns:
            List of assigned region names
        """
        # Sort regions by current load (ascending)
        sorted_regions = sorted(
            available_regions, key=lambda region: self._region_assignment_counter[region]
        )

        regions_needed = min(target_count, len(available_regions))
        assigned_regions = sorted_regions[:regions_needed]

        # Update assignment counters
        for region in assigned_regions:
            self._region_assignment_counter[region] += 1

        return assigned_regions

    def _log_distribution_stats(
        self, assignments: List[RegionAssignment], available_regions: List[str]
    ) -> None:
        """
        Log statistics about the region distribution.

        Args:
            assignments: List of region assignments
            available_regions: List of available regions
        """
        total_assignments = sum(len(assignment.assigned_regions) for assignment in assignments)
        unique_regions_used = len(
            set(region for assignment in assignments for region in assignment.assigned_regions)
        )
        max_assignments_per_region = (
            max(self._region_assignment_counter.values()) if self._region_assignment_counter else 0
        )

        self._logger.info(
            ParallelLogMessages.REGION_DISTRIBUTION_CALCULATED.format(
                request_count=len(assignments), region_count=len(available_regions)
            )
        )

        self._logger.info(
            ParallelLogMessages.REGION_DISTRIBUTION_STATS.format(
                total_assignments=total_assignments,
                unique_regions=unique_regions_used,
                max_per_region=max_assignments_per_region,
            )
        )

        # Log detailed region load distribution
        self._logger.debug("Region load distribution:")
        for region, count in sorted(self._region_assignment_counter.items()):
            self._logger.debug(f"  {region}: {count} assignments")

    def get_region_load_distribution(self) -> Dict[str, int]:
        """
        Get current region load distribution.

        Returns:
            Dictionary mapping region names to assignment counts
        """
        return self._region_assignment_counter.copy()

    def reset_load_tracking(self) -> None:
        """Reset the region load tracking counters."""
        self._region_assignment_counter.clear()
        self._last_assigned_region_index = 0
        self._logger.debug("Region load tracking reset")

    def get_load_balancing_strategy(self) -> LoadBalancingStrategy:
        """
        Get the current load balancing strategy.

        Returns:
            Current load balancing strategy
        """
        return self._load_balancing_strategy

    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy) -> None:
        """
        Set the load balancing strategy.

        Args:
            strategy: New load balancing strategy to use
        """
        self._load_balancing_strategy = strategy
        self._logger.info(f"Load balancing strategy changed to: {strategy.value}")

    def optimize_region_assignments(
        self, assignments: List[RegionAssignment], available_regions: List[str]
    ) -> List[RegionAssignment]:
        """
        Optimize existing region assignments for better load distribution.

        Args:
            assignments: Current region assignments to optimize
            available_regions: List of available regions

        Returns:
            Optimized list of region assignments
        """
        # Calculate current load distribution
        current_load = {}
        for region in available_regions:
            current_load[region] = 0

        for assignment in assignments:
            for region in assignment.assigned_regions:
                if region in current_load:
                    current_load[region] += 1

        # Find assignments that could be rebalanced
        optimized_assignments = []

        for assignment in assignments:
            optimized_regions = self._optimize_single_assignment(
                current_regions=assignment.assigned_regions,
                available_regions=available_regions,
                current_load=current_load,
            )

            optimized_assignment = RegionAssignment(
                request_id=assignment.request_id,
                assigned_regions=optimized_regions,
                priority=assignment.priority,
            )
            optimized_assignments.append(optimized_assignment)

        self._logger.info(f"Optimized region assignments for {len(assignments)} requests")
        return optimized_assignments

    def _optimize_single_assignment(
        self, current_regions: List[str], available_regions: List[str], current_load: Dict[str, int]
    ) -> List[str]:
        """
        Optimize region assignment for a single request.

        Args:
            current_regions: Current regions assigned to the request
            available_regions: All available regions
            current_load: Current load distribution across regions

        Returns:
            Optimized list of regions for the request
        """
        # For now, keep current assignment unless there's a significant imbalance
        # This can be enhanced with more sophisticated optimization algorithms

        # Calculate load variance
        loads = list(current_load.values())
        if not loads:
            return current_regions

        avg_load = sum(loads) / len(loads)
        variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)

        # If variance is low, keep current assignment
        if variance < 2.0:  # Threshold for rebalancing
            return current_regions

        # Otherwise, try to rebalance by replacing high-load regions with low-load ones
        optimized_regions = []
        sorted_by_load = sorted(available_regions, key=lambda r: current_load[r])

        for region in current_regions:
            if current_load[region] > avg_load * 1.5:  # High load region
                # Try to replace with a lower load region that's not already in current assignment
                for low_load_region in sorted_by_load:
                    if (
                        low_load_region not in optimized_regions
                        and low_load_region
                        not in current_regions  # Avoid using regions already in current assignment
                        and current_load[low_load_region] < avg_load
                    ):
                        optimized_regions.append(low_load_region)
                        break
                else:
                    # Keep original if no better alternative
                    optimized_regions.append(region)
            else:
                optimized_regions.append(region)

        return optimized_regions
