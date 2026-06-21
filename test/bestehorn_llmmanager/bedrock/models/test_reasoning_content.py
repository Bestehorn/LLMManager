"""
Tests for the ReasoningContent typed reasoning object (issue #32).
"""

import pytest

from bestehorn_llmmanager.bedrock.models.reasoning_content import ReasoningContent


class TestReasoningContentFromBlock:
    """Parse ReasoningContent from a reasoningContent block payload."""

    def test_from_reasoning_text_with_signature(self):
        payload = {"reasoningText": {"text": "step by step", "signature": "sig-abc"}}
        rc = ReasoningContent.from_reasoning_block(reasoning_block=payload)
        assert rc.text == "step by step"
        assert rc.signature == "sig-abc"
        assert rc.redacted_content is None

    def test_from_reasoning_text_without_signature(self):
        payload = {"reasoningText": {"text": "thinking"}}
        rc = ReasoningContent.from_reasoning_block(reasoning_block=payload)
        assert rc.text == "thinking"
        assert rc.signature is None

    def test_from_redacted_content(self):
        payload = {"redactedContent": b"\x01\x02"}
        rc = ReasoningContent.from_reasoning_block(reasoning_block=payload)
        assert rc.text is None
        assert rc.signature is None
        assert rc.redacted_content == b"\x01\x02"


class TestReasoningContentToBlock:
    """Reconstruct a re-submittable content block."""

    def test_to_block_text_and_signature(self):
        rc = ReasoningContent(text="step by step", signature="sig-abc")
        block = rc.to_content_block()
        assert block == {
            "reasoningContent": {"reasoningText": {"text": "step by step", "signature": "sig-abc"}}
        }

    def test_to_block_text_no_signature(self):
        rc = ReasoningContent(text="thinking")
        block = rc.to_content_block()
        assert block == {"reasoningContent": {"reasoningText": {"text": "thinking"}}}
        assert "signature" not in block["reasoningContent"]["reasoningText"]

    def test_to_block_redacted(self):
        rc = ReasoningContent(redacted_content=b"\x01\x02")
        block = rc.to_content_block()
        assert block == {"reasoningContent": {"redactedContent": b"\x01\x02"}}

    def test_to_block_empty_raises(self):
        with pytest.raises(ValueError):
            ReasoningContent().to_content_block()

    def test_round_trip_preserves_signature(self):
        """from_reasoning_block -> to_content_block preserves text and signature."""
        original = {"reasoningText": {"text": "deduce", "signature": "sig-xyz"}}
        rc = ReasoningContent.from_reasoning_block(reasoning_block=original)
        rebuilt = rc.to_content_block()
        assert rebuilt["reasoningContent"]["reasoningText"]["signature"] == "sig-xyz"
        assert rebuilt["reasoningContent"]["reasoningText"]["text"] == "deduce"

    def test_is_frozen(self):
        import dataclasses

        rc = ReasoningContent(text="x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            rc.text = "y"  # type: ignore[misc]
