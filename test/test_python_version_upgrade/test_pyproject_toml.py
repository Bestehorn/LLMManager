"""
Unit tests for pyproject.toml Python version configuration.

This module validates that pyproject.toml has been correctly updated to:
- Support Python 3.10-3.14
- Remove Python 3.9 support
- Update tool configurations (black, mypy) for Python 3.10+

**Validates: Requirements 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5**
"""

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Python 3.11+ has tomllib built-in, earlier versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        pytest.skip("tomli not available for Python < 3.11", allow_module_level=True)


@pytest.fixture
def pyproject_config() -> Dict[str, Any]:
    """Load and parse pyproject.toml configuration."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


class TestPyprojectRequiresPython:
    """Test suite for requires-python field validation."""

    def test_requires_python_minimum_version(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify requires-python specifies minimum version of 3.10.

        **Validates: Requirements 1.2, 4.1**
        """
        requires_python = pyproject_config["project"]["requires-python"]
        assert (
            requires_python == ">=3.10,<4.0"
        ), f"Expected requires-python to be '>=3.10,<4.0', got '{requires_python}'"

    def test_requires_python_excludes_python_39(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify requires-python does not allow Python 3.9.

        **Validates: Requirements 1.2**
        """
        requires_python = pyproject_config["project"]["requires-python"]
        # The minimum version should be 3.10, which excludes 3.9
        assert (
            ">=3.10" in requires_python
        ), f"requires-python should specify >=3.10 to exclude Python 3.9, got '{requires_python}'"


class TestPyprojectClassifiers:
    """Test suite for Python version classifiers validation."""

    def test_python_39_classifier_removed(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify Python 3.9 classifier is not present.

        **Validates: Requirements 1.1, 4.3**
        """
        classifiers = pyproject_config["project"]["classifiers"]
        python_39_classifier = "Programming Language :: Python :: 3.9"
        assert (
            python_39_classifier not in classifiers
        ), "Python 3.9 classifier should be removed, but found in classifiers"

    def test_python_310_classifier_present(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify Python 3.10 classifier is present.

        **Validates: Requirements 4.2**
        """
        classifiers = pyproject_config["project"]["classifiers"]
        python_310_classifier = "Programming Language :: Python :: 3.10"
        assert (
            python_310_classifier in classifiers
        ), "Python 3.10 classifier should be present in classifiers"

    def test_python_311_classifier_present(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify Python 3.11 classifier is present.

        **Validates: Requirements 4.2**
        """
        classifiers = pyproject_config["project"]["classifiers"]
        python_311_classifier = "Programming Language :: Python :: 3.11"
        assert (
            python_311_classifier in classifiers
        ), "Python 3.11 classifier should be present in classifiers"

    def test_python_312_classifier_present(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify Python 3.12 classifier is present.

        **Validates: Requirements 4.2**
        """
        classifiers = pyproject_config["project"]["classifiers"]
        python_312_classifier = "Programming Language :: Python :: 3.12"
        assert (
            python_312_classifier in classifiers
        ), "Python 3.12 classifier should be present in classifiers"

    def test_python_313_classifier_present(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify Python 3.13 classifier is present.

        **Validates: Requirements 2.1, 4.2**
        """
        classifiers = pyproject_config["project"]["classifiers"]
        python_313_classifier = "Programming Language :: Python :: 3.13"
        assert (
            python_313_classifier in classifiers
        ), "Python 3.13 classifier should be present in classifiers"

    def test_python_314_classifier_present(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify Python 3.14 classifier is present.

        **Validates: Requirements 3.1, 4.2**
        """
        classifiers = pyproject_config["project"]["classifiers"]
        python_314_classifier = "Programming Language :: Python :: 3.14"
        assert (
            python_314_classifier in classifiers
        ), "Python 3.14 classifier should be present in classifiers"

    def test_all_supported_versions_present(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify all five supported Python versions (3.10-3.14) are in classifiers.

        **Validates: Requirements 1.1, 2.1, 3.1, 4.2**
        """
        classifiers = pyproject_config["project"]["classifiers"]
        expected_versions = ["3.10", "3.11", "3.12", "3.13", "3.14"]

        for version in expected_versions:
            classifier = f"Programming Language :: Python :: {version}"
            assert (
                classifier in classifiers
            ), f"Python {version} classifier should be present in classifiers"


class TestBlackConfiguration:
    """Test suite for Black tool configuration validation."""

    def test_black_target_version_includes_all_versions(
        self, pyproject_config: Dict[str, Any]
    ) -> None:
        """
        Verify black target-version includes all five Python versions.

        **Validates: Requirements 4.4**
        """
        target_versions = pyproject_config["tool"]["black"]["target-version"]
        expected_versions = ["py310", "py311", "py312", "py313", "py314"]

        assert (
            target_versions == expected_versions
        ), f"Expected black target-version to be {expected_versions}, got {target_versions}"

    def test_black_target_version_excludes_py39(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify black target-version does not include py39.

        **Validates: Requirements 1.1, 4.4**
        """
        target_versions = pyproject_config["tool"]["black"]["target-version"]
        assert (
            "py39" not in target_versions
        ), f"py39 should not be in black target-version, got {target_versions}"

    def test_black_target_version_starts_with_py310(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify black target-version starts with py310.

        **Validates: Requirements 4.4**
        """
        target_versions = pyproject_config["tool"]["black"]["target-version"]
        assert (
            target_versions[0] == "py310"
        ), f"First black target-version should be py310, got {target_versions[0]}"


class TestMypyConfiguration:
    """Test suite for mypy tool configuration validation."""

    def test_mypy_python_version_is_310(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify mypy python_version is set to 3.10.

        **Validates: Requirements 4.5**
        """
        python_version = pyproject_config["tool"]["mypy"]["python_version"]
        assert (
            python_version == "3.10"
        ), f"Expected mypy python_version to be '3.10', got '{python_version}'"

    def test_mypy_python_version_not_39(self, pyproject_config: Dict[str, Any]) -> None:
        """
        Verify mypy python_version is not 3.9.

        **Validates: Requirements 1.1, 4.5**
        """
        python_version = pyproject_config["tool"]["mypy"]["python_version"]
        assert (
            python_version != "3.9"
        ), f"mypy python_version should not be '3.9', got '{python_version}'"
