"""
Unit tests for tox.ini configuration validation.

This module validates that tox.ini has been correctly updated to support
Python 3.10-3.14 and remove support for Python 3.8 and 3.9.

**Validates: Requirements 4.7, 4.8**
"""

import configparser
from pathlib import Path


def test_tox_envlist_includes_all_supported_versions():
    """
    Test that tox.ini envlist includes py310, py311, py312, py313, py314.

    **Validates: Requirement 4.7**
    """
    tox_ini_path = Path("tox.ini")
    assert tox_ini_path.exists(), "tox.ini file not found"

    config = configparser.ConfigParser()
    config.read(tox_ini_path)

    assert "tox" in config, "tox.ini missing [tox] section"

    envlist = config["tox"]["envlist"]
    envlist_items = [env.strip() for env in envlist.split(",")]

    # Verify all supported Python versions are present
    expected_versions = ["py310", "py311", "py312", "py313", "py314"]
    for version in expected_versions:
        assert (
            version in envlist_items
        ), f"Expected Python version {version} not found in tox envlist"


def test_tox_envlist_excludes_py38_and_py39():
    """
    Test that tox.ini envlist does not include py38 or py39.

    **Validates: Requirement 4.8**
    """
    tox_ini_path = Path("tox.ini")
    assert tox_ini_path.exists(), "tox.ini file not found"

    config = configparser.ConfigParser()
    config.read(tox_ini_path)

    assert "tox" in config, "tox.ini missing [tox] section"

    envlist = config["tox"]["envlist"]
    envlist_items = [env.strip() for env in envlist.split(",")]

    # Verify removed Python versions are not present
    removed_versions = ["py38", "py39"]
    for version in removed_versions:
        assert (
            version not in envlist_items
        ), f"Removed Python version {version} should not be in tox envlist"


def test_tox_envlist_includes_other_environments():
    """
    Test that tox.ini envlist includes other environments (lint, type, docs).

    This ensures that the update didn't accidentally remove other important
    test environments.

    **Validates: Requirement 4.7**
    """
    tox_ini_path = Path("tox.ini")
    assert tox_ini_path.exists(), "tox.ini file not found"

    config = configparser.ConfigParser()
    config.read(tox_ini_path)

    assert "tox" in config, "tox.ini missing [tox] section"

    envlist = config["tox"]["envlist"]
    envlist_items = [env.strip() for env in envlist.split(",")]

    # Verify other important environments are present
    other_environments = ["lint", "type", "docs"]
    for env in other_environments:
        assert env in envlist_items, f"Expected environment {env} not found in tox envlist"


def test_tox_envlist_exact_order():
    """
    Test that tox.ini envlist has the expected exact order.

    This is a comprehensive test that verifies the complete envlist matches
    the expected configuration.

    **Validates: Requirements 4.7, 4.8**
    """
    tox_ini_path = Path("tox.ini")
    assert tox_ini_path.exists(), "tox.ini file not found"

    config = configparser.ConfigParser()
    config.read(tox_ini_path)

    assert "tox" in config, "tox.ini missing [tox] section"

    envlist = config["tox"]["envlist"]
    envlist_items = [env.strip() for env in envlist.split(",")]

    # Expected complete envlist
    expected_envlist = ["py310", "py311", "py312", "py313", "py314", "lint", "type", "docs"]

    assert (
        envlist_items == expected_envlist
    ), f"tox envlist does not match expected. Got: {envlist_items}, Expected: {expected_envlist}"
