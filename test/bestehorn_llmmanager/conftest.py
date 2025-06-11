"""
Pytest configuration and shared fixtures for the LLMManager test suite.

This module provides common fixtures, utilities, and configuration for all tests.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

import pytest
import sys
from pathlib import Path

# Import integration testing components
# Temporarily commenting out to test basic functionality
# TODO: Fix these imports after ensuring basic package structure works
# from bestehorn_llmmanager.bedrock.testing.integration_config import IntegrationTestConfig, load_integration_config
# from bestehorn_llmmanager.bedrock.testing.integration_markers import IntegrationTestMarkers
# from bestehorn_llmmanager.bedrock.testing.aws_test_client import AWSTestClient


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing HTML parsers."""
    return """
    <html>
        <head><title>Test HTML</title></head>
        <body>
            <table>
                <thead>
                    <tr>
                        <th>Provider</th>
                        <th>Model ID</th>
                        <th>Regions supported</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Amazon</td>
                        <td>amazon.titan-text-express-v1</td>
                        <td>us-east-1, us-west-2</td>
                    </tr>
                </tbody>
            </table>
        </body>
    </html>
    """


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing serializers."""
    return {
        "retrieval_timestamp": "2024-01-01T12:00:00",
        "models": [
            {
                "provider": "Amazon",
                "model_id": "amazon.titan-text-express-v1",
                "regions_supported": ["us-east-1", "us-west-2"],
                "input_modalities": ["text"],
                "output_modalities": ["text"],
                "streaming_supported": True
            }
        ]
    }


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent timestamps in tests."""
    fixed_datetime = datetime(2024, 1, 1, 12, 0, 0)
    with pytest.MonkeyPatch().context() as m:
        mock_dt = Mock()
        mock_dt.now.return_value = fixed_datetime
        m.setattr("datetime.datetime", mock_dt)
        yield fixed_datetime


@pytest.fixture
def mock_requests():
    """Mock requests library for network testing."""
    with pytest.MonkeyPatch().context() as m:
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mock HTML content"
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        m.setattr("requests.get", mock_requests.get)
        yield mock_requests


@pytest.fixture
def sample_cris_html():
    """Sample CRIS HTML content for testing CRIS parsers."""
    return """
    <html>
        <body>
            <div class="expandable-section">
                <h3>Claude 3.5 Sonnet</h3>
                <div class="section-body">
                    <p>Inference profile ID: us.anthropic.claude-3-5-sonnet-20241022-v2:0</p>
                    <table>
                        <tr>
                            <th>Source regions</th>
                            <th>Destination regions</th>
                        </tr>
                        <tr>
                            <td>us-east-1, us-west-2</td>
                            <td>us-west-2</td>
                        </tr>
                    </table>
                </div>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_file_system(temp_dir):
    """Mock file system operations for testing."""
    def create_file(path: Path, content: str = ""):
        """Create a file with optional content."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path
    
    def create_json_file(path: Path, data: Dict[str, Any]):
        """Create a JSON file with data."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
        return path
    
    return {
        "temp_dir": temp_dir,
        "create_file": create_file,
        "create_json_file": create_json_file
    }


@pytest.fixture
def mock_logger():
    """Mock logger for testing logging behavior."""
    return Mock()


# Integration test fixtures
# TODO: Re-enable after fixing imports
# @pytest.fixture
# def integration_config():
#     """Load integration test configuration from environment."""
#     try:
#         config = load_integration_config()
#         if not config.enabled:
#             skip_reason = _get_integration_skip_reason()
#             pytest.skip(skip_reason)
#         return config
#     except Exception as e:
#         skip_reason = f"Failed to load integration test configuration: {str(e)}"
#         pytest.skip(skip_reason)


# def _get_integration_skip_reason() -> str:
#     """Get detailed reason why integration tests are skipped."""
#     from bestehorn_llmmanager.bedrock.testing.integration_config import (
#         _has_aws_environment_credentials, 
#         _has_aws_profile_credentials
#     )
#     
#     # Check if AWS credentials are available at all
#     has_env_creds = _has_aws_environment_credentials()
#     has_profile_creds = _has_aws_profile_credentials()
#     
#     if not has_env_creds and not has_profile_creds:
#         return (
#             "Integration tests skipped: No AWS credentials found. "
#             "Either set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY environment variables "
#             "or configure AWS CLI with 'aws configure' for default profile access."
#         )
#     
#     # If we get here, credentials should be available but integration is still disabled
#     return "Integration tests disabled despite available AWS credentials"


@pytest.fixture
def sample_test_messages():
    """Sample messages for testing Bedrock converse API."""
    return [
        {
            "role": "user",
            "content": [
                {
                    "text": "Hello! This is a test message for integration testing. Please respond with a simple greeting."
                }
            ]
        }
    ]


@pytest.fixture
def simple_inference_config():
    """Simple inference configuration for testing."""
    return {
        "maxTokens": 100,
        "temperature": 0.1,
        "topP": 0.9
    }


# TODO: Re-enable after fixing imports
# @pytest.fixture
# def aws_test_client(integration_config):
#     """Create AWS test client for integration tests."""
#     try:
#         return AWSTestClient(config=integration_config)
#     except Exception as e:
#         skip_reason = f"Failed to create AWS test client: {str(e)}"
#         pytest.skip(skip_reason)


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "network: Tests requiring network access")
    config.addinivalue_line("markers", "aws: Tests requiring AWS access")
    config.addinivalue_line("markers", "aws_integration: Tests requiring real AWS Bedrock API access")
    config.addinivalue_line("markers", "aws_fast: Fast integration tests (< 30 seconds)")
    config.addinivalue_line("markers", "aws_slow: Slow integration tests (> 30 seconds)")
    config.addinivalue_line("markers", "aws_low_cost: Low-cost tests (< $0.01 estimated)")
    config.addinivalue_line("markers", "aws_medium_cost: Medium-cost tests ($0.01 - $0.10 estimated)")
    config.addinivalue_line("markers", "aws_high_cost: High-cost tests (> $0.10 estimated)")
    config.addinivalue_line("markers", "aws_bedrock_runtime: Tests using Bedrock Runtime API")
    config.addinivalue_line("markers", "aws_streaming: Tests using streaming responses")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ["integration", "slow", "network", "aws"] 
                  for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker to tests with "slow" in name
        if "slow" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Add network marker to tests with "network" or "download" in name
        if any(keyword in item.name.lower() for keyword in ["network", "download", "request"]):
            item.add_marker(pytest.mark.network)
