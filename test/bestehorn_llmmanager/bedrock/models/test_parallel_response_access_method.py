"""
Unit tests for ParallelResponse access method statistics.

Tests the access method aggregation and statistics methods added to ParallelResponse
for tracking inference profile usage across parallel requests.
"""

import pytest

from src.bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse
from src.bestehorn_llmmanager.bedrock.models.parallel_structures import ParallelResponse


class TestParallelResponseAccessMethod:
    """Test suite for ParallelResponse access method statistics."""

    def test_get_access_method_statistics_empty(self):
        """Test access method statistics with no requests."""
        parallel_response = ParallelResponse(success=True)

        stats = parallel_response.get_access_method_statistics()

        assert stats["total_requests"] == 0
        assert stats["direct_access_count"] == 0
        assert stats["regional_cris_count"] == 0
        assert stats["global_cris_count"] == 0
        assert stats["profile_usage_count"] == 0
        assert stats["profile_usage_percentage"] == 0.0
        assert stats["access_method_breakdown"] == {}

    def test_get_access_method_statistics_all_direct(self):
        """Test access method statistics with all direct access."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
            "req2": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
            "req3": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        stats = parallel_response.get_access_method_statistics()

        assert stats["total_requests"] == 3
        assert stats["direct_access_count"] == 3
        assert stats["regional_cris_count"] == 0
        assert stats["global_cris_count"] == 0
        assert stats["profile_usage_count"] == 0
        assert stats["profile_usage_percentage"] == 0.0
        assert stats["access_method_breakdown"] == {"direct": 3}

    def test_get_access_method_statistics_all_profiles(self):
        """Test access method statistics with all profile access."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id="arn:aws:bedrock:us-east-1::inference-profile/profile1",
            ),
            "req2": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id="arn:aws:bedrock:us-east-1::inference-profile/profile2",
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        stats = parallel_response.get_access_method_statistics()

        assert stats["total_requests"] == 2
        assert stats["direct_access_count"] == 0
        assert stats["regional_cris_count"] == 2
        assert stats["global_cris_count"] == 0
        assert stats["profile_usage_count"] == 2
        assert stats["profile_usage_percentage"] == 100.0
        assert stats["access_method_breakdown"] == {"regional_cris": 2}

    def test_get_access_method_statistics_mixed(self):
        """Test access method statistics with mixed access methods."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
            "req2": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id="arn:aws:bedrock:us-east-1::inference-profile/profile1",
            ),
            "req3": BedrockResponse(
                success=True,
                access_method_used="global_cris",
                inference_profile_used=True,
                inference_profile_id="arn:aws:bedrock::123456789012:inference-profile/global-profile",
            ),
            "req4": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        stats = parallel_response.get_access_method_statistics()

        assert stats["total_requests"] == 4
        assert stats["direct_access_count"] == 2
        assert stats["regional_cris_count"] == 1
        assert stats["global_cris_count"] == 1
        assert stats["profile_usage_count"] == 2
        assert stats["profile_usage_percentage"] == 50.0
        assert stats["access_method_breakdown"] == {
            "direct": 2,
            "regional_cris": 1,
            "global_cris": 1,
        }

    def test_get_requests_by_access_method(self):
        """Test filtering requests by access method."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="direct",
            ),
            "req2": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
            ),
            "req3": BedrockResponse(
                success=True,
                access_method_used="direct",
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        direct_requests = parallel_response.get_requests_by_access_method("direct")
        assert len(direct_requests) == 2
        assert "req1" in direct_requests
        assert "req3" in direct_requests

        cris_requests = parallel_response.get_requests_by_access_method("regional_cris")
        assert len(cris_requests) == 1
        assert "req2" in cris_requests

    def test_get_requests_by_access_method_none_found(self):
        """Test filtering by access method when none match."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="direct",
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        global_requests = parallel_response.get_requests_by_access_method("global_cris")
        assert len(global_requests) == 0

    def test_get_profile_usage_details_no_profiles(self):
        """Test profile usage details when no profiles used."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        details = parallel_response.get_profile_usage_details()

        assert details["requests_using_profiles"] == []
        assert details["profile_ids_used"] == []
        assert details["profile_usage_by_request"] == {}

    def test_get_profile_usage_details_with_profiles(self):
        """Test profile usage details with multiple profiles."""
        profile1 = "arn:aws:bedrock:us-east-1::inference-profile/profile1"
        profile2 = "arn:aws:bedrock:us-west-2::inference-profile/profile2"

        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id=profile1,
            ),
            "req2": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
            "req3": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id=profile2,
            ),
            "req4": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id=profile1,  # Same profile as req1
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        details = parallel_response.get_profile_usage_details()

        assert len(details["requests_using_profiles"]) == 3
        assert "req1" in details["requests_using_profiles"]
        assert "req3" in details["requests_using_profiles"]
        assert "req4" in details["requests_using_profiles"]
        assert "req2" not in details["requests_using_profiles"]

        # Should have 2 unique profile IDs
        assert len(details["profile_ids_used"]) == 2
        assert profile1 in details["profile_ids_used"]
        assert profile2 in details["profile_ids_used"]

        # Check mapping
        assert details["profile_usage_by_request"]["req1"] == profile1
        assert details["profile_usage_by_request"]["req3"] == profile2
        assert details["profile_usage_by_request"]["req4"] == profile1
        assert "req2" not in details["profile_usage_by_request"]

    def test_get_profile_usage_details_ignores_none_profile_ids(self):
        """Test that profile usage details ignores requests with profile_used=True but no ID."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id=None,  # Missing profile ID
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        details = parallel_response.get_profile_usage_details()

        # Should not include req1 since profile_id is None
        assert details["requests_using_profiles"] == []
        assert details["profile_ids_used"] == []
        assert details["profile_usage_by_request"] == {}

    def test_access_method_statistics_with_none_access_method(self):
        """Test statistics when some responses have None access_method."""
        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
            "req2": BedrockResponse(
                success=True,
                access_method_used=None,  # No access method set
                inference_profile_used=False,
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        stats = parallel_response.get_access_method_statistics()

        assert stats["total_requests"] == 2
        assert stats["direct_access_count"] == 1
        assert stats["profile_usage_count"] == 0
        # req2 should not be counted in any access method

    def test_combined_statistics_and_details(self):
        """Test using both statistics and details methods together."""
        profile1 = "arn:aws:bedrock:us-east-1::inference-profile/profile1"

        responses = {
            "req1": BedrockResponse(
                success=True,
                access_method_used="direct",
                inference_profile_used=False,
            ),
            "req2": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id=profile1,
            ),
            "req3": BedrockResponse(
                success=True,
                access_method_used="regional_cris",
                inference_profile_used=True,
                inference_profile_id=profile1,
            ),
        }

        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
        )

        # Get statistics
        stats = parallel_response.get_access_method_statistics()
        assert stats["profile_usage_count"] == 2
        assert stats["profile_usage_percentage"] == pytest.approx(66.67, rel=0.01)

        # Get details
        details = parallel_response.get_profile_usage_details()
        assert len(details["requests_using_profiles"]) == 2
        assert len(details["profile_ids_used"]) == 1

        # Get filtered requests
        profile_requests = parallel_response.get_requests_by_access_method("regional_cris")
        assert len(profile_requests) == 2
