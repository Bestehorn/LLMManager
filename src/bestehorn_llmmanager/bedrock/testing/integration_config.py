"""
Integration test configuration management for AWS Bedrock testing.

This module provides configuration management for integration tests that require
real AWS Bedrock API access, including authentication, model selection, and
test environment setup.
"""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models.aws_regions import get_all_regions


class IntegrationTestError(Exception):
    """Base exception for integration test configuration errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize IntegrationTestError.

        Args:
            message: Error message
            details: Optional error details dictionary
        """
        super().__init__(message)
        self.details = details


@dataclass
class IntegrationTestConfig:
    """
    Configuration for AWS Bedrock integration tests.

    This class manages configuration for integration tests including AWS authentication,
    test models, regions, and execution parameters.

    Attributes:
        enabled: Whether integration tests are enabled
        aws_profile: AWS profile name for authentication
        test_regions: List of AWS regions to test against
        test_models: Dictionary of model IDs by provider for testing
        timeout_seconds: Timeout for individual API calls
        max_retries: Maximum retry attempts for failed operations
        cost_limit_usd: Maximum estimated cost limit for test execution
        skip_slow_tests: Whether to skip slow/expensive integration tests
        log_level: Logging level for integration tests
    """

    enabled: bool = field(default_factory=lambda: _determine_integration_enabled())
    aws_profile: Optional[str] = field(
        default_factory=lambda: os.getenv("AWS_INTEGRATION_TEST_PROFILE")
    )
    test_regions: List[str] = field(default_factory=lambda: _get_test_regions())
    test_models: Dict[str, str] = field(default_factory=lambda: _get_test_models())
    timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("AWS_INTEGRATION_TIMEOUT", "30"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("AWS_INTEGRATION_MAX_RETRIES", "3"))
    )
    cost_limit_usd: float = field(
        default_factory=lambda: float(os.getenv("AWS_INTEGRATION_COST_LIMIT", "1.0"))
    )
    skip_slow_tests: bool = field(
        default_factory=lambda: _get_env_bool("AWS_INTEGRATION_SKIP_SLOW", True)
    )
    log_level: str = field(default_factory=lambda: os.getenv("AWS_INTEGRATION_LOG_LEVEL", "INFO"))

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_configuration()
        self._setup_logging()

    def _validate_configuration(self) -> None:
        """
        Validate integration test configuration.

        Raises:
            IntegrationTestError: If configuration is invalid
        """
        if not self.enabled:
            return

        # Validate regions
        if not self.test_regions:
            raise IntegrationTestError(
                message="No test regions configured for integration tests",
                details={"configured_regions": self.test_regions},
            )

        all_regions = get_all_regions()
        for region in self.test_regions:
            if region not in all_regions:
                raise IntegrationTestError(
                    message=f"Invalid AWS region configured: {region}",
                    details={"invalid_region": region, "valid_regions": all_regions},
                )

        # Validate models
        if not self.test_models:
            raise IntegrationTestError(
                message="No test models configured for integration tests",
                details={"configured_models": self.test_models},
            )

        # Validate timeout
        if self.timeout_seconds <= 0:
            raise IntegrationTestError(
                message="Invalid timeout configuration",
                details={"timeout_seconds": self.timeout_seconds},
            )

        # Validate cost limit
        if self.cost_limit_usd < 0:
            raise IntegrationTestError(
                message="Invalid cost limit configuration",
                details={"cost_limit_usd": self.cost_limit_usd},
            )

    def _setup_logging(self) -> None:
        """Setup logging configuration for integration tests."""
        if not self.enabled:
            return

        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.getLogger(__name__).setLevel(log_level)

    def is_region_enabled(self, region: str) -> bool:
        """
        Check if a specific region is enabled for testing.

        Args:
            region: AWS region identifier

        Returns:
            True if region is enabled for testing
        """
        return self.enabled and region in self.test_regions

    def is_model_enabled(self, model_id: str) -> bool:
        """
        Check if a specific model is enabled for testing.

        Args:
            model_id: Model identifier

        Returns:
            True if model is enabled for testing
        """
        return self.enabled and model_id in self.test_models.values()

    def get_test_model_for_provider(self, provider: str) -> Optional[str]:
        """
        Get the test model ID for a specific provider.

        Args:
            provider: Model provider name (e.g., 'anthropic', 'amazon')

        Returns:
            Model ID if configured, None otherwise
        """
        return self.test_models.get(provider.lower())

    def get_primary_test_region(self) -> str:
        """
        Get the primary region for testing.

        Returns:
            Primary test region identifier

        Raises:
            IntegrationTestError: If no regions are configured
        """
        if not self.test_regions:
            raise IntegrationTestError(
                message="No test regions configured", details={"test_regions": self.test_regions}
            )

        return self.test_regions[0]

    def should_skip_slow_test(self) -> bool:
        """
        Check if slow/expensive tests should be skipped.

        Returns:
            True if slow tests should be skipped
        """
        return not self.enabled or self.skip_slow_tests

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            "enabled": self.enabled,
            "aws_profile": self.aws_profile,
            "test_regions": self.test_regions,
            "test_models": self.test_models,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "cost_limit_usd": self.cost_limit_usd,
            "skip_slow_tests": self.skip_slow_tests,
            "log_level": self.log_level,
        }


def _get_env_bool(env_var: str, default: bool) -> bool:
    """
    Get boolean value from environment variable.

    Args:
        env_var: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value from environment or default
    """
    value = os.getenv(env_var, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def _get_test_regions() -> List[str]:
    """
    Get test regions from environment configuration.

    Returns:
        List of AWS regions for testing
    """
    regions_env = os.getenv("AWS_INTEGRATION_TEST_REGIONS", "us-east-1,us-west-2")
    return [region.strip() for region in regions_env.split(",") if region.strip()]


def _get_test_models() -> Dict[str, str]:
    """
    Get test models from environment configuration.

    Returns:
        Dictionary mapping provider names to model friendly names
    """
    # Default test models (using friendly names that match UnifiedModelManager)
    default_models = {
        "anthropic": "Claude 3 Haiku",
        "amazon": "Titan Text G1 - Lite",
        "meta": "Llama 3 8B Instruct",
    }

    # Allow override via environment variables
    models = {}
    for provider, default_model in default_models.items():
        env_var = f"AWS_INTEGRATION_TEST_MODEL_{provider.upper()}"
        models[provider] = os.getenv(env_var, default_model)

    return models


def _determine_integration_enabled() -> bool:
    """
    Determine if integration tests should be enabled based on available credentials.

    Mirrors the logic from run_tests.py to provide consistent behavior.

    Returns:
        True if integration tests should be enabled
    """
    # Check if explicitly enabled via environment variable
    if _get_env_bool("AWS_INTEGRATION_TESTS_ENABLED", False):
        return True

    # Check if AWS integration is available via credentials
    if _is_aws_integration_available():
        # Handle default profile setup
        _handle_default_aws_profile_setup()
        return True

    return False


def _is_aws_integration_available() -> bool:
    """
    Check if AWS integration tests can be run (credentials available).

    Returns:
        True if AWS credentials are available
    """
    return _has_aws_environment_credentials() or _has_aws_profile_credentials()


def _has_aws_environment_credentials() -> bool:
    """
    Check if AWS credentials are available via environment variables.

    Returns:
        True if AWS credentials are set via environment variables
    """
    return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))


def _has_aws_profile_credentials() -> bool:
    """
    Check if AWS credentials are available via AWS CLI configuration.

    Returns:
        True if AWS CLI credentials are configured
    """
    try:
        # Try to use AWS CLI to check if credentials are configured
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # AWS CLI not available or credentials not configured
        return False


def _handle_default_aws_profile_setup() -> None:
    """
    Handle setup for default AWS profile when no explicit profile is specified.
    """
    # Check if AWS credentials are already set via environment variables
    if _has_aws_environment_credentials():
        return

    # Check if a profile is already specified
    if os.getenv("AWS_INTEGRATION_TEST_PROFILE"):
        return

    # Use default profile and print warning
    default_profile = "default"
    print(
        f"⚠️  No AWS profile specified for integration tests, using default profile: '{default_profile}'"
    )
    print("   If this profile doesn't exist, tests may fail with authentication errors.")
    print("   Set AWS_INTEGRATION_TEST_PROFILE environment variable to use a different profile.")

    # Set default profile
    os.environ["AWS_INTEGRATION_TEST_PROFILE"] = default_profile


def load_integration_config() -> IntegrationTestConfig:
    """
    Load integration test configuration from environment.

    Returns:
        Configured IntegrationTestConfig instance

    Raises:
        IntegrationTestError: If configuration is invalid
    """
    try:
        return IntegrationTestConfig()
    except Exception as e:
        raise IntegrationTestError(
            message=f"Failed to load integration test configuration: {str(e)}",
            details={"original_error": str(e)},
        ) from e
