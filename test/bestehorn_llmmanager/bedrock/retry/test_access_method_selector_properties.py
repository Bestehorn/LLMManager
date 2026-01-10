"""
Property-based tests for AccessMethodSelector.

Feature: inference-profile-support
Tests universal properties of access method selection logic.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from src.bestehorn_llmmanager.bedrock.retry.access_method_selector import (
    AccessMethodSelector,
)
from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
    AccessMethodPreference,
)
from src.bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)


# Strategy for generating valid ModelAccessInfo instances
@st.composite
def model_access_info_strategy(draw):
    """Generate valid ModelAccessInfo instances with at least one access method."""
    # Generate simple region names
    region = draw(st.sampled_from(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]))

    # Generate at least one access method
    has_direct = draw(st.booleans())
    has_regional = draw(st.booleans())
    has_global = draw(st.booleans())

    # Ensure at least one is True
    if not (has_direct or has_regional or has_global):
        # Randomly pick one to be True
        choice = draw(st.integers(min_value=0, max_value=2))
        if choice == 0:
            has_direct = True
        elif choice == 1:
            has_regional = True
        else:
            has_global = True

    # Generate IDs based on flags
    model_id = f"model-{draw(st.integers(min_value=1, max_value=1000))}" if has_direct else None
    regional_id = (
        f"regional-profile-{draw(st.integers(min_value=1, max_value=1000))}"
        if has_regional
        else None
    )
    global_id = (
        f"global-profile-{draw(st.integers(min_value=1, max_value=1000))}" if has_global else None
    )

    return ModelAccessInfo(
        region=region,
        has_direct_access=has_direct,
        has_regional_cris=has_regional,
        has_global_cris=has_global,
        model_id=model_id,
        regional_cris_profile_id=regional_id,
        global_cris_profile_id=global_id,
    )


# Strategy for generating AccessMethodPreference instances
@st.composite
def access_method_preference_strategy(draw):
    """Generate valid AccessMethodPreference instances with exactly one preference."""
    # Generate exactly one True preference
    choice = draw(st.integers(min_value=0, max_value=2))

    if choice == 0:
        return AccessMethodPreference(
            prefer_direct=True,
            prefer_regional_cris=False,
            prefer_global_cris=False,
        )
    elif choice == 1:
        return AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=True,
            prefer_global_cris=False,
        )
    else:
        return AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=False,
            prefer_global_cris=True,
        )


class TestAccessMethodSelectorProperties:
    """Property-based tests for AccessMethodSelector."""

    @given(
        access_info=model_access_info_strategy(),
        preference=st.one_of(st.none(), access_method_preference_strategy()),
    )
    @settings(max_examples=100)
    def test_property_selection_consistency(self, access_info, preference):
        """
        Property 2: Access Method Selection Consistency

        For any ModelAccessInfo with multiple access methods available,
        selecting an access method multiple times with the same learned
        preference must return the same result.

        Validates: Requirements 2.1, 2.2
        Feature: inference-profile-support, Property 2: Access Method Selection Consistency
        """
        # Create selector
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Select access method twice with same inputs
        result1 = selector.select_access_method(
            access_info=access_info,
            learned_preference=preference,
        )
        result2 = selector.select_access_method(
            access_info=access_info,
            learned_preference=preference,
        )

        # Results must be identical
        assert result1 == result2, (
            f"Selection inconsistency: first call returned {result1}, "
            f"second call returned {result2}"
        )

        # Result must be a tuple of (model_id, access_method_name)
        assert isinstance(result1, tuple), f"Result must be tuple, got {type(result1)}"
        assert len(result1) == 2, f"Result must have 2 elements, got {len(result1)}"

        model_id_used, access_method_name = result1

        # Verify model_id_used is a string
        assert isinstance(model_id_used, str), f"Model ID must be string, got {type(model_id_used)}"

        # Verify access_method_name is one of the valid names
        valid_methods = {
            AccessMethodNames.DIRECT,
            AccessMethodNames.REGIONAL_CRIS,
            AccessMethodNames.GLOBAL_CRIS,
        }
        assert (
            access_method_name in valid_methods
        ), f"Access method '{access_method_name}' not in valid methods: {valid_methods}"

        # Verify the selected method is actually available
        if access_method_name == AccessMethodNames.DIRECT:
            assert access_info.has_direct_access, "Selected DIRECT but has_direct_access is False"
            assert (
                model_id_used == access_info.model_id
            ), f"Selected DIRECT but model_id mismatch: {model_id_used} != {access_info.model_id}"
        elif access_method_name == AccessMethodNames.REGIONAL_CRIS:
            assert (
                access_info.has_regional_cris
            ), "Selected REGIONAL_CRIS but has_regional_cris is False"
            assert model_id_used == access_info.regional_cris_profile_id, (
                f"Selected REGIONAL_CRIS but profile_id mismatch: "
                f"{model_id_used} != {access_info.regional_cris_profile_id}"
            )
        elif access_method_name == AccessMethodNames.GLOBAL_CRIS:
            assert access_info.has_global_cris, "Selected GLOBAL_CRIS but has_global_cris is False"
            assert model_id_used == access_info.global_cris_profile_id, (
                f"Selected GLOBAL_CRIS but profile_id mismatch: "
                f"{model_id_used} != {access_info.global_cris_profile_id}"
            )

    @given(access_info=model_access_info_strategy())
    @settings(max_examples=100)
    def test_property_preference_order_respected(self, access_info):
        """
        Property: Preference order is respected when no learned preference.

        For any ModelAccessInfo, when no learned preference is provided,
        the selector must follow the default preference order:
        Direct → Regional CRIS → Global CRIS

        Validates: Requirements 2.1, 2.2, 6.2
        Feature: inference-profile-support
        """
        # Create selector
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Select without learned preference
        model_id_used, access_method_name = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        # Verify preference order is respected
        if access_info.has_direct_access:
            # Direct should be selected first if available
            assert (
                access_method_name == AccessMethodNames.DIRECT
            ), f"Expected DIRECT to be selected when available, got {access_method_name}"
        elif access_info.has_regional_cris:
            # Regional CRIS should be selected if direct not available
            assert access_method_name == AccessMethodNames.REGIONAL_CRIS, (
                f"Expected REGIONAL_CRIS to be selected when direct not available, "
                f"got {access_method_name}"
            )
        elif access_info.has_global_cris:
            # Global CRIS should be selected if neither direct nor regional available
            assert access_method_name == AccessMethodNames.GLOBAL_CRIS, (
                f"Expected GLOBAL_CRIS to be selected when only global available, "
                f"got {access_method_name}"
            )

    @given(
        access_info=model_access_info_strategy(),
        preference=access_method_preference_strategy(),
    )
    @settings(max_examples=100)
    def test_property_learned_preference_applied(self, access_info, preference):
        """
        Property: Learned preference is applied when available.

        For any ModelAccessInfo and learned preference, if the preferred
        method is available in the access info, it must be selected.

        Validates: Requirements 2.1, 2.2, 5.4
        Feature: inference-profile-support
        """
        # Create selector
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        model_id_used, access_method_name = selector.select_access_method(
            access_info=access_info,
            learned_preference=preference,
        )

        preferred_method = preference.get_preferred_method()

        # Check if preferred method is available
        if preferred_method == AccessMethodNames.DIRECT and access_info.has_direct_access:
            # Preferred method is available, must be selected
            assert (
                access_method_name == AccessMethodNames.DIRECT
            ), f"Learned preference for DIRECT not applied, got {access_method_name}"
        elif preferred_method == AccessMethodNames.REGIONAL_CRIS and access_info.has_regional_cris:
            # Preferred method is available, must be selected
            assert (
                access_method_name == AccessMethodNames.REGIONAL_CRIS
            ), f"Learned preference for REGIONAL_CRIS not applied, got {access_method_name}"
        elif preferred_method == AccessMethodNames.GLOBAL_CRIS and access_info.has_global_cris:
            # Preferred method is available, must be selected
            assert (
                access_method_name == AccessMethodNames.GLOBAL_CRIS
            ), f"Learned preference for GLOBAL_CRIS not applied, got {access_method_name}"
        # If preferred method not available, fallback to default order (tested elsewhere)

    @given(
        access_info=model_access_info_strategy(),
        failed_method=st.sampled_from(
            [
                AccessMethodNames.DIRECT,
                AccessMethodNames.REGIONAL_CRIS,
                AccessMethodNames.GLOBAL_CRIS,
            ]
        ),
    )
    @settings(max_examples=100)
    def test_property_fallback_ordering(self, access_info, failed_method):
        """
        Property 4: Fallback Access Method Ordering

        For any ModelAccessInfo with multiple access methods, the fallback
        methods must be ordered by preference (direct → regional CRIS → global CRIS)
        and must not include the failed method.

        Validates: Requirements 2.3, 4.4
        Feature: inference-profile-support, Property 4: Fallback Access Method Ordering
        """
        # Create selector
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Get fallback methods
        fallback_methods = selector.get_fallback_access_methods(
            access_info=access_info,
            failed_method=failed_method,
        )

        # Verify fallback methods is a list
        assert isinstance(
            fallback_methods, list
        ), f"Fallback methods must be list, got {type(fallback_methods)}"

        # Verify each fallback is a tuple of (model_id, access_method_name)
        for fallback in fallback_methods:
            assert isinstance(fallback, tuple), f"Each fallback must be tuple, got {type(fallback)}"
            assert len(fallback) == 2, f"Each fallback must have 2 elements, got {len(fallback)}"

            model_id_used, access_method_name = fallback

            # Verify types
            assert isinstance(
                model_id_used, str
            ), f"Model ID must be string, got {type(model_id_used)}"
            assert isinstance(
                access_method_name, str
            ), f"Access method name must be string, got {type(access_method_name)}"

        # Verify failed method is not in fallback list
        fallback_method_names = [method_name for _, method_name in fallback_methods]
        assert (
            failed_method not in fallback_method_names
        ), f"Failed method '{failed_method}' should not be in fallback list: {fallback_method_names}"

        # Verify fallback methods are ordered by preference
        # Expected order: direct → regional_cris → global_cris (excluding failed method)
        expected_order = [
            AccessMethodNames.DIRECT,
            AccessMethodNames.REGIONAL_CRIS,
            AccessMethodNames.GLOBAL_CRIS,
        ]

        # Filter expected order to only include available methods (excluding failed)
        expected_available = []
        for method in expected_order:
            if method == failed_method:
                continue

            if method == AccessMethodNames.DIRECT and access_info.has_direct_access:
                expected_available.append(method)
            elif method == AccessMethodNames.REGIONAL_CRIS and access_info.has_regional_cris:
                expected_available.append(method)
            elif method == AccessMethodNames.GLOBAL_CRIS and access_info.has_global_cris:
                expected_available.append(method)

        # Verify fallback list matches expected order
        assert fallback_method_names == expected_available, (
            f"Fallback methods not in expected order. "
            f"Expected: {expected_available}, Got: {fallback_method_names}"
        )

        # Verify each fallback method is actually available
        for model_id_used, access_method_name in fallback_methods:
            if access_method_name == AccessMethodNames.DIRECT:
                assert (
                    access_info.has_direct_access
                ), "Fallback includes DIRECT but has_direct_access is False"
                assert (
                    model_id_used == access_info.model_id
                ), f"Fallback DIRECT model_id mismatch: {model_id_used} != {access_info.model_id}"
            elif access_method_name == AccessMethodNames.REGIONAL_CRIS:
                assert (
                    access_info.has_regional_cris
                ), "Fallback includes REGIONAL_CRIS but has_regional_cris is False"
                assert model_id_used == access_info.regional_cris_profile_id, (
                    f"Fallback REGIONAL_CRIS profile_id mismatch: "
                    f"{model_id_used} != {access_info.regional_cris_profile_id}"
                )
            elif access_method_name == AccessMethodNames.GLOBAL_CRIS:
                assert (
                    access_info.has_global_cris
                ), "Fallback includes GLOBAL_CRIS but has_global_cris is False"
                assert model_id_used == access_info.global_cris_profile_id, (
                    f"Fallback GLOBAL_CRIS profile_id mismatch: "
                    f"{model_id_used} != {access_info.global_cris_profile_id}"
                )
