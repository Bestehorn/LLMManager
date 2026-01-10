"""
Tests for ParameterCompatibilityTracker.

Includes property-based tests and unit tests for compatibility tracking,
optimization, and cross-instance persistence.
"""

import concurrent.futures
from typing import Any, Dict

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.tracking.parameter_compatibility_tracker import (
    ParameterCompatibilityTracker,
)

# Hypothesis strategies for test data generation
model_id_strategy = st.sampled_from(
    [
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "amazon.titan-text-express-v1",
        "meta.llama3-1-70b-instruct-v1:0",
    ]
)

region_strategy = st.sampled_from(
    ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"]
)

# Strategy for valid additionalModelRequestFields
parameters_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))),
    values=st.recursive(
        st.one_of(
            st.text(max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
        ),
        lambda children: st.lists(children, max_size=5)
        | st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cs",))),
            children,
            max_size=5,
        ),
        max_leaves=10,
    ),
    min_size=1,
    max_size=5,
)


class TestParameterCompatibilityTrackerPropertyTests:
    """Property-based tests for ParameterCompatibilityTracker."""

    def setup_method(self) -> None:
        """Reset singleton instance before each test."""
        ParameterCompatibilityTracker._instance = None

    @settings(max_examples=100)
    @given(
        model_id=model_id_strategy,
        region=region_strategy,
        parameters=parameters_strategy,
    )
    def test_property_9_compatibility_tracking_success(
        self, model_id: str, region: str, parameters: Dict[str, Any]
    ) -> None:
        """
        Property 9: Compatibility Tracking - Success Recording

        Feature: additional-model-request-fields, Property 9: Compatibility Tracking
        Validates: Requirements 5.1, 5.2

        For any model/region/parameter combination, when record_success() is called,
        the system SHALL correctly track it as compatible.
        """
        tracker = ParameterCompatibilityTracker.get_instance()

        # Record success
        tracker.record_success(model_id=model_id, region=region, parameters=parameters)

        # Verify it's not marked as incompatible
        assert not tracker.is_known_incompatible(
            model_id=model_id, region=region, parameters=parameters
        ), "Successfully recorded combination should not be marked as incompatible"

        # Verify statistics reflect the recording
        stats = tracker.get_statistics()
        assert stats["total_combinations"] >= 1, "Should have at least one tracked combination"
        assert stats["compatible_count"] >= 1, "Should have at least one compatible combination"
        assert model_id in stats["models_tracked"], "Model should be in tracked models"
        assert region in stats["regions_tracked"], "Region should be in tracked regions"

    @settings(max_examples=100)
    @given(
        model_id=model_id_strategy,
        region=region_strategy,
        parameters=parameters_strategy,
    )
    def test_property_9_compatibility_tracking_failure(
        self, model_id: str, region: str, parameters: Dict[str, Any]
    ) -> None:
        """
        Property 9: Compatibility Tracking - Failure Recording

        Feature: additional-model-request-fields, Property 9: Compatibility Tracking
        Validates: Requirements 5.1, 5.2

        For any model/region/parameter combination, when record_failure() is called,
        the system SHALL correctly track it as incompatible.
        """
        tracker = ParameterCompatibilityTracker.get_instance()

        # Create a mock error
        error = ValueError("Unsupported parameter")

        # Record failure
        tracker.record_failure(model_id=model_id, region=region, parameters=parameters, error=error)

        # Verify it's marked as incompatible
        assert tracker.is_known_incompatible(
            model_id=model_id, region=region, parameters=parameters
        ), "Failed combination should be marked as incompatible"

        # Verify statistics reflect the recording
        stats = tracker.get_statistics()
        assert stats["total_combinations"] >= 1, "Should have at least one tracked combination"
        assert stats["incompatible_count"] >= 1, "Should have at least one incompatible combination"
        assert model_id in stats["models_tracked"], "Model should be in tracked models"
        assert region in stats["regions_tracked"], "Region should be in tracked regions"

    @settings(max_examples=100)
    @given(
        model_id=model_id_strategy,
        region=region_strategy,
        parameters=parameters_strategy,
    )
    def test_property_10_compatibility_based_optimization(
        self, model_id: str, region: str, parameters: Dict[str, Any]
    ) -> None:
        """
        Property 10: Compatibility-Based Retry Optimization

        Feature: additional-model-request-fields, Property 10: Compatibility-Based Retry Optimization
        Validates: Requirements 5.4

        For any model/region/parameter combination that has been recorded as incompatible,
        is_known_incompatible() SHALL return True, enabling retry optimization.
        """
        tracker = ParameterCompatibilityTracker.get_instance()

        # Initially, unknown combinations should not be marked as incompatible
        assert not tracker.is_known_incompatible(
            model_id=model_id, region=region, parameters=parameters
        ), "Unknown combination should not be marked as incompatible"

        # Record as incompatible
        error = ValueError("Parameter not supported")
        tracker.record_failure(model_id=model_id, region=region, parameters=parameters, error=error)

        # Now it should be known as incompatible
        assert tracker.is_known_incompatible(
            model_id=model_id, region=region, parameters=parameters
        ), "Recorded incompatible combination should be detected"

        # Record as compatible (overwrite)
        tracker.record_success(model_id=model_id, region=region, parameters=parameters)

        # Should no longer be marked as incompatible
        assert not tracker.is_known_incompatible(
            model_id=model_id, region=region, parameters=parameters
        ), "Combination marked as compatible should not be incompatible"


class TestParameterCompatibilityTrackerUnitTests:
    """Unit tests for ParameterCompatibilityTracker."""

    def setup_method(self) -> None:
        """Reset singleton instance before each test."""
        ParameterCompatibilityTracker._instance = None

    def test_cross_instance_persistence(self) -> None:
        """
        Test cross-instance persistence (Requirement 5.5).

        Create multiple ParameterCompatibilityTracker instances and verify
        they share the same underlying data.
        """
        # Get first instance
        tracker1 = ParameterCompatibilityTracker.get_instance()

        # Record some data
        model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
        region = "us-east-1"
        parameters = {"anthropic_beta": ["context-1m-2025-08-07"]}

        tracker1.record_success(model_id=model_id, region=region, parameters=parameters)

        # Get second instance
        tracker2 = ParameterCompatibilityTracker.get_instance()

        # Verify they are the same instance
        assert tracker1 is tracker2, "get_instance() should return the same singleton instance"

        # Verify data is shared
        assert not tracker2.is_known_incompatible(
            model_id=model_id, region=region, parameters=parameters
        ), "Second instance should see data from first instance"

        stats = tracker2.get_statistics()
        assert stats["total_combinations"] >= 1, "Second instance should see tracked combinations"

    def test_thread_safety_concurrent_access(self) -> None:
        """
        Test thread safety with concurrent access (Requirement 5.5).

        Verify that concurrent recording from multiple threads doesn't cause
        data corruption or race conditions.
        """
        tracker = ParameterCompatibilityTracker.get_instance()

        # Define test data
        test_data = [
            (
                f"model-{i}",
                f"region-{i % 3}",
                {"param": f"value-{i}"},
                i % 2 == 0,  # Alternate between success and failure
            )
            for i in range(50)
        ]

        def record_data(model_id: str, region: str, params: Dict[str, Any], success: bool) -> None:
            """Record data in tracker."""
            if success:
                tracker.record_success(model_id=model_id, region=region, parameters=params)
            else:
                error = ValueError("Test error")
                tracker.record_failure(
                    model_id=model_id, region=region, parameters=params, error=error
                )

        # Execute recordings concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(record_data, model_id, region, params, success)
                for model_id, region, params, success in test_data
            ]
            concurrent.futures.wait(futures)

        # Verify all data was recorded
        stats = tracker.get_statistics()
        assert stats["total_combinations"] == len(test_data), "All combinations should be tracked"

        # Verify correct success/failure counts
        expected_successes = sum(1 for _, _, _, success in test_data if success)
        expected_failures = len(test_data) - expected_successes

        assert (
            stats["compatible_count"] == expected_successes
        ), "Should have correct number of successes"
        assert (
            stats["incompatible_count"] == expected_failures
        ), "Should have correct number of failures"

    def test_parameter_hashing_consistency(self) -> None:
        """
        Test that parameter hashing is consistent for equivalent dictionaries.

        Dictionaries with the same content but different insertion order
        should produce the same hash.
        """
        tracker = ParameterCompatibilityTracker.get_instance()

        # Create two dictionaries with same content, different order
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}

        model_id = "test-model"
        region = "us-east-1"

        # Record with first parameter order
        tracker.record_success(model_id=model_id, region=region, parameters=params1)

        # Check with second parameter order - should be recognized as same
        assert not tracker.is_known_incompatible(
            model_id=model_id, region=region, parameters=params2
        ), "Equivalent parameters with different order should be recognized as same"

    def test_empty_statistics_initially(self) -> None:
        """Test that statistics are empty for a new tracker instance."""
        tracker = ParameterCompatibilityTracker.get_instance()

        stats = tracker.get_statistics()

        assert stats["total_combinations"] == 0, "New tracker should have no combinations"
        assert stats["compatible_count"] == 0, "New tracker should have no compatible combinations"
        assert (
            stats["incompatible_count"] == 0
        ), "New tracker should have no incompatible combinations"
        assert len(stats["models_tracked"]) == 0, "New tracker should have no tracked models"
        assert len(stats["regions_tracked"]) == 0, "New tracker should have no tracked regions"

    def test_unknown_combination_not_incompatible(self) -> None:
        """
        Test that unknown combinations are not marked as incompatible.

        Only explicitly recorded failures should be marked as incompatible.
        """
        tracker = ParameterCompatibilityTracker.get_instance()

        # Check an unknown combination
        assert not tracker.is_known_incompatible(
            model_id="unknown-model",
            region="unknown-region",
            parameters={"unknown": "parameter"},
        ), "Unknown combinations should not be marked as incompatible"

    def test_nested_parameters_hashing(self) -> None:
        """Test that nested parameter structures are hashed correctly."""
        tracker = ParameterCompatibilityTracker.get_instance()

        # Create nested parameters
        params = {
            "anthropic_beta": ["context-1m-2025-08-07", "tool-use-2025-01-24"],
            "nested": {"key1": "value1", "key2": [1, 2, 3]},
        }

        model_id = "test-model"
        region = "us-east-1"

        # Record failure
        error = ValueError("Test error")
        tracker.record_failure(model_id=model_id, region=region, parameters=params, error=error)

        # Verify it's tracked
        assert tracker.is_known_incompatible(
            model_id=model_id, region=region, parameters=params
        ), "Nested parameters should be tracked correctly"
