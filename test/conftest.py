"""
Pytest configuration and shared fixtures for the LLMManager test suite.

This module provides common fixtures, utilities, and configuration for all tests.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

import pytest
import sys
from pathlib import Path

# Add the src directory to Python path so that bedrock modules can be imported
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


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


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "network: Tests requiring network access")
    config.addinivalue_line("markers", "aws: Tests requiring AWS access")


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
