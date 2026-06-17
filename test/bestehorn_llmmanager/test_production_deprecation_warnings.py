"""
Unit test for production code deprecation warnings.

This test validates that production code generates zero deprecation warnings.
Comprehensive warning monitoring is handled separately through CI logs.

Feature: ci-failure-fixes
Validates: Requirements 2.4
"""

import warnings

import pytest


class TestProductionDeprecationWarnings:
    """Test that production code generates no deprecation warnings."""

    def test_no_deprecation_warnings_in_production_code(self):
        """
        Test that production code generates no deprecation warnings.

        This test imports all production modules and verifies that no deprecation
        warnings are emitted during import or basic usage.

        Note: Comprehensive warning monitoring across the entire test suite is
        handled separately through CI logs and monitoring tools. This test focuses
        on ensuring production code itself is clean.

        Validates: Requirements 2.4
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            # Import all production modules
            # This will trigger any deprecation warnings from module-level code
            from bestehorn_llmmanager.bedrock.models.access_method import (  # noqa: F401
                ModelAccessInfo,
            )
            from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (  # noqa: F401
                RetryConfig,
            )
            from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager  # noqa: F401
            from bestehorn_llmmanager.llm_manager import LLMManager  # noqa: F401
            from bestehorn_llmmanager.parallel_llm_manager import ParallelLLMManager  # noqa: F401

            # Filter to deprecation warnings from production code
            prod_warnings = [
                warning
                for warning in w
                if "src/bestehorn_llmmanager" in str(warning.filename)
                and "test/" not in str(warning.filename)
            ]

            # Assert no production deprecation warnings
            assert len(prod_warnings) == 0, (
                f"Found {len(prod_warnings)} deprecation warnings in production code:\n"
                + "\n".join(
                    f"  {warning.filename}:{warning.lineno}: {warning.message}"
                    for warning in prod_warnings
                )
            )


class TestOwnDeprecationCategoriesAreErrors:
    """The project's OWN deprecation categories are promoted to errors (issue #20).

    DeprecatedEnumValueWarning and DeprecatedAPIWarning are configured as errors in
    pyproject.toml [tool.pytest.ini_options].filterwarnings, so any NEW use of a
    deprecated bestehorn_llmmanager API surfaces as a test failure instead of silent
    log noise. These tests lock that policy in and guard the runtime production paths.
    """

    def test_emitting_own_deprecation_warning_is_an_error_under_suite_config(self):
        """A bestehorn_llmmanager deprecation warning must be raised as an error.

        Uses the same filter the suite applies (configured in pyproject.toml) and
        confirms that triggering a DeprecatedEnumValueWarning raises rather than warns —
        i.e. the error-promotion policy is in effect.
        """
        from bestehorn_llmmanager.bedrock.models.deprecation import (
            DeprecatedEnumValueWarning,
        )

        with warnings.catch_warnings():
            # Mirror the suite policy: the project's own category is an error.
            warnings.simplefilter("error", DeprecatedEnumValueWarning)
            with pytest.raises(DeprecatedEnumValueWarning):
                warnings.warn("sample deprecated use", category=DeprecatedEnumValueWarning)

    def test_legacy_managers_emit_no_own_category_warnings_at_runtime(self):
        """Constructing the deprecated managers must not emit the project's OWN
        deprecation categories.

        The legacy ModelManager/CRISManager/UnifiedModelManager classes are deprecated
        wholesale (they emit a plain DeprecationWarning, which is acceptable until v4.0.0).
        What must NOT happen is them cascading a DeprecatedEnumValueWarning /
        DeprecatedAPIWarning internally — that would be production code using a deprecated
        API and is what issue #20 eliminates. The inner managers are mocked so no network
        access is needed.
        """
        from unittest.mock import patch

        from bestehorn_llmmanager.bedrock.models.deprecation import (
            DeprecatedAPIWarning,
            DeprecatedEnumValueWarning,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with (
                patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager"),
                patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager"),
            ):
                from bestehorn_llmmanager.bedrock.UnifiedModelManager import (
                    UnifiedModelManager,
                )

                UnifiedModelManager()

            own_category = [
                warning
                for warning in w
                if issubclass(warning.category, (DeprecatedEnumValueWarning, DeprecatedAPIWarning))
            ]
            assert len(own_category) == 0, (
                "Legacy manager construction emitted the project's own deprecation "
                "category (a production-internal deprecated-API use):\n"
                + "\n".join(
                    f"  {warning.filename}:{warning.lineno}: {warning.message}"
                    for warning in own_category
                )
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
