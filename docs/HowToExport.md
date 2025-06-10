# How to Export LLMManager Package

This document describes how to extract and package the LLMManager components for use in other projects.

## Overview

The LLMManager project includes an extraction mechanism that creates a distributable ZIP file containing all the essential components needed to use LLMManager in other projects. This allows you to integrate LLMManager functionality without needing to publish it as a formal Python package.

## What Gets Extracted

The extraction process includes:

### Included Components
- **Core Modules**: `LLMManager.py` and `ParallelLLMManager.py`
- **Bedrock Package**: Complete `src/bedrock/` directory with all submodules
- **Supporting Files**: LICENSE file (if present)
- **Package Metadata**: Generated `__init__.py` and `README.md` files

### Excluded Components
- Test files (`test/` directory)
- Development notebooks (`notebooks/` directory)
- Documentation (`docs/` directory)
- Workspace files (`workspace/` directory)
- Examples and images
- Configuration files like `pytest.ini`, `requirements-test.txt`

## Package Structure

The extracted package creates the following structure:

```
bestehorn/
├── __init__.py              # Generated package initialization
├── README.md                # Generated usage documentation
├── LLMManager.py            # Main LLM manager class
├── ParallelLLMManager.py    # Parallel processing manager
└── bedrock/                 # Complete bedrock module
    ├── __init__.py
    ├── UnifiedModelManager.py
    ├── auth/
    ├── models/
    ├── parsers/
    ├── retry/
    └── [all other bedrock submodules]
```

## Usage Instructions

### 1. Basic Extraction

Run the extraction script from the project root:

```bash
python extract_llm_manager.py
```

This creates `dist/bestehorn-llmmanager-v1.0.0.zip` with default settings.

### 2. Custom Package Name and Version

```bash
python extract_llm_manager.py --package-name mypackage --version 2.1.0
```

### 3. Custom Output Directory

```bash
python extract_llm_manager.py --output-dir /path/to/output
```

### 4. Keep Temporary Files (for debugging)

```bash
python extract_llm_manager.py --no-cleanup
```

### 5. Validate Environment Only

```bash
python extract_llm_manager.py --validate-only
```

### 6. Enable Debug Logging

```bash
python extract_llm_manager.py --log-level DEBUG
```

## Using the Extracted Package

### 1. Extract to Target Project

```bash
cd /path/to/your/project
unzip bestehorn-llmmanager-v1.0.0.zip
```

### 2. Import and Use

```python
# Import the main classes
from bestehorn import LLMManager, ParallelLLMManager

# Basic usage
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"]
)

response = manager.converse(
    messages=[{"role": "user", "content": [{"text": "Hello!"}]}]
)

print(response.get_content())

# Parallel processing
parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)

# Create multiple requests
from bestehorn.bedrock.models.parallel_structures import BedrockConverseRequest

requests = [
    BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hello"}]}]),
    BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "How are you?"}]}])
]

parallel_response = parallel_manager.converse_parallel(requests=requests)
```

## Requirements

The extracted package requires:
- Python 3.8+
- boto3 (AWS SDK)
- Properly configured AWS credentials

## Technical Details

### Extraction Process

The extraction system follows a modular architecture:

1. **Source Validation** (`source_validator.py`):
   - Validates project structure
   - Identifies extractable files
   - Ensures all required components are present

2. **File Management** (`file_manager.py`):
   - Handles file copying operations
   - Creates directory structures
   - Manages path transformations

3. **Package Generation** (`package_generator.py`):
   - Creates package metadata files
   - Generates `__init__.py` with proper imports
   - Creates usage documentation

4. **ZIP Creation** (`zip_manager.py`):
   - Creates compressed distribution archives
   - Validates ZIP file integrity
   - Provides compression statistics

5. **Main Orchestrator** (`llm_manager_extractor.py`):
   - Coordinates the entire extraction process
   - Handles error management
   - Provides progress reporting

### Import Compatibility

The source code uses relative imports throughout to ensure portability:
- All imports within the `src/` directory use relative import syntax (e.g., `from .bedrock.auth.auth_manager import AuthManager`)
- This ensures the extracted package works correctly in any target project structure
- The package structure maintains the same relationships as the source
- No additional code modifications are required during extraction

### Version Management

The extraction script supports semantic versioning:
- Version string is embedded in the package metadata
- ZIP file names include version information
- Package `__init__.py` includes version information

## Error Handling

The extraction script provides comprehensive error handling:

### Common Issues and Solutions

1. **Source Validation Errors**:
   - Ensure you're running from the LLMManager project root
   - Verify all required files are present in `src/`

2. **Permission Errors**:
   - Check write permissions for the output directory
   - Ensure sufficient disk space

3. **Import Errors in Target Project**:
   - Verify the package was extracted to the correct location
   - Check Python path includes the extraction directory
   - Ensure all required dependencies are installed

### Debug Mode

Use `--log-level DEBUG` for detailed extraction information:

```bash
python extract_llm_manager.py --log-level DEBUG --no-cleanup
```

This provides:
- Detailed file operation logs
- Timing information for each step
- Validation details
- Temporary file locations (when using `--no-cleanup`)

## Best Practices

### For Distribution
1. Always validate the extraction environment first
2. Use semantic versioning for different releases
3. Test the extracted package in a separate environment
4. Include the generated README.md with distribution

### For Integration
1. Extract to a dedicated subdirectory in your project
2. Add the package directory to your project's `.gitignore` if appropriate
3. Document the LLMManager dependency in your project documentation
4. Pin to specific versions for production use

## Automation

The extraction script can be integrated into build processes:

```bash
#!/bin/bash
# Build script example

# Extract LLMManager package
python extract_llm_manager.py --version $(git describe --tags) --output-dir build/

# Continue with your build process...
```

## Support

For issues with the extraction process:
1. Run with `--validate-only` to check environment
2. Use `--log-level DEBUG` for detailed diagnostics
3. Check the generated logs in the console output
4. Verify all requirements are met as documented above

The extraction mechanism is designed to be robust and provide clear error messages for troubleshooting.
