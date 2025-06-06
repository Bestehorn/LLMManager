# LLMManager - AWS Bedrock Management System

## Overview

LLMManager is a comprehensive Python framework for managing AWS Bedrock Large Language Model (LLM) interactions. It provides a unified, production-ready interface for working with multiple LLMs across regions with automatic failover, retry logic, multi-modal message support, and parallel processing capabilities.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Installation](#installation)
5. [Basic Usage](#basic-usage)
6. [Advanced Features](#advanced-features)
7. [Documentation Index](#documentation-index)
8. [Examples](#examples)
9. [Development](#development)

## Quick Start

```python
from src.LLMManager import LLMManager
from src.bedrock.models.message_builder_factory import create_user_message

# Initialize LLM Manager
manager = LLMManager(
    models=["Claude 3.5 Sonnet", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)

# Create a simple text message
message = create_user_message() \
    .add_text("Hello! Please introduce yourself.") \
    .build()

# Send request with automatic retry and failover
response = manager.converse(messages=[message])
print(response.get_content())
```

## Architecture Overview

The LLMManager system follows a modular, layered architecture designed for production use:

```
┌─────────────────────────────────────────────────┐
│                 LLMManager                      │  ← Main Interface
├─────────────────────────────────────────────────┤
│ ParallelLLMManager │ MessageBuilder │ RetryMgr  │  ← Core Services
├─────────────────────────────────────────────────┤
│  UnifiedModelMgr  │   CRISManager   │ AuthMgr   │  ← Model Management
├─────────────────────────────────────────────────┤
│   ModelManager    │   Downloaders   │ Parsers   │  ← Data Acquisition
├─────────────────────────────────────────────────┤
│   AWS Bedrock     │  Cross-Region   │ DirectAPI │  ← AWS Integration
└─────────────────────────────────────────────────┘
```

### Key Design Principles

- **Modular Architecture**: Clear separation of concerns with well-defined interfaces
- **Type Safety**: Comprehensive type hints and immutable data structures
- **Production Ready**: Extensive error handling, logging, and retry mechanisms
- **Extensible**: Plugin architecture for custom parsers, serializers, and authenticators
- **Performance**: Parallel processing, intelligent caching, and resource optimization

## Core Components

### 1. LLMManager
**Primary interface** for all LLM interactions with automatic failover and retry logic.
- Multi-model, multi-region support
- Authentication handling
- Request validation and error handling
- Comprehensive response objects

### 2. ParallelLLMManager
**Parallel processing engine** for high-throughput LLM operations.
- Concurrent request execution
- Load balancing strategies
- Failure handling with configurable strategies
- Performance optimization

### 3. MessageBuilder
**Fluent interface** for constructing multi-modal messages.
- Text, image, document, and video support
- Automatic format detection
- Size validation and optimization
- Converse API compatibility

### 4. UnifiedModelManager
**Centralized model registry** combining direct and cross-region access information.
- Model availability tracking
- Access method recommendations
- Region-specific capabilities
- Correlation between different data sources

### 5. CRISManager
**Cross-Region Inference System** manager for routing requests across AWS regions.
- Dynamic region mapping
- Multi-regional inference profiles
- Optimal routing recommendations
- Real-time availability tracking

### 6. ModelManager
**Foundational model catalog** manager for AWS Bedrock model information.
- Automated model discovery
- Capability and region mapping
- Structured model metadata
- Version tracking

## Installation

### Prerequisites

- Python 3.9 or higher
- AWS credentials configured (AWS CLI, environment variables, or IAM roles)
- Required Python packages (see requirements.txt)

### Setup

```bash
# Clone the repository
git clone https://github.com/Bestehorn/LLMManager.git
cd LLMManager

# Install dependencies
pip install -r requirements.txt

# Add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/LLMManager/src"

# Verify installation
python -c "from src.LLMManager import LLMManager; print('Installation successful!')"
```

### AWS Configuration

Ensure AWS credentials are configured with Bedrock permissions:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Option 3: IAM Roles (recommended for production)
```

## Basic Usage

### Simple Text Conversation

```python
from src.LLMManager import LLMManager
from src.bedrock.models.message_builder_factory import create_user_message

manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"]
)

message = create_user_message().add_text("What is machine learning?").build()
response = manager.converse(messages=[message])

print(f"Response: {response.get_content()}")
print(f"Model used: {response.model_used}")
print(f"Tokens used: {response.get_usage()}")
```

### Multi-Modal Messages

```python
# Create message with text and image
message = create_user_message() \
    .add_text("Please analyze this image:") \
    .add_local_image("path/to/image.jpg") \
    .build()

response = manager.converse(messages=[message])
```

### Multi-Turn Conversation

```python
messages = [
    create_user_message().add_text("Hello, I'm working on a Python project.").build(),
    # ... add assistant response
    create_user_message().add_text("Can you help me with error handling?").build()
]

response = manager.converse(messages=messages)
```

### Streaming Responses

```python
streaming_response = manager.converse_stream(messages=[message])

for chunk in streaming_response:
    print(chunk, end="", flush=True)
```

## Advanced Features

### Parallel Processing

```python
from src.bedrock.ParallelLLMManager import ParallelLLMManager
from src.bedrock.models.parallel_structures import ParallelProcessingConfig

config = ParallelProcessingConfig(
    max_parallel_requests=5,
    load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN
)

parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku", "Claude 3.5 Sonnet"],
    regions=["us-east-1", "us-west-2"],
    parallel_config=config
)

# Execute multiple requests in parallel
requests = [create_request_1(), create_request_2(), create_request_3()]
responses = parallel_manager.converse_parallel(requests)
```

### Custom Authentication

```python
from src.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-aws-profile"
)

manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"],
    auth_config=auth_config
)
```

### Response Validation and Retry

```python
from src.bedrock.models.llm_manager_structures import ResponseValidationConfig

validation_config = ResponseValidationConfig(
    max_validation_attempts=3,
    validation_function=lambda response: len(response.get_content()) > 10
)

response = manager.converse(
    messages=[message],
    response_validation_config=validation_config
)
```

## Documentation Index

### Core Documentation
- [LLMManager Documentation](LLMManager_Documentation.md) - Main interface documentation
- [ParallelLLMManager Documentation](ParallelLLMManager_Documentation.md) - Parallel processing guide
- [MessageBuilder Documentation](MessageBuilder.md) - Multi-modal message construction
- [UnifiedModelManager Documentation](UnifiedModelManager_Documentation.md) - Model registry management

### Specialized Components
- [CRISManager Documentation](CRISManager_Documentation.md) - Cross-region inference management
- [ModelManager Documentation](ModelManager_Documentation.md) - Foundational model catalog
- [Authentication Documentation](Authentication_Documentation.md) - Authentication and authorization
- [Retry and Error Handling](RetryManager_Documentation.md) - Retry logic and error handling

### Data Formats and Structures
- [CRIS JSON Format Specification](CRIS_JSON_Format.md) - Cross-region inference data format
- [Data Structures Reference](DataStructures_Documentation.md) - Core data models
- [Constants and Configuration](Constants_Documentation.md) - Configuration options and constants

### Advanced Topics
- [Architecture and Design](Architecture_Documentation.md) - System architecture and design patterns
- [Performance and Optimization](Performance_Documentation.md) - Performance tuning and optimization
- [Extension and Customization](Extension_Documentation.md) - Extending the framework
- [Testing Framework](TESTING.md) - Comprehensive testing documentation

### Examples and Tutorials
- [Getting Started Guide](GettingStarted_Documentation.md) - Step-by-step tutorial
- [Common Use Cases](UseCases_Documentation.md) - Real-world examples
- [Best Practices](BestPractices_Documentation.md) - Production deployment guidelines
- [Troubleshooting Guide](Troubleshooting_Documentation.md) - Common issues and solutions

## Examples

See the `notebooks/` directory for Jupyter notebook examples:

- **HelloWorld_LLMManager.ipynb** - Basic LLMManager usage
- **MessageBuilder_Demo.ipynb** - Multi-modal message examples
- **ParallelLLMManager_Demo.ipynb** - Parallel processing examples
- **UnifiedModelManager.ipynb** - Model management examples
- **CRISManager.ipynb** - Cross-region inference examples

## Development

### Project Structure

```
LLMManager/
├── src/                    # Production code
│   ├── LLMManager.py      # Main interface
│   └── bedrock/           # Core modules
│       ├── auth/          # Authentication
│       ├── models/        # Data structures
│       ├── parsers/       # Content parsers
│       └── ...           # Other components
├── test/                  # Test suite (mirrors src/)
├── docs/                  # Documentation
├── notebooks/             # Example notebooks
├── examples/              # Example files and data
└── workspace/             # Development workspace
```

### Development Guidelines

The project follows strict development standards:

- **Modular Design**: Functions and classes are broken into independent, reusable pieces
- **Type Safety**: All code uses comprehensive type hints
- **Error Handling**: Functions throw exceptions for errors, return None for expected failures
- **Testing**: Comprehensive unit tests with 80%+ coverage requirement
- **Documentation**: All components are thoroughly documented

### Contributing

1. Follow the coding standards in `prompts/CodingStandards.txt`
2. Maintain test coverage above 80%
3. Update documentation for any changes
4. Use type hints throughout
5. Follow the modular design principles

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --html

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
```

## Support and Resources

- **Source Code**: See `src/` directory for complete implementation
- **Examples**: Check `notebooks/` and `examples/` directories
- **Tests**: Reference `test/` directory for usage examples
- **Issues**: Report issues through your project's issue tracking system

## License

See LICENSE file for license information.

---

**Note**: This framework is designed for production use with AWS Bedrock. Ensure proper AWS credentials and permissions are configured before use.
