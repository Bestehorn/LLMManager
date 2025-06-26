# Bestehorn LLMManager

[![PyPI version](https://badge.fury.io/py/bestehorn-llmmanager.svg)](https://badge.fury.io/py/bestehorn-llmmanager)
[![Python Versions](https://img.shields.io/pypi/pyversions/bestehorn-llmmanager.svg)](https://pypi.org/project/bestehorn-llmmanager/)
[![Build Status](https://github.com/Bestehorn/LLMManager/workflows/CI/badge.svg)](https://github.com/Bestehorn/LLMManager/actions)
[![Coverage Status](https://codecov.io/gh/Bestehorn/LLMManager/branch/main/graph/badge.svg)](https://codecov.io/gh/Bestehorn/LLMManager)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive Python library for managing AWS Bedrock Converse API interactions with support for multiple models, regions, authentication methods, and parallel processing.

## Features

- **Multi-Model Support**: Work with multiple LLM models simultaneously
- **Multi-Region Failover**: Automatic failover across AWS regions
- **Flexible Authentication**: Support for profiles, credentials, IAM roles
- **Intelligent Retry Logic**: Graceful degradation with configurable retry strategies
- **Parallel Processing**: Execute multiple requests concurrently across regions
- **Comprehensive Response Handling**: Detailed response management and validation
- **Full Converse API Support**: All AWS Bedrock Converse API features supported

## Installation

### From PyPI (Recommended)

```bash
pip install bestehorn-llmmanager
```

### From Source (Development)

For development or integration into other projects:

```bash
git clone https://github.com/Bestehorn/LLMManager.git
cd LLMManager
pip install -e .
```

### With Development Dependencies

```bash
pip install -e .[dev]
```

## Quick Start

### Basic Usage

```python
from bestehorn_llmmanager import LLMManager

# Initialize with models and regions
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"]
)

# Send a conversation request
response = manager.converse(
    messages=[{"role": "user", "content": [{"text": "Hello! How are you?"}]}]
)

print(response.get_content())
```

### Parallel Processing

```python
from bestehorn_llmmanager import ParallelLLMManager
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

# Initialize parallel manager
parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)

# Create multiple requests
requests = [
    BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "What is AI?"}]}]),
    BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Explain machine learning"}]}])
]

# Execute in parallel
parallel_response = parallel_manager.converse_parallel(
    requests=requests,
    target_regions_per_request=2
)

print(f"Success rate: {parallel_response.get_success_rate():.1f}%")
```

### With Authentication Configuration

```python
from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig, AuthenticationType
)

# Configure authentication
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-aws-profile"
)

manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    auth_config=auth_config
)
```

## Requirements

- Python 3.8+
- AWS credentials configured (AWS CLI, environment variables, or IAM roles)
- Internet access for initial model data download

### Dependencies

- `boto3>=1.28.0` - AWS SDK
- `beautifulsoup4>=4.12.0` - HTML parsing
- `requests>=2.31.0` - HTTP requests

## Configuration

### AWS Credentials

The library supports multiple authentication methods:

1. **AWS Profiles**: Use named profiles from `~/.aws/credentials`
2. **Environment Variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
3. **IAM Roles**: For EC2 instances or Lambda functions
4. **Default Credential Chain**: Standard AWS credential resolution

### Model Data

The library automatically downloads and caches AWS Bedrock model information on first use. This requires internet connectivity initially but uses cached data for subsequent runs.

## Advanced Usage

### Custom Retry Configuration

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RetryConfig, RetryStrategy
)

retry_config = RetryConfig(
    max_attempts=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay_seconds=1.0
)

manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    retry_config=retry_config
)
```

### Response Validation

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    ResponseValidationConfig
)

validation_config = ResponseValidationConfig(
    max_validation_attempts=3,
    validation_prompt="Is this response appropriate and helpful?"
)

response = manager.converse(
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    response_validation_config=validation_config
)
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd bestehorn-llmmanager

# Install in editable mode with development dependencies
pip install -e .[dev]

# Run tests
pytest

# Run tests with coverage
pytest --cov=bestehorn_llmmanager
```

### Project Structure

```
bestehorn-llmmanager/
├── src/
│   └── bestehorn_llmmanager/
│       ├── __init__.py
│       ├── llm_manager.py
│       ├── parallel_llm_manager.py
│       └── bedrock/
├── test/
├── docs/
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
# Unit tests only
pytest test/bestehorn_llmmanager/

# Integration tests (requires AWS credentials)
pytest test/integration/ -m integration

# All tests
pytest
```

## API Reference

### LLMManager

Primary interface for single AWS Bedrock requests.

**Key Methods:**
- `converse()`: Send conversation requests
- `converse_stream()`: Send streaming conversation requests
- `validate_configuration()`: Check configuration validity
- `refresh_model_data()`: Update model information

### ParallelLLMManager

Interface for parallel processing of multiple requests.

**Key Methods:**
- `converse_parallel()`: Execute multiple requests in parallel
- `get_parallel_config()`: Get current parallel configuration
- `validate_configuration()`: Validate parallel and base configuration

## Error Handling

The library provides comprehensive error handling with specific exception types:

- `LLMManagerError`: Base exception for all library errors
- `ConfigurationError`: Configuration-related errors
- `AuthenticationError`: AWS authentication failures
- `RequestValidationError`: Request validation failures
- `RetryExhaustedError`: All retry attempts failed
- `ParallelProcessingError`: Parallel execution errors

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Support

For issues and questions:
- Check the documentation in the `docs/` directory
- Review existing issues on GitHub
- Create a new issue with detailed information about your problem
