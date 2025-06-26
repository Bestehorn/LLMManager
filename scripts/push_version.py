#!/usr/bin/env python3
"""Script to automate version bumping and release process.

This script handles the version bumping and git operations required
to create a new release of the bestehorn-llmmanager package.
"""

import argparse
import subprocess
import sys
import os
import logging
from typing import Optional, List, Tuple
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


def check_bump2version() -> bool:
    """Check if bump2version is installed.
    
    Returns:
        True if bump2version is available, False otherwise
    """
    logger.info("Checking for bump2version...")
    
    success, stdout, stderr = run_command(
        cmd="which bump2version",
        description="Checking bump2version installation",
        check=False
    )
    
    if not success:
        logger.error("bump2version not found. Install with: pip install bump2version")
        return False
    
    logger.info("bump2version is installed")
    return True


def get_current_version() -> Optional[str]:
    """Get the current package version.
    
    Returns:
        Current version string or None if error
    """
    logger.info("Getting current version...")
    
    # Read version from __init__.py
    init_file_path = os.path.join("src", "bestehorn_llmmanager", "__init__.py")
    
    if not os.path.exists(init_file_path):
        logger.error(f"File not found: {init_file_path}")
        return None
    
    try:
        with open(init_file_path, 'r') as f:
            for line in f:
                if line.startswith('__version__'):
                    # Extract version from line like: __version__ = "1.0.0"
                    version = line.split('=')[1].strip().strip('"\'')
                    logger.info(f"Current version: {version}")
                    return version
    except Exception as e:
        logger.error(f"Error reading version: {e}")
        return None
    
    logger.error("Version not found in __init__.py")
    return None


def bump_version(version_type: VersionType) -> bool:
    """Bump the package version using bump2version.
    
    Args:
        version_type: Type of version bump (patch, minor, major)
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Bumping {version_type.value} version...")
    
    success, stdout, stderr = run_command(
        cmd=f"bump2version {version_type.value}",
        description=f"Bumping {version_type.value} version",
        check=False
    )
    
    if not success:
        logger.error(f"Failed to bump version")
        return False
    
    logger.info("Version bumped successfully")
    return True


def get_new_version() -> Optional[str]:
    """Get the new version after bumping.
    
    Returns:
        New version string or None if error
    """
    return get_current_version()


def push_changes() -> bool:
    """Push the changes and tags to remote repository.
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Pushing changes to remote...")
    
    # Push commits
    success, stdout, stderr = run_command(
        cmd="git push origin main",
        description="Pushing commits",
        check=False
    )
    
    if not success:
        logger.error("Failed to push commits")
        return False
    
    # Push tags
    success, stdout, stderr = run_command(
        cmd="git push origin --tags",
        description="Pushing tags",
        check=False
    )
    
    if not success:
        logger.error("Failed to push tags")
        return False
    
    logger.info("Changes and tags pushed successfully")
    return True


def main() -> int:
    """Main function to handle version release.
    
    Returns:
        0 if successful, 1 otherwise
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Automate version bumping and release process"
    )
    parser.add_argument(
        "-t", "--type",
        type=str,
        choices=VALID_VERSION_TYPES,
        default=DEFAULT_VERSION_TYPE,
        help=f"Type of version bump (default: {DEFAULT_VERSION_TYPE})"
    )
    
    args = parser.parse_args()
    version_type = VersionType(args.type)
    
    logger.info(f"Starting release process for {PACKAGE_NAME}")
    logger.info(f"Version bump type: {version_type.value}")
    logger.info("=" * 60)
    
    # Pre-flight checks
    checks = [
        ("Git status", check_git_status),
        ("bump2version availability", check_bump2version),
    ]
    
    for check_name, check_func in checks:
        logger.info(f"\nChecking {check_name}...")
        if not check_func():
            logger.error(f"❌ {check_name} check failed")
            return 1
        logger.info(f"✅ {check_name} check passed")
    
    # Check current branch
    current_branch = check_current_branch()
    if not current_branch:
        logger.error("❌ Failed to get current branch")
        return 1
    
    if current_branch not in ["main", "master"]:
        logger.warning(f"⚠️  You are on branch '{current_branch}', not 'main' or 'master'")
        response = input("Do you want to continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Release cancelled by user")
            return 1
    
    # Get current version
    current_version = get_current_version()
    if not current_version:
        logger.error("❌ Failed to get current version")
        return 1
    
    logger.info(f"\nCurrent version: {current_version}")
    
    # Calculate new version (for display)
    version_parts = current_version.split('.')
    if len(version_parts) != 3:
        logger.error(f"❌ Invalid version format: {current_version}")
        return 1
    
    major, minor, patch = map(int, version_parts)
    
    # Initialize new_version
    new_version = ""
    
    if version_type == VersionType.PATCH:
        new_version = f"{major}.{minor}.{patch + 1}"
    elif version_type == VersionType.MINOR:
        new_version = f"{major}.{minor + 1}.0"
    elif version_type == VersionType.MAJOR:
        new_version = f"{major + 1}.0.0"
    else:
        logger.error(f"❌ Invalid version type: {version_type}")
        return 1
    
    logger.info(f"New version will be: {new_version}")
    
    # Confirm with user
    logger.info("\n" + "=" * 60)
    logger.info("RELEASE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Package: {PACKAGE_NAME}")
    logger.info(f"Current version: {current_version}")
    logger.info(f"New version: {new_version}")
    logger.info(f"Version type: {version_type.value}")
    logger.info(f"Current branch: {current_branch}")
    logger.info("=" * 60)
    
    response = input("\nProceed with release? (y/N): ")
    if response.lower() != 'y':
        logger.info("Release cancelled by user")
        return 1
    
    # Perform version bump
    logger.info("\n" + "=" * 60)
    logger.info("EXECUTING RELEASE")
    logger.info("=" * 60)
    
    if not bump_version(version_type):
        logger.error("❌ Failed to bump version")
        return 1
    
    # Verify new version
    actual_new_version = get_new_version()
    if not actual_new_version:
        logger.error("❌ Failed to get new version after bump")
        return 1
    
    if actual_new_version != new_version:
        logger.warning(f"⚠️  Expected version {new_version}, but got {actual_new_version}")
    
    # Push changes
    if not push_changes():
        logger.error("❌ Failed to push changes")
        logger.error("You may need to push manually:")
        logger.error("  git push origin main --tags")
        return 1
    
    # Success!
    logger.info("\n" + "=" * 60)
    logger.info("🎉 RELEASE SUCCESSFUL!")
    logger.info("=" * 60)
    logger.info(f"Version {actual_new_version} has been released")
    logger.info(f"Tag v{actual_new_version} has been pushed")
    logger.info("\nThe GitHub Actions workflow will now:")
    logger.info("1. Run tests on multiple Python versions")
    logger.info("2. Build the package")
    logger.info("3. Publish to TestPyPI")
    logger.info("4. Publish to PyPI")
    logger.info("5. Create a GitHub release")
    logger.info("\nMonitor the progress at:")
    logger.info("https://github.com/Bestehorn/LLMManager/actions")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
