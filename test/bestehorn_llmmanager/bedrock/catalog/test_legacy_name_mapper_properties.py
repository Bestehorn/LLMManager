"""
Property-based tests for LegacyNameMapper.

This module contains property-based tests that validate universal properties
of the legacy name mapping system.

**Validates: Requirements 1.4, 4.1, 4.2, 4.3**
"""

from hypothesis import given
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.catalog.legacy_name_mapper import LegacyNameMapper
from bestehorn_llmmanager.bedrock.catalog.legacy_name_mappings import (
    LEGACY_NAME_MAPPINGS,
)


class TestLegacyNameMapperProperties:
    """Property-based tests for LegacyNameMapper."""

    @given(
        legacy_name=(
            st.sampled_from(list(LEGACY_NAME_MAPPINGS.keys()))
            if LEGACY_NAME_MAPPINGS
            else st.just("Claude 3 Haiku")
        )
    )
    def test_property_legacy_name_backward_compatibility(self, legacy_name: str) -> None:
        """
        Property 3: Legacy Name Backward Compatibility.

        For any model name that existed in UnifiedModelManager, if that model
        still exists in BedrockModelCatalog (possibly under a different name),
        then resolving the legacy name must return a valid model.

        **Validates: Requirements 1.4, 4.1, 4.2, 4.3**

        Args:
            legacy_name: Legacy model name from UnifiedModelManager
        """
        # Create mapper instance
        legacy_mapper = LegacyNameMapper()

        # Resolve the legacy name
        catalog_name = legacy_mapper.resolve_legacy_name(user_name=legacy_name)

        # Property: Legacy name must resolve to a valid catalog name
        assert (
            catalog_name is not None
        ), f"Legacy name '{legacy_name}' should resolve to a catalog name"

        # Property: Resolved name must be a non-empty string
        assert isinstance(
            catalog_name, str
        ), f"Resolved catalog name must be a string, got {type(catalog_name)}"
        assert len(catalog_name) > 0, "Resolved catalog name must not be empty"

        # Property: The mapping must be consistent (same input → same output)
        catalog_name_2 = legacy_mapper.resolve_legacy_name(user_name=legacy_name)
        assert catalog_name == catalog_name_2, (
            f"Legacy name resolution must be consistent: "
            f"'{legacy_name}' resolved to '{catalog_name}' first time "
            f"but '{catalog_name_2}' second time"
        )

    @given(
        legacy_name=(
            st.sampled_from(list(LEGACY_NAME_MAPPINGS.keys()))
            if LEGACY_NAME_MAPPINGS
            else st.just("Claude 3 Haiku")
        )
    )
    def test_property_legacy_name_is_recognized(self, legacy_name: str) -> None:
        """
        Property: All legacy names must be recognized as legacy names.

        For any legacy name in the mappings, is_legacy_name() must return True.

        **Validates: Requirements 1.4, 4.1**

        Args:
            legacy_name: Legacy model name from UnifiedModelManager
        """
        # Create mapper instance
        legacy_mapper = LegacyNameMapper()

        # Property: Legacy name must be recognized
        assert legacy_mapper.is_legacy_name(
            user_name=legacy_name
        ), f"Legacy name '{legacy_name}' should be recognized as a legacy name"

    @given(
        legacy_name=(
            st.sampled_from(list(LEGACY_NAME_MAPPINGS.keys()))
            if LEGACY_NAME_MAPPINGS
            else st.just("Claude 3 Haiku")
        ),
        # Generate case variations
        case_transform=st.sampled_from(["lower", "upper", "title", "original"]),
    )
    def test_property_legacy_name_case_insensitivity(
        self, legacy_name: str, case_transform: str
    ) -> None:
        """
        Property: Legacy name resolution should be case-insensitive.

        For any legacy name, resolving it with different casing should
        return the same catalog name (via normalization).

        **Validates: Requirements 2.1, 4.2**

        Args:
            legacy_name: Legacy model name from UnifiedModelManager
            case_transform: Case transformation to apply
        """
        # Create mapper instance
        legacy_mapper = LegacyNameMapper()

        # Apply case transformation
        if case_transform == "lower":
            transformed_name = legacy_name.lower()
        elif case_transform == "upper":
            transformed_name = legacy_name.upper()
        elif case_transform == "title":
            transformed_name = legacy_name.title()
        else:  # original
            transformed_name = legacy_name

        # Resolve both original and transformed names
        original_result = legacy_mapper.resolve_legacy_name(user_name=legacy_name)
        transformed_result = legacy_mapper.resolve_legacy_name(user_name=transformed_name)

        # Property: Both should resolve to the same catalog name
        # (or both should be None, but we know original_result is not None)
        assert original_result == transformed_result, (
            f"Legacy name resolution should be case-insensitive: "
            f"'{legacy_name}' resolved to '{original_result}' "
            f"but '{transformed_name}' resolved to '{transformed_result}'"
        )

    @given(
        legacy_name=(
            st.sampled_from(list(LEGACY_NAME_MAPPINGS.keys()))
            if LEGACY_NAME_MAPPINGS
            else st.just("Claude 3 Haiku")
        )
    )
    def test_property_legacy_name_not_deprecated(self, legacy_name: str) -> None:
        """
        Property: Active legacy names should not be marked as deprecated.

        For any legacy name in the active mappings, is_deprecated() must return False.

        **Validates: Requirements 4.4**

        Args:
            legacy_name: Legacy model name from UnifiedModelManager
        """
        # Create mapper instance
        legacy_mapper = LegacyNameMapper()

        # Property: Active legacy names should not be deprecated
        assert not legacy_mapper.is_deprecated(
            user_name=legacy_name
        ), f"Active legacy name '{legacy_name}' should not be marked as deprecated"

        # Property: Active legacy names should not have deprecation info
        deprecation_info = legacy_mapper.get_deprecation_info(user_name=legacy_name)
        assert deprecation_info is None, (
            f"Active legacy name '{legacy_name}' should not have deprecation info, "
            f"but got: {deprecation_info}"
        )
