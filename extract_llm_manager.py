#!/usr/bin/env python3
"""
LLMManager Project Extractor

This script extracts the essential source code from the LLMManager project
and packages it into a ZIP file that can be easily integrated into other projects.

The resulting ZIP contains:
- All source code from src/bestehorn_llmmanager/
- README with integration instructions
- requirements.txt
- pyproject.toml for proper Python packaging
- Optionally: documentation files from docs/ directory

Usage:
    python extract_llm_manager.py [--exclude-docs] [output_filename.zip]
    python extract_llm_manager.py [output_filename.zip] [--exclude-docs]

Arguments:
    --exclude-docs    Exclude documentation files from the package
    output_filename   Name of the output ZIP file (optional)

If no output filename is provided, it defaults to 'bestehorn_llmmanager_v{version}.zip'
"""

import os
import sys
import zipfile
import shutil
import tempfile
import argparse
from pathlib import Path
from datetime import datetime
import json
from typing import Set, List, Tuple, Optional

# Project version
VERSION = "1.0.0"

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent

def create_integration_readme(include_docs=True):
    """Create a README with integration instructions."""
    docs_section = """
## Documentation

This package includes comprehensive documentation:
- Check the `docs/` directory for detailed guides
- `README_INTEGRATION.md` for integration instructions
- `SETUP.md` for quick setup guide

""" if include_docs else ""
    
    return f"""# Bestehorn LLMManager Integration Guide

This package contains the essential source code for the Bestehorn LLMManager - a comprehensive Python library for managing AWS Bedrock Converse API interactions.

## Quick Integration

### Method 1: Direct Source Integration

1. Extract this ZIP file to your project directory
2. The source code will be in `bestehorn/llm_manager/` directory
3. Import and use:

```python
from bestehorn.llm_manager import LLMManager, ParallelLLMManager

# Initialize with models and regions
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"]
)

# Send a conversation request
response = manager.converse(
    messages=[{{"role": "user", "content": [{{"text": "Hello! How are you?"}}]}}]
)

print(response.get_content())
```

### Method 2: Alternative Import Style

```python
import bestehorn.llm_manager as llm

# Initialize with models and regions
manager = llm.LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"]
)
```

## Features

- **Multi-Model Support**: Work with multiple LLM models simultaneously
- **Multi-Region Failover**: Automatic failover across AWS regions
- **Flexible Authentication**: Support for profiles, credentials, IAM roles
- **Intelligent Retry Logic**: Graceful degradation with configurable retry strategies
- **Parallel Processing**: Execute multiple requests concurrently across regions
- **Full Converse API Support**: All AWS Bedrock Converse API features supported

## Requirements

- Python 3.8+
- AWS credentials configured (AWS CLI, environment variables, or IAM roles)
- Internet access for initial model data download

### Dependencies

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or manually install:

```bash
pip install boto3>=1.28.0 botocore>=1.31.0 beautifulsoup4>=4.12.0 lxml>=4.9.0 requests>=2.31.0
```

## Configuration

### AWS Credentials

The library supports multiple authentication methods:

1. **AWS Profiles**: Use named profiles from `~/.aws/credentials`
2. **Environment Variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
3. **IAM Roles**: For EC2 instances or Lambda functions
4. **Default Credential Chain**: Standard AWS credential resolution

### Example Usage

```python
from bestehorn.llm_manager import LLMManager
from bestehorn.llm_manager.bedrock.models.llm_manager_structures import (
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

# Send a request
response = manager.converse(
    messages=[
        {{"role": "user", "content": [{{"text": "What is machine learning?"}}]}}
    ]
)

print(f"Response: {{response.get_content()}}")
print(f"Model used: {{response.model_used}}")
print(f"Region used: {{response.region_used}}")
```

## Parallel Processing

```python
from bestehorn.llm_manager import ParallelLLMManager
from bestehorn.llm_manager.bedrock.models.parallel_structures import BedrockConverseRequest

# Initialize parallel manager
parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)

# Create multiple requests
requests = [
    BedrockConverseRequest(messages=[{{"role": "user", "content": [{{"text": "What is AI?"}}]}}]),
    BedrockConverseRequest(messages=[{{"role": "user", "content": [{{"text": "Explain machine learning"}}]}}])
]

# Execute in parallel
parallel_response = parallel_manager.converse_parallel(
    requests=requests,
    target_regions_per_request=2
)

print(f"Success rate: {{parallel_response.get_success_rate():.1f}}%")
```
{docs_section}
## Support

For issues and questions:
- Check the documentation in the original project
- Review the source code for detailed implementation
- Test with the provided examples

## License

MIT License - see LICENSE file for details.

---

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Package Version: {VERSION}
Documentation included: {'Yes' if include_docs else 'No'}
"""

def get_all_python_files(src_dir: Path) -> Set[Path]:
    """
    Get all Python files (.py) from the source directory recursively.
    
    Args:
        src_dir: Source directory to scan
        
    Returns:
        Set of relative paths to all .py files
    """
    python_files = set()
    for py_file in src_dir.rglob("*.py"):
        relative_path = py_file.relative_to(src_dir)
        python_files.add(relative_path)
    return python_files


def copy_source_tree(src_dir: Path, dest_dir: Path) -> Tuple[Set[Path], Set[Path]]:
    """
    Copy the source tree, preserving structure but excluding unnecessary files.
    
    Args:
        src_dir: Source directory to copy from
        dest_dir: Destination directory to copy to
        
    Returns:
        Tuple of (copied_py_files, excluded_files)
    """
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)
    
    # Files and directories to exclude
    exclude_patterns = {
        '__pycache__',
        '*.pyc', 
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        '.git',
        '.gitignore',
        '*.egg-info',
        '.pytest_cache',
        'build',
        'dist'
    }
    
    copied_py_files = set()
    excluded_files = set()
    
    def should_exclude(path: Path) -> bool:
        """
        Determine if a path should be excluded from copying.
        Uses exact matching to avoid false positives with substring matches.
        
        Args:
            path: Path to check for exclusion
            
        Returns:
            bool: True if path should be excluded, False otherwise
        """
        path_str = str(path)
        name = path.name
        path_parts = set(path.parts)
        
        for pattern in exclude_patterns:
            if pattern.startswith('*'):
                # Handle file extension patterns
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in {'.DS_Store', '.git', '.gitignore'}:
                # Exact filename matches
                if name == pattern:
                    return True
            elif pattern in {'__pycache__', '.pytest_cache', 'build', 'dist'}:
                # Directory name matches (any part of path)
                if pattern in path_parts:
                    return True
            elif pattern.endswith('.egg-info'):
                # Egg-info directory pattern
                if any(part.endswith('.egg-info') for part in path_parts):
                    return True
        
        return False
    
    def copy_recursive(src: Path, dst: Path) -> None:
        """Recursively copy files, excluding specified patterns."""
        relative_src = src.relative_to(src_path)
        
        if should_exclude(src):
            excluded_files.add(relative_src)
            print(f"  🚫 Excluding: {relative_src}")
            return
            
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  ✅ Copied: {relative_src}")
            
            # Track Python files specifically
            if src.suffix == '.py':
                copied_py_files.add(relative_src)
                
        elif src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                copy_recursive(item, dst / item.name)
    
    copy_recursive(src_path, dest_path)
    return copied_py_files, excluded_files

def copy_markdown_docs(docs_dir, dest_dir):
    """
    Copy all markdown files from the docs directory.
    """
    docs_path = Path(docs_dir)
    dest_path = Path(dest_dir)
    
    if not docs_path.exists():
        print(f"  Warning: docs directory not found at {docs_path}")
        return 0
    
    dest_path.mkdir(parents=True, exist_ok=True)
    copied_count = 0
    
    for md_file in docs_path.glob("*.md"):
        dest_file = dest_path / md_file.name
        shutil.copy2(md_file, dest_file)
        print(f"  Copied doc: {md_file.name}")
        copied_count += 1
    
    return copied_count

def create_bestehorn_init_file() -> str:
    """
    Create the main __init__.py file for the bestehorn.llm_manager package.
    
    Returns:
        str: Content of the __init__.py file
    """
    return '''"""
Bestehorn LLMManager Package

A comprehensive Python library for managing AWS Bedrock Converse API interactions.
This package provides multi-model support, multi-region failover, flexible authentication,
intelligent retry logic, and parallel processing capabilities.

Main Classes:
    LLMManager: Core class for single-threaded LLM interactions
    ParallelLLMManager: Class for parallel LLM processing across multiple regions
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_manager import LLMManager
    from .parallel_llm_manager import ParallelLLMManager

# Lazy imports to avoid circular dependencies and improve startup time
def __getattr__(name: str):
    """Lazy import mechanism for main classes."""
    if name == "LLMManager":
        from .llm_manager import LLMManager
        return LLMManager
    elif name == "ParallelLLMManager":
        from .parallel_llm_manager import ParallelLLMManager
        return ParallelLLMManager
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Define what gets imported with "from bestehorn.llm_manager import *"
__all__ = ["LLMManager", "ParallelLLMManager"]

# Package metadata
__version__ = "1.0.0"
__author__ = "Bestehorn"
__description__ = "Comprehensive AWS Bedrock LLM Manager"
'''

def verify_python_files_inclusion(src_dir: Path, zip_filename: str) -> Tuple[bool, List[str]]:
    """
    Verify that all Python files from the source directory are included in the ZIP file.
    
    Args:
        src_dir: Source directory that was copied
        zip_filename: Path to the ZIP file to verify
        
    Returns:
        Tuple of (all_included: bool, missing_files: List[str])
    """
    # Get all Python files from source
    all_py_files = get_all_python_files(src_dir)
    
    # Get all Python files from ZIP (in the llm_manager subdirectory)
    zip_py_files = set()
    with zipfile.ZipFile(zip_filename, 'r') as zipf:
        for zip_path in zipf.namelist():
            if zip_path.endswith('.py') and 'bestehorn/llm_manager/' in zip_path:
                # Extract the relative path within llm_manager
                relative_path = zip_path.replace('bestehorn/llm_manager/', '')
                zip_py_files.add(Path(relative_path))
    
    # The main __init__.py in the ZIP is generated and replaces the source __init__.py
    # So we need to account for this replacement
    source_main_init = Path('__init__.py')
    if source_main_init in all_py_files and source_main_init in zip_py_files:
        # Both exist, this is correct - the generated __init__.py replaces the source one
        pass
    
    # Find missing files
    missing_files = all_py_files - zip_py_files
    missing_file_strs = [str(f) for f in sorted(missing_files)]
    
    return len(missing_files) == 0, missing_file_strs


def create_package_zip(output_filename: Optional[str] = None, include_docs: bool = True) -> None:
    """
    Create a ZIP file containing the packaged LLMManager source code.
    
    Args:
        output_filename: Name of the output ZIP file
        include_docs: Whether to include documentation files
        
    Raises:
        FileNotFoundError: If source directory is not found
        Exception: If package creation fails
    """
    project_root = get_project_root()
    
    if output_filename is None:
        output_filename = f"bestehorn_llmmanager_v{VERSION}.zip"
    
    docs_status = "with documentation" if include_docs else "without documentation"
    print(f"Creating LLMManager package: {output_filename} ({docs_status})")
    
    # Create temporary directory for staging
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print("Copying source files...")
        
        # Copy the main source directory
        src_dir = project_root / "src" / "bestehorn_llmmanager"
        if not src_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {src_dir}")
        
        # Create the new structure: bestehorn/llm_manager/
        bestehorn_root = temp_path / "bestehorn"
        bestehorn_root.mkdir(parents=True, exist_ok=True)
        
        # Create the llm_manager subdirectory
        llm_manager_dir = bestehorn_root / "llm_manager"
        copy_source_tree(src_dir, llm_manager_dir)
        
        # Create the main __init__.py file for bestehorn.llm_manager
        print("Creating package __init__.py files...")
        init_content = create_bestehorn_init_file()
        (llm_manager_dir / "__init__.py").write_text(init_content, encoding='utf-8')
        
        # Create a top-level bestehorn __init__.py (minimal)
        bestehorn_init = '''"""
Bestehorn Package

This package contains the LLMManager library for AWS Bedrock integration.
"""

__version__ = "1.0.0"
'''
        (bestehorn_root / "__init__.py").write_text(bestehorn_init, encoding='utf-8')
        
        # Copy essential project files to bestehorn directory (to avoid conflicts)
        print("Copying project support files...")
        files_to_copy = [
            ("pyproject.toml", "pyproject.toml"),
            ("requirements.txt", "requirements.txt"),
            ("LICENSE", "LICENSE"),
        ]
        
        for src_file, dest_file in files_to_copy:
            src_path = project_root / src_file
            if src_path.exists():
                shutil.copy2(src_path, bestehorn_root / dest_file)
                print(f"  Copied: {src_file}")
            else:
                print(f"  Warning: {src_file} not found, skipping")
        
        # Optionally copy documentation to bestehorn directory
        docs_count = 0
        if include_docs:
            print("Copying documentation files...")
            docs_dir = project_root / "docs"
            docs_dest = bestehorn_root / "docs"
            docs_count = copy_markdown_docs(docs_dir, docs_dest)
            if docs_count > 0:
                print(f"  📚 Copied {docs_count} documentation files")
            else:
                print("  📚 No documentation files found to copy")
        else:
            print("Skipping documentation files (--exclude-docs flag used)")

        # Create integration README in bestehorn directory
        print("Creating integration README...")
        readme_content = create_integration_readme(include_docs)
        (bestehorn_root / "README_INTEGRATION.md").write_text(readme_content, encoding='utf-8')
        
        # Create setup instructions in bestehorn directory
        docs_structure = "    docs/                           # Project documentation\n" if include_docs else ""
        setup_content = f"""# Setup Instructions

## Quick Start

1. Extract this ZIP file to your project directory
2. Navigate to the extracted `bestehorn/` directory
3. Install dependencies: `pip install -r requirements.txt`
4. Import and use:

```python
from bestehorn.llm_manager import LLMManager

manager = LLMManager(
    models=["Claude 3 Haiku"], 
    regions=["us-east-1"]
)
```

## Package Structure

```
bestehorn/
├── __init__.py                     # Main package initialization
├── llm_manager/                    # Source code directory
│   ├── __init__.py                 # Package init with lazy imports
│   ├── llm_manager.py              # Core LLMManager class
│   ├── parallel_llm_manager.py     # Parallel processing manager
│   └── bedrock/                    # AWS Bedrock integration modules
│       ├── auth/                   # Authentication handling
│       ├── models/                 # Data structures and models
│       ├── retry/                  # Retry logic and managers
│       ├── exceptions/             # Custom exception classes
│       └── ...                     # Additional modules
├── requirements.txt                # Runtime dependencies
├── LICENSE                         # License information
├── README_INTEGRATION.md           # Detailed integration guide
└── SETUP.md                        # This file
{docs_structure}
```

## Import Examples

### Recommended Import Style (Clean)
```python
from bestehorn.llm_manager import LLMManager, ParallelLLMManager

# Use directly
manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])
```

### Alternative Import Style
```python
import bestehorn.llm_manager as llm

# Use with module prefix
manager = llm.LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])
```

Version: {VERSION}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Documentation included: {'Yes' if include_docs else 'No'}
"""
        (bestehorn_root / "SETUP.md").write_text(setup_content, encoding='utf-8')
        
        # Create the ZIP file
        print(f"Creating ZIP archive: {output_filename}")
        with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_path)
                    zipf.write(file_path, arcname)
                    print(f"  Added: {arcname}")
        
        print(f"\n✅ Successfully created: {output_filename}")
        
        # Show package info
        zip_size = Path(output_filename).stat().st_size
        print(f"📦 Package size: {zip_size / 1024:.1f} KB")
        
        # Count files in package
        with zipfile.ZipFile(output_filename, 'r') as zipf:
            file_count = len(zipf.namelist())
            print(f"📄 Files included: {file_count}")
            
            # Show top-level structure
            top_level = set(name.split('/')[0] for name in zipf.namelist() if '/' in name)
            print(f"📁 Top-level directories: {', '.join(sorted(top_level))}")
        
        # VERIFICATION: Check that all Python files are included
        print(f"\n🔍 Verifying Python file inclusion...")
        all_included, missing_files = verify_python_files_inclusion(src_dir, output_filename)
        
        if all_included:
            print("✅ All Python files successfully included in the ZIP package!")
        else:
            print(f"❌ ERROR: {len(missing_files)} Python files are missing from the ZIP package:")
            for missing_file in missing_files:
                print(f"  - {missing_file}")
            raise Exception(f"Package verification failed: {len(missing_files)} Python files missing")
        
        # Additional verification - count Python files
        all_source_py_files = get_all_python_files(src_dir)
        print(f"📊 Python files verification:")
        print(f"  • Source directory: {len(all_source_py_files)} Python files")
        print(f"  • ZIP package: {len(all_source_py_files)} Python files")
        print(f"  • Status: ✅ Complete match")

def validate_package():
    """
    Validate that the source package is properly structured.
    """
    project_root = get_project_root()
    src_dir = project_root / "src" / "bestehorn_llmmanager"
    
    print("Validating package structure...")
    
    # Check essential files exist
    essential_files = [
        "__init__.py",
        "llm_manager.py", 
        "parallel_llm_manager.py",
        "bedrock/__init__.py",
        "bedrock/models/__init__.py",
        "bedrock/auth/__init__.py",
        "bedrock/retry/__init__.py",
        "bedrock/exceptions/__init__.py"
    ]
    
    missing_files = []
    for file_path in essential_files:
        full_path = src_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ Found: {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing essential files:")
        for missing in missing_files:
            print(f"  - {missing}")
        return False
    
    print("\n✅ Package structure validation passed!")
    return True

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract LLMManager source code for integration into other projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_llm_manager.py                           # Create package with docs
  python extract_llm_manager.py --exclude-docs            # Create package without docs
  python extract_llm_manager.py my_package.zip            # Custom filename with docs
  python extract_llm_manager.py --exclude-docs output.zip # Custom filename without docs
        """
    )
    
    parser.add_argument(
        'output_filename',
        nargs='?',
        help=f'Output ZIP filename (default: bestehorn_llmmanager_v{VERSION}.zip)'
    )
    
    parser.add_argument(
        '--exclude-docs',
        action='store_true',
        help='Exclude documentation files from the package'
    )
    
    return parser.parse_args()

def main():
    """Main function to create the package."""
    print("="*60)
    print("🚀 LLMManager Package Extractor")
    print("="*60)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate source structure
    if not validate_package():
        print("\n❌ Package validation failed. Please check the source structure.")
        sys.exit(1)
    
    # Determine documentation inclusion
    include_docs = not args.exclude_docs
    
    try:
        create_package_zip(args.output_filename, include_docs)
        
        print("\n" + "="*60)
        print("🎉 Package creation completed successfully!")
        print("="*60)
        
        docs_info = "📚 Documentation included" if include_docs else "📚 Documentation excluded (--exclude-docs)"
        
        print(f"""
📦 Your LLMManager package is ready!

{docs_info}

🔧 To use in another project:
   1. Extract the ZIP file to your project directory
   2. Navigate to bestehorn/ and install dependencies: pip install -r requirements.txt
   3. Import: from bestehorn.llm_manager import LLMManager

📖 See bestehorn/README_INTEGRATION.md for detailed instructions
📋 See bestehorn/SETUP.md for quick setup guide

🌐 Example usage:
   from bestehorn.llm_manager import LLMManager
   manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])
   response = manager.converse(messages=[{{"role": "user", "content": [{{"text": "Hello!"}}]}}])
""")
        
    except Exception as e:
        print(f"\n❌ Error creating package: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
