"""
Property-based tests for name normalization.

This module contains property-based tests using Hypothesis to verify
universal properties of model name normalization.

**Feature: fix-integration-test-models**

Properties tested:
1. Normalization Idempotence
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.catalog.name_normalizer import normalize_model_name

# ============================================================================
# Hypothesis Strategies
# ============================================================================


@st.composite
def model_name_strategy(draw: st.DrawFn) -> str:
    """
    Generate random model names for testing.

    Generates model names with various characteristics:
    - Different cases (upper, lower, mixed)
    - Special characters (-, _, .)
    - Multiple spaces
    - Version numbers
    - Empty strings
    """
    # Generate base components
    providers = ["Claude", "Titan", "Llama", "Mistral", "Cohere"]
    versions = ["3", "3.5", "4", "4.5", "2.1", "8B", "70B"]
    variants = ["Haiku", "Sonnet", "Opus", "Lite", "Express", "Instruct"]
    prefixes = ["APAC", "EU", "US", ""]

    # Randomly select components
    prefix = draw(st.sampled_from(prefixes))
    provider = draw(st.sampled_from(providers))
    version = draw(st.sampled_from(versions))
    variant = draw(st.sampled_from(variants))

    # Build name with random separators and spacing
    separator = draw(st.sampled_from([" ", "-", "_", "."]))
    spacing = draw(st.sampled_from(["", " ", "  ", "   "]))

    parts = []
    if prefix:
        parts.append(prefix)
    parts.extend([provider, version, variant])

    # Join with random separators and spacing
    name = separator.join(parts)

    # Add random extra spacing
    if spacing:
        name = spacing + name + spacing

    # Randomly change case
    case_transform = draw(st.sampled_from(["upper", "lower", "title", "none"]))
    if case_transform == "upper":
        name = name.upper()
    elif case_transform == "lower":
        name = name.lower()
    elif case_transform == "title":
        name = name.title()

    return name


# ============================================================================
# Property 2: Normalization Idempotence
# **Feature: fix-integration-test-models, Property 2: Normalization Idempotence**
# **Validates: Requirements 2.1**
# ============================================================================


class TestProperty2NormalizationIdempotence:
    """
    Property 2: Normalization Idempotence.

    For any model name, normalizing it multiple times must produce the same
    result as normalizing it once.
    """

    @given(model_name=model_name_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_2_normalization_is_idempotent(self, model_name: str) -> None:
        """
        Property: For any model name, normalize(normalize(name)) == normalize(name).

        This property verifies that normalization is idempotent - applying it
        multiple times produces the same result as applying it once.
        """
        # First normalization
        normalized_once = normalize_model_name(name=model_name)

        # Second normalization
        normalized_twice = normalize_model_name(name=normalized_once)

        # Third normalization (extra verification)
        normalized_thrice = normalize_model_name(name=normalized_twice)

        # Property: All normalizations should produce the same result
        assert (
            normalized_once == normalized_twice
        ), f"Normalization not idempotent: '{normalized_once}' != '{normalized_twice}'"

        assert (
            normalized_twice == normalized_thrice
        ), f"Normalization not idempotent: '{normalized_twice}' != '{normalized_thrice}'"

    @given(
        model_name=st.one_of(
            st.just(None),
            st.just(""),
            st.just("   "),
            st.just("\t\n"),
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_property_2_normalization_handles_empty_input(self, model_name: str) -> None:
        """
        Property: For any empty/None input, normalization is idempotent.

        This property verifies that normalization handles edge cases like
        None, empty strings, and whitespace-only strings correctly.
        """
        # First normalization
        normalized_once = normalize_model_name(name=model_name)

        # Second normalization
        normalized_twice = normalize_model_name(name=normalized_once)

        # Property: Should always produce empty string
        assert normalized_once == "", f"Expected empty string, got '{normalized_once}'"
        assert normalized_twice == "", f"Expected empty string, got '{normalized_twice}'"

        # Property: Idempotence holds
        assert (
            normalized_once == normalized_twice
        ), f"Normalization not idempotent for empty input: '{normalized_once}' != '{normalized_twice}'"

    @given(
        model_name=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Pd", "Pc", "Zs"),
                whitelist_characters="-_. ",
            ),
            min_size=1,
            max_size=100,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_normalization_idempotent_for_arbitrary_text(self, model_name: str) -> None:
        """
        Property: For any arbitrary text, normalization is idempotent.

        This property verifies idempotence for a wide range of arbitrary
        text inputs, not just model-like names.
        """
        # First normalization
        normalized_once = normalize_model_name(name=model_name)

        # Second normalization
        normalized_twice = normalize_model_name(name=normalized_once)

        # Property: Idempotence holds
        assert (
            normalized_once == normalized_twice
        ), f"Normalization not idempotent: '{normalized_once}' != '{normalized_twice}'"
