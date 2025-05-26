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
