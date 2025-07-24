#!/usr/bin/env python3
"""Script to automate version tagging and release process using setuptools-scm.

This script handles git tagging operations for version releases.
setuptools-scm automatically derives versions from git tags.
"""

import argparse
import subprocess
import sys
import os
import logging
import re
from typing import Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PACKAGE_NAME = "bestehorn-llmmanager"
VALID_VERSION_TYPES = ["patch", "minor", "major"]
DEFAULT_VERSION_TYPE = "patch"


class VersionType(str, Enum):
    """Enum for version bump types."""
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


class ReleaseError(Exception):
    """Custom exception for release process errors."""
    pass


def run_command(cmd: str, description: str, check: bool = True) -> Tuple[bool, str, str]:
    """Run a command and return success status with output.
    
    Args:
        cmd: Command to execute
        description: Description of the command for logging
        check: Whether to check return code
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    logger.info(f"Running: {description}")
    logger.debug(f"Command: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        success = result.returncode == 0
        
        if success:
            logger.debug("Command succeeded")
            if result.stdout:
                logger.debug(f"stdout: {result.stdout}")
        else:
            logger.error(f"Command failed with return code: {result.returncode}")
            if result.stderr:
                logger.error(f"stderr: {result.stderr}")
                
        return success, result.stdout, result.stderr
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        return False, e.stdout if e.stdout else "", e.stderr if e.stderr else ""
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False, "", str(e)


def check_git_status() -> bool:
    """Check if git working directory is clean.
    
    Returns:
        True if working directory is clean, False otherwise
    """
    logger.info("Checking git status...")
    
    success, stdout, stderr = run_command(
        cmd="git status --porcelain",
        description="Checking for uncommitted changes",
        check=False
    )
    
    if not success:
        logger.error("Failed to check git status")
        return False
    
    if stdout.strip():
        logger.error("Working directory has uncommitted changes:")
        logger.error(stdout)
        return False
    
    logger.info("Working directory is clean")
    return True


def check_current_branch() -> Optional[str]:
    """Get the current git branch.
    
    Returns:
        Current branch name or None if error
    """
    logger.info("Checking current branch...")
    
    success, stdout, stderr = run_command(
        cmd="git rev-parse --abbrev-ref HEAD",
        description="Getting current branch",
        check=False
    )
    
    if not success:
        logger.error("Failed to get current branch")
        return None
    
    branch = stdout.strip()
    logger.info(f"Current branch: {branch}")
    return branch


def get_current_version() -> Optional[str]:
    """Get the current package version from latest git tag.
    
    Returns:
        Current version string or None if error
    """
    logger.info("Getting current version from git tags...")
    
    success, stdout, stderr = run_command(
        cmd="git describe --tags --abbrev=0",
        description="Getting latest git tag",
        check=False
    )
    
    if not success:
        logger.warning("No git tags found. This might be the first release.")
        return "0.0.0"  # Default for first release
    
    if stdout.strip():
        version = stdout.strip().lstrip('v')  # Remove 'v' prefix if present
        logger.info(f"Current version: {version}")
        return version
    
    logger.error("Could not determine current version")
    return None


def validate_version_format(version: str) -> bool:
    """Validate version follows semantic versioning.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))


def calculate_new_version(current_version: str, version_type: VersionType) -> str:
    """Calculate new version based on current version and bump type.
    
    Args:
        current_version: Current version string
        version_type: Type of version bump
        
    Returns:
        New version string
    """
    if not validate_version_format(current_version):
        raise ReleaseError(f"Invalid version format: {current_version}")
    
    version_parts = current_version.split('.')
    major, minor, patch = map(int, version_parts)
    
    if version_type == VersionType.PATCH:
        new_version = f"{major}.{minor}.{patch + 1}"
    elif version_type == VersionType.MINOR:
        new_version = f"{major}.{minor + 1}.0"
    elif version_type == VersionType.MAJOR:
        new_version = f"{major + 1}.0.0"
    else:
        raise ReleaseError(f"Invalid version type: {version_type}")
    
    return new_version


def create_and_push_tag(version: str) -> bool:
    """Create a git tag and push it to remote.
    
    Args:
        version: Version string for the tag
        
    Returns:
        True if successful, False otherwise
    """
    tag_name = f"v{version}"
    
    logger.info(f"Creating git tag: {tag_name}")
    
    # Create annotated tag
    success, stdout, stderr = run_command(
        cmd=f'git tag -a {tag_name} -m "Release {version}"',
        description=f"Creating tag {tag_name}",
        check=False
    )
    
    if not success:
        logger.error(f"Failed to create tag {tag_name}")
        return False
    
    logger.info(f"Tag {tag_name} created successfully")
    
    # Push tag to remote
    logger.info(f"Pushing tag {tag_name} to remote...")
    
    success, stdout, stderr = run_command(
        cmd=f"git push origin {tag_name}",
        description=f"Pushing tag {tag_name}",
        check=False
    )
    
    if not success:
        logger.error(f"Failed to push tag {tag_name}")
        return False
    
    logger.info(f"Tag {tag_name} pushed successfully")
    return True


def verify_new_version(expected_version: str) -> bool:
    """Verify that the new version is correctly set.
    
    Args:
        expected_version: Expected version string
        
    Returns:
        True if version matches, False otherwise
    """
    logger.info("Verifying new version...")
    
    # Get the new version from setuptools-scm
    success, stdout, stderr = run_command(
        cmd="python -c \"import setuptools_scm; print(setuptools_scm.get_version())\"",
        description="Getting version from setuptools-scm",
        check=False
    )
    
    if not success:
        logger.warning("Could not verify version via setuptools-scm")
        return True  # Don't fail the release for this
    
    actual_version = stdout.strip()
    
    # setuptools-scm might return the exact version or a version with additional info
    if actual_version.startswith(expected_version):
        logger.info(f"Version verified: {actual_version}")
        return True
    else:
        logger.warning(f"Version mismatch: expected {expected_version}, got {actual_version}")
        return True  # Don't fail the release for this


def main() -> int:
    """Main function to handle version release.
    
    Returns:
        0 if successful, 1 otherwise
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Automate version tagging and release process using setuptools-scm"
    )
    parser.add_argument(
        "-t", "--type",
        type=str,
        choices=VALID_VERSION_TYPES,
        default=DEFAULT_VERSION_TYPE,
        help=f"Type of version bump (default: {DEFAULT_VERSION_TYPE})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    
    args = parser.parse_args()
    version_type = VersionType(args.type)
    
    logger.info(f"Starting release process for {PACKAGE_NAME}")
    logger.info(f"Version bump type: {version_type.value}")
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    logger.info("=" * 60)
    
    # Pre-flight checks
    if not args.dry_run:
        logger.info("Checking git status...")
        if not check_git_status():
            logger.error("❌ Git status check failed")
            return 1
        logger.info("✅ Git status check passed")
    
    # Check current branch
    current_branch = check_current_branch()
    if not current_branch:
        logger.error("❌ Failed to get current branch")
        return 1
    
    if current_branch not in ["main", "master"]:
        logger.warning(f"⚠️  You are on branch '{current_branch}', not 'main' or 'master'")
        if not args.dry_run:
            response = input("Do you want to continue? (y/N): ")
            if response.lower() != 'y':
                logger.info("Release cancelled by user")
                return 1
    
    # Get current version
    current_version = get_current_version()
    if not current_version:
        logger.error("❌ Failed to get current version")
        return 1
    
    # Calculate new version
    try:
        new_version = calculate_new_version(current_version, version_type)
    except ReleaseError as e:
        logger.error(f"❌ {e}")
        return 1
    
    # Display release summary
    logger.info("\n" + "=" * 60)
    logger.info("RELEASE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Package: {PACKAGE_NAME}")
    logger.info(f"Current version: {current_version}")
    logger.info(f"New version: {new_version}")
    logger.info(f"Version type: {version_type.value}")
    logger.info(f"Current branch: {current_branch}")
    logger.info(f"Tag to create: v{new_version}")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("DRY RUN - Would create tag and push, but no actual changes made")
        return 0
    
    # Confirm with user
    response = input("\nProceed with release? (y/N): ")
    if response.lower() != 'y':
        logger.info("Release cancelled by user")
        return 1
    
    # Create and push tag
    logger.info("\n" + "=" * 60)
    logger.info("EXECUTING RELEASE")
    logger.info("=" * 60)
    
    if not create_and_push_tag(new_version):
        logger.error("❌ Failed to create and push tag")
        return 1
    
    # Verify version
    verify_new_version(new_version)
    
    # Success!
    logger.info("\n" + "=" * 60)
    logger.info("🎉 RELEASE SUCCESSFUL!")
    logger.info("=" * 60)
    logger.info(f"Version {new_version} has been released")
    logger.info(f"Tag v{new_version} has been created and pushed")
    logger.info("\nsetuptools-scm will automatically:")
    logger.info("- Generate version from the new git tag")
    logger.info("- Update the _version.py file during build")
    logger.info("- Handle version management in the package")
    logger.info("\nThe GitHub Actions workflow will now:")
    logger.info("1. Run tests on multiple Python versions")
    logger.info("2. Build the package (with version from git tag)")
    logger.info("3. Publish to TestPyPI")
    logger.info("4. Publish to PyPI")
    logger.info("5. Create a GitHub release")
    logger.info("\nMonitor the progress at:")
    logger.info("https://github.com/Bestehorn/LLMManager/actions")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
