#!/usr/bin/env python3
"""
Test runner script for the LLMManager project.

This script provides a convenient way to run tests with various options
and generate comprehensive reports.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --fast             # Skip slow tests
    python run_tests.py --html             # Generate HTML report
    python run_tests.py --parallel         # Run tests in parallel
    python run_tests.py --help             # Show help
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*50}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {' '.join(cmd)}")
    print('='*50)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED (exit code: {e.returncode})")
        return False
    except FileNotFoundError:
        print(f"\n❌ {description} - FAILED (command not found)")
        return False


def _configure_aws_integration_environment(args) -> None:
    """
    Configure AWS integration test environment based on command line arguments.
    
    Args:
        args: Parsed command line arguments
    """
    # Check if AWS integration is explicitly requested
    if _is_aws_integration_explicitly_requested(args=args):
        _enable_aws_integration_tests()
        _configure_aws_profile(args=args)
    # For --all, only configure AWS if credentials are available
    elif args.all:
        if _is_aws_integration_available():
            print("✅ AWS credentials detected - enabling integration tests")
            _enable_aws_integration_tests()
            _configure_aws_profile(args=args)
        else:
            # AWS not available for --all, inform user but continue with unit tests only
            print("ℹ️  AWS integration tests skipped - no AWS credentials detected")
            print("   Configure AWS credentials to run integration tests with --all")
            print("   Currently running unit tests only")


def _is_aws_integration_explicitly_requested(args) -> bool:
    """
    Check if AWS integration tests are explicitly requested via command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        True if AWS integration tests are explicitly requested
    """
    return any([
        args.aws_integration,
        args.aws_fast,
        args.aws_low_cost,
        args.aws_profile is not None
    ])


def _is_aws_integration_available() -> bool:
    """
    Check if AWS integration tests can be run (credentials available).
    
    Returns:
        True if AWS credentials are available
    """
    return _has_aws_environment_credentials() or _has_aws_profile_credentials()


def _has_aws_profile_credentials() -> bool:
    """
    Check if AWS credentials are available via AWS CLI configuration.
    
    Returns:
        True if AWS CLI credentials are configured
    """
    try:
        # Try to use AWS CLI to check if credentials are configured
        result = subprocess.run(
            ['aws', 'sts', 'get-caller-identity'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # AWS CLI not available or credentials not configured
        return False


def _enable_aws_integration_tests() -> None:
    """Enable AWS integration tests by setting environment variable."""
    os.environ['AWS_INTEGRATION_TESTS_ENABLED'] = 'true'


def _configure_aws_profile(args) -> None:
    """
    Configure AWS profile for integration tests.
    
    Args:
        args: Parsed command line arguments
    """
    if args.aws_profile:
        _set_aws_profile(profile_name=args.aws_profile)
    else:
        _handle_default_aws_profile()


def _set_aws_profile(profile_name: str) -> None:
    """
    Set the AWS profile for integration tests.
    
    Args:
        profile_name: Name of the AWS CLI profile to use
    """
    os.environ['AWS_INTEGRATION_TEST_PROFILE'] = profile_name
    print(f"Using AWS profile: {profile_name}")


def _handle_default_aws_profile() -> None:
    """Handle the case where no AWS profile is explicitly specified."""
    # Check if AWS credentials are already set via environment variables
    if _has_aws_environment_credentials():
        return
    
    # Warn about using default profile
    default_profile = "default"
    print(f"⚠️  No AWS profile specified, attempting to use default profile: '{default_profile}'")
    print("   If this profile doesn't exist, tests will fail with authentication errors.")
    print("   Use --aws-profile=<profile_name> to specify a different profile.")
    
    # Set default profile
    os.environ['AWS_INTEGRATION_TEST_PROFILE'] = default_profile


def _has_aws_environment_credentials() -> bool:
    """
    Check if AWS credentials are available via environment variables.
    
    Returns:
        True if AWS credentials are set via environment variables
    """
    return bool(
        os.getenv('AWS_ACCESS_KEY_ID') and 
        os.getenv('AWS_SECRET_ACCESS_KEY')
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for the LLMManager project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests with coverage
  python run_tests.py --unit             # Run only unit tests
  python run_tests.py --fast --parallel  # Quick test run
  python run_tests.py --integration      # Run only integration tests
  python run_tests.py --all              # Run both unit and AWS integration tests
  python run_tests.py --aws-integration  # Run only AWS integration tests
  python run_tests.py --html             # Generate HTML reports
        """
    )
    
    parser.add_argument(
        '--unit', action='store_true',
        help='Run only unit tests (marked with @pytest.mark.unit)'
    )
    
    parser.add_argument(
        '--integration', action='store_true',
        help='Run only integration tests (marked with @pytest.mark.integration)'
    )
    
    parser.add_argument(
        '--aws-integration', action='store_true',
        help='Run AWS integration tests (requires AWS credentials and enabled environment)'
    )
    
    parser.add_argument(
        '--aws-fast', action='store_true',
        help='Run only fast AWS integration tests (< 30 seconds)'
    )
    
    parser.add_argument(
        '--aws-low-cost', action='store_true',
        help='Run only low-cost AWS integration tests (< $0.01 estimated)'
    )
    
    parser.add_argument(
        '--aws-profile', type=str, metavar='PROFILE',
        help='AWS CLI profile name to use for integration tests'
    )
    
    parser.add_argument(
        '--all', action='store_true',
        help='Run both mocked unit tests and AWS integration tests'
    )
    
    parser.add_argument(
        '--fast', action='store_true',
        help='Skip slow tests (marked with @pytest.mark.slow)'
    )
    
    parser.add_argument(
        '--no-coverage', action='store_true',
        help='Run tests without coverage reporting'
    )
    
    parser.add_argument(
        '--html', action='store_true',
        help='Generate HTML test report'
    )
    
    parser.add_argument(
        '--parallel', action='store_true',
        help='Run tests in parallel using pytest-xdist'
    )
    
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Run tests in verbose mode'
    )
    
    parser.add_argument(
        '--fail-fast', '-x', action='store_true',
        help='Stop on first test failure'
    )
    
    parser.add_argument(
        '--install-deps', action='store_true',
        help='Install test dependencies before running tests'
    )
    
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what commands would be run without executing them'
    )
    
    args = parser.parse_args()
    
    # Configure AWS integration test environment
    _configure_aws_integration_environment(args=args)
    
    # Install dependencies if requested
    if args.install_deps:
        install_cmd = [sys.executable, '-m', 'pip', 'install', '-r', 'requirements-test.txt']
        if args.dry_run:
            print(f"Would run: {' '.join(install_cmd)}")
        else:
            if not run_command(install_cmd, "Installing test dependencies"):
                return 1
    
    # Build pytest command
    pytest_cmd = [sys.executable, '-m', 'pytest']
    
    # Add test selection options
    if args.unit:
        pytest_cmd.extend(['-m', 'unit'])
    elif args.integration:
        pytest_cmd.extend(['-m', 'integration'])
    elif args.aws_integration:
        pytest_cmd.extend(['-m', 'aws_integration'])
    elif args.aws_fast:
        pytest_cmd.extend(['-m', 'aws_integration and aws_fast'])
    elif args.aws_low_cost:
        pytest_cmd.extend(['-m', 'aws_integration and aws_low_cost'])
    elif args.all:
        # Check if AWS integration is actually enabled
        if os.getenv('AWS_INTEGRATION_TESTS_ENABLED') == 'true':
            # Run both unit tests and aws_integration tests
            pytest_cmd.extend(['-m', 'unit or aws_integration'])
        else:
            # Only run unit tests if AWS integration is not available
            pytest_cmd.extend(['-m', 'unit'])
    
    # Add speed options
    if args.fast:
        pytest_cmd.extend(['-m', 'not slow'])
    
    if args.fail_fast:
        pytest_cmd.append('-x')
    
    # Add verbosity
    if args.verbose:
        pytest_cmd.append('-v')
    else:
        pytest_cmd.append('-q')
    
    # Add parallel execution
    if args.parallel:
        pytest_cmd.extend(['-n', 'auto'])
    
    # Add coverage options (default unless disabled)
    if not args.no_coverage:
        pytest_cmd.extend([
            '--cov=src',
            '--cov-report=term-missing',
            '--cov-report=json:coverage.json'
        ])
        
        if args.html:
            pytest_cmd.extend([
                '--cov-report=html:htmlcov',
                '--html=test_results.html',
                '--self-contained-html'
            ])
    elif args.html:
        pytest_cmd.extend([
            '--html=test_results.html',
            '--self-contained-html'
        ])
    
    # Add test directory
    pytest_cmd.append('test/')
    
    if args.dry_run:
        print(f"Would run: {' '.join(pytest_cmd)}")
        return 0
    
    # Run the tests
    success = run_command(pytest_cmd, "Running tests")
    
    if success:
        print(f"\n🎉 All tests completed successfully!")
        
        if not args.no_coverage:
            print("\n📊 Coverage report generated:")
            print("  - Terminal: Displayed above")
            print("  - JSON: coverage.json")
            
            if args.html:
                print("  - HTML: htmlcov/index.html")
        
        if args.html:
            print("\n📄 Test report generated: test_results.html")
            
        return 0
    else:
        print(f"\n💥 Tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
