"""Tests for issue #21: _fetch_inference_profiles must paginate via nextToken.

Regression context: the fetcher called list_inference_profiles once and returned only the
first page. If a region returns more than one page of SYSTEM_DEFINED profiles, the later
pages (which may include global.* profiles) were silently lost. The fix follows nextToken
until exhausted and returns the union of all pages, while leaving the single-page case
(no nextToken) byte-for-byte unchanged.
"""

from unittest.mock import MagicMock, patch

from bestehorn_llmmanager.bedrock.catalog.api_fetcher import BedrockAPIFetcher


def _mock_auth_manager() -> MagicMock:
    return MagicMock()


class TestFetchInferenceProfilesPagination:
    """P6 — multi-page responses are unioned; single-page unchanged."""

    def test_paginates_across_multiple_pages(self) -> None:
        auth = _mock_auth_manager()
        client = MagicMock()
        page1 = [{"inferenceProfileId": "us.anthropic.claude-opus-4-8"}]
        page2 = [{"inferenceProfileId": "global.anthropic.claude-opus-4-8"}]
        page3 = [{"inferenceProfileId": "eu.anthropic.claude-opus-4-8"}]
        client.list_inference_profiles.side_effect = [
            {"inferenceProfileSummaries": page1, "nextToken": "tok1"},
            {"inferenceProfileSummaries": page2, "nextToken": "tok2"},
            {"inferenceProfileSummaries": page3},  # no nextToken -> last page
        ]
        with patch.object(auth, "get_bedrock_control_client", return_value=client):
            fetcher = BedrockAPIFetcher(auth_manager=auth)
            result = fetcher._fetch_inference_profiles(region="us-east-1")

        ids = [p["inferenceProfileId"] for p in result]
        assert ids == [
            "us.anthropic.claude-opus-4-8",
            "global.anthropic.claude-opus-4-8",
            "eu.anthropic.claude-opus-4-8",
        ]
        assert client.list_inference_profiles.call_count == 3
        # First call must NOT carry a nextToken; later calls must pass the prior token.
        first_call = client.list_inference_profiles.call_args_list[0]
        assert "nextToken" not in first_call.kwargs
        assert first_call.kwargs.get("typeEquals") == "SYSTEM_DEFINED"
        assert client.list_inference_profiles.call_args_list[1].kwargs.get("nextToken") == "tok1"
        assert client.list_inference_profiles.call_args_list[2].kwargs.get("nextToken") == "tok2"

    def test_single_page_no_token_unchanged(self) -> None:
        auth = _mock_auth_manager()
        client = MagicMock()
        client.list_inference_profiles.return_value = {
            "inferenceProfileSummaries": [{"inferenceProfileId": "us.anthropic.claude-opus-4-8"}]
        }
        with patch.object(auth, "get_bedrock_control_client", return_value=client):
            fetcher = BedrockAPIFetcher(auth_manager=auth)
            result = fetcher._fetch_inference_profiles(region="us-east-1")

        assert len(result) == 1
        # Exactly one call, with the type filter and no nextToken (backward compatible).
        client.list_inference_profiles.assert_called_once_with(typeEquals="SYSTEM_DEFINED")
