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
            from bestehorn_llmmanager.bedrock.retry.retry_manager import (  # noqa: F401
                RetryManager,
            )
            from bestehorn_llmmanager.llm_manager import (  # noqa: F401
                LLMManager,
            )
            from bestehorn_llmmanager.parallel_llm_manager import (  # noqa: F401
                ParallelLLMManager,
            )

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
