"""
Unit tests for GitHub Actions CI workflow Python version configuration.

This module validates that .github/workflows/ci.yml has been correctly updated to:
- Test Python 3.10-3.14 in the test matrix
- Remove Python 3.9 from the test matrix
- Ensure all test jobs use the correct matrix

**Validates: Requirements 1.3, 2.3, 3.3, 4.6, 8.4**
"""

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


@pytest.fixture
def ci_workflow() -> Dict[str, Any]:
    """Load and parse .github/workflows/ci.yml configuration."""
    ci_workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
    with open(ci_workflow_path, encoding="utf-8") as f:
        result: Dict[str, Any] = yaml.safe_load(f)
        return result


class TestCIWorkflowMatrix:
    """Test suite for CI workflow test matrix validation."""

    def test_matrix_includes_all_supported_versions(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify CI matrix includes exactly Python 3.10, 3.11, 3.12, 3.13, and 3.14.

        **Validates: Requirements 2.3, 3.3, 4.6, 8.4**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        expected_versions = ["3.10", "3.11", "3.12", "3.13", "3.14"]

        assert (
            matrix == expected_versions
        ), f"Expected CI matrix to be {expected_versions}, got {matrix}"

    def test_matrix_excludes_python_39(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify Python 3.9 is not in the CI test matrix.

        **Validates: Requirements 1.3, 8.4**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.9" not in matrix, f"Python 3.9 should not be in CI matrix, got {matrix}"

    def test_matrix_includes_python_310(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify Python 3.10 is in the CI test matrix.

        **Validates: Requirements 4.6**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.10" in matrix, "Python 3.10 should be in CI matrix"

    def test_matrix_includes_python_311(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify Python 3.11 is in the CI test matrix.

        **Validates: Requirements 4.6**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.11" in matrix, "Python 3.11 should be in CI matrix"

    def test_matrix_includes_python_312(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify Python 3.12 is in the CI test matrix.

        **Validates: Requirements 4.6**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.12" in matrix, "Python 3.12 should be in CI matrix"

    def test_matrix_includes_python_313(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify Python 3.13 is in the CI test matrix.

        **Validates: Requirements 2.3, 4.6**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.13" in matrix, "Python 3.13 should be in CI matrix"

    def test_matrix_includes_python_314(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify Python 3.14 is in the CI test matrix.

        **Validates: Requirements 3.3, 4.6**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.14" in matrix, "Python 3.14 should be in CI matrix"

    def test_matrix_has_exactly_five_versions(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify CI matrix has exactly 5 Python versions.

        **Validates: Requirements 4.6, 8.4**
        """
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert len(matrix) == 5, f"Expected 5 Python versions in CI matrix, got {len(matrix)}"


class TestCIWorkflowTestJob:
    """Test suite for CI workflow test job configuration."""

    def test_test_job_uses_matrix(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify test job uses the python-version matrix variable.

        **Validates: Requirements 4.6**
        """
        test_job = ci_workflow["jobs"]["test"]
        steps = test_job["steps"]

        # Find the setup-python step
        setup_python_step = None
        for step in steps:
            if "Set up Python" in step.get("name", ""):
                setup_python_step = step
                break

        assert setup_python_step is not None, "Could not find 'Set up Python' step in test job"
        assert (
            setup_python_step["with"]["python-version"] == "${{ matrix.python-version }}"
        ), "Test job should use matrix.python-version variable"

    def test_test_job_has_strategy_matrix(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify test job has a strategy matrix defined.

        **Validates: Requirements 4.6**
        """
        test_job = ci_workflow["jobs"]["test"]
        assert "strategy" in test_job, "Test job should have a strategy defined"
        assert "matrix" in test_job["strategy"], "Test job strategy should have a matrix"
        assert (
            "python-version" in test_job["strategy"]["matrix"]
        ), "Test job matrix should have python-version"


class TestCIWorkflowOtherJobs:
    """Test suite for other CI workflow jobs (lint, build)."""

    def test_lint_job_uses_supported_python_version(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify lint job uses a supported Python version (3.10+).

        **Validates: Requirements 4.6**
        """
        lint_job = ci_workflow["jobs"]["lint"]
        steps = lint_job["steps"]

        # Find the setup-python step
        setup_python_step = None
        for step in steps:
            if "Set up Python" in step.get("name", ""):
                setup_python_step = step
                break

        assert setup_python_step is not None, "Could not find 'Set up Python' step in lint job"
        python_version = setup_python_step["with"]["python-version"]

        # Lint job should use a fixed version that's in our supported range
        supported_versions = ["3.10", "3.11", "3.12", "3.13", "3.14"]
        assert (
            python_version in supported_versions
        ), f"Lint job should use a supported Python version, got {python_version}"

    def test_build_job_uses_supported_python_version(self, ci_workflow: Dict[str, Any]) -> None:
        """
        Verify build job uses a supported Python version (3.10+).

        **Validates: Requirements 4.6**
        """
        build_job = ci_workflow["jobs"]["build"]
        steps = build_job["steps"]

        # Find the setup-python step
        setup_python_step = None
        for step in steps:
            if "Set up Python" in step.get("name", ""):
                setup_python_step = step
                break

        assert setup_python_step is not None, "Could not find 'Set up Python' step in build job"
        python_version = setup_python_step["with"]["python-version"]

        # Build job should use a fixed version that's in our supported range
        supported_versions = ["3.10", "3.11", "3.12", "3.13", "3.14"]
        assert (
            python_version in supported_versions
        ), f"Build job should use a supported Python version, got {python_version}"
