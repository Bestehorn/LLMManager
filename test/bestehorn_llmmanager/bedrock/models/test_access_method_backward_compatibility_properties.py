"""
Property-based tests for ModelAccessInfo backward compatibility.

INTENTIONAL DEPRECATION TESTS:
This test file intentionally uses deprecated APIs (access_method property,
inference_profile_id property, ModelAccessMethod.BOTH, ModelAccessMethod.CRIS_ONLY)
to verify backward compatibility. These tests ensure that deprecated APIs continue
to work correctly while emitting appropriate deprecation warnings.

The deprecation warnings from this file are EXPECTED and should not be counted
as issues. These tests validate Requirements 2.5 (backward compatibility).

Feature: ci-failure-fixes
Property 6: Deprecated API Backward Compatibility
Validates: Requirements 2.5
"""

import warnings

from hypothesis import given
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo, ModelAccessMethod
from bestehorn_llmmanager.bedrock.models.deprecation import DeprecatedEnumValueWarning

# Strategy for generating valid model IDs
model_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=".-_"),
    min_size=10,
    max_size=50,
).map(lambda x: f"anthropic.{x}" if "." not in x else x)

# Strategy for generating valid profile IDs
profile_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=".-_"),
    min_size=10,
    max_size=50,
).map(lambda x: f"us.{x}" if "." not in x else x)

# Strategy for generating valid regions
region_strategy = st.sampled_from(
    ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"]
)


# Strategy for generating ModelAccessInfo with direct access
@st.composite
def direct_access_info(draw):
    """Generate ModelAccessInfo with direct access."""
    region = draw(region_strategy)
    model_id = draw(model_id_strategy)
    return ModelAccessInfo(region=region, has_direct_access=True, model_id=model_id)


# Strategy for generating ModelAccessInfo with regional CRIS only
@st.composite
def regional_cris_only_info(draw):
    """Generate ModelAccessInfo with regional CRIS only."""
    region = draw(region_strategy)
    profile_id = draw(profile_id_strategy)
    return ModelAccessInfo(
        region=region, has_regional_cris=True, regional_cris_profile_id=profile_id
    )


# Strategy for generating ModelAccessInfo with global CRIS only
@st.composite
def global_cris_only_info(draw):
    """Generate ModelAccessInfo with global CRIS only."""
    region = draw(region_strategy)
    profile_id = draw(profile_id_strategy)
    return ModelAccessInfo(region=region, has_global_cris=True, global_cris_profile_id=profile_id)


# Strategy for generating ModelAccessInfo with both direct and regional CRIS
@st.composite
def direct_and_regional_cris_info(draw):
    """Generate ModelAccessInfo with both direct and regional CRIS."""
    region = draw(region_strategy)
    model_id = draw(model_id_strategy)
    profile_id = draw(profile_id_strategy)
    return ModelAccessInfo(
        region=region,
        has_direct_access=True,
        has_regional_cris=True,
        model_id=model_id,
        regional_cris_profile_id=profile_id,
    )


# Strategy for generating ModelAccessInfo with both direct and global CRIS
@st.composite
def direct_and_global_cris_info(draw):
    """Generate ModelAccessInfo with both direct and global CRIS."""
    region = draw(region_strategy)
    model_id = draw(model_id_strategy)
    profile_id = draw(profile_id_strategy)
    return ModelAccessInfo(
        region=region,
        has_direct_access=True,
        has_global_cris=True,
        model_id=model_id,
        global_cris_profile_id=profile_id,
    )


# Strategy for generating ModelAccessInfo with all three access methods
@st.composite
def all_access_methods_info(draw):
    """Generate ModelAccessInfo with all three access methods."""
    region = draw(region_strategy)
    model_id = draw(model_id_strategy)
    regional_profile_id = draw(profile_id_strategy)
    global_profile_id = draw(profile_id_strategy)
    return ModelAccessInfo(
        region=region,
        has_direct_access=True,
        has_regional_cris=True,
        has_global_cris=True,
        model_id=model_id,
        regional_cris_profile_id=regional_profile_id,
        global_cris_profile_id=global_profile_id,
    )


class TestBackwardCompatibilityProperties:
    """
    Property-based tests for backward compatibility of deprecated APIs.

    Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
    Validates: Requirements 2.5
    """

    @given(direct_access_info())
    def test_direct_access_backward_compatibility(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo with direct access, the deprecated access_method
        property should return DIRECT.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            access_method = access_info.access_method

            # Should return DIRECT
            assert access_method == ModelAccessMethod.DIRECT

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    @given(st.one_of(regional_cris_only_info(), global_cris_only_info()))
    def test_cris_only_backward_compatibility(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo with CRIS-only access (no direct), the deprecated
        access_method property should return CRIS_ONLY.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            access_method = access_info.access_method

            # Should return CRIS_ONLY
            assert access_method == ModelAccessMethod.CRIS_ONLY

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    @given(
        st.one_of(
            direct_and_regional_cris_info(),
            direct_and_global_cris_info(),
            all_access_methods_info(),
        )
    )
    def test_both_access_backward_compatibility(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo with both direct and CRIS access, the deprecated
        access_method property should return BOTH.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            access_method = access_info.access_method

            # Should return BOTH
            assert access_method == ModelAccessMethod.BOTH

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    @given(regional_cris_only_info())
    def test_inference_profile_id_regional_backward_compatibility(
        self, access_info: ModelAccessInfo
    ):
        """
        Property: For any ModelAccessInfo with regional CRIS, the deprecated
        inference_profile_id property should return the regional profile ID.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile_id = access_info.inference_profile_id

            # Should return regional profile ID
            assert profile_id == access_info.regional_cris_profile_id

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    @given(global_cris_only_info())
    def test_inference_profile_id_global_backward_compatibility(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo with global CRIS only, the deprecated
        inference_profile_id property should return the global profile ID.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile_id = access_info.inference_profile_id

            # Should return global profile ID
            assert profile_id == access_info.global_cris_profile_id

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    @given(all_access_methods_info())
    def test_inference_profile_id_prefers_regional(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo with both regional and global CRIS, the deprecated
        inference_profile_id property should prefer regional over global.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile_id = access_info.inference_profile_id

            # Should prefer regional profile ID
            assert profile_id == access_info.regional_cris_profile_id

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    @given(direct_access_info())
    def test_inference_profile_id_none_for_direct_only(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo with direct access only (no CRIS), the deprecated
        inference_profile_id property should return None.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile_id = access_info.inference_profile_id

            # Should return None
            assert profile_id is None

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)

    @given(
        st.one_of(
            direct_access_info(),
            regional_cris_only_info(),
            global_cris_only_info(),
            direct_and_regional_cris_info(),
            direct_and_global_cris_info(),
            all_access_methods_info(),
        )
    )
    def test_deprecated_properties_always_emit_warnings(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo, accessing deprecated properties should always
        emit deprecation warnings.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        # Test access_method property
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = access_info.access_method
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)
            assert "access_method" in str(w[0].message).lower()

        # Test inference_profile_id property
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = access_info.inference_profile_id
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedEnumValueWarning)
            assert "inference_profile_id" in str(w[0].message).lower()

    @given(
        st.one_of(
            direct_access_info(),
            regional_cris_only_info(),
            global_cris_only_info(),
            direct_and_regional_cris_info(),
            direct_and_global_cris_info(),
            all_access_methods_info(),
        )
    )
    def test_current_api_no_warnings(self, access_info: ModelAccessInfo):
        """
        Property: For any ModelAccessInfo, accessing current API properties should not
        emit any warnings.

        Feature: ci-failure-fixes, Property 6: Deprecated API Backward Compatibility
        Validates: Requirements 2.5
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Access all current API properties
            _ = access_info.has_direct_access
            _ = access_info.has_regional_cris
            _ = access_info.has_global_cris
            _ = access_info.model_id
            _ = access_info.regional_cris_profile_id
            _ = access_info.global_cris_profile_id
            _ = access_info.region

            # Should not emit any warnings
            assert len(w) == 0
