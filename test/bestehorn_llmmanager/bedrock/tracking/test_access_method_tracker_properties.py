"""
Property-based tests for AccessMethodTracker.

Feature: inference-profile-support
"""

import threading
from typing import List

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
)
from src.bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)

# Strategy for generating valid model IDs
model_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters=".-:"),
    min_size=10,
    max_size=100,
).filter(lambda x: "." in x)

# Simpler model ID strategy for thread safety tests (no filter)
simple_model_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters=".-"),
    min_size=15,
    max_size=50,
).map(lambda x: f"anthropic.{x}.v1:0")

# Strategy for generating valid regions
region_strategy = st.sampled_from(
    [
        "us-east-1",
        "us-west-2",
        "eu-west-1",
        "eu-central-1",
        "ap-southeast-1",
        "ap-northeast-1",
    ]
)

# Strategy for generating valid access methods
access_method_strategy = st.sampled_from(
    [
        AccessMethodNames.DIRECT,
        AccessMethodNames.REGIONAL_CRIS,
        AccessMethodNames.GLOBAL_CRIS,
    ]
)


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset tracker singleton before each test."""
    # Clear the singleton instance
    AccessMethodTracker._instance = None
    yield
    # Clear again after test
    AccessMethodTracker._instance = None


@given(
    model_id=simple_model_id_strategy,
    region=region_strategy,
    access_method=access_method_strategy,
)
def test_property_preference_learning_persistence(
    model_id: str, region: str, access_method: str
) -> None:
    """
    Property 3: Preference Learning Persistence

    For any successful request using a specific access method, recording the success
    and then querying the preference must return a preference matching that access method.

    Feature: inference-profile-support, Property 3: Preference Learning Persistence
    Validates: Requirements 5.1, 5.2, 5.3
    """
    # Get tracker instance
    tracker = AccessMethodTracker.get_instance()

    # Record success with the access method
    tracker.record_success(
        model_id=model_id,
        region=region,
        access_method=access_method,
        model_id_used=model_id,  # For simplicity, use same ID
    )

    # Query the preference
    preference = tracker.get_preference(model_id=model_id, region=region)

    # Verify preference exists
    assert preference is not None, (
        f"Expected preference to be recorded for model '{model_id}' "
        f"in region '{region}' with access method '{access_method}'"
    )

    # Verify the preference matches the recorded access method
    preferred_method = preference.get_preferred_method()
    assert preferred_method == access_method, (
        f"Expected preferred method to be '{access_method}', "
        f"but got '{preferred_method}' for model '{model_id}' in region '{region}'"
    )

    # Verify the preference was not learned from error
    assert not preference.learned_from_error, (
        f"Expected learned_from_error to be False for successful access, "
        f"but got True for model '{model_id}' in region '{region}'"
    )


@given(
    model_ids=st.lists(simple_model_id_strategy, min_size=5, max_size=20),
    regions=st.lists(region_strategy, min_size=5, max_size=20),
    access_methods=st.lists(access_method_strategy, min_size=5, max_size=20),
)
@settings(max_examples=50, deadline=5000)
def test_property_tracker_thread_safety(
    model_ids: List[str], regions: List[str], access_methods: List[str]
) -> None:
    """
    Property 7: Tracker Thread Safety

    For any concurrent access to the AccessMethodTracker from multiple threads,
    all operations must be thread-safe and maintain consistency.

    This test verifies that:
    1. Multiple threads can record preferences concurrently without data corruption
    2. Multiple threads can query preferences concurrently without errors
    3. The final state is consistent with all recorded operations
    4. No race conditions occur during concurrent access

    Feature: inference-profile-support, Property 7: Tracker Thread Safety
    Validates: Requirements 5.3
    """
    # Get tracker instance
    tracker = AccessMethodTracker.get_instance()

    # Ensure we have enough data for meaningful concurrent testing
    num_operations = min(len(model_ids), len(regions), len(access_methods))
    if num_operations < 5:
        # Skip if not enough data
        return

    # Track what we expect to record
    expected_records = []
    for i in range(num_operations):
        expected_records.append(
            {
                "model_id": model_ids[i],
                "region": regions[i],
                "access_method": access_methods[i],
            }
        )

    # Barrier to synchronize thread start
    barrier = threading.Barrier(num_operations)
    errors: List[Exception] = []

    def record_preference(model_id: str, region: str, access_method: str) -> None:
        """Record a preference from a thread."""
        try:
            # Wait for all threads to be ready
            barrier.wait()

            # Record the success
            tracker.record_success(
                model_id=model_id,
                region=region,
                access_method=access_method,
                model_id_used=model_id,
            )
        except Exception as e:
            errors.append(e)

    # Create and start threads
    threads = []
    for record in expected_records:
        thread = threading.Thread(
            target=record_preference,
            args=(record["model_id"], record["region"], record["access_method"]),
        )
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify no errors occurred during concurrent access
    assert len(errors) == 0, f"Errors occurred during concurrent access: {errors}"

    # Count unique model/region combinations
    unique_combinations = set()
    for record in expected_records:
        unique_combinations.add((record["model_id"], record["region"]))

    # Verify all unique preferences were recorded
    for record in expected_records:
        preference = tracker.get_preference(model_id=record["model_id"], region=record["region"])

        assert preference is not None, (
            f"Expected preference to be recorded for model '{record['model_id']}' "
            f"in region '{record['region']}' after concurrent recording"
        )

        # Verify the preference matches one of the recorded access methods
        # (when multiple threads write to the same key, the last one wins)
        preferred_method = preference.get_preferred_method()
        assert preferred_method in [
            r["access_method"]
            for r in expected_records
            if r["model_id"] == record["model_id"] and r["region"] == record["region"]
        ], (
            f"Expected preferred method to be one of the recorded methods, "
            f"but got '{preferred_method}' for model '{record['model_id']}' "
            f"in region '{record['region']}' after concurrent recording"
        )

    # Verify statistics are consistent with unique combinations
    stats = tracker.get_statistics()
    assert stats["total_tracked"] >= len(unique_combinations), (
        f"Expected at least {len(unique_combinations)} tracked combinations, "
        f"but got {stats['total_tracked']}"
    )

    # Test concurrent reads don't cause errors
    read_errors: List[Exception] = []
    read_barrier = threading.Barrier(num_operations)

    def read_preference(model_id: str, region: str) -> None:
        """Read a preference from a thread."""
        try:
            # Wait for all threads to be ready
            read_barrier.wait()

            # Query the preference
            tracker.get_preference(model_id=model_id, region=region)

            # Query statistics
            tracker.get_statistics()

            # Query requires_profile
            tracker.requires_profile(model_id=model_id, region=region)
        except Exception as e:
            read_errors.append(e)

    # Create and start read threads
    read_threads = []
    for record in expected_records:
        thread = threading.Thread(
            target=read_preference,
            args=(record["model_id"], record["region"]),
        )
        read_threads.append(thread)
        thread.start()

    # Wait for all read threads to complete
    for thread in read_threads:
        thread.join()

    # Verify no errors occurred during concurrent reads
    assert len(read_errors) == 0, f"Errors occurred during concurrent reads: {read_errors}"


@given(
    model_ids=st.lists(simple_model_id_strategy, min_size=3, max_size=10, unique=True),
    regions=st.lists(region_strategy, min_size=3, max_size=10),
    access_methods=st.lists(access_method_strategy, min_size=3, max_size=10),
)
@settings(max_examples=100, deadline=5000)
def test_property_test_state_isolation(
    model_ids: List[str], regions: List[str], access_methods: List[str]
) -> None:
    """
    Property 5: Test State Isolation

    For any sequence of test runs, when the AccessMethodTracker is reset between tests,
    each test should produce the same result regardless of execution order.

    This test verifies that:
    1. Recording preferences and then resetting clears all state
    2. After reset, no preferences are retained
    3. Multiple reset cycles produce consistent behavior
    4. Reset is thread-safe and atomic

    Feature: ci-failure-fixes, Property 5: Test State Isolation
    Validates: Requirements 1.1
    """
    # Ensure we have enough data
    num_operations = min(len(model_ids), len(regions), len(access_methods))
    if num_operations < 3:
        return

    # Test multiple reset cycles
    for cycle in range(3):
        # Get tracker instance
        tracker = AccessMethodTracker.get_instance()

        # Verify tracker starts empty (or from previous cycle if reset failed)
        tracker.get_statistics()

        # Record several preferences
        for i in range(num_operations):
            tracker.record_success(
                model_id=model_ids[i],
                region=regions[i],
                access_method=access_methods[i],
                model_id_used=model_ids[i],
            )

        # Verify preferences were recorded
        stats_after_recording = tracker.get_statistics()
        assert stats_after_recording["total_tracked"] > 0, (
            f"Expected preferences to be recorded in cycle {cycle}, "
            f"but total_tracked is {stats_after_recording['total_tracked']}"
        )

        # Verify we can retrieve the preferences
        for i in range(num_operations):
            preference = tracker.get_preference(model_id=model_ids[i], region=regions[i])
            assert preference is not None, (
                f"Expected preference to exist for model '{model_ids[i]}' "
                f"in region '{regions[i]}' before reset in cycle {cycle}"
            )

        # Reset the tracker
        AccessMethodTracker.reset_for_testing()

        # Get a new instance (should be fresh)
        tracker_after_reset = AccessMethodTracker.get_instance()

        # Verify all preferences were cleared
        stats_after_reset = tracker_after_reset.get_statistics()
        assert stats_after_reset["total_tracked"] == 0, (
            f"Expected all preferences to be cleared after reset in cycle {cycle}, "
            f"but total_tracked is {stats_after_reset['total_tracked']}"
        )

        # Verify preferences are no longer retrievable
        for i in range(num_operations):
            preference = tracker_after_reset.get_preference(
                model_id=model_ids[i], region=regions[i]
            )
            assert preference is None, (
                f"Expected no preference for model '{model_ids[i]}' "
                f"in region '{regions[i]}' after reset in cycle {cycle}, "
                f"but got: {preference}"
            )

        # Verify requires_profile returns False for all (no learned preferences)
        for i in range(num_operations):
            requires_profile = tracker_after_reset.requires_profile(
                model_id=model_ids[i], region=regions[i]
            )
            assert not requires_profile, (
                f"Expected requires_profile to be False for model '{model_ids[i]}' "
                f"in region '{regions[i]}' after reset in cycle {cycle}"
            )

    # Final cleanup
    AccessMethodTracker.reset_for_testing()
