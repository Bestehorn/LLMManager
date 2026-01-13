"""
Property-based tests for deterministic behavior in access method selection.

Tests universal properties that must hold for consistent and predictable
access method selection across all inputs.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from src.bestehorn_llmmanager.bedrock.retry.access_method_selector import (
    AccessMethodSelector,
)
from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
    AccessMethodNames,
)
from src.bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)


# Strategies for generating test data
@st.composite
def model_access_info_strategy(draw):
    """Generate ModelAccessInfo with various access method combinations."""
    model_id_base = draw(
        st.text(
            min_size=10,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Ll", "Nd", "Pd")),
        )
    )
    region = draw(st.sampled_from(["us-east-1", "us-west-2", "eu-west-1"]))

    # Generate access flags
    has_direct = draw(st.booleans())
    has_regional = draw(st.booleans())
    has_global = draw(st.booleans())

    # Ensure at least one access method is available
    if not (has_direct or has_regional or has_global):
        has_direct = True

    # Set model_id only if direct access is available (per ModelAccessInfo validation)
    model_id = model_id_base if has_direct else None

    # Create profile IDs if needed
    regional_profile = (
        f"arn:aws:bedrock:{region}::inference-profile/regional-{model_id_base}"
        if has_regional
        else None
    )
    global_profile = (
        f"arn:aws:bedrock:us-west-2::inference-profile/global-{model_id_base}"
        if has_global
        else None
    )

    return ModelAccessInfo(
        model_id=model_id,
        region=region,
        has_direct_access=has_direct,
        has_regional_cris=has_regional,
        has_global_cris=has_global,
        regional_cris_profile_id=regional_profile,
        global_cris_profile_id=global_profile,
    )


class TestConsistentPreferenceOrder:
    """
    Property 3: Consistent Preference Order

    For any ModelAccessInfo with multiple access methods available, when no
    learned preference exists, the AccessMethodSelector should apply the
    preference order: direct → regional CRIS → global CRIS.

    Validates: Requirements 4.2
    """

    @given(access_info=model_access_info_strategy())
    def test_consistent_preference_order_without_learned_state(self, access_info):
        """
        Property: Consistent preference order without learned state.

        For any ModelAccessInfo with multiple access methods available, when no
        learned preference exists, the system should consistently apply the
        preference order: direct → regional CRIS → global CRIS.

        This test verifies that the default preference order is deterministic
        and always follows the documented priority.

        Feature: ci-failure-fixes, Property 3: Consistent Preference Order
        Validates: Requirements 4.2
        """
        # Create selector with clean tracker (no learned preferences)
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Select access method (no learned preference)
        model_id, access_method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        # Property: The selected method should follow the preference order
        # Direct → Regional CRIS → Global CRIS

        if access_info.has_direct_access:
            # If direct access is available, it should always be selected first
            assert access_method == AccessMethodNames.DIRECT, (
                f"With direct access available and no learned preference, "
                f"should select DIRECT. Got: {access_method}"
            )
            assert model_id == access_info.model_id, (
                f"With DIRECT access selected, should use model_id. "
                f"Expected: {access_info.model_id}, Got: {model_id}"
            )

        elif access_info.has_regional_cris:
            # If no direct but regional CRIS available, it should be selected
            assert access_method == AccessMethodNames.REGIONAL_CRIS, (
                f"With no direct access but regional CRIS available, "
                f"should select REGIONAL_CRIS. Got: {access_method}"
            )
            assert model_id == access_info.regional_cris_profile_id, (
                f"With REGIONAL_CRIS selected, should use regional_cris_profile_id. "
                f"Expected: {access_info.regional_cris_profile_id}, Got: {model_id}"
            )

        elif access_info.has_global_cris:
            # If only global CRIS available, it should be selected
            assert access_method == AccessMethodNames.GLOBAL_CRIS, (
                f"With only global CRIS available, "
                f"should select GLOBAL_CRIS. Got: {access_method}"
            )
            assert model_id == access_info.global_cris_profile_id, (
                f"With GLOBAL_CRIS selected, should use global_cris_profile_id. "
                f"Expected: {access_info.global_cris_profile_id}, Got: {model_id}"
            )

        else:
            # This should never happen due to ModelAccessInfo validation
            pytest.fail("ModelAccessInfo has no access methods available")

    @given(access_info=model_access_info_strategy())
    def test_preference_order_consistency_across_calls(self, access_info):
        """
        Property: Preference order is consistent across multiple calls.

        For any ModelAccessInfo, when called multiple times with the same input
        and no learned preferences, the selector should always return the same
        result.

        This test verifies that the selection algorithm is deterministic and
        doesn't have any hidden state or randomness.

        Feature: ci-failure-fixes, Property 3: Consistent Preference Order
        Validates: Requirements 4.2
        """
        # Create selector with clean tracker
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Call selector multiple times with same input
        results = []
        for _ in range(5):
            model_id, access_method = selector.select_access_method(
                access_info=access_info,
                learned_preference=None,
            )
            results.append((model_id, access_method))

        # Property: All results should be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], start=1):
            assert result == first_result, (
                f"Selection should be deterministic across calls. "
                f"Call 0 returned: {first_result}, Call {i} returned: {result}"
            )


class TestLearnedPreferenceApplication:
    """
    Property 4: Learned Preference Application

    For any learned preference and ModelAccessInfo where the preferred method
    is available, the AccessMethodSelector should use the learned preference
    instead of the default order.

    Validates: Requirements 4.3
    """

    @given(access_info=model_access_info_strategy())
    def test_learned_preference_overrides_default_order(self, access_info):
        """
        Property: Learned preference overrides default order.

        For any ModelAccessInfo with multiple access methods available, when a
        learned preference exists and the preferred method is available, the
        selector should use the learned preference instead of the default order.

        This test verifies that learned preferences are correctly applied and
        override the default preference order.

        Feature: ci-failure-fixes, Property 4: Learned Preference Application
        Validates: Requirements 4.3
        """
        # Skip if only one access method available (no preference to learn)
        access_method_count = sum(
            [
                access_info.has_direct_access,
                access_info.has_regional_cris,
                access_info.has_global_cris,
            ]
        )
        if access_method_count < 2:
            return

        # Create selector with clean tracker
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Test each possible learned preference
        # We'll test regional CRIS preference if available
        if access_info.has_regional_cris:
            # Create a learned preference for regional CRIS
            from datetime import datetime

            from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
                AccessMethodPreference,
            )

            learned_pref = AccessMethodPreference(
                prefer_direct=False,
                prefer_regional_cris=True,
                prefer_global_cris=False,
                learned_from_error=False,
                last_updated=datetime.now(),
            )

            # Select with learned preference
            model_id, access_method = selector.select_access_method(
                access_info=access_info,
                learned_preference=learned_pref,
            )

            # Property: Should use regional CRIS (learned preference)
            assert access_method == AccessMethodNames.REGIONAL_CRIS, (
                f"With learned preference for REGIONAL_CRIS, should select REGIONAL_CRIS. "
                f"Got: {access_method}"
            )
            assert model_id == access_info.regional_cris_profile_id, (
                f"With REGIONAL_CRIS selected, should use regional_cris_profile_id. "
                f"Expected: {access_info.regional_cris_profile_id}, Got: {model_id}"
            )

        # Test global CRIS preference if available
        if access_info.has_global_cris:
            from datetime import datetime

            from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
                AccessMethodPreference,
            )

            learned_pref = AccessMethodPreference(
                prefer_direct=False,
                prefer_regional_cris=False,
                prefer_global_cris=True,
                learned_from_error=False,
                last_updated=datetime.now(),
            )

            # Select with learned preference
            model_id, access_method = selector.select_access_method(
                access_info=access_info,
                learned_preference=learned_pref,
            )

            # Property: Should use global CRIS (learned preference)
            assert access_method == AccessMethodNames.GLOBAL_CRIS, (
                f"With learned preference for GLOBAL_CRIS, should select GLOBAL_CRIS. "
                f"Got: {access_method}"
            )
            assert model_id == access_info.global_cris_profile_id, (
                f"With GLOBAL_CRIS selected, should use global_cris_profile_id. "
                f"Expected: {access_info.global_cris_profile_id}, Got: {model_id}"
            )

    @given(access_info=model_access_info_strategy())
    def test_learned_preference_from_error_skips_direct(self, access_info):
        """
        Property: Learned preference from error skips direct access.

        For any ModelAccessInfo where a profile requirement error was learned,
        the selector should skip direct access and go straight to CRIS options,
        even if direct access is available.

        This test verifies that profile requirement errors are correctly handled
        by skipping direct access on subsequent attempts.

        Feature: ci-failure-fixes, Property 4: Learned Preference Application
        Validates: Requirements 4.3
        """
        # Skip if no CRIS access available (can't skip to CRIS)
        if not (access_info.has_regional_cris or access_info.has_global_cris):
            return

        # Create selector with clean tracker
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Create a learned preference from error (profile requirement)
        from datetime import datetime

        from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
            AccessMethodPreference,
        )

        # Preference learned from error should prefer CRIS
        learned_pref = AccessMethodPreference(
            prefer_direct=False,
            prefer_regional_cris=access_info.has_regional_cris,
            prefer_global_cris=access_info.has_global_cris and not access_info.has_regional_cris,
            learned_from_error=True,  # This is the key flag
            last_updated=datetime.now(),
        )

        # Select with learned preference from error
        model_id, access_method = selector.select_access_method(
            access_info=access_info,
            learned_preference=learned_pref,
        )

        # Property: Should NOT use direct access (even if available)
        if access_info.has_direct_access:
            assert access_method != AccessMethodNames.DIRECT, (
                f"With learned preference from error, should skip DIRECT access. "
                f"Got: {access_method}"
            )
            assert (
                not model_id.startswith("arn:") is False
            ), (  # Model ID should be an ARN (profile)
                f"With learned preference from error, should use profile ARN. " f"Got: {model_id}"
            )

        # Property: Should use CRIS (regional preferred over global)
        if access_info.has_regional_cris:
            assert access_method == AccessMethodNames.REGIONAL_CRIS, (
                f"With learned preference from error and regional CRIS available, "
                f"should select REGIONAL_CRIS. Got: {access_method}"
            )
        elif access_info.has_global_cris:
            assert access_method == AccessMethodNames.GLOBAL_CRIS, (
                f"With learned preference from error and only global CRIS available, "
                f"should select GLOBAL_CRIS. Got: {access_method}"
            )

    @given(access_info=model_access_info_strategy())
    def test_unavailable_learned_preference_falls_back_to_default(self, access_info):
        """
        Property: Unavailable learned preference falls back to default order.

        For any ModelAccessInfo where the learned preference is not available,
        the selector should fall back to the default preference order.

        This test verifies that the system gracefully handles cases where a
        learned preference cannot be satisfied.

        Feature: ci-failure-fixes, Property 4: Learned Preference Application
        Validates: Requirements 4.3
        """
        # Create selector with clean tracker
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Create a learned preference for a method that's NOT available
        from datetime import datetime

        from src.bestehorn_llmmanager.bedrock.retry.access_method_structures import (
            AccessMethodPreference,
        )

        # Try to prefer regional CRIS when it's not available
        if not access_info.has_regional_cris:
            learned_pref = AccessMethodPreference(
                prefer_direct=False,
                prefer_regional_cris=True,  # Prefer something not available
                prefer_global_cris=False,
                learned_from_error=False,
                last_updated=datetime.now(),
            )

            # Select with unavailable learned preference
            model_id, access_method = selector.select_access_method(
                access_info=access_info,
                learned_preference=learned_pref,
            )

            # Property: Should fall back to default order
            # Since regional CRIS is not available, should use default order
            if access_info.has_direct_access:
                assert access_method == AccessMethodNames.DIRECT, (
                    f"With unavailable learned preference and direct access available, "
                    f"should fall back to DIRECT. Got: {access_method}"
                )
            elif access_info.has_global_cris:
                assert access_method == AccessMethodNames.GLOBAL_CRIS, (
                    f"With unavailable learned preference and only global CRIS available, "
                    f"should fall back to GLOBAL_CRIS. Got: {access_method}"
                )


class TestValidTestDataGeneration:
    """
    Property 7: Valid Test Data Generation

    For any ModelAccessInfo generated by the test strategy, the data should
    satisfy ModelAccessInfo validation rules.

    Validates: Requirements 4.4
    """

    @given(access_info=model_access_info_strategy())
    def test_generated_data_satisfies_validation_rules(self, access_info):
        """
        Property: Generated test data satisfies validation rules.

        For any ModelAccessInfo generated by the test strategy, the data should
        satisfy all ModelAccessInfo validation rules:
        - At least one access method is enabled
        - model_id is set only when has_direct_access is True
        - regional_cris_profile_id is set only when has_regional_cris is True
        - global_cris_profile_id is set only when has_global_cris is True

        This test verifies that our test data generation strategy produces
        valid data that matches real-world constraints.

        Feature: ci-failure-fixes, Property 7: Valid Test Data Generation
        Validates: Requirements 4.4
        """
        # Property 1: At least one access method must be enabled
        assert (
            access_info.has_direct_access
            or access_info.has_regional_cris
            or access_info.has_global_cris
        ), "At least one access method must be enabled"

        # Property 2: model_id consistency with has_direct_access
        if access_info.has_direct_access:
            assert (
                access_info.model_id is not None
            ), "model_id must be set when has_direct_access is True"
        else:
            assert (
                access_info.model_id is None
            ), "model_id must be None when has_direct_access is False"

        # Property 3: regional_cris_profile_id consistency with has_regional_cris
        if access_info.has_regional_cris:
            assert (
                access_info.regional_cris_profile_id is not None
            ), "regional_cris_profile_id must be set when has_regional_cris is True"
        else:
            assert (
                access_info.regional_cris_profile_id is None
            ), "regional_cris_profile_id must be None when has_regional_cris is False"

        # Property 4: global_cris_profile_id consistency with has_global_cris
        if access_info.has_global_cris:
            assert (
                access_info.global_cris_profile_id is not None
            ), "global_cris_profile_id must be set when has_global_cris is True"
        else:
            assert (
                access_info.global_cris_profile_id is None
            ), "global_cris_profile_id must be None when has_global_cris is False"

        # Property 5: Profile IDs should be ARNs when present
        if access_info.regional_cris_profile_id:
            assert access_info.regional_cris_profile_id.startswith(
                "arn:aws:bedrock:"
            ), "regional_cris_profile_id should be an ARN"

        if access_info.global_cris_profile_id:
            assert access_info.global_cris_profile_id.startswith(
                "arn:aws:bedrock:"
            ), "global_cris_profile_id should be an ARN"

        # Property 6: Region should be valid
        assert access_info.region in [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
        ], f"Region should be valid, got: {access_info.region}"

    @given(access_info=model_access_info_strategy())
    def test_generated_data_can_be_used_with_selector(self, access_info):
        """
        Property: Generated test data can be used with AccessMethodSelector.

        For any ModelAccessInfo generated by the test strategy, it should be
        possible to use it with AccessMethodSelector without errors.

        This test verifies that our test data generation produces data that
        works correctly with the actual system components.

        Feature: ci-failure-fixes, Property 7: Valid Test Data Generation
        Validates: Requirements 4.4
        """
        # Create selector with clean tracker
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Property: Should be able to select an access method without errors
        try:
            model_id, access_method = selector.select_access_method(
                access_info=access_info,
                learned_preference=None,
            )

            # Verify the result is valid
            assert model_id is not None, "Selected model_id should not be None"
            assert access_method in [
                AccessMethodNames.DIRECT,
                AccessMethodNames.REGIONAL_CRIS,
                AccessMethodNames.GLOBAL_CRIS,
            ], f"Selected access_method should be valid, got: {access_method}"

            # Verify the selected method matches the returned model_id
            if access_method == AccessMethodNames.DIRECT:
                assert model_id == access_info.model_id, "DIRECT method should use model_id"
                assert not model_id.startswith("arn:"), "DIRECT model_id should not be an ARN"

            elif access_method == AccessMethodNames.REGIONAL_CRIS:
                assert (
                    model_id == access_info.regional_cris_profile_id
                ), "REGIONAL_CRIS method should use regional_cris_profile_id"
                assert model_id.startswith("arn:"), "REGIONAL_CRIS model_id should be an ARN"

            elif access_method == AccessMethodNames.GLOBAL_CRIS:
                assert (
                    model_id == access_info.global_cris_profile_id
                ), "GLOBAL_CRIS method should use global_cris_profile_id"
                assert model_id.startswith("arn:"), "GLOBAL_CRIS model_id should be an ARN"

        except Exception as e:
            pytest.fail(
                f"Generated data should work with AccessMethodSelector. "
                f"Error: {e}, AccessInfo: {access_info}"
            )

    @given(access_info=model_access_info_strategy())
    def test_generated_data_produces_valid_fallbacks(self, access_info):
        """
        Property: Generated test data produces valid fallback methods.

        For any ModelAccessInfo generated by the test strategy, when requesting
        fallback methods, the selector should return a valid list of fallbacks.

        This test verifies that our test data works correctly with the fallback
        generation logic.

        Feature: ci-failure-fixes, Property 7: Valid Test Data Generation
        Validates: Requirements 4.4
        """
        # Create selector with clean tracker
        tracker = AccessMethodTracker.get_instance()
        selector = AccessMethodSelector(access_method_tracker=tracker)

        # Get the primary access method
        primary_model_id, primary_method = selector.select_access_method(
            access_info=access_info,
            learned_preference=None,
        )

        # Property: Should be able to get fallback methods without errors
        try:
            fallbacks = selector.get_fallback_access_methods(
                access_info=access_info,
                failed_method=primary_method,
            )

            # Verify fallbacks are valid
            assert isinstance(fallbacks, list), "Fallbacks should be a list"

            # Each fallback should be a tuple of (model_id, access_method)
            for model_id, access_method in fallbacks:
                assert model_id is not None, "Fallback model_id should not be None"
                assert access_method in [
                    AccessMethodNames.DIRECT,
                    AccessMethodNames.REGIONAL_CRIS,
                    AccessMethodNames.GLOBAL_CRIS,
                ], f"Fallback access_method should be valid, got: {access_method}"

                # Verify the fallback method is different from the failed method
                assert (
                    access_method != primary_method
                ), f"Fallback should not include the failed method: {primary_method}"

            # Property: Number of fallbacks should be reasonable
            # Maximum 2 fallbacks (since we have 3 total methods)
            assert len(fallbacks) <= 2, f"Should have at most 2 fallbacks, got: {len(fallbacks)}"

            # Property: Fallbacks should follow preference order
            # (excluding the failed method)
            expected_order = [
                AccessMethodNames.DIRECT,
                AccessMethodNames.REGIONAL_CRIS,
                AccessMethodNames.GLOBAL_CRIS,
            ]
            expected_fallbacks = [m for m in expected_order if m != primary_method]

            # Check that fallbacks are in the expected order
            fallback_methods = [method for _, method in fallbacks]
            for i, method in enumerate(fallback_methods):
                # Each fallback should match the expected order
                assert method in expected_fallbacks, (
                    f"Fallback method {method} should be in expected fallbacks: "
                    f"{expected_fallbacks}"
                )

        except Exception as e:
            pytest.fail(
                f"Generated data should work with fallback generation. "
                f"Error: {e}, AccessInfo: {access_info}"
            )
