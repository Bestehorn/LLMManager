"""
Unit tests for RegionDistributionManager.
"""

from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.distributors.region_distribution_manager import (
    RegionDistributionManager,
)
from bestehorn_llmmanager.bedrock.exceptions.parallel_exceptions import (
    ParallelConfigurationError,
    RegionDistributionError,
)
from bestehorn_llmmanager.bedrock.models.parallel_structures import (
    BedrockConverseRequest,
    LoadBalancingStrategy,
    RegionAssignment,
)


class TestRegionDistributionManager:
    """Test cases for RegionDistributionManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RegionDistributionManager()
        self.sample_regions = ["us-east-1", "us-west-2", "eu-west-1"]
        self.sample_requests = [
            BedrockConverseRequest(
                request_id="req-1", messages=[{"role": "user", "content": [{"text": "test1"}]}]
            ),
            BedrockConverseRequest(
                request_id="req-2", messages=[{"role": "user", "content": [{"text": "test2"}]}]
            ),
            BedrockConverseRequest(
                request_id="req-3", messages=[{"role": "user", "content": [{"text": "test3"}]}]
            ),
        ]

    def test_init_default_strategy(self):
        """Test initialization with default strategy."""
        manager = RegionDistributionManager()
        assert manager.get_load_balancing_strategy() == LoadBalancingStrategy.ROUND_ROBIN
        assert manager.get_region_load_distribution() == {}

    def test_init_custom_strategy(self):
        """Test initialization with custom strategy."""
        manager = RegionDistributionManager(load_balancing_strategy=LoadBalancingStrategy.RANDOM)
        assert manager.get_load_balancing_strategy() == LoadBalancingStrategy.RANDOM

    def test_distribute_requests_valid_parameters(self):
        """Test distribute_requests with valid parameters."""
        assignments = self.manager.distribute_requests(
            requests=self.sample_requests,
            available_regions=self.sample_regions,
            target_regions_per_request=2,
        )

        assert len(assignments) == len(self.sample_requests)
        for assignment in assignments:
            assert isinstance(assignment, RegionAssignment)
            assert len(assignment.assigned_regions) == 2
            assert all(region in self.sample_regions for region in assignment.assigned_regions)

    def test_validate_distribution_parameters_empty_requests(self):
        """Test validation with empty requests list."""
        with pytest.raises(ParallelConfigurationError) as exc_info:
            self.manager._validate_distribution_parameters(
                requests=[], available_regions=self.sample_regions, target_regions_per_request=2
            )
        assert "Request list cannot be empty" in str(exc_info.value)

    def test_validate_distribution_parameters_empty_regions(self):
        """Test validation with empty regions list."""
        with pytest.raises(ParallelConfigurationError) as exc_info:
            self.manager._validate_distribution_parameters(
                requests=self.sample_requests, available_regions=[], target_regions_per_request=2
            )
        assert "Available regions list cannot be empty" in str(exc_info.value)

    def test_validate_distribution_parameters_invalid_target_regions(self):
        """Test validation with invalid target regions count."""
        with pytest.raises(ParallelConfigurationError) as exc_info:
            self.manager._validate_distribution_parameters(
                requests=self.sample_requests,
                available_regions=self.sample_regions,
                target_regions_per_request=0,
            )
        assert exc_info.value.invalid_parameter == "target_regions_per_request"

    def test_validate_distribution_parameters_insufficient_regions(self):
        """Test validation when target regions exceed available regions."""
        with pytest.raises(RegionDistributionError) as exc_info:
            self.manager._validate_distribution_parameters(
                requests=self.sample_requests,
                available_regions=["us-east-1"],
                target_regions_per_request=2,
            )
        assert exc_info.value.requested_regions == 2
        assert exc_info.value.available_regions == 1

    def test_initialize_region_tracking(self):
        """Test region tracking initialization."""
        self.manager._initialize_region_tracking(self.sample_regions)

        load_distribution = self.manager.get_region_load_distribution()
        assert len(load_distribution) == len(self.sample_regions)
        for region in self.sample_regions:
            assert load_distribution[region] == 0

    def test_assign_regions_round_robin(self):
        """Test round-robin region assignment."""
        self.manager._initialize_region_tracking(self.sample_regions)

        # First assignment
        regions1 = self.manager._assign_regions_round_robin(self.sample_regions, 2)
        assert len(regions1) == 2
        assert regions1 == ["us-east-1", "us-west-2"]

        # Second assignment should continue round-robin
        regions2 = self.manager._assign_regions_round_robin(self.sample_regions, 2)
        assert len(regions2) == 2
        assert regions2 == ["eu-west-1", "us-east-1"]

    def test_assign_regions_round_robin_more_target_than_available(self):
        """Test round-robin when target count exceeds available regions."""
        self.manager._initialize_region_tracking(["us-east-1", "us-west-2"])
        regions = self.manager._assign_regions_round_robin(["us-east-1", "us-west-2"], 5)
        assert len(regions) == 2  # Should be limited by available regions

    @patch("random.sample")
    def test_assign_regions_random(self, mock_sample):
        """Test random region assignment."""
        mock_sample.return_value = ["us-east-1", "eu-west-1"]
        self.manager._initialize_region_tracking(self.sample_regions)

        regions = self.manager._assign_regions_random(self.sample_regions, 2)
        assert len(regions) == 2
        assert regions == ["us-east-1", "eu-west-1"]
        mock_sample.assert_called_once_with(self.sample_regions, 2)

    def test_assign_regions_least_loaded(self):
        """Test least-loaded region assignment."""
        self.manager._initialize_region_tracking(self.sample_regions)

        # Manually set some load
        self.manager._region_assignment_counter["us-east-1"] = 5
        self.manager._region_assignment_counter["us-west-2"] = 1
        self.manager._region_assignment_counter["eu-west-1"] = 3

        regions = self.manager._assign_regions_least_loaded(self.sample_regions, 2)
        assert len(regions) == 2
        assert "us-west-2" in regions  # Should include least loaded
        assert "us-east-1" not in regions  # Should not include most loaded

    def test_assign_regions_for_request_round_robin(self):
        """Test region assignment for single request with round-robin."""
        self.manager._initialize_region_tracking(self.sample_regions)

        regions = self.manager._assign_regions_for_request(
            request=self.sample_requests[0],
            available_regions=self.sample_regions,
            target_regions_per_request=2,
        )
        assert len(regions) == 2

    def test_assign_regions_for_request_random(self):
        """Test region assignment for single request with random strategy."""
        manager = RegionDistributionManager(LoadBalancingStrategy.RANDOM)
        manager._initialize_region_tracking(self.sample_regions)

        with patch("random.sample", return_value=["us-east-1", "us-west-2"]):
            regions = manager._assign_regions_for_request(
                request=self.sample_requests[0],
                available_regions=self.sample_regions,
                target_regions_per_request=2,
            )
            assert len(regions) == 2

    def test_assign_regions_for_request_least_loaded(self):
        """Test region assignment for single request with least-loaded strategy."""
        manager = RegionDistributionManager(LoadBalancingStrategy.LEAST_LOADED)
        manager._initialize_region_tracking(self.sample_regions)

        regions = manager._assign_regions_for_request(
            request=self.sample_requests[0],
            available_regions=self.sample_regions,
            target_regions_per_request=2,
        )
        assert len(regions) == 2

    def test_create_region_assignments(self):
        """Test creation of region assignments for multiple requests."""
        self.manager._initialize_region_tracking(self.sample_regions)

        assignments = self.manager._create_region_assignments(
            requests=self.sample_requests,
            available_regions=self.sample_regions,
            target_regions_per_request=2,
        )

        assert len(assignments) == len(self.sample_requests)
        for i, assignment in enumerate(assignments):
            assert assignment.request_id == self.sample_requests[i].request_id
            assert len(assignment.assigned_regions) == 2
            assert assignment.priority == 0

    def test_create_region_assignments_with_none_request_id(self):
        """Test creation of region assignments when request has no ID."""
        # Create request and manually set request_id to None after initialization
        request_without_id = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "test"}]}]
        )
        # Manually override the auto-generated request_id to simulate None case
        request_without_id.request_id = None
        
        self.manager._initialize_region_tracking(self.sample_regions)

        assignments = self.manager._create_region_assignments(
            requests=[request_without_id],
            available_regions=self.sample_regions,
            target_regions_per_request=1,
        )

        assert len(assignments) == 1
        assert assignments[0].request_id == "unknown"

    def test_log_distribution_stats(self):
        """Test logging of distribution statistics."""
        with patch.object(self.manager, '_logger') as mock_logger:
            self.manager._initialize_region_tracking(self.sample_regions)
            assignments = [
                RegionAssignment(
                    request_id="req-1", assigned_regions=["us-east-1", "us-west-2"], priority=0
                ),
                RegionAssignment(request_id="req-2", assigned_regions=["eu-west-1"], priority=0),
            ]

            self.manager._log_distribution_stats(assignments, self.sample_regions)

            # Check that info logs were called
            assert mock_logger.info.call_count >= 2
            assert mock_logger.debug.call_count >= 1

    def test_get_region_load_distribution(self):
        """Test getting region load distribution."""
        self.manager._initialize_region_tracking(self.sample_regions)
        self.manager._region_assignment_counter["us-east-1"] = 5

        distribution = self.manager.get_region_load_distribution()
        assert distribution["us-east-1"] == 5
        assert "us-west-2" in distribution

        # Should return a copy, not the original
        distribution["us-east-1"] = 10
        assert self.manager._region_assignment_counter["us-east-1"] == 5

    def test_reset_load_tracking(self):
        """Test resetting load tracking."""
        self.manager._initialize_region_tracking(self.sample_regions)
        self.manager._region_assignment_counter["us-east-1"] = 5
        self.manager._last_assigned_region_index = 2

        self.manager.reset_load_tracking()

        assert len(self.manager._region_assignment_counter) == 0
        assert self.manager._last_assigned_region_index == 0

    def test_set_load_balancing_strategy(self):
        """Test setting load balancing strategy."""
        with patch.object(self.manager, '_logger') as mock_logger:
            self.manager.set_load_balancing_strategy(LoadBalancingStrategy.RANDOM)

            assert self.manager.get_load_balancing_strategy() == LoadBalancingStrategy.RANDOM
            mock_logger.info.assert_called_once()

    def test_optimize_region_assignments(self):
        """Test optimization of region assignments."""
        assignments = [
            RegionAssignment(
                request_id="req-1", assigned_regions=["us-east-1", "us-west-2"], priority=0
            ),
            RegionAssignment(request_id="req-2", assigned_regions=["eu-west-1"], priority=1),
        ]

        with patch.object(self.manager, '_logger') as mock_logger:
            optimized = self.manager.optimize_region_assignments(assignments, self.sample_regions)

            assert len(optimized) == len(assignments)
            for i, opt_assignment in enumerate(optimized):
                assert opt_assignment.request_id == assignments[i].request_id
                assert opt_assignment.priority == assignments[i].priority

            mock_logger.info.assert_called_once()

    def test_optimize_single_assignment_low_variance(self):
        """Test optimization of single assignment with low variance."""
        current_regions = ["us-east-1", "us-west-2"]
        current_load = {"us-east-1": 1, "us-west-2": 1, "eu-west-1": 1}

        optimized = self.manager._optimize_single_assignment(
            current_regions=current_regions,
            available_regions=self.sample_regions,
            current_load=current_load,
        )

        # Should keep current assignment due to low variance
        assert optimized == current_regions

    def test_optimize_single_assignment_high_variance(self):
        """Test optimization of single assignment with high variance."""
        current_regions = ["us-east-1", "us-west-2"]
        current_load = {"us-east-1": 10, "us-west-2": 1, "eu-west-1": 1}

        optimized = self.manager._optimize_single_assignment(
            current_regions=current_regions,
            available_regions=self.sample_regions,
            current_load=current_load,
        )

        # Should try to replace high-load region
        assert len(optimized) == len(current_regions)
        # us-east-1 should be replaced with eu-west-1 (lower load)
        assert "eu-west-1" in optimized

    def test_optimize_single_assignment_empty_load(self):
        """Test optimization with empty current load."""
        current_regions = ["us-east-1"]
        current_load = {}

        optimized = self.manager._optimize_single_assignment(
            current_regions=current_regions,
            available_regions=self.sample_regions,
            current_load=current_load,
        )

        # Should return current regions when load is empty
        assert optimized == current_regions

    def test_optimize_single_assignment_no_better_alternative(self):
        """Test optimization when no better alternative exists."""
        current_regions = ["us-east-1", "us-west-2", "eu-west-1"]
        current_load = {"us-east-1": 10, "us-west-2": 8, "eu-west-1": 9}

        optimized = self.manager._optimize_single_assignment(
            current_regions=current_regions,
            available_regions=self.sample_regions,
            current_load=current_load,
        )

        # Should keep all regions since no better alternatives
        assert set(optimized) == set(current_regions)

    def test_distribute_requests_integration(self):
        """Test full integration of distribute_requests method."""
        assignments = self.manager.distribute_requests(
            requests=self.sample_requests,
            available_regions=self.sample_regions,
            target_regions_per_request=1,
        )

        assert len(assignments) == len(self.sample_requests)

        # Check load distribution was updated
        load_distribution = self.manager.get_region_load_distribution()
        total_assignments = sum(load_distribution.values())
        assert total_assignments == len(self.sample_requests)

    def test_error_handling_in_distribute_requests(self):
        """Test error handling in distribute_requests method."""
        # Test with empty requests
        with pytest.raises(ParallelConfigurationError):
            self.manager.distribute_requests(
                requests=[], available_regions=self.sample_regions, target_regions_per_request=2
            )

        # Test with insufficient regions
        with pytest.raises(RegionDistributionError):
            self.manager.distribute_requests(
                requests=self.sample_requests,
                available_regions=["us-east-1"],
                target_regions_per_request=2,
            )
