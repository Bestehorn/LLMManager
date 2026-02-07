"""
Property-based test for LLMManager boto3_config type validation.

Tests validate that LLMManager raises ConfigurationError when boto3_config
is provided with a value that is not an instance of Boto3Config and is not None.

Feature: boto3-timeout-config, Property 4: invalid type rejection
"""

from unittest.mock import Mock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    ConfigurationError,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import Boto3Config
from bestehorn_llmmanager.llm_manager import LLMManager

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy for values that are NOT Boto3Config and NOT None.
# Covers strings, ints, floats, booleans, dicts, lists, tuples, and bytes.
non_boto3_config_strategy = st.one_of(
    st.text(min_size=0, max_size=50),
    st.integers(min_value=-10_000, max_value=10_000),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.integers(),
        max_size=5,
    ),
    st.lists(elements=st.integers(), max_size=5),
    st.tuples(st.integers()),
    st.binary(min_size=0, max_size=20),
)


# ---------------------------------------------------------------------------
# Property Test
# ---------------------------------------------------------------------------


class TestLLMManagerInvalidBoto3ConfigTypeRejection:
    """Property-based test for invalid boto3_config type rejection.

    Validates: Requirements 4.1
    """

    @settings(max_examples=100)
    @given(invalid_value=non_boto3_config_strategy)
    def test_invalid_type_raises_configuration_error(self, invalid_value: object) -> None:
        """
        Property 4: Invalid type rejection.

        For any non-Boto3Config, non-None value, LLMManager raises ConfigurationError
        when passed as boto3_config.

        **Validates: Requirements 4.1**
        """
        mock_catalog = Mock()
        mock_catalog.ensure_catalog_available.return_value = Mock()
        mock_catalog.is_model_available.return_value = True
        mock_catalog.get_model_info.return_value = Mock(
            model_id="test-model-id",
            has_direct_access=True,
            has_regional_cris=False,
            has_global_cris=False,
            regional_cris_profile_id=None,
            global_cris_profile_id=None,
        )

        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_catalog,
        ):
            with pytest.raises(ConfigurationError):
                LLMManager(
                    models=["Claude Haiku 4 5 20251001"],
                    regions=["us-east-1"],
                    boto3_config=invalid_value,  # type: ignore[arg-type]
                )


# ---------------------------------------------------------------------------
# Unit Tests — LLMManager creates default Boto3Config when None
# ---------------------------------------------------------------------------


class TestLLMManagerDefaultBoto3Config:
    """Unit tests for LLMManager creating default Boto3Config when boto3_config=None.

    Validates: Requirements 2.1, 2.3
    """

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.llm_manager.AuthManager")
    def test_creates_default_boto3_config_when_none(
        self,
        mock_auth_manager_cls: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """LLMManager creates a default Boto3Config() when boto3_config=None is passed."""
        mock_catalog = Mock()
        mock_catalog.ensure_catalog_available.return_value = None
        mock_catalog.get_model_info.return_value = Mock(
            model_id="test-model-id",
            has_direct_access=True,
            has_regional_cris=False,
            has_global_cris=False,
            regional_cris_profile_id=None,
            global_cris_profile_id=None,
        )
        mock_catalog_cls.return_value = mock_catalog

        mock_auth_instance = Mock()
        mock_auth_manager_cls.return_value = mock_auth_instance

        LLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1"],
            boto3_config=None,
        )

        # AuthManager should have been called with a Boto3Config instance (not None)
        call_kwargs = mock_auth_manager_cls.call_args
        boto3_config_arg = call_kwargs.kwargs.get("boto3_config")
        assert boto3_config_arg is not None
        assert isinstance(boto3_config_arg, Boto3Config)

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.llm_manager.AuthManager")
    def test_default_boto3_config_has_bedrock_optimized_defaults(
        self,
        mock_auth_manager_cls: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """Default Boto3Config created by LLMManager has Bedrock-optimized defaults."""
        mock_catalog = Mock()
        mock_catalog.ensure_catalog_available.return_value = None
        mock_catalog.get_model_info.return_value = Mock(
            model_id="test-model-id",
            has_direct_access=True,
            has_regional_cris=False,
            has_global_cris=False,
            regional_cris_profile_id=None,
            global_cris_profile_id=None,
        )
        mock_catalog_cls.return_value = mock_catalog

        mock_auth_instance = Mock()
        mock_auth_manager_cls.return_value = mock_auth_instance

        LLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1"],
            boto3_config=None,
        )

        call_kwargs = mock_auth_manager_cls.call_args
        boto3_config_arg = call_kwargs.kwargs.get("boto3_config")
        assert boto3_config_arg.read_timeout == 600
        assert boto3_config_arg.connect_timeout == 60
        assert boto3_config_arg.max_pool_connections == 10
        assert boto3_config_arg.retries_max_attempts == 3

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.llm_manager.AuthManager")
    def test_custom_boto3_config_forwarded_to_auth_manager(
        self,
        mock_auth_manager_cls: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """Custom Boto3Config is forwarded unchanged to AuthManager."""
        mock_catalog = Mock()
        mock_catalog.ensure_catalog_available.return_value = None
        mock_catalog.get_model_info.return_value = Mock(
            model_id="test-model-id",
            has_direct_access=True,
            has_regional_cris=False,
            has_global_cris=False,
            regional_cris_profile_id=None,
            global_cris_profile_id=None,
        )
        mock_catalog_cls.return_value = mock_catalog

        mock_auth_instance = Mock()
        mock_auth_manager_cls.return_value = mock_auth_instance

        custom_config = Boto3Config(
            read_timeout=900,
            connect_timeout=120,
            max_pool_connections=20,
            retries_max_attempts=5,
        )

        LLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1"],
            boto3_config=custom_config,
        )

        call_kwargs = mock_auth_manager_cls.call_args
        boto3_config_arg = call_kwargs.kwargs.get("boto3_config")
        assert boto3_config_arg is custom_config
