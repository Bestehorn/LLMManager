"""
Root conftest.py file for test configuration.
This file is automatically loaded by pytest and configures the test environment.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

# Add the src directory to Python path so tests can import the package
project_root = Path(__file__).parent.parent
src_path = project_root / "src"

# Remove any existing test directory from sys.path to avoid conflicts
test_path = project_root / "test"
if str(test_path) in sys.path:
    sys.path.remove(str(test_path))

# Add src to the beginning of sys.path - this must be first!
# Remove it first if it exists, then add at position 0
if str(src_path) in sys.path:
    sys.path.remove(str(src_path))
sys.path.insert(0, str(src_path))

# Also set PYTHONPATH environment variable
os.environ["PYTHONPATH"] = str(src_path) + os.pathsep + os.environ.get("PYTHONPATH", "")

# Print debug info to help diagnose import issues
print("Python path setup in conftest.py:")
print(f"  Project root: {project_root}")
print(f"  Src path: {src_path}")
print(f"  sys.path[0]: {sys.path[0]}")
print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")

# Check if bestehorn_llmmanager can be imported
try:
    import bestehorn_llmmanager

    print(f"  bestehorn_llmmanager location: {bestehorn_llmmanager.__file__}")
except ImportError as e:
    print(f"  Failed to import bestehorn_llmmanager: {e}")


# Test fixtures
@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_test_messages() -> List[Dict[str, object]]:
    """Sample messages for testing Bedrock converse API."""
    return [
        {
            "role": "user",
            "content": [
                {
                    "text": "Hello! This is a test message for integration testing. Please respond with a simple greeting."
                }
            ],
        }
    ]


@pytest.fixture
def simple_inference_config() -> Dict[str, object]:
    """Simple inference configuration for testing."""
    return {"maxTokens": 100, "temperature": 0.1, "topP": 0.9}


# Pytest configuration hooks
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers and settings."""
    # These markers are already defined in pytest.ini, but we'll add them here too for completeness
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "network: Tests requiring network access")
    config.addinivalue_line("markers", "aws: Tests requiring AWS access")
    config.addinivalue_line(
        "markers", "aws_integration: Tests requiring real AWS Bedrock API access"
    )
    config.addinivalue_line("markers", "aws_fast: Fast integration tests (< 30 seconds)")
    config.addinivalue_line("markers", "aws_slow: Slow integration tests (> 30 seconds)")
    config.addinivalue_line("markers", "aws_low_cost: Low-cost tests (< $0.01 estimated)")
    config.addinivalue_line(
        "markers", "aws_medium_cost: Medium-cost tests ($0.01 - $0.10 estimated)"
    )
    config.addinivalue_line("markers", "aws_high_cost: High-cost tests (> $0.10 estimated)")
    config.addinivalue_line("markers", "aws_bedrock_runtime: Tests using Bedrock Runtime API")
    config.addinivalue_line("markers", "aws_streaming: Tests using streaming responses")
