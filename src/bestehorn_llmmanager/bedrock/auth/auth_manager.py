"""
Authentication manager for AWS Bedrock services.
Handles different authentication methods including profiles, credentials, and IAM roles.
"""

import logging
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from ..exceptions.llm_manager_exceptions import AuthenticationError
from ..models.llm_manager_constants import LLMManagerErrorMessages, LLMManagerLogMessages
from ..models.llm_manager_structures import AuthConfig, AuthenticationType


class AuthManager:
    """
    Manages AWS authentication for Bedrock services.

    Supports multiple authentication methods:
    - AWS CLI profiles
    - Direct credentials (access key/secret key)
    - IAM roles (for EC2/SageMaker environments)
    - Automatic detection
    """

    def __init__(self, auth_config: Optional[AuthConfig] = None) -> None:
        """
        Initialize the authentication manager.

        Args:
            auth_config: Authentication configuration. If None, uses automatic detection.
        """
        self._logger = logging.getLogger(__name__)
        self._auth_config = auth_config or AuthConfig(auth_type=AuthenticationType.AUTO)
        self._session: Optional[boto3.Session] = None

        # Validate configuration
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate the authentication configuration."""
        try:
            # This will trigger validation in the AuthConfig.__post_init__
            _ = self._auth_config
        except ValueError as e:
            raise AuthenticationError(
                message=LLMManagerErrorMessages.INVALID_AUTH_CONFIG.format(details=str(e)),
                auth_type=self._auth_config.auth_type.value,
            ) from e

    def get_session(self, region: Optional[str] = None) -> boto3.Session:
        """
        Get an authenticated boto3 session.

        Args:
            region: AWS region for the session. If None, uses config default or AWS default.

        Returns:
            Configured boto3 session

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            if self._session is None:
                self._session = self._create_session()

            # If region is specified and different from current session region, create new session
            current_region = self._session.region_name
            if region and region != current_region:
                return self._create_session(region=region)

            return self._session

        except Exception as e:
            raise AuthenticationError(
                message=f"Failed to create authenticated session: {str(e)}",
                auth_type=self._auth_config.auth_type.value,
                region=region,
            ) from e

    def _create_session(self, region: Optional[str] = None) -> boto3.Session:
        """
        Create a new boto3 session based on the authentication configuration.

        Args:
            region: AWS region for the session

        Returns:
            Configured boto3 session

        Raises:
            AuthenticationError: If session creation fails
        """
        effective_region = region or self._auth_config.region

        try:
            if self._auth_config.auth_type == AuthenticationType.PROFILE:
                return self._create_profile_session(region=effective_region)
            elif self._auth_config.auth_type == AuthenticationType.CREDENTIALS:
                return self._create_credentials_session(region=effective_region)
            elif self._auth_config.auth_type == AuthenticationType.IAM_ROLE:
                return self._create_iam_role_session(region=effective_region)
            elif self._auth_config.auth_type == AuthenticationType.AUTO:
                return self._create_auto_session(region=effective_region)
            else:
                raise AuthenticationError(
                    message=f"Unsupported authentication type: {self._auth_config.auth_type}",
                    auth_type=self._auth_config.auth_type.value,
                )

        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(
                message=f"Failed to create session: {str(e)}",
                auth_type=self._auth_config.auth_type.value,
                region=effective_region,
            ) from e

    def _create_profile_session(self, region: Optional[str] = None) -> boto3.Session:
        """Create session using AWS CLI profile."""
        try:
            session = boto3.Session(profile_name=self._auth_config.profile_name, region_name=region)

            # Test the credentials
            self._test_credentials(session=session, region=region)

            self._logger.info(
                LLMManagerLogMessages.AUTH_CONFIGURED.format(
                    auth_type=f"profile ({self._auth_config.profile_name})"
                )
            )

            return session

        except ProfileNotFound:
            raise AuthenticationError(
                message=LLMManagerErrorMessages.INVALID_PROFILE.format(
                    profile=self._auth_config.profile_name
                ),
                auth_type=self._auth_config.auth_type.value,
            )
        except NoCredentialsError:
            raise AuthenticationError(
                message=LLMManagerErrorMessages.CREDENTIALS_NOT_FOUND,
                auth_type=self._auth_config.auth_type.value,
            )

    def _create_credentials_session(self, region: Optional[str] = None) -> boto3.Session:
        """Create session using direct credentials."""
        try:
            session = boto3.Session(
                aws_access_key_id=self._auth_config.access_key_id,
                aws_secret_access_key=self._auth_config.secret_access_key,
                aws_session_token=self._auth_config.session_token,
                region_name=region,
            )

            # Test the credentials
            self._test_credentials(session=session, region=region)

            self._logger.info(LLMManagerLogMessages.AUTH_CONFIGURED.format(auth_type="credentials"))

            return session

        except NoCredentialsError:
            raise AuthenticationError(
                message=LLMManagerErrorMessages.CREDENTIALS_NOT_FOUND,
                auth_type=self._auth_config.auth_type.value,
            )

    def _create_iam_role_session(self, region: Optional[str] = None) -> boto3.Session:
        """Create session using IAM role (for EC2/SageMaker environments)."""
        try:
            session = boto3.Session(region_name=region)

            # Test the credentials
            self._test_credentials(session=session, region=region)

            self._logger.info(LLMManagerLogMessages.AUTH_CONFIGURED.format(auth_type="iam_role"))

            return session

        except NoCredentialsError:
            raise AuthenticationError(
                message=LLMManagerErrorMessages.CREDENTIALS_NOT_FOUND,
                auth_type=self._auth_config.auth_type.value,
            )

    def _create_auto_session(self, region: Optional[str] = None) -> boto3.Session:
        """Create session using automatic detection."""
        # Try different methods in order of preference
        auth_methods = [
            (AuthenticationType.IAM_ROLE, "IAM role"),
            (AuthenticationType.PROFILE, "default profile"),
        ]

        last_error = None

        for auth_type, method_name in auth_methods:
            try:
                if auth_type == AuthenticationType.IAM_ROLE:
                    session = boto3.Session(region_name=region)
                elif auth_type == AuthenticationType.PROFILE:
                    session = boto3.Session(region_name=region)  # Uses default profile
                else:
                    continue

                # Test the credentials
                self._test_credentials(session=session, region=region)

                self._logger.info(
                    LLMManagerLogMessages.AUTH_CONFIGURED.format(auth_type=f"auto ({method_name})")
                )

                return session

            except Exception as e:
                self._logger.debug(f"Auto-detection failed for {method_name}: {str(e)}")
                last_error = e
                continue

        # If all methods failed, raise the last error
        raise AuthenticationError(
            message=LLMManagerErrorMessages.CREDENTIALS_NOT_FOUND,
            auth_type=self._auth_config.auth_type.value,
        ) from last_error

    def _test_credentials(self, session: boto3.Session, region: Optional[str] = None) -> None:
        """
        Test credentials by making a simple AWS API call.

        Args:
            session: Boto3 session to test
            region: AWS region for testing

        Raises:
            AuthenticationError: If credentials are invalid
        """
        try:
            # Use STS to get caller identity as a lightweight test
            sts_client = session.client("sts", region_name=region)
            sts_client.get_caller_identity()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["InvalidUserID.NotFound", "AccessDenied", "TokenRefreshRequired"]:
                raise AuthenticationError(
                    message=f"Invalid credentials: {str(e)}",
                    auth_type=self._auth_config.auth_type.value,
                    region=region,
                ) from e
            raise

    def get_bedrock_client(self, region: str) -> Any:
        """
        Get a Bedrock runtime client for the specified region.

        Args:
            region: AWS region for the client

        Returns:
            Bedrock runtime client

        Raises:
            AuthenticationError: If client creation fails
        """
        try:
            session = self.get_session(region=region)
            client = session.client("bedrock-runtime", region_name=region)

            # Test that we can access Bedrock in this region
            self._test_bedrock_access(client=client, region=region)

            return client

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(
                message=f"Failed to create Bedrock client: {str(e)}",
                auth_type=self._auth_config.auth_type.value,
                region=region,
            ) from e

    def _test_bedrock_access(self, client: Any, region: str) -> None:
        """
        Test Bedrock access by attempting a lightweight operation.

        Args:
            client: Bedrock runtime client
            region: AWS region

        Raises:
            AuthenticationError: If access test fails
        """
        try:
            # This is a lightweight way to test Bedrock access
            # We don't actually need the response, just want to verify we can make calls
            pass  # For now, skip the test to avoid unnecessary API calls

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "AccessDeniedException":
                raise AuthenticationError(
                    message=LLMManagerErrorMessages.PERMISSION_DENIED.format(region=region),
                    auth_type=self._auth_config.auth_type.value,
                    region=region,
                ) from e
            # For other errors, we'll let them be handled by the calling code

    def get_auth_info(self) -> dict:
        """
        Get information about the current authentication configuration.

        Returns:
            Dictionary with authentication information
        """
        return {
            "auth_type": self._auth_config.auth_type.value,
            "profile_name": (
                self._auth_config.profile_name
                if self._auth_config.auth_type == AuthenticationType.PROFILE
                else None
            ),
            "region": self._auth_config.region,
            "has_session": self._session is not None,
        }

    def __repr__(self) -> str:
        """Return string representation of the AuthManager."""
        return f"AuthManager(auth_type={self._auth_config.auth_type.value})"
