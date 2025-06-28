"""
Unit tests for ContentFilter class.

Tests the content filtering and restoration functionality that fixes
the image analysis issue in the LLMManager.
"""

from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.filters.content_filter import ContentFilter
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    ContentFilterState,
    FilteredContent,
)


class TestContentFilter:
    """Test cases for ContentFilter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.content_filter = ContentFilter()

        # Sample request with image content
        self.sample_request_with_image = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {ConverseAPIFields.TEXT: "Please analyze this image."},
                        {
                            ConverseAPIFields.IMAGE: {
                                ConverseAPIFields.FORMAT: "jpeg",
                                ConverseAPIFields.SOURCE: {
                                    ConverseAPIFields.BYTES: "base64_encoded_image_data"
                                },
                            }
                        },
                    ],
                }
            ],
            ConverseAPIFields.INFERENCE_CONFIG: {ConverseAPIFields.MAX_TOKENS: 1000},
        }

        # Sample request with multiple content types
        self.sample_request_multimodal = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {ConverseAPIFields.TEXT: "Analyze these files."},
                        {
                            ConverseAPIFields.IMAGE: {
                                ConverseAPIFields.FORMAT: "png",
                                ConverseAPIFields.SOURCE: {ConverseAPIFields.BYTES: "image_data"},
                            }
                        },
                        {
                            ConverseAPIFields.DOCUMENT: {
                                ConverseAPIFields.NAME: "document.pd",
                                ConverseAPIFields.FORMAT: "pdf",
                                ConverseAPIFields.SOURCE: {
                                    ConverseAPIFields.BYTES: "document_data"
                                },
                            }
                        },
                    ],
                }
            ]
        }

    def test_create_filter_state(self):
        """Test creating a filter state from request."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_with_image)

        assert isinstance(filter_state, ContentFilterState)
        assert filter_state.original_request == self.sample_request_with_image
        assert len(filter_state.disabled_features) == 0
        assert len(filter_state.filtered_content) == 0

    def test_apply_filters_image_processing(self):
        """Test filtering image content."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_with_image)
        disabled_features = {"image_processing"}

        filtered_request = self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features=disabled_features
        )

        # Check that image content is removed
        messages = filtered_request[ConverseAPIFields.MESSAGES]
        assert len(messages) == 1
        content_blocks = messages[0][ConverseAPIFields.CONTENT]
        assert len(content_blocks) == 1  # Only text block should remain
        assert ConverseAPIFields.TEXT in content_blocks[0]
        # Check that no image blocks remain in the content
        image_blocks = [block for block in content_blocks if ConverseAPIFields.IMAGE in block]
        assert len(image_blocks) == 0

        # Check that filter state is updated
        assert "image_processing" in filter_state.disabled_features
        assert "image_processing" in filter_state.filtered_content
        assert len(filter_state.filtered_content["image_processing"]) == 1

    def test_apply_filters_multiple_features(self):
        """Test filtering multiple content types."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_multimodal)
        disabled_features = {"image_processing", "document_processing"}

        filtered_request = self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features=disabled_features
        )

        # Check that only text content remains
        messages = filtered_request[ConverseAPIFields.MESSAGES]
        assert len(messages) == 1
        content_blocks = messages[0][ConverseAPIFields.CONTENT]
        assert len(content_blocks) == 1  # Only text block should remain
        assert ConverseAPIFields.TEXT in content_blocks[0]

        # Check filter state
        assert "image_processing" in filter_state.disabled_features
        assert "document_processing" in filter_state.disabled_features
        assert len(filter_state.filtered_content["image_processing"]) == 1
        assert len(filter_state.filtered_content["document_processing"]) == 1

    def test_restore_features(self):
        """Test restoring previously filtered features."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_with_image)

        # First, apply filtering
        self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"image_processing"}
        )

        # Then restore the feature
        restored_request = self.content_filter.restore_features(
            filter_state=filter_state, features_to_restore={"image_processing"}
        )

        # Check that image content is restored
        messages = restored_request[ConverseAPIFields.MESSAGES]
        content_blocks = messages[0][ConverseAPIFields.CONTENT]
        assert len(content_blocks) == 2  # Text and image blocks

        # Find the image block
        image_block = None
        for block in content_blocks:
            if ConverseAPIFields.IMAGE in block:
                image_block = block
                break

        assert image_block is not None
        assert image_block[ConverseAPIFields.IMAGE][ConverseAPIFields.FORMAT] == "jpeg"

    def test_partial_restore_features(self):
        """Test restoring only some filtered features."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_multimodal)

        # Filter both image and document processing
        self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"image_processing", "document_processing"}
        )

        # Restore only image processing
        restored_request = self.content_filter.restore_features(
            filter_state=filter_state, features_to_restore={"image_processing"}
        )

        # Check that image is restored but document is still filtered
        messages = restored_request[ConverseAPIFields.MESSAGES]
        content_blocks = messages[0][ConverseAPIFields.CONTENT]
        assert len(content_blocks) == 2  # Text and image blocks

        # Check content types
        has_text = any(ConverseAPIFields.TEXT in block for block in content_blocks)
        has_image = any(ConverseAPIFields.IMAGE in block for block in content_blocks)
        has_document = any(ConverseAPIFields.DOCUMENT in block for block in content_blocks)

        assert has_text
        assert has_image
        assert not has_document  # Should still be filtered

    def test_get_supported_features_for_model_multimodal(self):
        """Test feature detection for multimodal models."""
        # Test Claude model (should support multimodal)
        features = self.content_filter.get_supported_features_for_model("Claude 3.5 Sonnet")

        expected_features = {
            "image_processing",
            "document_processing",
            "video_processing",
            "tool_use",
            "guardrails",
            "prompt_caching",
        }

        assert features == expected_features

    def test_get_supported_features_for_model_text_only(self):
        """Test feature detection for text-only models."""
        # Test a text-only model
        features = self.content_filter.get_supported_features_for_model("AI21 Jurassic")

        # Should not support multimodal features
        assert "image_processing" not in features
        assert "document_processing" not in features
        assert "video_processing" not in features

        # Should support basic features
        assert "guardrails" in features
        assert "prompt_caching" in features

    def test_should_restore_features_for_model(self):
        """Test feature restoration logic for different models."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_with_image)

        # Disable image processing
        self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"image_processing"}
        )

        # Test with multimodal model - should restore
        should_restore, features_to_restore = self.content_filter.should_restore_features_for_model(
            filter_state=filter_state, model_name="Claude 3.5 Sonnet"
        )

        assert should_restore
        assert "image_processing" in features_to_restore

        # Test with text-only model - should not restore
        should_restore, features_to_restore = self.content_filter.should_restore_features_for_model(
            filter_state=filter_state, model_name="AI21 Jurassic"
        )

        assert not should_restore
        assert len(features_to_restore) == 0

    def test_filter_messages_with_empty_content(self):
        """Test filtering when message has no remaining content."""
        request_with_only_image = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {
                            ConverseAPIFields.IMAGE: {
                                ConverseAPIFields.FORMAT: "jpeg",
                                ConverseAPIFields.SOURCE: {ConverseAPIFields.BYTES: "image_data"},
                            }
                        }
                    ],
                }
            ]
        }

        filter_state = self.content_filter.create_filter_state(request_with_only_image)

        with patch.object(self.content_filter._logger, "warning") as mock_warning:
            filtered_request = self.content_filter.apply_filters(
                filter_state=filter_state, disabled_features={"image_processing"}
            )

            # Should log warning about empty message
            mock_warning.assert_called_once()
            assert "no remaining content" in mock_warning.call_args[0][0]

        # Message should be completely filtered out
        assert len(filtered_request[ConverseAPIFields.MESSAGES]) == 0

    def test_filter_summary(self):
        """Test getting filter summary."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_multimodal)

        # Apply filtering
        self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"image_processing", "document_processing"}
        )

        # Get summary
        summary = self.content_filter.get_filter_summary(filter_state)

        assert "image_processing" in summary["disabled_features"]
        assert "document_processing" in summary["disabled_features"]
        assert summary["total_filtered_items"] == 2
        assert summary["filtered_image_processing_count"] == 1
        assert summary["filtered_document_processing_count"] == 1

    def test_filter_guardrails_config(self):
        """Test filtering guardrails configuration."""
        request_with_guardrails = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [{ConverseAPIFields.TEXT: "Hello"}],
                }
            ],
            ConverseAPIFields.GUARDRAIL_CONFIG: {
                "guardrailIdentifier": "test-guardrail",
                "guardrailVersion": "1",
            },
        }

        filter_state = self.content_filter.create_filter_state(request_with_guardrails)

        filtered_request = self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"guardrails"}
        )

        # Guardrail config should be removed
        assert ConverseAPIFields.GUARDRAIL_CONFIG not in filtered_request

        # Should be stored for restoration
        assert "guardrails" in filter_state.filtered_content

    def test_no_filtering_when_no_disabled_features(self):
        """Test that no filtering occurs when no features are disabled."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_with_image)

        filtered_request = self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features=set()
        )

        # Request should be unchanged
        assert filtered_request == self.sample_request_with_image
        assert len(filter_state.disabled_features) == 0
        assert len(filter_state.filtered_content) == 0

    def test_filtered_content_structure(self):
        """Test the structure of filtered content tracking."""
        filter_state = self.content_filter.create_filter_state(self.sample_request_with_image)

        self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"image_processing"}
        )

        # Check FilteredContent structure
        filtered_items = filter_state.filtered_content["image_processing"]
        assert len(filtered_items) == 1

        filtered_item = filtered_items[0]
        assert isinstance(filtered_item, FilteredContent)
        assert filtered_item.message_index == 0
        assert filtered_item.block_index == 1  # Image is second content block
        assert ConverseAPIFields.IMAGE in filtered_item.content_block


class TestContentFilterIntegration:
    """Integration tests for ContentFilter with retry logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.content_filter = ContentFilter()

    def test_image_restoration_scenario(self):
        """Test the main scenario: image filtered then restored."""
        # This simulates the bug scenario described in the task
        request_with_image = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {
                            ConverseAPIFields.TEXT: "Please analyze this image and tell me what you see."
                        },
                        {
                            ConverseAPIFields.IMAGE: {
                                ConverseAPIFields.FORMAT: "jpeg",
                                ConverseAPIFields.SOURCE: {
                                    ConverseAPIFields.BYTES: "base64_image_data"
                                },
                            }
                        },
                    ],
                }
            ]
        }

        filter_state = self.content_filter.create_filter_state(request_with_image)

        # Simulate first model (text-only) - filter image
        filtered_for_text_model = self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"image_processing"}
        )

        # Verify image is filtered out
        content_blocks = filtered_for_text_model[ConverseAPIFields.MESSAGES][0][
            ConverseAPIFields.CONTENT
        ]
        assert len(content_blocks) == 1  # Only text remains
        assert ConverseAPIFields.TEXT in content_blocks[0]

        # Simulate second model (multimodal) - restore image
        should_restore, features_to_restore = self.content_filter.should_restore_features_for_model(
            filter_state=filter_state, model_name="Claude 3.5 Sonnet"
        )

        assert should_restore
        assert "image_processing" in features_to_restore

        # Restore the image
        restored_for_multimodal = self.content_filter.restore_features(
            filter_state=filter_state, features_to_restore=features_to_restore
        )

        # Verify image is restored
        content_blocks = restored_for_multimodal[ConverseAPIFields.MESSAGES][0][
            ConverseAPIFields.CONTENT
        ]
        assert len(content_blocks) == 2  # Text and image

        # Find and verify image block
        image_block = None
        text_block = None
        for block in content_blocks:
            if ConverseAPIFields.IMAGE in block:
                image_block = block
            elif ConverseAPIFields.TEXT in block:
                text_block = block

        assert image_block is not None
        assert text_block is not None
        assert image_block[ConverseAPIFields.IMAGE][ConverseAPIFields.FORMAT] == "jpeg"
        assert (
            text_block[ConverseAPIFields.TEXT]
            == "Please analyze this image and tell me what you see."
        )

    def test_multiple_retry_attempts_with_restoration(self):
        """Test multiple retry attempts with different model capabilities."""
        multimodal_request = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {ConverseAPIFields.TEXT: "Process these files."},
                        {ConverseAPIFields.IMAGE: {"format": "png", "source": {"bytes": "img"}}},
                        {
                            ConverseAPIFields.DOCUMENT: {
                                "name": "doc.pd",
                                "format": "pd",
                                "source": {"bytes": "doc"},
                            }
                        },
                    ],
                }
            ]
        }

        filter_state = self.content_filter.create_filter_state(multimodal_request)

        # First attempt: text-only model, filter both image and document
        filtered_attempt1 = self.content_filter.apply_filters(
            filter_state=filter_state, disabled_features={"image_processing", "document_processing"}
        )

        content_blocks = filtered_attempt1[ConverseAPIFields.MESSAGES][0][ConverseAPIFields.CONTENT]
        assert len(content_blocks) == 1  # Only text

        # Second attempt: partial multimodal model (images only)
        should_restore, features_to_restore = self.content_filter.should_restore_features_for_model(
            filter_state=filter_state,
            model_name="Claude 3.5 Sonnet",  # Supports images and documents
        )

        assert should_restore
        assert "image_processing" in features_to_restore
        assert "document_processing" in features_to_restore

        # Restore all features
        fully_restored = self.content_filter.restore_features(
            filter_state=filter_state, features_to_restore=features_to_restore
        )

        content_blocks = fully_restored[ConverseAPIFields.MESSAGES][0][ConverseAPIFields.CONTENT]
        assert len(content_blocks) == 3  # Text, image, and document


if __name__ == "__main__":
    pytest.main([__file__])
