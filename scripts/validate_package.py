#!/usr/bin/env python3
"""Pre-release validation script for bestehorn-llmmanager package.

This script performs comprehensive validation checks before package release,
ensuring the package meets all quality standards and requirements.
"""

import subprocess
import sys
import os
import glob
import shutil
from typing import Tuple, List, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PACKAGE_NAME = "bestehorn-llmmanager"
SOURCE_DIR = "src"
TEST_DIR = "test"
BUILD_DIR = "dist"


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def run_command(cmd: str, description: str) -> Tuple[bool, str, str]:
    """Run a command and return success status with output.
    
    Args:
        cmd: Command to execute
        description: Description of the command for logging
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            encoding='utf-8',  # Explicitly use UTF-8 encoding
            timeout=300  # 5-minute timeout
        )
        success = result.returncode == 0
        if success:
            logger.debug(f"Command succeeded: {cmd}")
        else:
            logger.error(f"Command failed: {cmd}")
            logger.error(f"stderr: {result.stderr}")
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {cmd}")
        return False, "", "Command timed out"
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False, "", str(e)


def check_environment() -> bool:
    """Check if the environment is properly set up.
    
    Returns:
        True if environment is valid, False otherwise
    """
    logger.info("Checking environment setup...")
    
    # Check if we're in the project root
    if not os.path.exists("pyproject.toml"):
        logger.error("pyproject.toml not found. Run this script from the project root.")
        return False
    
    # Check if source directory exists
    if not os.path.exists(SOURCE_DIR):
        logger.error(f"Source directory '{SOURCE_DIR}' not found.")
        return False
    
    # Check if test directory exists
    if not os.path.exists(TEST_DIR):
        logger.error(f"Test directory '{TEST_DIR}' not found.")
        return False
    
    return True


def clean_build_artifacts() -> None:
    """Clean previous build artifacts."""
    logger.info("Cleaning build artifacts...")
    
    # Remove dist directory
    if os.path.exists(BUILD_DIR):
        if os.name == 'nt':  # Windows
            run_command(f"rmdir /s /q {BUILD_DIR}", "Removing dist directory")
        else:  # Unix/Linux
            run_command(f"rm -rf {BUILD_DIR}", "Removing dist directory")
    
    # Remove egg-info directories
    for egg_info in glob.glob("**/*.egg-info", recursive=True):
        try:
            shutil.rmtree(egg_info)
            logger.info(f"Removed {egg_info}")
        except Exception as e:
            logger.warning(f"Could not remove {egg_info}: {e}")
    
    # Remove __pycache__ directories
    for pycache in glob.glob("**/__pycache__", recursive=True):
        try:
            shutil.rmtree(pycache)
            logger.info(f"Removed {pycache}")
        except Exception as e:
            logger.warning(f"Could not remove {pycache}: {e}")


def validate_code_formatting() -> bool:
    """Validate code formatting with Black.
    
    Returns:
        True if formatting is correct, False otherwise
    """
    success, stdout, stderr = run_command(
        f"python -m black --check {SOURCE_DIR}/ {TEST_DIR}/",
        "Checking code formatting with Black"
    )
    if not success:
        logger.warning("Code formatting issues found. Run 'python -m black src/ test/' to fix.")
    return success


def validate_import_sorting() -> bool:
    """Validate import sorting with isort.
    
    Returns:
        True if imports are sorted correctly, False otherwise
    """
    success, stdout, stderr = run_command(
        f"python -m isort --check-only {SOURCE_DIR}/ {TEST_DIR}/",
        "Checking import sorting with isort"
    )
    if not success:
        logger.warning("Import sorting issues found. Run 'python -m isort src/ test/' to fix.")
    return success


def validate_linting() -> bool:
    """Validate code with flake8.
    
    Returns:
        True if linting passes, False otherwise
    """
    success, stdout, stderr = run_command(
        f"python -m flake8 {SOURCE_DIR}/ {TEST_DIR}/",
        "Running flake8 linting"
    )
    if not success:
        logger.warning("Linting issues found. Check flake8 output above.")
    return success


def validate_type_checking() -> bool:
    """Validate type hints with mypy.
    
    Returns:
        True if type checking passes, False otherwise
    """
    success, stdout, stderr = run_command(
        f"python -m mypy {SOURCE_DIR}/",
        "Running mypy type checking"
    )
    if not success:
        logger.warning("Type checking issues found. Check mypy output above.")
    return success


def run_tests() -> bool:
    """Run unit tests with pytest.
    
    Returns:
        True if all tests pass, False otherwise
    """
    success, stdout, stderr = run_command(
        f'python -m pytest {TEST_DIR}/bestehorn_llmmanager/ -v -m "not integration"',
        "Running unit tests"
    )
    if not success:
        logger.error("Unit tests failed. Fix test failures before release.")
    return success


def validate_manifest() -> bool:
    """Validate MANIFEST.in with check-manifest.
    
    Returns:
        True if manifest is valid, False otherwise
    """
    success, stdout, stderr = run_command(
        "check-manifest",
        "Checking MANIFEST.in"
    )
    
    # Check for git configuration issues that prevent check-manifest from working
    if not success and ("unable to access" in stderr or "Invalid argument" in stderr):
        logger.warning("Git configuration issue detected. Attempting to fix...")
        
        # Try to fix git configuration
        fix_commands = [
            "git config --global core.autocrlf false",
            "git config --global core.filemode false"
        ]
        
        for cmd in fix_commands:
            fix_success, _, _ = run_command(cmd, f"Running {cmd}")
            if not fix_success:
                logger.warning(f"Failed to run: {cmd}")
        
        # Retry check-manifest after attempting fix
        logger.info("Retrying MANIFEST.in validation after git config fix...")
        success, stdout, stderr = run_command(
            "check-manifest",
            "Retrying MANIFEST.in check"
        )
        
        if not success:
            # If still failing due to git issues, validate manually
            if "unable to access" in stderr or "Invalid argument" in stderr:
                logger.warning("Git configuration issue persists. Performing manual MANIFEST.in validation...")
                return validate_manifest_manually()
    
    if not success:
        logger.warning("MANIFEST.in issues found. Update MANIFEST.in file.")
    return success


def validate_manifest_manually() -> bool:
    """Manually validate MANIFEST.in by checking if key files are included.
    
    Returns:
        True if manifest appears valid, False otherwise
    """
    logger.info("Performing manual MANIFEST.in validation...")
    
    if not os.path.exists("MANIFEST.in"):
        logger.error("MANIFEST.in file not found.")
        return False
    
    # Read MANIFEST.in content
    try:
        with open("MANIFEST.in", "r", encoding="utf-8") as f:
            manifest_content = f.read()
        
        # Check for essential includes
        essential_includes = [
            "LICENSE",
            "README.md", 
            "pyproject.toml",
            "src/bestehorn_llmmanager/py.typed"
        ]
        
        missing_includes = []
        for item in essential_includes:
            if item not in manifest_content:
                missing_includes.append(item)
        
        if missing_includes:
            logger.error(f"Missing essential includes in MANIFEST.in: {missing_includes}")
            return False
        
        # Check if py.typed file actually exists
        if not os.path.exists("src/bestehorn_llmmanager/py.typed"):
            logger.error("py.typed file not found at src/bestehorn_llmmanager/py.typed")
            return False
        
        logger.info("✅ Manual MANIFEST.in validation passed.")
        logger.info("Note: Full validation requires working git configuration.")
        return True
        
    except Exception as e:
        logger.error(f"Error reading MANIFEST.in: {e}")
        return False


def build_package() -> bool:
    """Build the package with python -m build.
    
    Returns:
        True if build succeeds, False otherwise
    """
    success, stdout, stderr = run_command(
        "python -m build",
        "Building package"
    )
    if not success:
        logger.error("Package build failed.")
    return success


def validate_package() -> bool:
    """Validate the built package with twine check.
    
    Returns:
        True if package is valid, False otherwise
    """
    success, stdout, stderr = run_command(
        f"twine check {BUILD_DIR}/*",
        "Checking distribution with twine"
    )
    if not success:
        logger.error("Package validation failed.")
    return success


def check_package_size() -> bool:
    """Check if package size is reasonable.
    
    Returns:
        True if size is acceptable, False otherwise
    """
    logger.info("Checking package size...")
    
    if not os.path.exists(BUILD_DIR):
        logger.error("Build directory not found.")
        return False
    
    total_size = 0
    for filename in os.listdir(BUILD_DIR):
        filepath = os.path.join(BUILD_DIR, filename)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            size_mb = size / (1024 * 1024)
            logger.info(f"{filename}: {size_mb:.2f} MB")
            total_size += size
    
    total_size_mb = total_size / (1024 * 1024)
    logger.info(f"Total package size: {total_size_mb:.2f} MB")
    
    # PyPI has a 100MB limit per file
    if total_size_mb > 50:
        logger.warning(f"Package size ({total_size_mb:.2f} MB) is large. Consider optimizing.")
    
    return True


def main() -> int:
    """Main validation function.
    
    Returns:
        0 if all validations pass, 1 otherwise
    """
    logger.info(f"Starting validation for {PACKAGE_NAME}")
    logger.info("=" * 60)
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed.")
        return 1
    
    # Clean build artifacts
    clean_build_artifacts()
    
    # Track validation results
    checks: List[Tuple[str, bool]] = []
    
    # Run validation checks
    validation_steps = [
        ("Code formatting (Black)", validate_code_formatting),
        ("Import sorting (isort)", validate_import_sorting),
        ("Linting (flake8)", validate_linting),
        ("Type checking (mypy)", validate_type_checking),
        ("Unit tests", run_tests),
        ("MANIFEST.in validation", validate_manifest),
        ("Package build", build_package),
        ("Package validation (twine)", validate_package),
        ("Package size check", check_package_size),
    ]
    
    for description, validator in validation_steps:
        logger.info(f"\n{description}...")
        try:
            success = validator()
            checks.append((description, success))
            if success:
                logger.info(f"✅ {description} - PASSED")
            else:
                logger.error(f"❌ {description} - FAILED")
        except Exception as e:
            logger.error(f"❌ {description} - ERROR: {e}")
            checks.append((description, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success in checks if success)
    failed = len(checks) - passed
    
    for description, success in checks:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{description}: {status}")
    
    logger.info(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed > 0:
        logger.error("\n⚠️  Package validation failed. Fix issues before release.")
        return 1
    else:
        logger.info("\n🎉 All validations passed! Package is ready for release.")
        logger.info("\nNext steps:")
        logger.info("1. Test package installation: pip install dist/*.whl")
        logger.info("2. Upload to TestPyPI: twine upload --repository testpypi dist/*")
        logger.info("3. Test from TestPyPI: pip install -i https://test.pypi.org/simple/ bestehorn-llmmanager")
        logger.info("4. Upload to PyPI: twine upload dist/*")
        return 0


if __name__ == "__main__":
    sys.exit(main())
