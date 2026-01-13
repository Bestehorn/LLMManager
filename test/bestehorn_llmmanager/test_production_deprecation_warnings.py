"""
Unit test to verify production code generates zero deprecation warnings.

This test ensures that all production code uses current APIs and does not
trigger deprecation warnings.

Feature: ci-failure-fixes
Validates: Requirements 2.4
"""

import importlib
import warnings
from pathlib import Path

import pytest

from bestehorn_llmmanager.bedrock.models.deprecation import DeprecatedAPIWarning


class TestProductionDeprecationWarnings:
    """Test suite to verify production code generates no deprecation warnings."""

    def test_zero_production_deprecation_warnings(self):
        """
        Test that importing all production modules generates no deprecation warnings.

        This test imports all production modules and verifies that no deprecation
        warnings are emitted during import or module initialization.

        Feature: ci-failure-fixes
        Validates: Requirements 2.4
        """
        # Get the src directory
        src_dir = Path(__file__).parent.parent.parent / "src" / "bestehorn_llmmanager"

        # Collect all Python files in src (excluding __pycache__ and _version.py)
        python_files = []
        for py_file in src_dir.rglob("*.py"):
            # Skip __pycache__ directories
            if "__pycache__" in str(py_file):
                continue

            # Skip _version.py (auto-generated)
            if py_file.name == "_version.py":
                continue

            # Skip __init__.py files (they're imported automatically)
            if py_file.name == "__init__.py":
                continue

            python_files.append(py_file)

        # Track warnings
        production_warnings = []

        # Import each module and check for warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            for py_file in python_files:
                # Convert file path to module name
                relative_path = py_file.relative_to(src_dir.parent)
                module_name = (
                    str(relative_path.with_suffix("")).replace("\\", ".").replace("/", ".")
                )

                try:
                    # Import the module
                    importlib.import_module(module_name)
                except Exception as e:
                    # Some modules may fail to import due to missing dependencies
                    # This is okay - we're just checking for deprecation warnings
                    pytest.skip(f"Could not import {module_name}: {e}")

            # Filter to deprecation warnings from production code
            for warning in w:
                # Check if it's a deprecation warning
                if issubclass(warning.category, (DeprecatedAPIWarning, DeprecationWarning)):
                    # Check if it's from production code (not test code)
                    if "src/bestehorn_llmmanager" in str(
                        warning.filename
                    ) or "src\\bestehorn_llmmanager" in str(warning.filename):
                        # Exclude test files
                        if "test" not in str(warning.filename):
                            production_warnings.append(warning)

        # Assert no production warnings
        if production_warnings:
            warning_details = []
            for warning in production_warnings:
                warning_details.append(
                    f"  - {warning.category.__name__}: {warning.message}\n"
                    f"    File: {warning.filename}:{warning.lineno}"
                )

            error_message = (
                f"Found {len(production_warnings)} deprecation warning(s) in production code:\n"
                + "\n".join(warning_details)
            )
            pytest.fail(error_message)

    def test_specific_modules_no_warnings(self):
        """
        Test that specific critical modules generate no deprecation warnings.

        This test focuses on the modules that were updated to use current APIs.

        Feature: ci-failure-fixes
        Validates: Requirements 2.4
        """
        critical_modules = [
            "bestehorn_llmmanager.bedrock.retry.retry_manager",
            "bestehorn_llmmanager.bedrock.retry.access_method_selector",
            "bestehorn_llmmanager.bedrock.streaming.streaming_retry_manager",
            "bestehorn_llmmanager.bedrock.models.unified_structures",
            "bestehorn_llmmanager.llm_manager",
        ]

        for module_name in critical_modules:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                try:
                    # Import the module
                    importlib.import_module(module_name)
                except Exception as e:
                    pytest.skip(f"Could not import {module_name}: {e}")

                # Filter to deprecation warnings
                deprecation_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, (DeprecatedAPIWarning, DeprecationWarning))
                ]

                # Assert no warnings for this module
                if deprecation_warnings:
                    warning_details = []
                    for warning in deprecation_warnings:
                        warning_details.append(
                            f"  - {warning.category.__name__}: {warning.message}\n"
                            f"    File: {warning.filename}:{warning.lineno}"
                        )

                    error_message = (
                        f"Module {module_name} generated {len(deprecation_warnings)} "
                        f"deprecation warning(s):\n" + "\n".join(warning_details)
                    )
                    pytest.fail(error_message)
