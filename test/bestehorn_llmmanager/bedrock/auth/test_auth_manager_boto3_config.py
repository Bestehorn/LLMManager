"""
Unit tests for AuthManager boto3 config propagation.

Tests verify that when a Boto3Config is provided to AuthManager, the resulting
botocore.config.Config is correctly passed to session.client() calls for both
bedrock-runtime and bedrock control plane clients. Also verifies backward
compatibility when no Boto3Config is provided.

Validates: Requirements 2.2, 5.1, 5.2
"""

from unittest.mock import Mock, patch

import botocore.config

from bestehorn_llmmanager.bedrock.auth.auth_manager import AuthManager
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig,
    AuthenticationType,
    Boto3Config,
)


class TestAuthManagerBedrockRuntimeClientWithConfig:
    """Tests that bedrock-runtime clients receive botocore config when Boto3Config is provided.

    Validates: Requirements 2.2, 5.1
    """

    def setup_method(self) -> None:
        """Set up test fixtures with a Boto3Config."""
        self.boto3_config = Boto3Config(
            read_timeout=900,
            connect_timeout=120,
            max_pool_connections=20,
            retries_max_attempts=5,
        )
        self.auth_config = AuthConfig(auth_type=AuthenticationType.AUTO)
        self.auth_manager = AuthManager(
            auth_config=self.auth_config,
            boto3_config=self.boto3_config,
        )

    @patch.object(AuthManager, "_test_bedrock_access")
    @patch.object(AuthManager, "get_session")
    def test_bedrock_runtime_client_receives_botocore_config(
        self,
        mock_get_session: Mock,
        mock_test_bedrock_access: Mock,
    ) -> None:
        """session.client('bedrock-runtime') receives config= kwarg with botocore Config."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_client(region="us-east-1")

        mock_session.client.assert_called_once_with(
            "bedrock-runtime",
            region_name="us-east-1",
            config=self.auth_manager._botocore_config,
        )

    @patch.object(AuthManager, "_test_bedrock_access")
    @patch.object(AuthManager, "get_session")
    def test_bedrock_runtime_config_is_botocore_config_instance(
        self,
        mock_get_session: Mock,
        mock_test_bedrock_access: Mock,
    ) -> None:
        """The config passed to bedrock-runtime client is a botocore.config.Config instance."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_client(region="us-east-1")

        call_kwargs = mock_session.client.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert isinstance(config_arg, botocore.config.Config)

    @patch.object(AuthManager, "_test_bedrock_access")
    @patch.object(AuthManager, "get_session")
    def test_bedrock_runtime_config_preserves_read_timeout(
        self,
        mock_get_session: Mock,
        mock_test_bedrock_access: Mock,
    ) -> None:
        """The botocore config passed to bedrock-runtime preserves read_timeout value."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_client(region="us-west-2")

        call_kwargs = mock_session.client.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.read_timeout == 900

    @patch.object(AuthManager, "_test_bedrock_access")
    @patch.object(AuthManager, "get_session")
    def test_bedrock_runtime_config_preserves_connect_timeout(
        self,
        mock_get_session: Mock,
        mock_test_bedrock_access: Mock,
    ) -> None:
        """The botocore config passed to bedrock-runtime preserves connect_timeout value."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_client(region="us-west-2")

        call_kwargs = mock_session.client.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.connect_timeout == 120


class TestAuthManagerBedrockControlClientWithConfig:
    """Tests that bedrock control plane clients receive botocore config.

    Validates: Requirements 2.2, 5.2
    """

    def setup_method(self) -> None:
        """Set up test fixtures with a Boto3Config."""
        self.boto3_config = Boto3Config(
            read_timeout=900,
            connect_timeout=120,
            max_pool_connections=20,
            retries_max_attempts=5,
        )
        self.auth_config = AuthConfig(auth_type=AuthenticationType.AUTO)
        self.auth_manager = AuthManager(
            auth_config=self.auth_config,
            boto3_config=self.boto3_config,
        )

    @patch.object(AuthManager, "get_session")
    def test_bedrock_control_client_receives_botocore_config(
        self,
        mock_get_session: Mock,
    ) -> None:
        """session.client('bedrock') receives config= kwarg with botocore Config."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_control_client(region="us-east-1")

        mock_session.client.assert_called_once_with(
            "bedrock",
            region_name="us-east-1",
            config=self.auth_manager._botocore_config,
        )

    @patch.object(AuthManager, "get_session")
    def test_bedrock_control_config_is_botocore_config_instance(
        self,
        mock_get_session: Mock,
    ) -> None:
        """The config passed to bedrock control client is a botocore.config.Config instance."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_control_client(region="eu-west-1")

        call_kwargs = mock_session.client.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert isinstance(config_arg, botocore.config.Config)

    @patch.object(AuthManager, "get_session")
    def test_bedrock_control_config_preserves_read_timeout(
        self,
        mock_get_session: Mock,
    ) -> None:
        """The botocore config passed to bedrock control client preserves read_timeout."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_control_client(region="eu-west-1")

        call_kwargs = mock_session.client.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.read_timeout == 900


class TestAuthManagerBothClientsReceiveSameConfig:
    """Tests that both client types receive the same botocore config instance.

    Validates: Requirements 5.1, 5.2
    """

    def setup_method(self) -> None:
        """Set up test fixtures with a Boto3Config."""
        self.boto3_config = Boto3Config(
            read_timeout=300,
            connect_timeout=30,
            max_pool_connections=15,
            retries_max_attempts=2,
        )
        self.auth_manager = AuthManager(
            auth_config=AuthConfig(auth_type=AuthenticationType.AUTO),
            boto3_config=self.boto3_config,
        )

    @patch.object(AuthManager, "_test_bedrock_access")
    @patch.object(AuthManager, "get_session")
    def test_both_clients_receive_same_config_object(
        self,
        mock_get_session: Mock,
        mock_test_bedrock_access: Mock,
    ) -> None:
        """Both bedrock-runtime and bedrock clients receive the same config object."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_client(region="us-east-1")
        runtime_call_kwargs = mock_session.client.call_args_list[0]
        runtime_config = runtime_call_kwargs.kwargs.get("config") or runtime_call_kwargs[1].get(
            "config"
        )

        mock_session.client.reset_mock()
        self.auth_manager.get_bedrock_control_client(region="us-east-1")
        control_call_kwargs = mock_session.client.call_args_list[0]
        control_config = control_call_kwargs.kwargs.get("config") or control_call_kwargs[1].get(
            "config"
        )

        assert runtime_config is control_config


class TestAuthManagerBackwardCompatNoConfig:
    """Tests backward compatibility when no Boto3Config is provided.

    Validates: Requirements 2.2, 5.1, 5.2
    """

    def setup_method(self) -> None:
        """Set up test fixtures without Boto3Config (backward compat)."""
        self.auth_config = AuthConfig(auth_type=AuthenticationType.AUTO)
        self.auth_manager = AuthManager(auth_config=self.auth_config)

    def test_botocore_config_is_none_when_no_boto3_config(self) -> None:
        """AuthManager._botocore_config is None when no Boto3Config is provided."""
        assert self.auth_manager._botocore_config is None

    @patch.object(AuthManager, "_test_bedrock_access")
    @patch.object(AuthManager, "get_session")
    def test_bedrock_runtime_client_receives_config_none(
        self,
        mock_get_session: Mock,
        mock_test_bedrock_access: Mock,
    ) -> None:
        """session.client('bedrock-runtime') receives config=None when no Boto3Config."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_client(region="us-east-1")

        mock_session.client.assert_called_once_with(
            "bedrock-runtime",
            region_name="us-east-1",
            config=None,
        )

    @patch.object(AuthManager, "get_session")
    def test_bedrock_control_client_receives_config_none(
        self,
        mock_get_session: Mock,
    ) -> None:
        """session.client('bedrock') receives config=None when no Boto3Config."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_control_client(region="us-east-1")

        mock_session.client.assert_called_once_with(
            "bedrock",
            region_name="us-east-1",
            config=None,
        )


class TestAuthManagerDefaultBoto3Config:
    """Tests that AuthManager correctly converts default Boto3Config.

    Validates: Requirements 2.2, 5.1, 5.2
    """

    def setup_method(self) -> None:
        """Set up test fixtures with default Boto3Config."""
        self.auth_manager = AuthManager(
            auth_config=AuthConfig(auth_type=AuthenticationType.AUTO),
            boto3_config=Boto3Config(),
        )

    def test_default_boto3_config_produces_botocore_config(self) -> None:
        """Default Boto3Config() produces a non-None botocore config."""
        assert self.auth_manager._botocore_config is not None
        assert isinstance(
            self.auth_manager._botocore_config,
            botocore.config.Config,
        )

    def test_default_boto3_config_has_600_read_timeout(self) -> None:
        """Default Boto3Config produces botocore config with 600s read_timeout."""
        assert self.auth_manager._botocore_config is not None
        assert self.auth_manager._botocore_config.read_timeout == 600

    @patch.object(AuthManager, "_test_bedrock_access")
    @patch.object(AuthManager, "get_session")
    def test_default_config_propagates_to_bedrock_runtime(
        self,
        mock_get_session: Mock,
        mock_test_bedrock_access: Mock,
    ) -> None:
        """Default Boto3Config propagates 600s read_timeout to bedrock-runtime client."""
        mock_session = Mock()
        mock_client = Mock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        self.auth_manager.get_bedrock_client(region="us-east-1")

        call_kwargs = mock_session.client.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg is not None
        assert config_arg.read_timeout == 600
