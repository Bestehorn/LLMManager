"""
Cross-file consistency tests for Python version configuration.

This module validates that all configuration files and documentation are
synchronized and specify consistent Python version requirements:
- pyproject.toml, ci.yml, and tox.ini specify the same versions
- Documentation matches configuration files
- No conflicting version specifications exist

**Validates: Requirements 1.4, 2.5, 3.5, 4.1-4.8**
"""

import configparser
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

import pytest
import yaml

# Python 3.11+ has tomllib built-in, earlier versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        pytest.skip("tomli not available for Python < 3.11", allow_module_level=True)


# Constants for expected Python versions
EXPECTED_PYTHON_VERSIONS: List[str] = ["3.10", "3.11", "3.12", "3.13", "3.14"]
EXPECTED_PY_VERSIONS: List[str] = ["py310", "py311", "py312", "py313", "py314"]
REMOVED_PYTHON_VERSIONS: List[str] = ["3.8", "3.9"]
REMOVED_PY_VERSIONS: List[str] = ["py38", "py39"]


@pytest.fixture
def pyproject_config() -> Dict[str, Any]:
    """Load and parse pyproject.toml configuration."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


@pytest.fixture
def ci_workflow() -> Dict[str, Any]:
    """Load and parse .github/workflows/ci.yml configuration."""
    ci_workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
    with open(ci_workflow_path, encoding="utf-8") as f:
        result: Dict[str, Any] = yaml.safe_load(f)
        return result


@pytest.fixture
def tox_config() -> configparser.ConfigParser:
    """Load and parse tox.ini configuration."""
    tox_ini_path = Path(__file__).parent.parent.parent / "tox.ini"
    config = configparser.ConfigParser()
    config.read(tox_ini_path)
    return config


def extract_python_versions_from_classifiers(classifiers: List[str]) -> Set[str]:
    """
    Extract Python version numbers from PyPI classifiers.

    Args:
        classifiers: List of PyPI classifier strings

    Returns:
        Set of Python version strings (e.g., {"3.10", "3.11", ...})
    """
    versions = set()
    for classifier in classifiers:
        if classifier.startswith("Programming Language :: Python :: 3."):
            # Extract version like "3.10" from "Programming Language :: Python :: 3.10"
            version = classifier.split("::")[-1].strip()
            versions.add(version)
    return versions


def extract_python_versions_from_tox_envlist(envlist: str) -> Set[str]:
    """
    Extract Python version numbers from tox envlist.

    Args:
        envlist: Comma-separated list of tox environments

    Returns:
        Set of Python version strings (e.g., {"3.10", "3.11", ...})
    """
    versions = set()
    envlist_items = [env.strip() for env in envlist.split(",")]

    for env in envlist_items:
        if env.startswith("py3"):
            # Convert "py310" to "3.10", "py311" to "3.11", etc.
            if len(env) == 5:  # e.g., "py310"
                major = env[2]
                minor = env[3:5]
                versions.add(f"{major}.{minor}")
    return versions


class TestConfigurationFileConsistency:
    """Test suite for cross-file configuration consistency."""

    def test_all_config_files_specify_same_python_versions(
        self,
        pyproject_config: Dict[str, Any],
        ci_workflow: Dict[str, Any],
        tox_config: configparser.ConfigParser,
    ) -> None:
        """
        Verify all configuration files specify the same Python versions.

        This test ensures that pyproject.toml classifiers, CI workflow matrix,
        and tox.ini envlist all specify the exact same set of Python versions.

        **Validates: Requirements 1.4, 2.5, 3.5, 4.1-4.8**
        """
        # Extract versions from each configuration file
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )

        ci_versions = set(ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"])

        tox_envlist = tox_config["tox"]["envlist"]
        tox_versions = extract_python_versions_from_tox_envlist(tox_envlist)

        # Expected versions
        expected_versions = set(EXPECTED_PYTHON_VERSIONS)

        # Verify all files have the same versions
        assert (
            pyproject_versions == expected_versions
        ), f"pyproject.toml classifiers mismatch. Expected: {expected_versions}, Got: {pyproject_versions}"

        assert (
            ci_versions == expected_versions
        ), f"CI workflow matrix mismatch. Expected: {expected_versions}, Got: {ci_versions}"

        assert (
            tox_versions == expected_versions
        ), f"tox.ini envlist mismatch. Expected: {expected_versions}, Got: {tox_versions}"

        # Verify all three are synchronized
        assert (
            pyproject_versions == ci_versions == tox_versions
        ), "Configuration files are not synchronized on Python versions"

    def test_pyproject_and_ci_workflow_synchronized(
        self, pyproject_config: Dict[str, Any], ci_workflow: Dict[str, Any]
    ) -> None:
        """
        Verify pyproject.toml and ci.yml specify the same Python versions.

        **Validates: Requirements 4.2, 4.6**
        """
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )

        ci_versions = set(ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"])

        assert (
            pyproject_versions == ci_versions
        ), f"pyproject.toml and ci.yml are not synchronized. pyproject: {pyproject_versions}, ci: {ci_versions}"

    def test_pyproject_and_tox_synchronized(
        self, pyproject_config: Dict[str, Any], tox_config: configparser.ConfigParser
    ) -> None:
        """
        Verify pyproject.toml and tox.ini specify the same Python versions.

        **Validates: Requirements 4.2, 4.7**
        """
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )

        tox_envlist = tox_config["tox"]["envlist"]
        tox_versions = extract_python_versions_from_tox_envlist(tox_envlist)

        assert (
            pyproject_versions == tox_versions
        ), f"pyproject.toml and tox.ini are not synchronized. pyproject: {pyproject_versions}, tox: {tox_versions}"

    def test_ci_workflow_and_tox_synchronized(
        self, ci_workflow: Dict[str, Any], tox_config: configparser.ConfigParser
    ) -> None:
        """
        Verify ci.yml and tox.ini specify the same Python versions.

        **Validates: Requirements 4.6, 4.7**
        """
        ci_versions = set(ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"])

        tox_envlist = tox_config["tox"]["envlist"]
        tox_versions = extract_python_versions_from_tox_envlist(tox_envlist)

        assert (
            ci_versions == tox_versions
        ), f"ci.yml and tox.ini are not synchronized. ci: {ci_versions}, tox: {tox_versions}"


class TestMinimumVersionConsistency:
    """Test suite for minimum Python version consistency."""

    def test_pyproject_requires_python_matches_minimum_classifier(
        self, pyproject_config: Dict[str, Any]
    ) -> None:
        """
        Verify requires-python minimum matches the lowest classifier version.

        The requires-python field should specify >=3.10, which matches the
        lowest Python version in the classifiers.

        **Validates: Requirements 1.2, 4.1, 4.2**
        """
        requires_python = pyproject_config["project"]["requires-python"]
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )

        # Get minimum version from classifiers
        min_version = min(pyproject_versions)

        # Verify requires-python specifies the correct minimum
        assert (
            f">={min_version}" in requires_python
        ), f"requires-python should specify >={min_version}, got {requires_python}"

    def test_mypy_python_version_matches_minimum_supported(
        self, pyproject_config: Dict[str, Any]
    ) -> None:
        """
        Verify mypy python_version matches the minimum supported version.

        mypy should be configured to use the minimum supported Python version
        to ensure compatibility across all supported versions.

        **Validates: Requirements 4.5**
        """
        mypy_version = pyproject_config["tool"]["mypy"]["python_version"]
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )

        # Get minimum version from classifiers
        min_version = min(pyproject_versions)

        assert (
            mypy_version == min_version
        ), f"mypy python_version should be {min_version}, got {mypy_version}"

    def test_black_target_versions_match_supported_versions(
        self, pyproject_config: Dict[str, Any]
    ) -> None:
        """
        Verify black target-version includes all supported Python versions.

        **Validates: Requirements 4.4**
        """
        black_targets = pyproject_config["tool"]["black"]["target-version"]
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )

        # Convert classifier versions to black format (e.g., "3.10" -> "py310")
        expected_black_targets = [f"py{v.replace('.', '')}" for v in sorted(pyproject_versions)]

        assert (
            black_targets == expected_black_targets
        ), f"black target-version should be {expected_black_targets}, got {black_targets}"


class TestRemovedVersionsConsistency:
    """Test suite for verifying removed versions are consistently absent."""

    def test_no_removed_versions_in_any_config_file(
        self,
        pyproject_config: Dict[str, Any],
        ci_workflow: Dict[str, Any],
        tox_config: configparser.ConfigParser,
    ) -> None:
        """
        Verify removed Python versions (3.8, 3.9) are not in any config file.

        **Validates: Requirements 1.1, 1.2, 1.3, 4.3, 4.8**
        """
        # Check pyproject.toml classifiers
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )
        for removed_version in REMOVED_PYTHON_VERSIONS:
            assert (
                removed_version not in pyproject_versions
            ), f"Removed version {removed_version} found in pyproject.toml classifiers"

        # Check CI workflow matrix
        ci_versions = set(ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"])
        for removed_version in REMOVED_PYTHON_VERSIONS:
            assert (
                removed_version not in ci_versions
            ), f"Removed version {removed_version} found in CI workflow matrix"

        # Check tox.ini envlist
        tox_envlist = tox_config["tox"]["envlist"]
        tox_envlist_items = [env.strip() for env in tox_envlist.split(",")]
        for removed_py_version in REMOVED_PY_VERSIONS:
            assert (
                removed_py_version not in tox_envlist_items
            ), f"Removed version {removed_py_version} found in tox.ini envlist"

    def test_black_target_version_excludes_removed_versions(
        self, pyproject_config: Dict[str, Any]
    ) -> None:
        """
        Verify black target-version does not include removed Python versions.

        **Validates: Requirements 1.1, 4.4**
        """
        black_targets = pyproject_config["tool"]["black"]["target-version"]

        for removed_py_version in REMOVED_PY_VERSIONS:
            assert (
                removed_py_version not in black_targets
            ), f"Removed version {removed_py_version} found in black target-version"


class TestDocumentationConfigurationConsistency:
    """Test suite for documentation and configuration consistency."""

    def test_documentation_matches_minimum_version_from_config(
        self, pyproject_config: Dict[str, Any]
    ) -> None:
        """
        Verify documentation references match the minimum version in config.

        This test ensures that README.md and tech-stack.md reference the same
        minimum Python version as specified in pyproject.toml.

        **Validates: Requirements 1.4, 1.5, 2.5, 2.6, 3.5, 3.6, 5.1, 5.4**
        """
        # Get minimum version from pyproject.toml
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )
        min_version = min(pyproject_versions)
        expected_doc_reference = f"Python {min_version}+"

        # Check README.md
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        with open(readme_path, encoding="utf-8") as f:
            readme_content = f.read()

        assert (
            expected_doc_reference in readme_content
        ), f"README.md should reference '{expected_doc_reference}'"

        # Check tech-stack.md
        tech_stack_path = (
            Path(__file__).parent.parent.parent / ".kiro" / "steering" / "tech-stack.md"
        )
        with open(tech_stack_path, encoding="utf-8") as f:
            tech_stack_content = f.read()

        assert (
            expected_doc_reference in tech_stack_content
        ), f"tech-stack.md should reference '{expected_doc_reference}'"

    def test_documentation_does_not_reference_removed_versions(self) -> None:
        """
        Verify documentation does not reference removed Python versions.

        **Validates: Requirements 1.4, 1.5, 5.2**
        """
        # Check README.md
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        with open(readme_path, encoding="utf-8") as f:
            readme_content = f.read()

        # Check examples/README.md
        examples_readme_path = Path(__file__).parent.parent.parent / "examples" / "README.md"
        with open(examples_readme_path, encoding="utf-8") as f:
            examples_content = f.read()

        # Check tech-stack.md
        tech_stack_path = (
            Path(__file__).parent.parent.parent / ".kiro" / "steering" / "tech-stack.md"
        )
        with open(tech_stack_path, encoding="utf-8") as f:
            tech_stack_content = f.read()

        # Verify removed versions are not referenced as supported
        for removed_version in REMOVED_PYTHON_VERSIONS:
            removed_reference = f"Python {removed_version}+"
            removed_runtime = f"python{removed_version}"

            assert (
                removed_reference not in readme_content
            ), f"README.md should not reference '{removed_reference}'"

            assert (
                removed_runtime not in examples_content.lower()
            ), f"examples/README.md should not reference '{removed_runtime}'"

            assert (
                removed_reference not in tech_stack_content
            ), f"tech-stack.md should not reference '{removed_reference}'"


class TestComprehensiveConsistency:
    """Test suite for comprehensive cross-file consistency validation."""

    def test_all_files_specify_exactly_five_python_versions(
        self,
        pyproject_config: Dict[str, Any],
        ci_workflow: Dict[str, Any],
        tox_config: configparser.ConfigParser,
    ) -> None:
        """
        Verify all configuration files specify exactly 5 Python versions.

        This is a comprehensive test that ensures the upgrade from 4 versions
        (3.9-3.12) to 5 versions (3.10-3.14) is complete and consistent.

        **Validates: Requirements 1.1-1.5, 2.1-2.6, 3.1-3.6, 4.1-4.8**
        """
        # Check pyproject.toml classifiers
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )
        assert (
            len(pyproject_versions) == 5
        ), f"pyproject.toml should have 5 Python version classifiers, got {len(pyproject_versions)}"

        # Check CI workflow matrix
        ci_versions = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert (
            len(ci_versions) == 5
        ), f"CI workflow should test 5 Python versions, got {len(ci_versions)}"

        # Check tox.ini envlist (count only py3XX environments)
        tox_envlist = tox_config["tox"]["envlist"]
        tox_envlist_items = [env.strip() for env in tox_envlist.split(",")]
        py3_envs = [env for env in tox_envlist_items if env.startswith("py3")]
        assert len(py3_envs) == 5, f"tox.ini should have 5 py3XX environments, got {len(py3_envs)}"

        # Check black target-version
        black_targets = pyproject_config["tool"]["black"]["target-version"]
        assert (
            len(black_targets) == 5
        ), f"black target-version should have 5 versions, got {len(black_targets)}"

    def test_version_range_is_310_to_314(
        self,
        pyproject_config: Dict[str, Any],
        ci_workflow: Dict[str, Any],
        tox_config: configparser.ConfigParser,
    ) -> None:
        """
        Verify all configuration files specify the version range 3.10-3.14.

        **Validates: Requirements 1.1-1.5, 2.1-2.6, 3.1-3.6, 4.1-4.8**
        """
        expected_versions = set(EXPECTED_PYTHON_VERSIONS)

        # Check pyproject.toml
        pyproject_versions = extract_python_versions_from_classifiers(
            pyproject_config["project"]["classifiers"]
        )
        assert (
            pyproject_versions == expected_versions
        ), f"pyproject.toml should specify versions {expected_versions}, got {pyproject_versions}"

        # Check CI workflow
        ci_versions = set(ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"])
        assert (
            ci_versions == expected_versions
        ), f"CI workflow should test versions {expected_versions}, got {ci_versions}"

        # Check tox.ini
        tox_envlist = tox_config["tox"]["envlist"]
        tox_versions = extract_python_versions_from_tox_envlist(tox_envlist)
        assert (
            tox_versions == expected_versions
        ), f"tox.ini should specify versions {expected_versions}, got {tox_versions}"
