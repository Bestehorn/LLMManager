"""
Canonical Bedrock Converse ``stopReason`` model.

This is the single source of truth for the Converse API ``stopReason`` values, shared by
the core ``ConverseAPIFields`` and the streaming ``StreamingConstants`` so the two never
drift apart (issue #37). It also classifies each stop reason for retry/failover decisions.
"""

from enum import Enum
from typing import Optional, Union


class StopReasonEnum(str, Enum):
    """The complete set of AWS Bedrock Converse ``stopReason`` values.

    Matches the ``bedrock-runtime`` ``StopReason`` enum exactly (all nine values). Member
    names map to the ``STOP_REASON_<NAME>`` constants exposed by ``ConverseAPIFields`` and
    ``StreamingConstants``.
    """

    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    GUARDRAIL_INTERVENED = "guardrail_intervened"
    CONTENT_FILTERED = "content_filtered"
    MALFORMED_MODEL_OUTPUT = "malformed_model_output"
    MALFORMED_TOOL_USE = "malformed_tool_use"
    MODEL_CONTEXT_WINDOW_EXCEEDED = "model_context_window_exceeded"


class StopReasonCategory(str, Enum):
    """How a stop reason should influence retry/failover decisions.

    - ``TERMINAL``: a normal completion; do not retry (end_turn, tool_use, stop_sequence,
      max_tokens).
    - ``RETRY_DIFFERENT_TARGET``: retrying the SAME model/region is futile or undesirable;
      a different target may succeed. ``model_context_window_exceeded`` (this model's
      window is too small for the input), ``guardrail_intervened`` and ``content_filtered``
      (policy outcome that another model/region may treat differently).
    - ``RETRYABLE``: a transient model glitch where a retry (same or different target) may
      help — ``malformed_model_output`` / ``malformed_tool_use``.
    - ``UNKNOWN``: an unrecognized or absent value (forward-compatible; never crashes).
    """

    TERMINAL = "terminal"
    RETRY_DIFFERENT_TARGET = "retry_different_target"
    RETRYABLE = "retryable"
    UNKNOWN = "unknown"


class StopReasonClassifier:
    """Classifies Bedrock ``stopReason`` values for retry/failover handling (issue #37)."""

    _TERMINAL = frozenset(
        {
            StopReasonEnum.END_TURN,
            StopReasonEnum.TOOL_USE,
            StopReasonEnum.STOP_SEQUENCE,
            StopReasonEnum.MAX_TOKENS,
        }
    )
    _RETRY_DIFFERENT_TARGET = frozenset(
        {
            StopReasonEnum.MODEL_CONTEXT_WINDOW_EXCEEDED,
            StopReasonEnum.GUARDRAIL_INTERVENED,
            StopReasonEnum.CONTENT_FILTERED,
        }
    )
    _RETRYABLE = frozenset(
        {
            StopReasonEnum.MALFORMED_MODEL_OUTPUT,
            StopReasonEnum.MALFORMED_TOOL_USE,
        }
    )

    @classmethod
    def _coerce(cls, reason: Optional[Union[str, StopReasonEnum]]) -> Optional[StopReasonEnum]:
        """Coerce a raw string / enum / None to a StopReasonEnum, or None if unrecognized."""
        if reason is None:
            return None
        if isinstance(reason, StopReasonEnum):
            return reason
        try:
            return StopReasonEnum(reason)
        except ValueError:
            return None

    @classmethod
    def categorize(cls, reason: Optional[Union[str, StopReasonEnum]]) -> StopReasonCategory:
        """
        Categorize a stop reason for retry/failover handling.

        Args:
            reason: A ``StopReasonEnum``, the raw API string (what
                ``BedrockResponse.get_stop_reason()`` returns), or None.

        Returns:
            The :class:`StopReasonCategory`. Unrecognized or absent values map to
            ``UNKNOWN`` (forward-compatible).
        """
        coerced = cls._coerce(reason)
        if coerced is None:
            return StopReasonCategory.UNKNOWN
        if coerced in cls._TERMINAL:
            return StopReasonCategory.TERMINAL
        if coerced in cls._RETRY_DIFFERENT_TARGET:
            return StopReasonCategory.RETRY_DIFFERENT_TARGET
        if coerced in cls._RETRYABLE:
            return StopReasonCategory.RETRYABLE
        return StopReasonCategory.UNKNOWN

    @classmethod
    def is_terminal(cls, reason: Optional[Union[str, StopReasonEnum]]) -> bool:
        """True if the stop reason represents a normal completion (no retry warranted)."""
        return cls.categorize(reason) == StopReasonCategory.TERMINAL

    @classmethod
    def is_retryable(cls, reason: Optional[Union[str, StopReasonEnum]]) -> bool:
        """True if a retry (a different target, or a fresh attempt) may help.

        Covers both ``RETRY_DIFFERENT_TARGET`` and ``RETRYABLE``; ``model_context_window_exceeded``
        is retryable only against a DIFFERENT target (see :meth:`categorize`), not the same
        model/region with the same oversized input.
        """
        return cls.categorize(reason) in (
            StopReasonCategory.RETRY_DIFFERENT_TARGET,
            StopReasonCategory.RETRYABLE,
        )
