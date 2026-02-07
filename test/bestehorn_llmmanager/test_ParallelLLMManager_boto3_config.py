"""
Unit tests for ParallelLLMManager boto3_config forwarding and end-to-end propagation.

Tests verify that ParallelLLMManager correctly forwards boto3_config to its
internal LLMManager instance, and that custom config values propagate all the
way to boto3 clients.

Validates: Requirements 2.1, 2.3, 3.1, 3.2, 3.3
"""

from unittest.mock import Mock, patch

from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    Boto3Config,
)
from bestehorn_llmmanager.parallel_llm_manager import ParallelLLMManager


class TestParallelLLMManagerForwardsBoto3Config:
    """Tests that ParallelLLMManager forwards boto3_config to internal LLMManager.

    Validates: Requirements 3.1, 3.2
    """

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.llm_manager.AuthManager")
    def test_forwards_custom_boto3_config_to_llm_manager(
        self,
        mock_auth_manager_cls: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """ParallelLLMManager forwards custom Boto3Config to internal LLMManager."""
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
        mock_auth_manager_cls.return_value = Mock()

        custom_config = Boto3Config(
            read_timeout=900,
            connect_timeout=120,
            max_pool_connections=20,
            retries_max_attempts=5,
        )

        ParallelLLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1", "us-west-2"],
            boto3_config=custom_config,
        )

        # The internal LLMManager's AuthManager should have received the config
        call_kwargs = mock_auth_manager_cls.call_args
        boto3_config_arg = call_kwargs.kwargs.get("boto3_config")
        assert boto3_config_arg is custom_config

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.llm_manager.AuthManager")
    def test_forwards_none_boto3_config_creates_default(
        self,
        mock_auth_manager_cls: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """ParallelLLMManager with boto3_config=None creates default Boto3Config."""
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
        mock_auth_manager_cls.return_value = Mock()

        ParallelLLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1", "us-west-2"],
            boto3_config=None,
        )

        # LLMManager should have defaulted to Boto3Config() and passed it
        call_kwargs = mock_auth_manager_cls.call_args
        boto3_config_arg = call_kwargs.kwargs.get("boto3_config")
        assert boto3_config_arg is not None
        assert isinstance(boto3_config_arg, Boto3Config)
        assert boto3_config_arg.read_timeout == 600


class TestParallelLLMManagerEndToEndPropagation:
    """Tests end-to-end propagation of boto3_config through to boto3 clients.

    Validates: Requirements 2.1, 2.3, 3.3
    """

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.bedrock.auth.auth_manager.AuthManager._test_credentials")
    def test_read_timeout_900_propagates_to_bedrock_runtime_client(
        self,
        mock_test_credentials: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """ParallelLLMManager with read_timeout=900 propagates to bedrock-runtime clients."""
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

        custom_config = Boto3Config(read_timeout=900)

        manager = ParallelLLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1", "us-west-2"],
            boto3_config=custom_config,
        )

        # Access the internal LLMManager's AuthManager to verify config
        internal_auth_manager = manager._llm_manager._auth_manager
        botocore_config = internal_auth_manager._botocore_config

        assert botocore_config is not None
        assert botocore_config.read_timeout == 900

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.bedrock.auth.auth_manager.AuthManager._test_credentials")
    def test_all_config_fields_propagate_end_to_end(
        self,
        mock_test_credentials: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """All Boto3Config fields propagate end-to-end to botocore config."""
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

        custom_config = Boto3Config(
            read_timeout=900,
            connect_timeout=120,
            max_pool_connections=25,
            retries_max_attempts=5,
        )

        manager = ParallelLLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1", "us-west-2"],
            boto3_config=custom_config,
        )

        internal_auth_manager = manager._llm_manager._auth_manager
        botocore_config = internal_auth_manager._botocore_config

        assert botocore_config is not None
        assert botocore_config.read_timeout == 900
        assert botocore_config.connect_timeout == 120
        assert botocore_config.max_pool_connections == 25
        assert botocore_config.retries == {"max_attempts": 5}

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.bedrock.auth.auth_manager.AuthManager._test_credentials")
    @patch("bestehorn_llmmanager.bedrock.auth.auth_manager.AuthManager._test_bedrock_access")
    def test_read_timeout_900_reaches_session_client_call(
        self,
        mock_test_bedrock_access: Mock,
        mock_test_credentials: Mock,
        mock_catalog_cls: Mock,
    ) -> None:
        """read_timeout=900 reaches the actual session.client() call for bedrock-runtime."""
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

        custom_config = Boto3Config(read_timeout=900)

        manager = ParallelLLMManager(
            models=["Claude Haiku 4 5 20251001"],
            regions=["us-east-1", "us-west-2"],
            boto3_config=custom_config,
        )

        # Mock the session to capture the client() call
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client

        internal_auth_manager = manager._llm_manager._auth_manager
        with patch.object(internal_auth_manager, "get_session", return_value=mock_session):
            internal_auth_manager.get_bedrock_client(region="us-east-1")

        call_kwargs = mock_session.client.call_args
        config_arg = call_kwargs.kwargs.get("config")
        assert config_arg is not None
        assert config_arg.read_timeout == 900
