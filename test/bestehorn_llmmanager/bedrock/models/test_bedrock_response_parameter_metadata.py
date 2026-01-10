"""
Property-based tests for BedrockResponse parameter metadata.

Tests Property 19: Response Metadata Completeness
Validates Requirements 10.4, 10.5
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RequestAttempt

# Strategy for generating parameter names
parameter_names_strategy = st.lists(
    st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))),
    min_size=1,
    max_size=5,
    unique=True,
)


# Strategy for generating additionalModelRequestFields
additional_fields_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(
        st.text(max_size=50),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.lists(st.text(max_size=20), max_size=5),
    ),
    min_size=1,
    max_size=5,
)


# Strategy for generating RequestAttempt
def request_attempt_strategy(success: bool = True) -> st.SearchStrategy[RequestAttempt]:
    """Generate RequestAttempt instances."""
    return st.builds(
        RequestAttempt,
        model_id=st.sampled_from(
            [
                "Claude 3 Haiku",
                "Claude 3 Sonnet",
                "Claude 3.5 Sonnet v2",
                "Claude Sonnet 4",
                "Titan Text Express",
            ]
        ),
        region=st.sampled_from(["us-east-1", "us-west-2", "eu-west-1"]),
        access_method=st.sampled_from(["direct", "cris"]),
        attempt_number=st.integers(min_value=1, max_value=10),
        start_time=st.just(datetime.now()),
        end_time=st.just(datetime.now()) if success else st.none(),
        success=st.just(success),
        error=st.none() if success else st.just(Exception("Test error")),
    )


class TestBedrockResponseParameterMetadata:
    """
    Property-based tests for BedrockResponse parameter metadata.

    Feature: additional-model-request-fields
    Property 19: Response Metadata Completeness
    """

    @settings(max_examples=100)
    @given(
        parameters_removed=parameter_names_strategy,
        original_fields=additional_fields_strategy,
        final_fields=st.one_of(st.none(), additional_fields_strategy),
    )
    def test_property_19_response_metadata_completeness(
        self,
        parameters_removed: List[str],
        original_fields: Dict[str, Any],
        final_fields: Optional[Dict[str, Any]],
    ) -> None:
        """
        Property 19: Response Metadata Completeness.

        For any response where parameters are removed during retry,
        the BedrockResponse SHALL include metadata indicating this occurred,
        and retry statistics SHALL include parameter compatibility information.

        Validates: Requirements 10.4, 10.5
        """
        # Create a response with parameter removal
        response = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=parameters_removed,
            original_additional_fields=original_fields,
            final_additional_fields=final_fields,
        )

        # Verify metadata is complete and accurate
        assert response.had_parameters_removed() is True
        assert response.parameters_removed == parameters_removed
        assert response.original_additional_fields == original_fields
        assert response.final_additional_fields == final_fields

        # Verify parameter warnings are generated
        warnings = response.get_parameter_warnings()
        assert len(warnings) > 0

        # Each removed parameter should have a warning
        for param_name in parameters_removed:
            assert any(param_name in warning for warning in warnings)

        # If multiple parameters removed, should have summary warning
        if len(parameters_removed) > 1:
            assert any("Total of" in warning for warning in warnings)
            assert any(str(len(parameters_removed)) in warning for warning in warnings)

    @settings(max_examples=100)
    @given(
        parameters_removed=parameter_names_strategy,
        original_fields=additional_fields_strategy,
    )
    def test_property_19_serialization_preserves_metadata(
        self,
        parameters_removed: List[str],
        original_fields: Dict[str, Any],
    ) -> None:
        """
        Property 19: Serialization preserves parameter metadata.

        For any response with parameter metadata, serializing to dict
        and deserializing SHALL preserve all parameter metadata fields.

        Validates: Requirements 10.4
        """
        # Create response with parameter metadata
        response = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=parameters_removed,
            original_additional_fields=original_fields,
            final_additional_fields=None,
        )

        # Serialize to dict
        response_dict = response.to_dict()

        # Verify metadata is in dict
        assert response_dict["parameters_removed"] == parameters_removed
        assert response_dict["original_additional_fields"] == original_fields
        assert response_dict["final_additional_fields"] is None

        # Deserialize from dict
        reconstructed = BedrockResponse.from_dict(response_dict)

        # Verify metadata is preserved
        assert reconstructed.parameters_removed == parameters_removed
        assert reconstructed.original_additional_fields == original_fields
        assert reconstructed.final_additional_fields is None
        assert reconstructed.had_parameters_removed() is True

    @settings(max_examples=100)
    @given(
        parameters_removed=parameter_names_strategy,
        original_fields=additional_fields_strategy,
        final_fields=additional_fields_strategy,
    )
    def test_property_19_json_serialization_preserves_metadata(
        self,
        parameters_removed: List[str],
        original_fields: Dict[str, Any],
        final_fields: Dict[str, Any],
    ) -> None:
        """
        Property 19: JSON serialization preserves parameter metadata.

        For any response with parameter metadata, converting to JSON
        and back SHALL preserve all parameter metadata fields.

        Validates: Requirements 10.4
        """
        import json

        # Create response with parameter metadata
        response = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=parameters_removed,
            original_additional_fields=original_fields,
            final_additional_fields=final_fields,
        )

        # Convert to JSON and back
        json_str = response.to_json()
        response_dict = json.loads(json_str)

        # Verify metadata is in JSON
        assert response_dict["parameters_removed"] == parameters_removed
        assert response_dict["original_additional_fields"] == original_fields
        assert response_dict["final_additional_fields"] == final_fields

        # Reconstruct from dict
        reconstructed = BedrockResponse.from_dict(response_dict)

        # Verify metadata is preserved
        assert reconstructed.parameters_removed == parameters_removed
        assert reconstructed.original_additional_fields == original_fields
        assert reconstructed.final_additional_fields == final_fields

    def test_property_19_no_parameters_removed(self) -> None:
        """
        Property 19: Response without parameter removal.

        For any response where no parameters were removed,
        had_parameters_removed() SHALL return False and
        get_parameter_warnings() SHALL return empty list.

        Validates: Requirements 10.4
        """
        # Create response without parameter removal
        response = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=None,
            original_additional_fields=None,
            final_additional_fields=None,
        )

        # Verify no parameters removed
        assert response.had_parameters_removed() is False
        assert response.get_parameter_warnings() == []

        # Also test with empty list
        response_empty = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=[],
            original_additional_fields=None,
            final_additional_fields=None,
        )

        assert response_empty.had_parameters_removed() is False
        assert response_empty.get_parameter_warnings() == []

    @settings(max_examples=100)
    @given(
        parameters_removed=parameter_names_strategy,
        original_fields=additional_fields_strategy,
        final_fields=additional_fields_strategy,
        attempts=st.lists(request_attempt_strategy(success=True), min_size=1, max_size=3),
    )
    def test_property_19_metadata_with_retry_statistics(
        self,
        parameters_removed: List[str],
        original_fields: Dict[str, Any],
        final_fields: Dict[str, Any],
        attempts: List[RequestAttempt],
    ) -> None:
        """
        Property 19: Metadata includes retry statistics.

        For any response with parameter removal and multiple attempts,
        the response SHALL include both parameter metadata and
        retry statistics that can be correlated.

        Validates: Requirements 10.4, 10.5
        """
        # Create response with parameter metadata and attempts
        response = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=parameters_removed,
            original_additional_fields=original_fields,
            final_additional_fields=final_fields,
            attempts=attempts,
        )

        # Verify parameter metadata is present
        assert response.had_parameters_removed() is True
        assert response.parameters_removed == parameters_removed

        # Verify retry statistics are present
        assert response.get_attempt_count() == len(attempts)
        assert response.get_successful_attempt() is not None

        # Verify both can be accessed together
        response_dict = response.to_dict()
        assert "parameters_removed" in response_dict
        assert "attempts" in response_dict
        assert len(response_dict["attempts"]) == len(attempts)

    @settings(max_examples=100)
    @given(
        param_name=st.text(min_size=1, max_size=30),
    )
    def test_property_19_single_parameter_warning_format(
        self,
        param_name: str,
    ) -> None:
        """
        Property 19: Single parameter warning format.

        For any response with a single parameter removed,
        the warning message SHALL include the parameter name
        and indicate incompatibility.

        Validates: Requirements 10.4
        """
        # Create response with single parameter removed
        response = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=[param_name],
            original_additional_fields={param_name: "value"},
            final_additional_fields=None,
        )

        # Get warnings
        warnings = response.get_parameter_warnings()

        # Should have at least one warning
        assert len(warnings) >= 1

        # Warning should mention the parameter name
        assert any(param_name in warning for warning in warnings)

        # Warning should mention incompatibility
        assert any("incompatibility" in warning.lower() for warning in warnings)

    @settings(max_examples=100)
    @given(
        parameters_removed=st.lists(
            st.text(min_size=1, max_size=20), min_size=2, max_size=5, unique=True
        ),
    )
    def test_property_19_multiple_parameters_summary_warning(
        self,
        parameters_removed: List[str],
    ) -> None:
        """
        Property 19: Multiple parameters summary warning.

        For any response with multiple parameters removed,
        the warnings SHALL include a summary indicating the
        total number of parameters removed.

        Validates: Requirements 10.4
        """
        # Create response with multiple parameters removed
        response = BedrockResponse(
            success=True,
            model_used="Claude Sonnet 4",
            region_used="us-east-1",
            parameters_removed=parameters_removed,
            original_additional_fields={p: "value" for p in parameters_removed},
            final_additional_fields=None,
        )

        # Get warnings
        warnings = response.get_parameter_warnings()

        # Should have warnings for each parameter plus summary
        assert len(warnings) > len(parameters_removed)

        # Should have summary warning
        summary_warnings = [w for w in warnings if "Total of" in w]
        assert len(summary_warnings) >= 1

        # Summary should mention the count
        assert any(str(len(parameters_removed)) in warning for warning in summary_warnings)
