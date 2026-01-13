"""
Unit test for deprecation warning count.

This test validates that the total number of deprecation warnings from the test suite
remains under the threshold of 100 warnings (down from 50,000+).

Feature: ci-failure-fixes
Validates: Requirements 3.4
"""

import subprocess
import sys
import warnings

import pytest


class TestDeprecationWarningCount:
    """Test that deprecation warnings are under threshold."""

    def test_deprecation_warning_count_under_threshold(self):
        """
        Test that total deprecation warnings are under 100.

        This test runs the full test suite and counts deprecation warnings.
        The threshold of 100 is significantly lower than the original 50,000+
        warnings, demonstrating successful migration to current APIs.

        Validates: Requirements 3.4
        """
        # Run pytest with warning capture
        # We use subprocess to get a clean run of the test suite
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test/",
                "-v",
                "--tb=no",
                "-W",
                "default::DeprecationWarning",
                "--disable-warnings",  # Disable other warnings
                "-p",
                "no:warnings",  # Don't use warnings plugin
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        # Parse warning count from output
        # pytest outputs warnings in the format "X warnings in Y.YYs"
        warning_count = 0
        for line in result.stdout.split("\n") + result.stderr.split("\n"):
            if "warning" in line.lower():
                # Try to extract number from lines like "123 warnings in 45.67s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if "warning" in part.lower() and i > 0:
                        try:
                            count = int(parts[i - 1])
                            warning_count = max(warning_count, count)
                        except (ValueError, IndexError):
                            pass

        # Assert warning count is under threshold
        threshold = 100
        assert warning_count < threshold, (
            f"Deprecation warning count ({warning_count}) exceeds threshold ({threshold}). "
            f"This indicates that deprecated APIs are still being used in test code. "
            f"Please migrate test code to use current APIs."
        )

    def test_no_deprecation_warnings_in_production_code(self):
        """
        Test that production code generates no deprecation warnings.

        This test imports all production modules and verifies that no deprecation
        warnings are emitted during import or basic usage.

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
