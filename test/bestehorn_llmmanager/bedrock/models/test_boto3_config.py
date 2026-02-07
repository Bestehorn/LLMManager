"""
Property-based tests for Boto3Config dataclass.

Tests validate that the Boto3Config frozen dataclass correctly preserves field values
through botocore.config.Config conversion and properly rejects invalid inputs.

Feature: boto3-timeout-config
"""

import botocore.config
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.models.llm_manager_structures import Boto3Config

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy for positive integers (valid for read_timeout, connect_timeout, max_pool_connections)
positive_int_strategy = st.integers(min_value=1, max_value=100_000)

# Strategy for non-negative integers (valid for retries_max_attempts; 0 disables retries)
non_negative_int_strategy = st.integers(min_value=0, max_value=1_000)

# Strategy for non-positive integers (invalid for read_timeout, connect_timeout, max_pool_connections)
non_positive_int_strategy = st.integers(max_value=0)

# Strategy for negative integers (invalid for retries_max_attempts)
negative_int_strategy = st.integers(max_value=-1)


# ---------------------------------------------------------------------------
# Composite strategy for valid Boto3Config instances
# ---------------------------------------------------------------------------
@st.composite
def valid_boto3_config(draw: st.DrawFn) -> Boto3Config:
    """Generate a valid Boto3Config with all fields in acceptable ranges."""
    return Boto3Config(
        read_timeout=draw(positive_int_strategy),
        connect_timeout=draw(positive_int_strategy),
        max_pool_connections=draw(positive_int_strategy),
        retries_max_attempts=draw(non_negative_int_strategy),
    )


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


class TestBoto3ConfigProperties:
    """Property-based tests for Boto3Config correctness properties."""

    @settings(max_examples=100)
    @given(config=valid_boto3_config())
    def test_round_trip_preservation(self, config: Boto3Config) -> None:
        """
        Property 1: Round-trip preservation.

        For any valid Boto3Config, to_botocore_config() produces a botocore.config.Config
        where read_timeout, connect_timeout, and max_pool_connections match the original
        values, and retries is a dict {"max_attempts": retries_max_attempts}.

        **Validates: Requirements 1.6, 1.7**
        """
        botocore_cfg = config.to_botocore_config()

        assert isinstance(botocore_cfg, botocore.config.Config)
        assert botocore_cfg.read_timeout == config.read_timeout
        assert botocore_cfg.connect_timeout == config.connect_timeout
        assert botocore_cfg.max_pool_connections == config.max_pool_connections
        assert botocore_cfg.retries == {"max_attempts": config.retries_max_attempts}

    @settings(max_examples=100)
    @given(value=non_positive_int_strategy)
    def test_positive_value_validation_read_timeout(self, value: int) -> None:
        """
        Property 2: Positive-value validation — read_timeout.

        For any non-positive int in read_timeout, ValueError is raised.

        **Validates: Requirements 4.2, 4.3, 4.4**
        """
        with pytest.raises(ValueError, match="read_timeout"):
            Boto3Config(read_timeout=value)

    @settings(max_examples=100)
    @given(value=non_positive_int_strategy)
    def test_positive_value_validation_connect_timeout(self, value: int) -> None:
        """
        Property 2: Positive-value validation — connect_timeout.

        For any non-positive int in connect_timeout, ValueError is raised.

        **Validates: Requirements 4.2, 4.3, 4.4**
        """
        with pytest.raises(ValueError, match="connect_timeout"):
            Boto3Config(connect_timeout=value)

    @settings(max_examples=100)
    @given(value=non_positive_int_strategy)
    def test_positive_value_validation_max_pool_connections(self, value: int) -> None:
        """
        Property 2: Positive-value validation — max_pool_connections.

        For any non-positive int in max_pool_connections, ValueError is raised.

        **Validates: Requirements 4.2, 4.3, 4.4**
        """
        with pytest.raises(ValueError, match="max_pool_connections"):
            Boto3Config(max_pool_connections=value)

    @settings(max_examples=100)
    @given(value=negative_int_strategy)
    def test_negative_retries_validation(self, value: int) -> None:
        """
        Property 3: Negative retries validation.

        For any negative int in retries_max_attempts, ValueError is raised.
        Zero is valid (disables retries).

        **Validates: Requirements 4.5**
        """
        with pytest.raises(ValueError, match="retries_max_attempts"):
            Boto3Config(retries_max_attempts=value)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


class TestBoto3ConfigDefaults:
    """Unit tests for Boto3Config default values.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
    """

    def test_default_read_timeout_is_600(self) -> None:
        """Default read_timeout is 600 seconds for long-running Bedrock inference."""
        config = Boto3Config()
        assert config.read_timeout == 600

    def test_default_connect_timeout_is_60(self) -> None:
        """Default connect_timeout is 60 seconds, matching boto3 default."""
        config = Boto3Config()
        assert config.connect_timeout == 60

    def test_default_max_pool_connections_is_10(self) -> None:
        """Default max_pool_connections is 10, matching boto3 default."""
        config = Boto3Config()
        assert config.max_pool_connections == 10

    def test_default_retries_max_attempts_is_3(self) -> None:
        """Default retries_max_attempts is 3, matching boto3 default."""
        config = Boto3Config()
        assert config.retries_max_attempts == 3


class TestBoto3ConfigImmutability:
    """Unit tests for Boto3Config frozen (immutable) behavior.

    Validates: Requirements 1.1
    """

    def test_frozen_read_timeout_raises(self) -> None:
        """Assignment to read_timeout raises FrozenInstanceError."""
        import dataclasses

        config = Boto3Config()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.read_timeout = 999  # type: ignore[misc]

    def test_frozen_connect_timeout_raises(self) -> None:
        """Assignment to connect_timeout raises FrozenInstanceError."""
        import dataclasses

        config = Boto3Config()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.connect_timeout = 999  # type: ignore[misc]

    def test_frozen_max_pool_connections_raises(self) -> None:
        """Assignment to max_pool_connections raises FrozenInstanceError."""
        import dataclasses

        config = Boto3Config()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.max_pool_connections = 999  # type: ignore[misc]

    def test_frozen_retries_max_attempts_raises(self) -> None:
        """Assignment to retries_max_attempts raises FrozenInstanceError."""
        import dataclasses

        config = Boto3Config()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.retries_max_attempts = 999  # type: ignore[misc]


class TestBoto3ConfigToBotocoreConfig:
    """Unit tests for Boto3Config.to_botocore_config() conversion.

    Validates: Requirements 1.6, 1.7
    """

    def test_returns_botocore_config_instance(self) -> None:
        """to_botocore_config() returns a botocore.config.Config instance."""
        config = Boto3Config()
        result = config.to_botocore_config()
        assert isinstance(result, botocore.config.Config)

    def test_retries_wrapped_as_dict_with_max_attempts_key(self) -> None:
        """retries is wrapped as dict with 'max_attempts' key in botocore Config."""
        config = Boto3Config(retries_max_attempts=5)
        result = config.to_botocore_config()
        assert result.retries == {"max_attempts": 5}

    def test_default_config_botocore_values(self) -> None:
        """Default Boto3Config produces correct botocore.config.Config values."""
        config = Boto3Config()
        result = config.to_botocore_config()

        assert result.read_timeout == 600
        assert result.connect_timeout == 60
        assert result.max_pool_connections == 10
        assert result.retries == {"max_attempts": 3}

    def test_custom_values_propagate_to_botocore_config(self) -> None:
        """Custom Boto3Config values propagate correctly to botocore.config.Config."""
        config = Boto3Config(
            read_timeout=900,
            connect_timeout=120,
            max_pool_connections=25,
            retries_max_attempts=0,
        )
        result = config.to_botocore_config()

        assert result.read_timeout == 900
        assert result.connect_timeout == 120
        assert result.max_pool_connections == 25
        assert result.retries == {"max_attempts": 0}
