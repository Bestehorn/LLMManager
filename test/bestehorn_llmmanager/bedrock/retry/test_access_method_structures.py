"""
Unit tests for access method data structures.

Tests the AccessMethodPreference dataclass and related structures.
"""

from datetime import datetime

from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
    AccessMethodPreference,
)


class TestAccessMethodPreference:
    """Test suite for AccessMethodPreference dataclass."""

    def test_default_initialization(self) -> None:
        """Test AccessMethodPreference with default values."""
        preference = AccessMethodPreference()

        assert preference.prefer_direct is True
        assert preference.prefer_regional_cris is False
        assert preference.prefer_global_cris is False
        assert preference.learned_from_error is False
        assert isinstance(preference.last_updated, datetime)

    def test_custom_initialization(self) -> None:
        """Test AccessMethodPreference with custom values."""
        custom_time = datetime(year=2024, month=1, day=15, hour=10, minute=30)
        preference = AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=True,
            prefer_global_cris=False,
            learned_from_error=True,
            last_updated=custom_time,
        )

        assert preference.prefer_direct is False
        assert preference.prefer_regional_cris is True
        assert preference.prefer_global_cris is False
        assert preference.learned_from_error is True
        assert preference.last_updated == custom_time

    def test_get_preferred_method_direct(self) -> None:
        """Test get_preferred_method returns 'direct' when prefer_direct is True."""
        preference = AccessMethodPreference(
            prefer_direct=True, prefer_regional_cris=False, prefer_global_cris=False
        )

        assert preference.get_preferred_method() == AccessMethodNames.DIRECT

    def test_get_preferred_method_regional_cris(self) -> None:
        """Test get_preferred_method returns 'regional_cris' when prefer_regional_cris is True."""
        preference = AccessMethodPreference(
            prefer_direct=False, prefer_regional_cris=True, prefer_global_cris=False
        )

        assert preference.get_preferred_method() == AccessMethodNames.REGIONAL_CRIS

    def test_get_preferred_method_global_cris(self) -> None:
        """Test get_preferred_method returns 'global_cris' when prefer_global_cris is True."""
        preference = AccessMethodPreference(
            prefer_direct=False, prefer_regional_cris=False, prefer_global_cris=True
        )

        assert preference.get_preferred_method() == AccessMethodNames.GLOBAL_CRIS

    def test_get_preferred_method_unknown(self) -> None:
        """Test get_preferred_method returns 'unknown' when no preference is set."""
        preference = AccessMethodPreference(
            prefer_direct=False, prefer_regional_cris=False, prefer_global_cris=False
        )

        assert preference.get_preferred_method() == AccessMethodNames.UNKNOWN

    def test_get_preferred_method_priority_direct_over_regional(self) -> None:
        """Test that direct preference takes priority over regional CRIS."""
        preference = AccessMethodPreference(
            prefer_direct=True, prefer_regional_cris=True, prefer_global_cris=False
        )

        assert preference.get_preferred_method() == AccessMethodNames.DIRECT

    def test_get_preferred_method_priority_direct_over_global(self) -> None:
        """Test that direct preference takes priority over global CRIS."""
        preference = AccessMethodPreference(
            prefer_direct=True, prefer_regional_cris=False, prefer_global_cris=True
        )

        assert preference.get_preferred_method() == AccessMethodNames.DIRECT

    def test_get_preferred_method_priority_regional_over_global(self) -> None:
        """Test that regional CRIS preference takes priority over global CRIS."""
        preference = AccessMethodPreference(
            prefer_direct=False, prefer_regional_cris=True, prefer_global_cris=True
        )

        assert preference.get_preferred_method() == AccessMethodNames.REGIONAL_CRIS

    def test_learned_from_error_flag(self) -> None:
        """Test learned_from_error flag can be set and retrieved."""
        preference_from_success = AccessMethodPreference(learned_from_error=False)
        preference_from_error = AccessMethodPreference(learned_from_error=True)

        assert preference_from_success.learned_from_error is False
        assert preference_from_error.learned_from_error is True

    def test_last_updated_timestamp(self) -> None:
        """Test last_updated timestamp is set correctly."""
        before_creation = datetime.now()
        preference = AccessMethodPreference()
        after_creation = datetime.now()

        # Timestamp should be between before and after creation
        assert before_creation <= preference.last_updated <= after_creation

    def test_last_updated_custom_timestamp(self) -> None:
        """Test last_updated can be set to a custom timestamp."""
        custom_time = datetime(year=2023, month=6, day=15, hour=14, minute=30, second=45)
        preference = AccessMethodPreference(last_updated=custom_time)

        assert preference.last_updated == custom_time

    def test_dataclass_equality(self) -> None:
        """Test that two AccessMethodPreference instances with same values are equal."""
        time1 = datetime(year=2024, month=1, day=1, hour=12, minute=0)
        preference1 = AccessMethodPreference(
            prefer_direct=True,
            prefer_regional_cris=False,
            prefer_global_cris=False,
            learned_from_error=False,
            last_updated=time1,
        )
        preference2 = AccessMethodPreference(
            prefer_direct=True,
            prefer_regional_cris=False,
            prefer_global_cris=False,
            learned_from_error=False,
            last_updated=time1,
        )

        assert preference1 == preference2

    def test_dataclass_inequality(self) -> None:
        """Test that two AccessMethodPreference instances with different values are not equal."""
        time1 = datetime(year=2024, month=1, day=1, hour=12, minute=0)
        preference1 = AccessMethodPreference(
            prefer_direct=True, prefer_regional_cris=False, last_updated=time1
        )
        preference2 = AccessMethodPreference(
            prefer_direct=False, prefer_regional_cris=True, last_updated=time1
        )

        assert preference1 != preference2


class TestAccessMethodNames:
    """Test suite for AccessMethodNames constants."""

    def test_direct_constant(self) -> None:
        """Test DIRECT constant value."""
        assert AccessMethodNames.DIRECT == "direct"

    def test_regional_cris_constant(self) -> None:
        """Test REGIONAL_CRIS constant value."""
        assert AccessMethodNames.REGIONAL_CRIS == "regional_cris"

    def test_global_cris_constant(self) -> None:
        """Test GLOBAL_CRIS constant value."""
        assert AccessMethodNames.GLOBAL_CRIS == "global_cris"

    def test_unknown_constant(self) -> None:
        """Test UNKNOWN constant value."""
        assert AccessMethodNames.UNKNOWN == "unknown"

    def test_constants_are_unique(self) -> None:
        """Test that all access method name constants are unique."""
        constants = [
            AccessMethodNames.DIRECT,
            AccessMethodNames.REGIONAL_CRIS,
            AccessMethodNames.GLOBAL_CRIS,
            AccessMethodNames.UNKNOWN,
        ]
        assert len(constants) == len(set(constants))
