# Project Structure Documentation

## Overview
This document describes the complete project structure of the LLMManager project, a Python package for managing Large Language Model interactions with AWS Bedrock.

## Root Directory Structure

```
LLMManager/
├── .gitallowed                    # Git configuration file
├── extract_llm_manager.py         # Extraction utility script
├── LICENSE                        # Project license file
├── pyproject.toml                 # Python project configuration
├── pytest.ini                     # Pytest configuration
├── README.md                      # Main project documentation
├── requirements-test.txt          # Testing dependencies
├── requirements.txt               # Production dependencies
├── run_tests.bat                  # Windows test runner script
├── run_tests.py                   # Python test runner script
├── api/                          # API-related files
├── docs/                         # Project documentation
├── examples/                     # Example files and resources
├── images/                       # Image assets
├── notebooks/                    # Jupyter notebooks for demonstrations
├── prompts/                      # AI prompt templates
├── src/                          # Source code (main package)
├── test/                         # Test files
├── videos/                       # Video assets
└── workspace/                    # Working directory
```

## Source Code Structure (`src/`)

The `src/` directory contains the main package implementation:

```
src/
├── bestehorn_llmmanager/         # Main Python package
├── docs/                         # Source documentation
└── bestehorn_llmmanager.egg-info/ # Package metadata
```

### Main Package Structure (`src/bestehorn_llmmanager/`)

```
bestehorn_llmmanager/
├── __init__.py                   # Package initialization
├── llm_manager.py               # Core LLM manager implementation
├── parallel_llm_manager.py      # Parallel processing manager
└── bedrock/                     # AWS Bedrock integration modules
```

## Bedrock Subdirectories (`src/bestehorn_llmmanager/bedrock/`)

The bedrock directory contains specialized modules for AWS Bedrock integration:

### Core Modules
- **`__init__.py`** - Package initialization
- **`CRISManager.py`** - CRIS (Claude Request Information System) management
- **`ModelManager.py`** - Individual model management
- **`UnifiedModelManager.py`** - Unified interface for multiple models

### Subdirectory Breakdown

#### `adapters/`
Contains adapter patterns for different service integrations and protocol translations.

#### `auth/`
Authentication and authorization management:
- **`auth_manager.py`** - Handles AWS authentication, credentials, and session management

#### `correlators/`
Data correlation and relationship management:
- **`model_cris_correlator.py`** - Correlates model responses with CRIS data structures

#### `distributors/`
Request distribution and load balancing:
- **`region_distribution_manager.py`** - Manages distribution of requests across AWS regions

#### `downloaders/`
File and content downloading utilities:
- **`base_downloader.py`** - Base class for download operations
- **`html_downloader.py`** - Specialized HTML content downloader

#### `exceptions/`
Custom exception classes:
- **`llm_manager_exceptions.py`** - LLM-specific exceptions
- **`parallel_exceptions.py`** - Parallel processing exceptions

#### `executors/`
Execution engines for different processing modes:
- **`parallel_executor.py`** - Base parallel execution framework
- **`thread_parallel_executor.py`** - Thread-based parallel execution

#### `filters/`
Content filtering and processing:
- **`content_filter.py`** - Filters and sanitizes content for LLM processing

#### `models/`
Data models, structures, and constants:
- Core model files:
  - **`access_method.py`** - Access method definitions
  - **`aws_regions.py`** - AWS region configurations
  - **`bedrock_response.py`** - Bedrock API response models
  - **`converse_message_builder.py`** - Message builder for conversations
  - **`data_structures.py`** - General data structures
  - **`message_builder_factory.py`** - Factory for message builders
  - **`message_builder_enums.py`** - Enumeration types for message building

- Constants and configurations:
  - **`constants.py`** - General constants
  - **`cris_constants.py`** - CRIS-specific constants
  - **`llm_manager_constants.py`** - LLM manager constants
  - **`message_builder_constants.py`** - Message builder constants
  - **`parallel_constants.py`** - Parallel processing constants
  - **`unified_constants.py`** - Unified manager constants

- Specialized structures:
  - **`cris_regional_structures.py`** - Regional CRIS data structures
  - **`cris_structures.py`** - Core CRIS data structures
  - **`llm_manager_structures.py`** - LLM manager data structures
  - **`parallel_structures.py`** - Parallel processing structures
  - **`unified_structures.py`** - Unified manager structures

##### `models/file_type_detector/`
File type detection utilities:
- **`base_detector.py`** - Base file type detector
- **`detector_constants.py`** - Detection constants
- **`file_type_detector.py`** - Main file type detection logic

#### `parsers/`
Response parsing and data extraction:
- **`base_parser.py`** - Base parser interface
- **`bedrock_parser.py`** - Bedrock response parser
- **`cris_parser.py`** - CRIS data parser
- **`enhanced_bedrock_parser.py`** - Enhanced Bedrock parsing capabilities

#### `retry/`
Retry logic and error recovery:
- **`retry_manager.py`** - Manages retry attempts and backoff strategies

#### `serializers/`
Data serialization utilities:
- **`json_serializer.py`** - JSON serialization/deserialization

#### `testing/`
Testing utilities and configurations:
- **`aws_test_client.py`** - AWS testing client
- **`integration_config.py`** - Integration test configuration
- **`integration_markers.py`** - Test markers for categorization

#### `validators/`
Input validation and data verification:
- **`request_validator.py`** - Validates requests before processing

## Other Important Directories

### `docs/`
Contains comprehensive documentation:
- API documentation
- User guides
- Integration guides
- Testing documentation

### `test/`
Mirror structure of `src/` with corresponding test files:
- Unit tests for all modules
- Integration tests
- Test configuration files

### `notebooks/`
Jupyter notebooks for:
- Demonstrations
- Examples
- Interactive tutorials
- Development testing

### `examples/`
Sample files and resources for testing and demonstration purposes.

### `prompts/`
AI prompt templates and configurations for various use cases.

## Architecture Overview

The project follows a modular architecture with clear separation of concerns:

1. **Core Layer** (`llm_manager.py`, `parallel_llm_manager.py`) - Main interfaces
2. **Service Layer** (`bedrock/` modules) - AWS Bedrock integration
3. **Utility Layer** (parsers, validators, serializers) - Support utilities
4. **Data Layer** (models, structures) - Data definitions and constants
5. **Infrastructure Layer** (auth, retry, testing) - Cross-cutting concerns

This structure enables:
- Easy testing and maintenance
- Clear dependency management
- Modular development
- Scalable architecture
- Clean separation between business logic and infrastructure concerns
