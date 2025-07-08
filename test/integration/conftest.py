"""
Integration test configuration and fixtures.

This file provides pytest fixtures specifically for integration tests that require
real AWS Bedrock API access, including authentication, test clients, and configuration.
"""

from typing import Any

import pytest

from bestehorn_llmmanager.bedrock.testing.aws_test_client import AWSTestClient
from bestehorn_llmmanager.bedrock.testing.integration_config import (
    IntegrationTestConfig,
    IntegrationTestError,
    load_integration_config,
)


@pytest.fixture(scope="session")
def integration_config() -> IntegrationTestConfig:
    """
    Provide integration test configuration for the test session.

    This fixture loads the integration test configuration from environment
    variables and validates that the test environment is properly set up.

    Returns:
        Configured IntegrationTestConfig instance

    Raises:
        pytest.skip: If integration tests are not enabled or configured
    """
    try:
        config = load_integration_config()

        # Skip integration tests if they're not enabled
        if not config.enabled:
            pytest.skip(
                "Integration tests are not enabled. Set AWS_INTEGRATION_TESTS_ENABLED=true to enable."
            )

        return config

    except IntegrationTestError as e:
        pytest.skip(f"Integration test configuration error: {e}")
    except Exception as e:
        pytest.skip(f"Failed to load integration test configuration: {e}")


@pytest.fixture(scope="session")
def aws_test_client(integration_config: IntegrationTestConfig) -> AWSTestClient:
    """
    Provide AWS test client for integration tests.

    This fixture creates and configures an AWSTestClient instance for making
    test requests to AWS Bedrock services with proper authentication and
    request tracking.

    Args:
        integration_config: Integration test configuration

    Returns:
        Configured AWSTestClient instance

    Raises:
        pytest.skip: If the test client cannot be initialized
    """
    try:
        client = AWSTestClient(config=integration_config)
        return client

    except IntegrationTestError as e:
        pytest.skip(f"AWS test client initialization failed: {e}")
    except Exception as e:
        pytest.skip(f"Failed to create AWS test client: {e}")


@pytest.fixture(autouse=True)
def check_integration_test_marker(request: Any, integration_config: IntegrationTestConfig) -> None:
    """
    Automatically check if integration tests should be skipped.

    This fixture runs automatically for all tests and will skip tests marked
    with integration markers if integration tests are not properly configured.

    Args:
        request: Pytest request object
        integration_config: Integration test configuration
    """
    # Get markers for the current test
    markers = [marker.name for marker in request.node.iter_markers()]

    # Skip if this is an integration test but integration tests are not enabled
    if (
        any(marker in markers for marker in ["integration", "aws_integration"])
        and not integration_config.enabled
    ):
        pytest.skip("Integration tests are disabled")

    # Skip slow tests if configured to skip them
    if "aws_slow" in markers and integration_config.should_skip_slow_test():
        pytest.skip("Slow integration tests are disabled")


@pytest.fixture(scope="function")
def test_session(aws_test_client: AWSTestClient, request: Any) -> Any:
    """
    Provide a test session for tracking requests and costs.

    This fixture creates a test session for tracking multiple requests
    within a single test function, including cost monitoring and
    performance metrics.

    Args:
        aws_test_client: AWS test client
        request: Pytest request object

    Returns:
        Active test session
    """
    # Create session ID from test node name
    session_id = f"{request.node.nodeid.replace('::', '_').replace('/', '_')}"

    # Start test session
    session = aws_test_client.start_test_session(session_id=session_id)

    yield session

    # End session and log summary
    summary = aws_test_client.end_test_session()
    if summary:
        print(f"\nTest session summary: {summary}")
