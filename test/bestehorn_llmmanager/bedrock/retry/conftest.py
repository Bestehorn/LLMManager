"""
Pytest fixtures for retry tests.

This module provides shared fixtures for retry-related tests, including
automatic state reset for the AccessMethodTracker singleton to ensure
test isolation.
"""

import pytest

from src.bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)


@pytest.fixture(autouse=True)
def reset_access_method_tracker():
    """
    Reset AccessMethodTracker before and after each test.

    This fixture ensures tests don't interfere with each other by clearing
    the singleton state before each test run. The autouse=True parameter
    means this fixture is automatically applied to all tests in this directory
    and its subdirectories.

    The fixture resets the tracker both before and after each test to ensure:
    1. Tests start with a clean slate (no learned preferences from previous tests)
    2. Tests clean up after themselves (no state leakage to subsequent tests)

    This is critical for property-based tests that run multiple times with
    different inputs, as the AccessMethodTracker singleton can retain state
    across test runs and cause non-deterministic behavior.

    Usage:
        This fixture is automatically applied to all tests in the retry directory.
        No explicit use is required in test functions.

    Example:
        def test_something():
            # AccessMethodTracker is automatically reset before this test
            tracker = AccessMethodTracker.get_instance()
            # tracker starts with empty state
            ...
            # AccessMethodTracker is automatically reset after this test
    """
    # Reset before test
    AccessMethodTracker.reset_for_testing()

    yield

    # Reset after test (cleanup)
    AccessMethodTracker.reset_for_testing()
