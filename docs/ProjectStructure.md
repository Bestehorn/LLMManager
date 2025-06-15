# LLMManager Project Structure

This document describes the complete project structure for the Bestehorn LLMManager library, including all directories and key files.

## Project Root Structure

```
LLMManager/
├── src/                          # Source code directory
├── test/                         # Test directory
├── docs/                         # Documentation directory
├── examples/                     # Example files and assets
├── notebooks/                    # Jupyter notebooks for demonstrations
├── prompts/                      # Prompt templates and configurations
├── images/                       # Image assets for testing and examples
├── videos/                       # Video assets for testing and examples
├── api/                          # API related files
├── workspace/                    # Working directory
├── requirements.txt              # Production dependencies
├── requirements-test.txt         # Test dependencies
├── pyproject.toml               # Python project configuration
├── pytest.ini                  # Pytest configuration
├── LICENSE                      # License file
├── README.md                    # Main project README
├── run_tests.bat               # Windows test runner script
├── run_tests.py                # Python test runner script
├── extract_llm_manager.py      # Utility script for extraction
└── .gitallowed                 # Git allowed files configuration
```

## Source Code Structure (`src/`)

The main source code is organized under `src/bestehorn_llmmanager/` following Python packaging conventions.

### Core Package Structure

```
src/bestehorn_llmmanager/
├── __init__.py                      # Package initialization and exports
├── llm_manager.py                   # Core LLMManager class
├── parallel_llm_manager.py          # Parallel processing manager
├── message_builder.py               # Consolidated MessageBuilder (NEW)
├── message_builder_enums.py         # MessageBuilder enums (NEW)
├── message_builder_constants.py     # MessageBuilder constants (NEW)
├── bedrock/                         # AWS Bedrock specific implementations
└── util/                            # Utility modules (NEW)
```

### Bedrock Implementation (`src/bestehorn_llmmanager/bedrock/`)

The bedrock directory contains all AWS Bedrock-specific implementations:

```
bedrock/
├── __init__.py                      # Bedrock package initialization
├── CRISManager.py                   # CRIS (Cross-Region Intelligence Service) manager
├── ModelManager.py                  # Individual model management
├── UnifiedModelManager.py           # Unified model management interface
├── adapters/                        # Protocol adapters
├── auth/                           # Authentication modules
├── correlators/                    # Model correlation services
├── distributors/                   # Region distribution logic
├── downloaders/                    # Content downloading utilities
├── exceptions/                     # Bedrock-specific exceptions
├── executors/                      # Execution engines
├── filters/                        # Content filtering
├── models/                         # Data models and structures
├── parsers/                        # Response parsers
├── retry/                          # Retry logic
├── serializers/                    # Data serialization
├── testing/                        # Testing utilities
└── validators/                     # Request validation
```

### Authentication (`src/bestehorn_llmmanager/bedrock/auth/`)

```
auth/
├── __init__.py                      # Auth package initialization
└── auth_manager.py                  # AWS authentication management
```

### Correlators (`src/bestehorn_llmmanager/bedrock/correlators/`)

```
correlators/
├── __init__.py                      # Correlators package initialization
└── model_cris_correlator.py        # Model-CRIS correlation logic
```

### Distributors (`src/bestehorn_llmmanager/bedrock/distributors/`)

```
distributors/
├── __init__.py                      # Distributors package initialization
└── region_distribution_manager.py   # Region distribution management
```

### Downloaders (`src/bestehorn_llmmanager/bedrock/downloaders/`)

```
downloaders/
├── __init__.py                      # Downloaders package initialization
├── base_downloader.py              # Base downloader interface
└── html_downloader.py              # HTML content downloader
```

### Exceptions (`src/bestehorn_llmmanager/bedrock/exceptions/`)

```
exceptions/
├── __init__.py                      # Exceptions package initialization
├── llm_manager_exceptions.py       # Core LLM manager exceptions
└── parallel_exceptions.py          # Parallel processing exceptions
```

### Executors (`src/bestehorn_llmmanager/bedrock/executors/`)

```
executors/
├── __init__.py                      # Executors package initialization
├── parallel_executor.py            # Base parallel execution
└── thread_parallel_executor.py     # Thread-based parallel execution
```

### Filters (`src/bestehorn_llmmanager/bedrock/filters/`)

```
filters/
├── __init__.py                      # Filters package initialization
└── content_filter.py              # Content filtering logic
```

### Models (`src/bestehorn_llmmanager/bedrock/models/`)

```
models/
├── __init__.py                      # Models package initialization
├── access_method.py                # Access method definitions
├── aws_regions.py                  # AWS region configurations
├── bedrock_response.py             # Bedrock response models
├── constants.py                    # General constants
├── cris_constants.py               # CRIS-specific constants
├── cris_regional_structures.py     # CRIS regional data structures
├── cris_structures.py              # CRIS data structures
├── data_structures.py              # General data structures
├── llm_manager_constants.py        # LLM manager constants
├── llm_manager_structures.py       # LLM manager data structures
├── parallel_constants.py           # Parallel processing constants
├── parallel_structures.py          # Parallel processing data structures
├── unified_constants.py            # Unified manager constants
└── unified_structures.py           # Unified manager data structures
```

**Note**: The original MessageBuilder components and file type detector have been moved to the package root and util directories respectively for better organization and to eliminate duplication.

### Parsers (`src/bestehorn_llmmanager/bedrock/parsers/`)

```
parsers/
├── __init__.py                      # Parsers package initialization
├── base_parser.py                  # Base parser interface
├── bedrock_parser.py               # Bedrock response parser
├── cris_parser.py                  # CRIS response parser
└── enhanced_bedrock_parser.py      # Enhanced Bedrock parser
```

### Retry (`src/bestehorn_llmmanager/bedrock/retry/`)

```
retry/
├── __init__.py                      # Retry package initialization
└── retry_manager.py                # Retry logic management
```

### Serializers (`src/bestehorn_llmmanager/bedrock/serializers/`)

```
serializers/
├── __init__.py                      # Serializers package initialization
└── json_serializer.py             # JSON serialization utilities
```

### Testing (`src/bestehorn_llmmanager/bedrock/testing/`)

```
testing/
├── __init__.py                      # Testing package initialization
├── aws_test_client.py              # AWS test client
├── integration_config.py           # Integration test configuration
└── integration_markers.py          # Pytest markers for integration tests
```

### Validators (`src/bestehorn_llmmanager/bedrock/validators/`)

```
validators/
├── __init__.py                      # Validators package initialization
└── request_validator.py            # Request validation logic
```

### Utility Modules (`src/bestehorn_llmmanager/util/`) - NEW

The util directory contains utility modules that can be used across the entire package:

```
util/
├── __init__.py                      # Util package initialization
└── file_type_detector/             # File type detection utilities
```

### File Type Detector (`src/bestehorn_llmmanager/util/file_type_detector/`) - NEW

This is the new consolidated location for file type detection functionality:

```
file_type_detector/
├── __init__.py                      # File type detector package initialization
├── base_detector.py                # Base detector interface and data structures
└── file_type_detector.py          # Main file type detector implementation
```

## Test Structure (`test/`)

The test directory mirrors the source structure:

```
test/
├── bestehorn_llmmanager/            # Main test package
├── integration/                     # Integration tests
└── __init__.py files throughout     # Test package initialization
```

### Main Test Package Structure

```
test/bestehorn_llmmanager/
├── __init__.py                      # Test package initialization
├── conftest.py                     # Pytest configuration and fixtures
├── test_LLMManager.py              # Core LLMManager tests
├── test_ParallelLLMManager.py      # Parallel manager tests
├── test_message_builder.py         # MessageBuilder tests (NEW)
├── bedrock/                        # Bedrock-specific tests
└── util/                           # Utility module tests (NEW)
```

### Bedrock Test Structure

```
test/bestehorn_llmmanager/bedrock/
├── __init__.py                      # Bedrock test package initialization
├── test_CRISManager.py             # CRIS manager tests
├── test_ModelManager.py            # Model manager tests
├── test_UnifiedModelManager.py     # Unified manager tests
├── test_UnifiedModelManager_*.py   # Additional unified manager test variations
├── auth/                           # Authentication tests
├── correlators/                    # Correlator tests
├── downloaders/                    # Downloader tests
├── exceptions/                     # Exception tests
├── executors/                      # Executor tests
├── filters/                        # Filter tests
├── models/                         # Model tests
├── parsers/                        # Parser tests
├── retry/                          # Retry tests
├── serializers/                    # Serializer tests
└── testing/                        # Testing utility tests
```

### Utility Tests (`test/bestehorn_llmmanager/util/`) - NEW

```
util/
├── __init__.py                      # Util test package initialization
└── file_type_detector/             # File type detector tests
```

### File Type Detector Tests (`test/bestehorn_llmmanager/util/file_type_detector/`) - NEW

```
file_type_detector/
├── __init__.py                      # File type detector test package initialization
└── test_base_detector.py          # Base detector tests
```

### Integration Tests

```
test/integration/
├── __init__.py                      # Integration test package initialization
├── test_integration_auth.py        # Authentication integration tests
├── test_integration_bedrock_api.py # Bedrock API integration tests
├── test_integration_llm_manager.py # LLM manager integration tests
└── test_integration_unified_model_manager.py # Unified manager integration tests
```

## Documentation Structure (`docs/`)

```
docs/
├── README.md                        # Documentation index
├── Authentication_Documentation.md  # Authentication guide
├── CRIS_JSON_Format.md             # CRIS JSON format specification
├── CRISManager_Documentation.md     # CRIS manager documentation
├── HowToExport.md                  # Export guide
├── INTEGRATION_TESTING.md          # Integration testing guide
├── LLMManager_Documentation.md     # Core LLM manager documentation
├── MessageBuilder.md               # MessageBuilder documentation
├── ModelManager_Documentation.md   # Model manager documentation
├── ParallelLLMManager_Documentation.md # Parallel manager documentation
├── RetryManager_Documentation.md   # Retry manager documentation
├── TESTING.md                      # Testing guide
├── UnifiedModelManager_Documentation.md # Unified manager documentation
└── forLLMConsumption.md            # LLM-specific documentation
```

## Examples and Assets

### Examples Directory (`examples/`)

```
examples/
├── The Eiffel Tower Press Kit - July 2024.pdf  # Example PDF document
└── TheEiffelTowerPressKit-July2024.pdf        # Alternative PDF document
```

### Images Directory (`images/`)

```
images/
├── 1200px-Tour_Eiffel_Wikimedia_Commons_(cropped).jpg  # Example image
└── Tokyo_Tower_2023.jpg                                # Example image
```

### Videos Directory (`videos/`)

```
videos/
└── EiffelTower.mp4                  # Example video file
```

## Notebooks Directory (`notebooks/`)

```
notebooks/
├── CRISManager.ipynb               # CRIS manager demonstration
├── HelloWorld_LLMManager.ipynb     # LLM manager introduction
├── HelloWorld_MessageBuilder.ipynb # MessageBuilder introduction
├── HelloWorld_MessageBuilder_Demo.ipynb # MessageBuilder demo
├── HelloWorld_MessageBuilder_Paths.ipynb # MessageBuilder path handling
├── ModelIDManager.ipynb            # Model ID manager demonstration
├── ParallelLLMManager_Demo.ipynb   # Parallel manager demo
├── ResponseValidation.ipynb        # Response validation examples
├── UnifiedModelManager.ipynb       # Unified manager demonstration
├── docs/                           # Notebook documentation
└── src/                            # Notebook source helpers
```

## Prompts Directory (`prompts/`)

```
prompts/
├── CodingStandards.txt             # Coding standards template
├── CRISParser.txt                  # CRIS parser prompt
├── FixTests.txt                    # Test fixing prompt
├── FoundationalModelParser.txt     # Foundational model parser prompt
├── InitialPrompt.txt               # Initial setup prompt
├── PromptBuilder.txt               # Prompt building template
└── TestCoverage.txt                # Test coverage prompt
```

## Key Design Principles

### 1. Modular Architecture
The project is organized into logical modules with clear separation of concerns:
- **Core managers** handle primary functionality
- **Bedrock-specific** implementations are isolated in the bedrock directory
- **Utilities** provide reusable functionality
- **Testing** mirrors the source structure

### 2. Consolidated Components
Recent refactoring has consolidated related functionality:
- **MessageBuilder** components moved from `bedrock/models/` to package root
- **File type detection** moved from `bedrock/models/` to `util/`
- **Enums and constants** consolidated to reduce duplication

### 3. Clear Separation of Concerns
- **Authentication** handled separately from core logic
- **Region distribution** managed independently
- **Content filtering** isolated for security
- **Error handling** centralized in exceptions

### 4. Comprehensive Testing
- **Unit tests** for all components
- **Integration tests** for end-to-end functionality
- **Test utilities** for common testing scenarios
- **Pytest configuration** for consistent testing

### 5. Documentation-Driven Development
- Comprehensive documentation for all components
- Example notebooks for learning and demonstration
- Clear API documentation
- Usage guides and best practices

## Import Paths

### Primary Imports
```python
from bestehorn_llmmanager import LLMManager, ParallelLLMManager
from bestehorn_llmmanager import MessageBuilder, create_user_message
from bestehorn_llmmanager import RolesEnum, ImageFormatEnum, DocumentFormatEnum
```

### Internal Imports
```python
from bestehorn_llmmanager.bedrock.auth import AuthManager
from bestehorn_llmmanager.bedrock.exceptions import RequestValidationError
from bestehorn_llmmanager.util.file_type_detector import FileTypeDetector
```

## Dependencies

### Core Dependencies (requirements.txt)
- AWS SDK components
- HTTP libraries
- JSON processing
- Logging utilities

### Test Dependencies (requirements-test.txt)
- pytest and plugins
- mock libraries
- coverage tools
- test utilities

This project structure provides a comprehensive, well-organized codebase that supports the development, testing, and maintenance of the LLMManager library while ensuring clear separation of concerns and easy extensibility.
