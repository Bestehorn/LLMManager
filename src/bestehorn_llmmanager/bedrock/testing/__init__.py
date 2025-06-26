"""
Testing utilities module for bedrock package.

This module provides utilities and configurations for integration testing
with real AWS Bedrock API endpoints.
"""

from .aws_test_client import AWSTestClient
from .integration_config import IntegrationTestConfig, IntegrationTestError
from .integration_markers import IntegrationTestMarkers

__all__ = [
    "IntegrationTestConfig",
    "IntegrationTestError",
    "IntegrationTestMarkers",
    "AWSTestClient",
]
