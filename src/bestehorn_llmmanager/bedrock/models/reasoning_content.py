"""
Typed reasoning / extended-thinking content for Bedrock Converse.

Defines :class:`ReasoningContent`, the typed view of a ``reasoningContent`` block (the
Chain-of-Thought a reasoning-capable model emits — Claude extended thinking, Nova
reasoning, DeepSeek-R1). The block is a union of either ``reasoningText`` (``text`` plus
a verification ``signature``) or encrypted ``redactedContent``. For correct multi-turn
conversations the block must be echoed back **unmodified** (text + signature), so this
class both parses a block from a response and reconstructs a re-submittable block.

References:
- ReasoningContentBlock (reasoningText | redactedContent):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ReasoningContentBlock.html
- ReasoningTextBlock (text [required], signature [optional]):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ReasoningTextBlock.html
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .llm_manager_constants import ConverseAPIFields


@dataclass(frozen=True)
class ReasoningContent:
    """
    A reasoning / extended-thinking content block from a response.

    Exactly one of (text, redacted_content) is normally populated, matching the
    ``reasoningContent`` union. When echoing reasoning back in a multi-turn request,
    pass ``text`` and ``signature`` through unmodified.

    Attributes:
        text: The model's reasoning text (the ``reasoningText.text``), or ``None`` for a
            redacted block.
        signature: The token verifying the reasoning text was model-generated
            (``reasoningText.signature``); must be echoed back unmodified. ``None`` if
            the model did not provide one.
        redacted_content: Encrypted reasoning bytes (the ``redactedContent`` member), or
            ``None`` when the block carries reasoning text instead.
    """

    text: Optional[str] = None
    signature: Optional[str] = None
    redacted_content: Optional[Any] = None

    @classmethod
    def from_reasoning_block(cls, reasoning_block: Dict[str, Any]) -> "ReasoningContent":
        """
        Build a :class:`ReasoningContent` from a ``reasoningContent`` block payload.

        Args:
            reasoning_block: The value under a content block's ``reasoningContent`` key
                — either ``{"reasoningText": {"text", "signature"?}}`` or
                ``{"redactedContent": <bytes>}``.

        Returns:
            The typed :class:`ReasoningContent`.
        """
        reasoning_text = reasoning_block.get(ConverseAPIFields.REASONING_TEXT)
        if isinstance(reasoning_text, dict):
            return cls(
                text=reasoning_text.get(ConverseAPIFields.TEXT),
                signature=reasoning_text.get(ConverseAPIFields.REASONING_SIGNATURE),
                redacted_content=reasoning_block.get(ConverseAPIFields.REASONING_REDACTED_CONTENT),
            )
        return cls(
            text=None,
            signature=None,
            redacted_content=reasoning_block.get(ConverseAPIFields.REASONING_REDACTED_CONTENT),
        )

    def to_content_block(self) -> Dict[str, Any]:
        """
        Reconstruct the re-submittable ``reasoningContent`` content block.

        Produces a block suitable for echoing back in a subsequent turn: a
        ``reasoningText`` member (with the signature preserved when present) when the
        reasoning is textual, or a ``redactedContent`` member when it is redacted.

        Returns:
            A content block dict ``{"reasoningContent": {...}}``.

        Raises:
            ValueError: If neither reasoning text nor redacted content is present.
        """
        if self.text is not None:
            reasoning_text: Dict[str, Any] = {ConverseAPIFields.TEXT: self.text}
            if self.signature is not None:
                reasoning_text[ConverseAPIFields.REASONING_SIGNATURE] = self.signature
            return {
                ConverseAPIFields.REASONING_CONTENT: {
                    ConverseAPIFields.REASONING_TEXT: reasoning_text
                }
            }
        if self.redacted_content is not None:
            return {
                ConverseAPIFields.REASONING_CONTENT: {
                    ConverseAPIFields.REASONING_REDACTED_CONTENT: self.redacted_content
                }
            }
        raise ValueError(
            "ReasoningContent has neither text nor redacted_content; cannot build a block."
        )
