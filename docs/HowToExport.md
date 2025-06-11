# How to Export LLMManager for Use in Other Projects

This document explains how to extract the LLMManager source code for integration into other projects.

## Overview

The `extract_llm_manager.py` script packages the essential LLMManager source code into a ZIP file that can be easily integrated into other projects. This allows you to use the LLMManager library in other projects without publishing it as a formal Python package.

## Usage

### Basic Usage

```bash
python extract_llm_manager.py
```

This creates `bestehorn_llmmanager_v1.0.0.zip` with the packaged source code **including documentation**.

### Exclude Documentation

```bash
python extract_llm_manager.py --exclude-docs
```

This creates the package **without** documentation files (smaller, source-only package).

### Custom Output Filename

```bash
python extract_llm_manager.py my_custom_package.zip            # With docs
python extract_llm_manager.py --exclude-docs my_package.zip   # Without docs
```

### Help

```bash
python extract_llm_manager.py --help
```

## What Gets Packaged

The extraction script includes:

### Source Code
- **All files from `src/bestehorn_llmmanager/`** - Complete source tree
- **Renamed to `bestehorn/`** - As requested for proper import structure

### Documentation (Optional)
- **README_INTEGRATION.md** - Comprehensive integration guide
- **SETUP.md** - Quick setup instructions
- **docs/** - All Markdown documentation from the project (unless `--exclude-docs` is used)

### Project Files
- **requirements.txt** - Runtime dependencies
- **pyproject.toml** - Python package configuration  
- **LICENSE** - License information

### Exclusions
- Test files and test directories
- Integration tests  
- Prompts (unless in docs/)
- Build artifacts and cache files
- Git metadata
- Documentation files (if `--exclude-docs` flag is used)

## Package Structure

After extraction, the ZIP contains:

```
bestehorn/                          # Main source directory
├── __init__.py                     # Package initialization
├── llm_manager.py                  # Core LLMManager class
├── parallel_llm_manager.py         # Parallel processing manager
└── bedrock/                        # AWS Bedrock integration
    ├── auth/                       # Authentication handling
    ├── models/                     # Data structures
    ├── retry/                      # Retry logic
    ├── exceptions/                 # Custom exceptions
    └── ...                         # Additional modules

README_INTEGRATION.md               # Integration documentation
SETUP.md                           # Quick setup guide
requirements.txt                   # Dependencies
pyproject.toml                     # Package configuration
LICENSE                            # License
```

## Integration in Other Projects

### Step 1: Extract Package

Extract the ZIP file to your target project directory:

```bash
unzip bestehorn_llmmanager_final.zip
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Import and Use

Use the import structure as requested:

```python
import bestehorn.llm_manager as LLMManager

# Initialize LLM Manager
manager = LLMManager.LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"]
)

# Send conversation request
response = manager.converse(
    messages=[{"role": "user", "content": [{"text": "Hello!"}]}]
)

print(response.get_content())
```

Alternative import styles:

```python
from bestehorn.llm_manager import LLMManager
from bestehorn.parallel_llm_manager import ParallelLLMManager
```

## Validation

The extraction script includes validation to ensure:

- All essential source files are present
- Package structure is correct
- Dependencies are included
- Documentation is generated

## Package Information

- **Size**: ~140 KB compressed
- **Files**: ~60 source files
- **Version**: 1.0.0
- **Python Requirements**: 3.8+

## Features Preserved

The extracted package retains all LLMManager features:

- ✅ Multi-model support
- ✅ Multi-region failover
- ✅ Flexible authentication
- ✅ Intelligent retry logic
- ✅ Parallel processing capabilities
- ✅ Full AWS Bedrock Converse API support

## Notes

- **No Code Changes**: The original project code remains unchanged
- **Standalone**: The extracted package is self-contained
- **Production Ready**: All essential functionality is preserved
- **Easy Integration**: Simple import structure for immediate use

## Troubleshooting

### Import Errors
- Ensure the `bestehorn/` directory is in your Python path
- Check that all dependencies are installed
- Verify AWS credentials are configured

### Missing Dependencies
- Run `pip install -r requirements.txt` in the extracted directory
- Check Python version compatibility (3.8+)

### AWS Authentication Issues
- Configure AWS CLI: `aws configure`
- Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Use IAM roles for EC2/Lambda environments

## Examples

See the extracted `README_INTEGRATION.md` for comprehensive examples including:
- Basic conversation requests
- Authentication configuration
- Parallel processing
- Error handling
- Advanced configurations

---

*Generated by extract_llm_manager.py - Version 1.0.0*
