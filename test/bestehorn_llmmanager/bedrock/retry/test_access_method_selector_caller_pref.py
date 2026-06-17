"""Tests for CR-2 (selector layer): caller-selectable access-method preference.

Regression context (issue #16): AccessMethodSelector.select_access_method only honored a
learned_preference from the runtime tracker; otherwise it used the fixed default order
direct -> regional_cris -> global_cris. There was no caller-facing way to prefer the
global CRIS profile. CR-2 adds an optional caller_preference that, when no learned
preference exists, selects the requested method if available and otherwise falls back to
the default order (never raising). Default (no caller_preference) is unchanged.
"""

import pytest

from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from bestehorn_llmmanager.bedrock.retry.access_method_selector import AccessMethodSelector
from bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
    AccessMethodPreference,
)
from bestehorn_llmmanager.bedrock.tracking.access_method_tracker import AccessMethodTracker


def _selector() -> AccessMethodSelector:
    return AccessMethodSelector(access_method_tracker=AccessMethodTracker.get_instance())


def _all_methods_info() -> ModelAccessInfo:
    return ModelAccessInfo(
        region="us-east-1",
        has_direct_access=True,
        has_regional_cris=True,
        has_global_cris=True,
        model_id="anthropic.claude-opus-4-8",
        regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/regional",
        global_cris_profile_id="global.anthropic.claude-opus-4-8",
    )


class TestCallerPreferenceFromMethodName:
    """AccessMethodPreference.from_method_name builds the right flags."""

    def test_global_cris(self) -> None:
        pref = AccessMethodPreference.from_method_name(AccessMethodNames.GLOBAL_CRIS)
        assert pref.prefer_global_cris is True
        assert pref.prefer_direct is False
        assert pref.learned_from_error is False

    def test_direct(self) -> None:
        pref = AccessMethodPreference.from_method_name(AccessMethodNames.DIRECT)
        assert pref.prefer_direct is True

    def test_invalid_name_raises(self) -> None:
        with pytest.raises(ValueError):
            AccessMethodPreference.from_method_name("nonsense")


class TestSelectWithCallerPreference:
    """P4/P7 — caller preference selects the requested method or degrades gracefully."""

    def test_global_cris_preference_returns_global_profile(self) -> None:
        """P4: prefer global_cris + has_global_cris -> global_cris_profile_id."""
        info = _all_methods_info()
        caller = AccessMethodPreference.from_method_name(AccessMethodNames.GLOBAL_CRIS)
        model_id, method = _selector().select_access_method(
            access_info=info, caller_preference=caller
        )
        assert method == AccessMethodNames.GLOBAL_CRIS
        assert model_id == info.global_cris_profile_id

    def test_caller_preference_falls_back_when_unavailable(self) -> None:
        """P7: prefer global_cris but only direct available -> default order (direct), no raise."""
        info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-opus-4-8",
        )
        caller = AccessMethodPreference.from_method_name(AccessMethodNames.GLOBAL_CRIS)
        model_id, method = _selector().select_access_method(
            access_info=info, caller_preference=caller
        )
        assert method == AccessMethodNames.DIRECT
        assert model_id == info.model_id

    def test_learned_preference_wins_over_caller_preference(self) -> None:
        """DL-002: a learned (from-error) preference takes precedence over caller preference."""
        info = _all_methods_info()
        learned = AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=True,
            prefer_global_cris=False,
            learned_from_error=True,
        )
        caller = AccessMethodPreference.from_method_name(AccessMethodNames.GLOBAL_CRIS)
        model_id, method = _selector().select_access_method(
            access_info=info, learned_preference=learned, caller_preference=caller
        )
        # learned regional_cris wins, not the caller's global_cris
        assert method == AccessMethodNames.REGIONAL_CRIS
        assert model_id == info.regional_cris_profile_id


class TestSelectBackwardCompat:
    """P6 — no caller preference -> selection identical to today (default order)."""

    def test_default_order_direct_first(self) -> None:
        info = _all_methods_info()
        model_id, method = _selector().select_access_method(access_info=info)
        assert method == AccessMethodNames.DIRECT
        assert model_id == info.model_id

    def test_default_order_regional_when_no_direct(self) -> None:
        info = ModelAccessInfo(
            region="us-east-1",
            has_regional_cris=True,
            has_global_cris=True,
            regional_cris_profile_id="arn:regional",
            global_cris_profile_id="global.x",
        )
        model_id, method = _selector().select_access_method(access_info=info)
        assert method == AccessMethodNames.REGIONAL_CRIS
        assert model_id == "arn:regional"
