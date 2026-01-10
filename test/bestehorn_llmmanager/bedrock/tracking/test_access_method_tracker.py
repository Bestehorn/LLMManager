"""
Unit tests for AccessMethodTracker.

This module contains unit tests for the AccessMethodTracker class,
verifying singleton pattern, preference recording, preference retrieval,
statistics generation, and thread safety.

**Feature: inference-profile-support**
"""

import threading
from datetime import datetime
from typing import List

import pytest

from bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
    AccessMethodPreference,
)
from bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset tracker singleton before and after each test."""
    # Clear the singleton instance before test
    AccessMethodTracker._instance = None
    yield
    # Clear again after test
    AccessMethodTracker._instance = None


class TestSingletonPattern:
    """Test singleton pattern implementation."""

    def test_get_instance_returns_same_instance(self) -> None:
        """Test that get_instance returns the same instance."""
        instance1 = AccessMethodTracker.get_instance()
        instance2 = AccessMethodTracker.get_instance()

        assert instance1 is instance2

    def test_direct_instantiation_returns_same_instance(self) -> None:
        """Test that direct instantiation returns the same instance."""
        instance1 = AccessMethodTracker()
        instance2 = AccessMethodTracker()

        assert instance1 is instance2

    def test_mixed_instantiation_returns_same_instance(self) -> None:
        """Test that mixed instantiation methods return the same instance."""
        instance1 = AccessMethodTracker.get_instance()
        instance2 = AccessMethodTracker()
        instance3 = AccessMethodTracker.get_instance()

        assert instance1 is instance2
        assert instance2 is instance3

    def test_singleton_persists_across_calls(self) -> None:
        """Test that singleton persists across multiple calls."""
        instances = [AccessMethodTracker.get_instance() for _ in range(10)]

        # All instances should be the same
        for instance in instances:
            assert instance is instances[0]

    def test_singleton_initialization_only_once(self) -> None:
        """Test that initialization only happens once."""
        tracker1 = AccessMethodTracker.get_instance()

        # Record a preference
        tracker1.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        # Get instance again
        tracker2 = AccessMethodTracker.get_instance()

        # Should have the same data
        preference = tracker2.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        assert preference is not None
        assert preference.get_preferred_method() == AccessMethodNames.DIRECT


class TestPreferenceRecording:
    """Test preference recording functionality."""

    def test_record_success_with_direct_access(self) -> None:
        """Test recording successful direct access."""
        tracker = AccessMethodTracker.get_instance()

        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        preference = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        assert preference is not None
        assert preference.prefer_direct is True
        assert preference.prefer_regional_cris is False
        assert preference.prefer_global_cris is False
        assert preference.learned_from_error is False

    def test_record_success_with_regional_cris(self) -> None:
        """Test recording successful regional CRIS access."""
        tracker = AccessMethodTracker.get_instance()

        tracker.record_success(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-west-2",
            access_method=AccessMethodNames.REGIONAL_CRIS,
            model_id_used="arn:aws:bedrock:us-west-2::inference-profile/test",
        )

        preference = tracker.get_preference(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-west-2",
        )

        assert preference is not None
        assert preference.prefer_direct is False
        assert preference.prefer_regional_cris is True
        assert preference.prefer_global_cris is False
        assert preference.learned_from_error is False

    def test_record_success_with_global_cris(self) -> None:
        """Test recording successful global CRIS access."""
        tracker = AccessMethodTracker.get_instance()

        tracker.record_success(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="eu-west-1",
            access_method=AccessMethodNames.GLOBAL_CRIS,
            model_id_used="arn:aws:bedrock::123456789012:inference-profile/test",
        )

        preference = tracker.get_preference(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="eu-west-1",
        )

        assert preference is not None
        assert preference.prefer_direct is False
        assert preference.prefer_regional_cris is False
        assert preference.prefer_global_cris is True
        assert preference.learned_from_error is False

    def test_record_profile_requirement(self) -> None:
        """Test recording profile requirement."""
        tracker = AccessMethodTracker.get_instance()

        tracker.record_profile_requirement(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
        )

        preference = tracker.get_preference(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
        )

        assert preference is not None
        assert preference.prefer_direct is False
        assert preference.prefer_regional_cris is True
        assert preference.prefer_global_cris is False
        assert preference.learned_from_error is True

    def test_record_success_updates_existing_preference(self) -> None:
        """Test that recording success updates existing preference."""
        tracker = AccessMethodTracker.get_instance()

        # First record direct access
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        # Then record regional CRIS access
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.REGIONAL_CRIS,
            model_id_used="arn:aws:bedrock:us-east-1::inference-profile/test",
        )

        preference = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        # Should have the latest preference (regional CRIS)
        assert preference is not None
        assert preference.prefer_direct is False
        assert preference.prefer_regional_cris is True
        assert preference.prefer_global_cris is False

    def test_record_multiple_models_and_regions(self) -> None:
        """Test recording preferences for multiple models and regions."""
        tracker = AccessMethodTracker.get_instance()

        # Record different preferences for different combinations
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-west-2",
            access_method=AccessMethodNames.REGIONAL_CRIS,
            model_id_used="arn:aws:bedrock:us-west-2::inference-profile/test",
        )

        tracker.record_success(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.GLOBAL_CRIS,
            model_id_used="arn:aws:bedrock::123456789012:inference-profile/test",
        )

        # Verify each preference is stored correctly
        pref1 = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )
        assert pref1 is not None
        assert pref1.prefer_direct is True

        pref2 = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-west-2",
        )
        assert pref2 is not None
        assert pref2.prefer_regional_cris is True

        pref3 = tracker.get_preference(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
        )
        assert pref3 is not None
        assert pref3.prefer_global_cris is True


class TestPreferenceRetrieval:
    """Test preference retrieval functionality."""

    def test_get_preference_returns_none_when_not_recorded(self) -> None:
        """Test that get_preference returns None when no preference recorded."""
        tracker = AccessMethodTracker.get_instance()

        preference = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        assert preference is None

    def test_get_preference_returns_correct_preference(self) -> None:
        """Test that get_preference returns the correct preference."""
        tracker = AccessMethodTracker.get_instance()

        # Record a preference
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        # Retrieve it
        preference = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        assert preference is not None
        assert preference.get_preferred_method() == AccessMethodNames.DIRECT

    def test_get_preference_is_case_sensitive_for_model_id(self) -> None:
        """Test that get_preference is case-sensitive for model ID."""
        tracker = AccessMethodTracker.get_instance()

        # Record with lowercase
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        # Try to retrieve with uppercase
        preference = tracker.get_preference(
            model_id="ANTHROPIC.CLAUDE-3-HAIKU-20240307-V1:0",
            region="us-east-1",
        )

        # Should not find it (case-sensitive)
        assert preference is None

    def test_get_preference_is_case_sensitive_for_region(self) -> None:
        """Test that get_preference is case-sensitive for region."""
        tracker = AccessMethodTracker.get_instance()

        # Record with lowercase
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        # Try to retrieve with uppercase
        preference = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="US-EAST-1",
        )

        # Should not find it (case-sensitive)
        assert preference is None

    def test_requires_profile_returns_false_when_not_recorded(self) -> None:
        """Test that requires_profile returns False when no preference recorded."""
        tracker = AccessMethodTracker.get_instance()

        result = tracker.requires_profile(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        assert result is False

    def test_requires_profile_returns_true_for_profile_requirement(self) -> None:
        """Test that requires_profile returns True for profile requirement."""
        tracker = AccessMethodTracker.get_instance()

        # Record profile requirement
        tracker.record_profile_requirement(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
        )

        result = tracker.requires_profile(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
        )

        assert result is True

    def test_requires_profile_returns_false_for_direct_access(self) -> None:
        """Test that requires_profile returns False for direct access."""
        tracker = AccessMethodTracker.get_instance()

        # Record successful direct access
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        result = tracker.requires_profile(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        assert result is False


class TestStatisticsGeneration:
    """Test statistics generation functionality."""

    def test_get_statistics_returns_zero_when_empty(self) -> None:
        """Test that get_statistics returns zero counts when empty."""
        tracker = AccessMethodTracker.get_instance()

        stats = tracker.get_statistics()

        assert stats["total_tracked"] == 0
        assert stats["profile_required_count"] == 0
        assert stats["direct_access_count"] == 0
        assert stats["regional_cris_count"] == 0
        assert stats["global_cris_count"] == 0
        assert stats["learned_from_error_count"] == 0

    def test_get_statistics_counts_direct_access(self) -> None:
        """Test that get_statistics counts direct access correctly."""
        tracker = AccessMethodTracker.get_instance()

        # Record direct access for multiple models
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-west-2",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        stats = tracker.get_statistics()

        assert stats["total_tracked"] == 2
        assert stats["direct_access_count"] == 2
        assert stats["regional_cris_count"] == 0
        assert stats["global_cris_count"] == 0
        assert stats["profile_required_count"] == 0

    def test_get_statistics_counts_regional_cris(self) -> None:
        """Test that get_statistics counts regional CRIS correctly."""
        tracker = AccessMethodTracker.get_instance()

        # Record regional CRIS access
        tracker.record_success(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.REGIONAL_CRIS,
            model_id_used="arn:aws:bedrock:us-east-1::inference-profile/test",
        )

        stats = tracker.get_statistics()

        assert stats["total_tracked"] == 1
        assert stats["direct_access_count"] == 0
        assert stats["regional_cris_count"] == 1
        assert stats["global_cris_count"] == 0

    def test_get_statistics_counts_global_cris(self) -> None:
        """Test that get_statistics counts global CRIS correctly."""
        tracker = AccessMethodTracker.get_instance()

        # Record global CRIS access
        tracker.record_success(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.GLOBAL_CRIS,
            model_id_used="arn:aws:bedrock::123456789012:inference-profile/test",
        )

        stats = tracker.get_statistics()

        assert stats["total_tracked"] == 1
        assert stats["direct_access_count"] == 0
        assert stats["regional_cris_count"] == 0
        assert stats["global_cris_count"] == 1

    def test_get_statistics_counts_profile_required(self) -> None:
        """Test that get_statistics counts profile requirements correctly."""
        tracker = AccessMethodTracker.get_instance()

        # Record profile requirement
        tracker.record_profile_requirement(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
        )

        stats = tracker.get_statistics()

        assert stats["total_tracked"] == 1
        assert stats["profile_required_count"] == 1
        assert stats["learned_from_error_count"] == 1

    def test_get_statistics_counts_mixed_preferences(self) -> None:
        """Test that get_statistics counts mixed preferences correctly."""
        tracker = AccessMethodTracker.get_instance()

        # Record various preferences
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        tracker.record_success(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.REGIONAL_CRIS,
            model_id_used="arn:aws:bedrock:us-east-1::inference-profile/test",
        )

        tracker.record_profile_requirement(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-west-2",
        )

        tracker.record_success(
            model_id="meta.llama3-70b-instruct-v1:0",
            region="eu-west-1",
            access_method=AccessMethodNames.GLOBAL_CRIS,
            model_id_used="arn:aws:bedrock::123456789012:inference-profile/test",
        )

        stats = tracker.get_statistics()

        assert stats["total_tracked"] == 4
        assert stats["direct_access_count"] == 1
        # record_profile_requirement sets prefer_regional_cris=True, so we have 2
        assert stats["regional_cris_count"] == 2
        assert stats["global_cris_count"] == 1
        assert stats["profile_required_count"] == 1
        assert stats["learned_from_error_count"] == 1

    def test_get_statistics_updates_after_preference_change(self) -> None:
        """Test that get_statistics updates after preference changes."""
        tracker = AccessMethodTracker.get_instance()

        # Record direct access
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        stats1 = tracker.get_statistics()
        assert stats1["direct_access_count"] == 1
        assert stats1["regional_cris_count"] == 0

        # Update to regional CRIS
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.REGIONAL_CRIS,
            model_id_used="arn:aws:bedrock:us-east-1::inference-profile/test",
        )

        stats2 = tracker.get_statistics()
        assert stats2["direct_access_count"] == 0
        assert stats2["regional_cris_count"] == 1
        assert stats2["total_tracked"] == 1  # Still only one combination


class TestThreadSafety:
    """Test thread safety with concurrent access."""

    def test_concurrent_record_success_is_thread_safe(self) -> None:
        """Test that concurrent record_success calls are thread-safe."""
        tracker = AccessMethodTracker.get_instance()
        num_threads = 10
        errors: List[Exception] = []

        def record_preference(thread_id: int) -> None:
            """Record a preference from a thread."""
            try:
                tracker.record_success(
                    model_id=f"model-{thread_id}",
                    region="us-east-1",
                    access_method=AccessMethodNames.DIRECT,
                    model_id_used=f"model-{thread_id}",
                )
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=record_preference, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all preferences were recorded
        stats = tracker.get_statistics()
        assert stats["total_tracked"] == num_threads

    def test_concurrent_get_preference_is_thread_safe(self) -> None:
        """Test that concurrent get_preference calls are thread-safe."""
        tracker = AccessMethodTracker.get_instance()

        # Record some preferences first
        for i in range(5):
            tracker.record_success(
                model_id=f"model-{i}",
                region="us-east-1",
                access_method=AccessMethodNames.DIRECT,
                model_id_used=f"model-{i}",
            )

        num_threads = 20
        errors: List[Exception] = []

        def read_preference(thread_id: int) -> None:
            """Read a preference from a thread."""
            try:
                model_id = f"model-{thread_id % 5}"
                preference = tracker.get_preference(
                    model_id=model_id,
                    region="us-east-1",
                )
                assert preference is not None
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=read_preference, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_mixed_operations_is_thread_safe(self) -> None:
        """Test that concurrent mixed operations are thread-safe."""
        tracker = AccessMethodTracker.get_instance()
        num_threads = 15
        errors: List[Exception] = []

        def mixed_operations(thread_id: int) -> None:
            """Perform mixed operations from a thread."""
            try:
                model_id = f"model-{thread_id % 5}"

                # Record success
                tracker.record_success(
                    model_id=model_id,
                    region="us-east-1",
                    access_method=AccessMethodNames.DIRECT,
                    model_id_used=model_id,
                )

                # Get preference
                tracker.get_preference(model_id=model_id, region="us-east-1")

                # Check requires_profile
                tracker.requires_profile(model_id=model_id, region="us-east-1")

                # Get statistics
                tracker.get_statistics()

                # Record profile requirement
                if thread_id % 3 == 0:
                    tracker.record_profile_requirement(
                        model_id=model_id,
                        region="us-west-2",
                    )
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=mixed_operations, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify statistics are consistent
        stats = tracker.get_statistics()
        assert stats["total_tracked"] > 0

    def test_concurrent_record_to_same_key_is_thread_safe(self) -> None:
        """Test that concurrent writes to the same key are thread-safe."""
        tracker = AccessMethodTracker.get_instance()
        num_threads = 20
        errors: List[Exception] = []
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        region = "us-east-1"

        # Barrier to synchronize thread start
        barrier = threading.Barrier(num_threads)

        def record_same_key(thread_id: int) -> None:
            """Record to the same key from multiple threads."""
            try:
                # Wait for all threads to be ready
                barrier.wait()

                # All threads write to the same key
                access_method = (
                    AccessMethodNames.DIRECT
                    if thread_id % 2 == 0
                    else AccessMethodNames.REGIONAL_CRIS
                )
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
        for i in range(num_threads):
            thread = threading.Thread(target=record_same_key, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify preference exists (last write wins)
        preference = tracker.get_preference(model_id=model_id, region=region)
        assert preference is not None

        # Verify statistics show only one tracked combination
        stats = tracker.get_statistics()
        assert stats["total_tracked"] == 1

    def test_singleton_is_thread_safe(self) -> None:
        """Test that singleton instantiation is thread-safe."""
        # Reset singleton
        AccessMethodTracker._instance = None

        num_threads = 20
        instances: List[AccessMethodTracker] = []
        errors: List[Exception] = []

        # Barrier to synchronize thread start
        barrier = threading.Barrier(num_threads)

        def get_instance_from_thread() -> None:
            """Get instance from a thread."""
            try:
                # Wait for all threads to be ready
                barrier.wait()

                # Get instance
                instance = AccessMethodTracker.get_instance()
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=get_instance_from_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all instances are the same
        assert len(instances) == num_threads
        for instance in instances:
            assert instance is instances[0]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_record_success_with_empty_model_id(self) -> None:
        """Test recording success with empty model ID."""
        tracker = AccessMethodTracker.get_instance()

        # Should not raise an error
        tracker.record_success(
            model_id="",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="",
        )

        # Should be able to retrieve it
        preference = tracker.get_preference(model_id="", region="us-east-1")
        assert preference is not None

    def test_record_success_with_empty_region(self) -> None:
        """Test recording success with empty region."""
        tracker = AccessMethodTracker.get_instance()

        # Should not raise an error
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        # Should be able to retrieve it
        preference = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="",
        )
        assert preference is not None

    def test_record_success_with_very_long_model_id(self) -> None:
        """Test recording success with very long model ID."""
        tracker = AccessMethodTracker.get_instance()

        long_model_id = "a" * 1000
        tracker.record_success(
            model_id=long_model_id,
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used=long_model_id,
        )

        preference = tracker.get_preference(model_id=long_model_id, region="us-east-1")
        assert preference is not None

    def test_record_success_with_special_characters_in_model_id(self) -> None:
        """Test recording success with special characters in model ID."""
        tracker = AccessMethodTracker.get_instance()

        special_model_id = "model-with-special-chars!@#$%^&*()"
        tracker.record_success(
            model_id=special_model_id,
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used=special_model_id,
        )

        preference = tracker.get_preference(
            model_id=special_model_id,
            region="us-east-1",
        )
        assert preference is not None

    def test_record_success_with_unicode_characters(self) -> None:
        """Test recording success with unicode characters."""
        tracker = AccessMethodTracker.get_instance()

        unicode_model_id = "model-with-unicode-🚀-chars"
        tracker.record_success(
            model_id=unicode_model_id,
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used=unicode_model_id,
        )

        preference = tracker.get_preference(
            model_id=unicode_model_id,
            region="us-east-1",
        )
        assert preference is not None

    def test_get_statistics_with_large_number_of_preferences(self) -> None:
        """Test get_statistics with large number of preferences."""
        tracker = AccessMethodTracker.get_instance()

        # Record many preferences
        num_preferences = 1000
        for i in range(num_preferences):
            tracker.record_success(
                model_id=f"model-{i}",
                region="us-east-1",
                access_method=AccessMethodNames.DIRECT,
                model_id_used=f"model-{i}",
            )

        stats = tracker.get_statistics()
        assert stats["total_tracked"] == num_preferences
        assert stats["direct_access_count"] == num_preferences

    def test_preference_last_updated_is_set(self) -> None:
        """Test that last_updated timestamp is set correctly."""
        tracker = AccessMethodTracker.get_instance()

        before = datetime.now()

        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        after = datetime.now()

        preference = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        assert preference is not None
        assert before <= preference.last_updated <= after

    def test_preference_last_updated_changes_on_update(self) -> None:
        """Test that last_updated changes when preference is updated."""
        tracker = AccessMethodTracker.get_instance()

        # Record first preference
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.DIRECT,
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        preference1 = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )
        assert preference1 is not None
        first_updated = preference1.last_updated

        # Wait a bit
        import time

        time.sleep(0.01)

        # Update preference
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method=AccessMethodNames.REGIONAL_CRIS,
            model_id_used="arn:aws:bedrock:us-east-1::inference-profile/test",
        )

        preference2 = tracker.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )
        assert preference2 is not None
        second_updated = preference2.last_updated

        # Timestamp should have changed
        assert second_updated > first_updated
