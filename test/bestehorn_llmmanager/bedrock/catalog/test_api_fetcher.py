"""
Tests for BedrockAPIFetcher class.

This module tests the API fetching functionality including:
- Foundation models API fetching
- Inference profiles API fetching
- Parallel execution across regions
- Error handling per region
- Retry logic
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from bestehorn_llmmanager.bedrock.auth.auth_manager import AuthManager
from bestehorn_llmmanager.bedrock.catalog.api_fetcher import BedrockAPIFetcher, RawCatalogData
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    APIFetchError,
    APIThrottleError,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig,
    AuthenticationType,
)


def _client_error(code: str, operation: str = "ListFoundationModels") -> ClientError:
    """Build a botocore ClientError with the given AWS error code."""
    return ClientError(
        error_response={"Error": {"Code": code, "Message": f"{code} occurred"}},
        operation_name=operation,
    )


@pytest.fixture
def mock_auth_manager():
    """Create a mock AuthManager for testing."""
    auth_config = AuthConfig(auth_type=AuthenticationType.AUTO)
    auth_manager = AuthManager(auth_config=auth_config)
    return auth_manager


@pytest.fixture
def sample_foundation_models():
    """Sample foundation models API response."""
    return [
        {
            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
            "modelName": "Claude 3 Sonnet",
            "providerName": "Anthropic",
        },
        {
            "modelId": "amazon.titan-text-express-v1",
            "modelName": "Titan Text G1 - Express",
            "providerName": "Amazon",
        },
    ]


@pytest.fixture
def sample_inference_profiles():
    """Sample inference profiles API response."""
    return [
        {
            "inferenceProfileId": "us.anthropic.claude-3-sonnet-20240229-v1:0",
            "inferenceProfileName": "Claude 3 Sonnet",
            "type": "SYSTEM_DEFINED",
        }
    ]


class TestRawCatalogData:
    """Tests for RawCatalogData container class."""

    def test_init_creates_empty_container(self):
        """Test that initialization creates empty data structures."""
        data = RawCatalogData()

        assert data.foundation_models == {}
        assert data.inference_profiles == {}
        assert data.successful_regions == []
        assert data.failed_regions == {}

    def test_add_region_data(self, sample_foundation_models, sample_inference_profiles):
        """Test adding data for a successful region."""
        data = RawCatalogData()
        data.add_region_data(
            region="us-east-1",
            models=sample_foundation_models,
            profiles=sample_inference_profiles,
        )

        assert "us-east-1" in data.foundation_models
        assert "us-east-1" in data.inference_profiles
        assert "us-east-1" in data.successful_regions
        assert len(data.foundation_models["us-east-1"]) == 2
        assert len(data.inference_profiles["us-east-1"]) == 1

    def test_has_data_returns_true_with_data(
        self, sample_foundation_models, sample_inference_profiles
    ):
        """Test has_data returns True when data exists."""
        data = RawCatalogData()
        data.add_region_data(
            region="us-east-1",
            models=sample_foundation_models,
            profiles=sample_inference_profiles,
        )

        assert data.has_data is True


class TestBedrockAPIFetcherInit:
    """Tests for BedrockAPIFetcher initialization."""

    def test_init_with_defaults(self, mock_auth_manager):
        """Test initialization with default parameters."""
        from bestehorn_llmmanager.bedrock.models.catalog_constants import CatalogDefaults

        fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)

        assert fetcher._auth_manager == mock_auth_manager
        assert fetcher._timeout == 30
        assert fetcher._max_workers == 10
        # Discovery retry budget raised for fan-out cold-start bursts (issue #30).
        assert fetcher._max_retries == CatalogDefaults.DEFAULT_MAX_RETRIES
        assert fetcher._max_retries >= 5


class TestBedrockAPIFetcherFetchFoundationModels:
    """Tests for _fetch_foundation_models method."""

    def test_fetch_foundation_models_success(self, mock_auth_manager, sample_foundation_models):
        """Test successful foundation models fetching."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": sample_foundation_models
        }

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)
            result = fetcher._fetch_foundation_models(region="us-east-1")

            assert len(result) == 2
            assert result == sample_foundation_models
            mock_client.list_foundation_models.assert_called_once()

    def test_fetch_foundation_models_empty_response(self, mock_auth_manager):
        """Test handling of empty model summaries."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {"modelSummaries": []}

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)
            result = fetcher._fetch_foundation_models(region="us-east-1")

            assert result == []


class TestBedrockAPIFetcherFetchAllData:
    """Tests for fetch_all_data method."""

    def test_fetch_all_data_single_region_success(
        self, mock_auth_manager, sample_foundation_models, sample_inference_profiles
    ):
        """Test successful fetching from a single region."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": sample_foundation_models
        }
        mock_client.list_inference_profiles.return_value = {
            "inferenceProfileSummaries": sample_inference_profiles
        }

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)
            result = fetcher.fetch_all_data(regions=["us-east-1"])

            assert result.has_data is True
            assert len(result.successful_regions) == 1
            assert "us-east-1" in result.successful_regions

    def test_add_region_failure(self):
        """Test recording a failed region query."""
        data = RawCatalogData()
        data.add_region_failure(region="us-west-2", error="Connection timeout")

        assert "us-west-2" in data.failed_regions
        assert data.failed_regions["us-west-2"] == "Connection timeout"
        assert "us-west-2" not in data.successful_regions

    def test_has_data_empty(self):
        """Test has_data returns False for empty container."""
        data = RawCatalogData()
        assert data.has_data is False

    def test_total_models(self, sample_foundation_models, sample_inference_profiles):
        """Test total_models counts across all regions."""
        data = RawCatalogData()
        data.add_region_data(
            region="us-east-1",
            models=sample_foundation_models,
            profiles=sample_inference_profiles,
        )
        data.add_region_data(
            region="us-west-2",
            models=sample_foundation_models[:1],
            profiles=[],
        )

        assert data.total_models == 3

    def test_total_profiles(self, sample_foundation_models, sample_inference_profiles):
        """Test total_profiles counts across all regions."""
        data = RawCatalogData()
        data.add_region_data(
            region="us-east-1",
            models=sample_foundation_models,
            profiles=sample_inference_profiles,
        )
        data.add_region_data(
            region="us-west-2",
            models=[],
            profiles=sample_inference_profiles,
        )

        assert data.total_profiles == 2


class TestBedrockAPIFetcherFetchInferenceProfiles:
    """Tests for _fetch_inference_profiles method."""

    def test_fetch_inference_profiles_success(self, mock_auth_manager, sample_inference_profiles):
        """Test successful inference profiles fetching."""
        mock_client = MagicMock()
        mock_client.list_inference_profiles.return_value = {
            "inferenceProfileSummaries": sample_inference_profiles
        }

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)
            result = fetcher._fetch_inference_profiles(region="us-east-1")

            assert len(result) == 1
            assert result == sample_inference_profiles
            mock_client.list_inference_profiles.assert_called_once_with(typeEquals="SYSTEM_DEFINED")

    def test_fetch_inference_profiles_empty_response(self, mock_auth_manager):
        """Test handling of empty inference profiles."""
        mock_client = MagicMock()
        mock_client.list_inference_profiles.return_value = {"inferenceProfileSummaries": []}

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)
            result = fetcher._fetch_inference_profiles(region="us-east-1")

            assert result == []

    def test_fetch_inference_profiles_missing_field(self, mock_auth_manager):
        """Test handling of missing inferenceProfileSummaries field."""
        mock_client = MagicMock()
        mock_client.list_inference_profiles.return_value = {}

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)
            result = fetcher._fetch_inference_profiles(region="us-east-1")

            assert result == []

    def test_fetch_inference_profiles_invalid_response_type(self, mock_auth_manager):
        """Test handling of invalid response type."""
        mock_client = MagicMock()
        mock_client.list_inference_profiles.return_value = {
            "inferenceProfileSummaries": "not a list"
        }

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager)

            with pytest.raises(APIFetchError, match="INFERENCE_PROFILE_SUMMARIES is not a list"):
                fetcher._fetch_inference_profiles(region="us-east-1")


class TestBedrockAPIFetcherRetryLogic:
    """Tests for retry logic with exponential backoff."""

    def test_retry_on_transient_error(self, mock_auth_manager, sample_foundation_models):
        """Test that transient errors trigger retry."""
        mock_client = MagicMock()

        mock_client.list_foundation_models.side_effect = [
            ClientError(
                error_response={"Error": {"Code": "ServiceUnavailable"}},
                operation_name="ListFoundationModels",
            ),
            ClientError(
                error_response={"Error": {"Code": "ServiceUnavailable"}},
                operation_name="ListFoundationModels",
            ),
            {"modelSummaries": sample_foundation_models},
        ]

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=3)
            result = fetcher._fetch_foundation_models(region="us-east-1")

            assert result == sample_foundation_models
            assert mock_client.list_foundation_models.call_count == 3

    def test_retry_exhausted(self, mock_auth_manager):
        """Test that retry logic eventually gives up."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = ClientError(
            error_response={"Error": {"Code": "ServiceUnavailable"}},
            operation_name="ListFoundationModels",
        )

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=3)

            with pytest.raises(ClientError):
                _ = fetcher._fetch_foundation_models(region="us-east-1")

            assert mock_client.list_foundation_models.call_count == 3


class TestBedrockAPIFetcherParallelExecution:
    """Tests for parallel execution across regions."""

    def test_parallel_execution_uses_thread_pool(
        self, mock_auth_manager, sample_foundation_models, sample_inference_profiles
    ):
        """Test that parallel execution uses ThreadPoolExecutor."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": sample_foundation_models
        }
        mock_client.list_inference_profiles.return_value = {
            "inferenceProfileSummaries": sample_inference_profiles
        }

        with patch.object(
            mock_auth_manager,
            "get_bedrock_control_client",
            return_value=mock_client,
        ):
            with patch(
                "bestehorn_llmmanager.bedrock.catalog.api_fetcher.ThreadPoolExecutor"
            ) as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor_class.return_value.__enter__.return_value = mock_executor

                mock_future = MagicMock()
                mock_future.result.return_value = (
                    sample_foundation_models,
                    sample_inference_profiles,
                )
                mock_executor.submit.return_value = mock_future

                with patch(
                    "bestehorn_llmmanager.bedrock.catalog.api_fetcher.as_completed",
                    return_value=[mock_future],
                ):
                    fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_workers=5)
                    _ = fetcher.fetch_all_data(regions=["us-east-1", "us-west-2"])

                    mock_executor_class.assert_called_once_with(max_workers=5)
                    assert mock_executor.submit.call_count == 2

    def test_parallel_execution_respects_max_workers(self, mock_auth_manager):
        """Test that max_workers parameter is respected."""
        with patch(
            "bestehorn_llmmanager.bedrock.catalog.api_fetcher.ThreadPoolExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value.__enter__.return_value = mock_executor

            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_workers=3)

            with patch.object(fetcher, "_fetch_region_data", return_value=([], [])):
                with patch(
                    "bestehorn_llmmanager.bedrock.catalog.api_fetcher.as_completed", return_value=[]
                ):
                    try:
                        fetcher.fetch_all_data(regions=["us-east-1"])
                    except APIFetchError:
                        pass

            mock_executor_class.assert_called_once_with(max_workers=3)


class TestBedrockAPIFetcherThrottleRetry:
    """Tests for issue #30: throttled control-plane discovery must RETRY (not fail-fast).

    Acceptance criteria from the change request:
    1. ThrottlingException on the first N calls then success -> discovery RETRIES and
       returns the catalog; no APIFetchError escapes.
    2. ThrottlingException is retried (predicate matches) while AccessDeniedException is
       NOT retried (fails fast).
    3. Backoff is jittered (the fetcher uses a jittered wait strategy).
    4. A partial-region throttle does not become a fatal failure: a model present in a
       successfully-fetched region is returned even if another region is throttle-exhausted.
    5. "Throttled, retries exhausted" is distinguishable from "genuinely not found"
       (a dedicated retryable APIThrottleError type, subclass of APIFetchError).
    """

    def _patch_client(self, mock_auth_manager, mock_client):
        return patch.object(
            mock_auth_manager, "get_bedrock_control_client", return_value=mock_client
        )

    def test_throttle_is_retried_then_succeeds_foundation_models(
        self, mock_auth_manager, sample_foundation_models
    ):
        """AC#1: a ThrottlingException on the first calls is retried until success."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = [
            _client_error("ThrottlingException"),
            _client_error("ThrottlingException"),
            {"modelSummaries": sample_foundation_models},
        ]
        with self._patch_client(mock_auth_manager, mock_client):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=5)
            result = fetcher._fetch_foundation_models(region="us-east-1")

        assert result == sample_foundation_models
        assert mock_client.list_foundation_models.call_count == 3

    def test_throttle_is_retried_then_succeeds_inference_profiles(
        self, mock_auth_manager, sample_inference_profiles
    ):
        """AC#1: throttled inference-profile discovery is retried until success."""
        mock_client = MagicMock()
        mock_client.list_inference_profiles.side_effect = [
            _client_error("ThrottlingException", operation="ListInferenceProfiles"),
            {"inferenceProfileSummaries": sample_inference_profiles},
        ]
        with self._patch_client(mock_auth_manager, mock_client):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=5)
            result = fetcher._fetch_inference_profiles(region="us-east-1")

        assert result == sample_inference_profiles
        assert mock_client.list_inference_profiles.call_count == 2

    def test_throttle_retries_exhausted_raises_throttle_error(self, mock_auth_manager):
        """AC#1/#5: when throttling never clears, a retryable APIThrottleError surfaces.

        APIThrottleError is a subclass of APIFetchError so existing `except APIFetchError`
        callers still catch it, but the type distinguishes "throttled" from "not found".
        """
        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = _client_error("ThrottlingException")
        with self._patch_client(mock_auth_manager, mock_client):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=3)
            with pytest.raises(APIThrottleError):
                fetcher._fetch_foundation_models(region="us-east-1")

        assert mock_client.list_foundation_models.call_count == 3
        assert issubclass(APIThrottleError, APIFetchError)

    def test_access_denied_is_not_retried(self, mock_auth_manager):
        """AC#2: AccessDeniedException is non-retryable -> fails fast on the first call."""
        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = _client_error("AccessDeniedException")
        with self._patch_client(mock_auth_manager, mock_client):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=5)
            with pytest.raises(APIFetchError) as exc_info:
                fetcher._fetch_foundation_models(region="us-east-1")

        # Exactly one call: not retried.
        assert mock_client.list_foundation_models.call_count == 1
        # And it is NOT the retryable throttle subtype.
        assert not isinstance(exc_info.value, APIThrottleError)

    def test_configurable_retry_budget_is_honored(self, mock_auth_manager):
        """AC (point 3): the per-instance max_retries actually bounds the attempts.

        Regression guard: previously the @retry decorator hardcoded the default, so the
        constructor max_retries argument was dead. A higher budget must mean more attempts.
        """
        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = _client_error("ThrottlingException")
        with self._patch_client(mock_auth_manager, mock_client):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=6)
            with pytest.raises(APIThrottleError):
                fetcher._fetch_foundation_models(region="us-east-1")

        assert mock_client.list_foundation_models.call_count == 6

    def test_default_retry_budget_raised_for_fanout(self):
        """AC (point 3): the default discovery retry budget is raised for fan-out bursts."""
        from bestehorn_llmmanager.bedrock.models.catalog_constants import CatalogDefaults

        assert CatalogDefaults.DEFAULT_MAX_RETRIES >= 5

    def test_backoff_uses_jitter(self, mock_auth_manager):
        """AC#3: the fetcher wait strategy is jittered (de-correlated), not plain exponential.

        A synchronized cold-start fleet must not retry in lockstep. We assert the
        configured tenacity wait strategy is a jittered variant.
        """
        from tenacity import wait_exponential_jitter, wait_random_exponential

        fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=5)
        wait_strategy = fetcher._build_retrying().wait
        assert isinstance(wait_strategy, (wait_exponential_jitter, wait_random_exponential))

    def test_partial_region_throttle_not_fatal_when_model_present_elsewhere(
        self, mock_auth_manager, sample_foundation_models, sample_inference_profiles
    ):
        """AC#4: throttle-exhausted on one region, success on another -> partial catalog.

        fetch_all_data must return data for the region(s) that succeeded rather than
        failing the whole sweep when at least one region was fetched.
        """
        good_client = MagicMock()
        good_client.list_foundation_models.return_value = {
            "modelSummaries": sample_foundation_models
        }
        good_client.list_inference_profiles.return_value = {
            "inferenceProfileSummaries": sample_inference_profiles
        }
        throttled_client = MagicMock()
        throttled_client.list_foundation_models.side_effect = _client_error("ThrottlingException")
        throttled_client.list_inference_profiles.side_effect = _client_error("ThrottlingException")

        def pick_client(region):
            return good_client if region == "us-east-1" else throttled_client

        with patch.object(mock_auth_manager, "get_bedrock_control_client", side_effect=pick_client):
            fetcher = BedrockAPIFetcher(auth_manager=mock_auth_manager, max_retries=3)
            result = fetcher.fetch_all_data(regions=["us-east-1", "us-west-2"])

        assert result.has_data is True
        assert "us-east-1" in result.successful_regions
        assert "us-west-2" in result.failed_regions
        assert len(result.foundation_models["us-east-1"]) == 2
