"""
Unit tests for BedrockResponse access method metadata.

Tests the new access method fields added to BedrockResponse for tracking
inference profile usage and access methods.
"""

from datetime import datetime

import pytest

from src.bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse
from src.bestehorn_llmmanager.bedrock.models.llm_manager_structures import RequestAttempt


class TestBedrockResponseAccessMethod:
    """Test suite for BedrockResponse access method metadata."""

    def test_access_method_fields_initialization(self):
        """Test that access method fields are properly initialized."""
        response = BedrockResponse(success=True)

        assert response.access_method_used is None
        assert response.inference_profile_used is False
        assert response.inference_profile_id is None

    def test_direct_access_method(self):
        """Test response with direct access method."""
        response = BedrockResponse(
            success=True,
            model_used="anthropic.claude-3-haiku-20240307-v1:0",
            region_used="us-east-1",
            access_method_used="direct",
            inference_profile_used=False,
            inference_profile_id=None,
        )

        assert response.access_method_used == "direct"
        assert response.inference_profile_used is False
        assert response.inference_profile_id is None

    def test_regional_cris_access_method(self):
        """Test response with regional CRIS profile."""
        profile_arn = (
            "arn:aws:bedrock:us-east-1::inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0"
        )

        response = BedrockResponse(
            success=True,
            model_used=profile_arn,
            region_used="us-east-1",
            access_method_used="regional_cris",
            inference_profile_used=True,
            inference_profile_id=profile_arn,
        )

        assert response.access_method_used == "regional_cris"
        assert response.inference_profile_used is True
        assert response.inference_profile_id == profile_arn

    def test_global_cris_access_method(self):
        """Test response with global CRIS profile."""
        profile_arn = "arn:aws:bedrock::123456789012:inference-profile/global.anthropic.claude-3-haiku-20240307-v1:0"

        response = BedrockResponse(
            success=True,
            model_used=profile_arn,
            region_used="us-east-1",
            access_method_used="global_cris",
            inference_profile_used=True,
            inference_profile_id=profile_arn,
        )

        assert response.access_method_used == "global_cris"
        assert response.inference_profile_used is True
        assert response.inference_profile_id == profile_arn

    def test_get_access_method(self):
        """Test get_access_method convenience method."""
        response = BedrockResponse(
            success=True,
            access_method_used="regional_cris",
        )

        assert response.get_access_method() == "regional_cris"

    def test_get_access_method_none(self):
        """Test get_access_method when not set."""
        response = BedrockResponse(success=True)

        assert response.get_access_method() is None

    def test_was_profile_used_true(self):
        """Test was_profile_used when profile was used."""
        response = BedrockResponse(
            success=True,
            inference_profile_used=True,
        )

        assert response.was_profile_used() is True

    def test_was_profile_used_false(self):
        """Test was_profile_used when profile was not used."""
        response = BedrockResponse(
            success=True,
            inference_profile_used=False,
        )

        assert response.was_profile_used() is False

    def test_get_profile_id_when_used(self):
        """Test get_profile_id when profile was used."""
        profile_arn = "arn:aws:bedrock:us-east-1::inference-profile/test-profile"

        response = BedrockResponse(
            success=True,
            inference_profile_used=True,
            inference_profile_id=profile_arn,
        )

        assert response.get_profile_id() == profile_arn

    def test_get_profile_id_when_not_used(self):
        """Test get_profile_id when profile was not used."""
        response = BedrockResponse(
            success=True,
            inference_profile_used=False,
            inference_profile_id=None,
        )

        assert response.get_profile_id() is None

    def test_get_profile_id_when_profile_used_but_id_set(self):
        """Test get_profile_id returns None when profile_used is False even if ID is set."""
        profile_arn = "arn:aws:bedrock:us-east-1::inference-profile/test-profile"

        response = BedrockResponse(
            success=True,
            inference_profile_used=False,
            inference_profile_id=profile_arn,
        )

        # Should return None because inference_profile_used is False
        assert response.get_profile_id() is None

    def test_get_access_method_info(self):
        """Test get_access_method_info comprehensive method."""
        profile_arn = "arn:aws:bedrock:us-east-1::inference-profile/test-profile"

        response = BedrockResponse(
            success=True,
            model_used=profile_arn,
            region_used="us-east-1",
            access_method_used="regional_cris",
            inference_profile_used=True,
            inference_profile_id=profile_arn,
        )

        info = response.get_access_method_info()

        assert info["access_method"] == "regional_cris"
        assert info["profile_used"] is True
        assert info["profile_id"] == profile_arn
        assert info["model_id"] == profile_arn
        assert info["region"] == "us-east-1"

    def test_get_access_method_info_direct_access(self):
        """Test get_access_method_info for direct access."""
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"

        response = BedrockResponse(
            success=True,
            model_used=model_id,
            region_used="us-west-2",
            access_method_used="direct",
            inference_profile_used=False,
            inference_profile_id=None,
        )

        info = response.get_access_method_info()

        assert info["access_method"] == "direct"
        assert info["profile_used"] is False
        assert info["profile_id"] is None
        assert info["model_id"] == model_id
        assert info["region"] == "us-west-2"

    def test_to_dict_includes_access_method_fields(self):
        """Test that to_dict includes access method fields."""
        profile_arn = "arn:aws:bedrock:us-east-1::inference-profile/test-profile"

        response = BedrockResponse(
            success=True,
            model_used=profile_arn,
            region_used="us-east-1",
            access_method_used="regional_cris",
            inference_profile_used=True,
            inference_profile_id=profile_arn,
        )

        response_dict = response.to_dict()

        assert "access_method_used" in response_dict
        assert "inference_profile_used" in response_dict
        assert "inference_profile_id" in response_dict
        assert response_dict["access_method_used"] == "regional_cris"
        assert response_dict["inference_profile_used"] is True
        assert response_dict["inference_profile_id"] == profile_arn

    def test_from_dict_includes_access_method_fields(self):
        """Test that from_dict properly deserializes access method fields."""
        profile_arn = "arn:aws:bedrock:us-east-1::inference-profile/test-profile"

        data = {
            "success": True,
            "model_used": profile_arn,
            "region_used": "us-east-1",
            "access_method_used": "regional_cris",
            "inference_profile_used": True,
            "inference_profile_id": profile_arn,
            "attempts": [],
            "validation_attempts": [],
        }

        response = BedrockResponse.from_dict(data)

        assert response.access_method_used == "regional_cris"
        assert response.inference_profile_used is True
        assert response.inference_profile_id == profile_arn

    def test_from_dict_defaults_profile_used_to_false(self):
        """Test that from_dict defaults inference_profile_used to False if not present."""
        data = {
            "success": True,
            "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
            "region_used": "us-east-1",
            "access_method_used": "direct",
            "attempts": [],
            "validation_attempts": [],
        }

        response = BedrockResponse.from_dict(data)

        assert response.inference_profile_used is False
        assert response.inference_profile_id is None

    def test_to_json_includes_access_method_fields(self):
        """Test that to_json includes access method fields."""
        import json

        profile_arn = "arn:aws:bedrock:us-east-1::inference-profile/test-profile"

        response = BedrockResponse(
            success=True,
            model_used=profile_arn,
            region_used="us-east-1",
            access_method_used="regional_cris",
            inference_profile_used=True,
            inference_profile_id=profile_arn,
        )

        json_str = response.to_json()
        parsed = json.loads(json_str)

        assert parsed["access_method_used"] == "regional_cris"
        assert parsed["inference_profile_used"] is True
        assert parsed["inference_profile_id"] == profile_arn

    def test_access_method_with_attempts(self):
        """Test access method fields work correctly with request attempts."""
        profile_arn = "arn:aws:bedrock:us-east-1::inference-profile/test-profile"

        attempt = RequestAttempt(
            model_id=profile_arn,
            region="us-east-1",
            access_method="regional_cris",
            attempt_number=1,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
        )

        response = BedrockResponse(
            success=True,
            model_used=profile_arn,
            region_used="us-east-1",
            access_method_used="regional_cris",
            inference_profile_used=True,
            inference_profile_id=profile_arn,
            attempts=[attempt],
        )

        assert response.get_attempt_count() == 1
        assert response.get_successful_attempt() == attempt
        assert response.access_method_used == "regional_cris"
        assert response.inference_profile_used is True
