"""
Unit tests for RequestValidator.
Tests request validation functionality for parallel processing.
"""

from unittest.mock import patch

import pytest

from bestehorn_llmmanager.bedrock.exceptions.parallel_exceptions import (
    RequestIdCollisionError,
    RequestValidationError,
)
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest
from bestehorn_llmmanager.bedrock.validators.request_validator import RequestValidator


class TestRequestValidator:
    """Test cases for RequestValidator initialization."""

    def test_initialization(self):
        """Test successful initialization."""
        validator = RequestValidator()

        assert hasattr(validator, "_logger")
        assert validator._logger.name == "bestehorn_llmmanager.bedrock.validators.request_validator"


class TestValidateRequestIds:
    """Test cases for validate_request_ids method."""

    def test_validate_request_ids_success(self):
        """Test successful validation with unique request IDs."""
        validator = RequestValidator()

        # Create requests with unique IDs
        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}], request_id="req-1"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}], request_id="req-2"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 3"}]}], request_id="req-3"
            ),
        ]

        # Should not raise any exception
        validator.validate_request_ids(requests=requests)

    def test_validate_request_ids_empty_list(self):
        """Test validation with empty request list."""
        validator = RequestValidator()

        with pytest.raises(RequestValidationError) as exc_info:
            validator.validate_request_ids(requests=[])

        assert "request list cannot be empty" in str(exc_info.value).lower()

    def test_validate_request_ids_collision_single_duplicate(self):
        """Test validation with single duplicate request ID."""
        validator = RequestValidator()

        # Create requests with duplicate IDs
        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                request_id="duplicate-id",
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}],
                request_id="unique-id",
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 3"}]}],
                request_id="duplicate-id",
            ),
        ]

        with pytest.raises(RequestIdCollisionError) as exc_info:
            validator.validate_request_ids(requests=requests)

        error = exc_info.value
        assert "duplicate-id" in error.duplicated_ids
        assert len(error.duplicated_ids["duplicate-id"]) == 2

    def test_validate_request_ids_collision_multiple_duplicates(self):
        """Test validation with multiple duplicate request IDs."""
        validator = RequestValidator()

        # Create requests with multiple duplicate IDs
        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}], request_id="dup-1"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}], request_id="dup-1"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 3"}]}], request_id="dup-2"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 4"}]}], request_id="dup-2"
            ),
        ]

        with pytest.raises(RequestIdCollisionError) as exc_info:
            validator.validate_request_ids(requests=requests)

        error = exc_info.value
        assert "dup-1" in error.duplicated_ids
        assert "dup-2" in error.duplicated_ids
        assert len(error.duplicated_ids["dup-1"]) == 2
        assert len(error.duplicated_ids["dup-2"]) == 2

    def test_validate_request_ids_with_none_id(self):
        """Test validation handles requests with None IDs gracefully."""
        validator = RequestValidator()

        # Manually create request with None ID (bypassing __post_init__)
        request1 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello 1"}]}], request_id="valid-id"
        )
        request2 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello 2"}]}]
        )
        # Manually set to None to test edge case
        request2.request_id = None

        requests = [request1, request2]

        # Should not raise exception (None IDs are filtered out)
        validator.validate_request_ids(requests=requests)

    @patch(
        "bestehorn_llmmanager.bedrock.validators.request_validator.RequestValidator._log_collision_details"
    )
    def test_validate_request_ids_logs_collision_details(self, mock_log):
        """Test that collision details are logged."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                request_id="collision-id",
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}],
                request_id="collision-id",
            ),
        ]

        with pytest.raises(RequestIdCollisionError):
            validator.validate_request_ids(requests=requests)

        mock_log.assert_called_once()


class TestGroupRequestsById:
    """Test cases for _group_requests_by_id method."""

    def test_group_requests_by_id_unique_ids(self):
        """Test grouping requests with unique IDs."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}], request_id="id-1"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}], request_id="id-2"
            ),
        ]

        grouped = validator._group_requests_by_id(requests=requests)

        assert len(grouped) == 2
        assert "id-1" in grouped
        assert "id-2" in grouped
        assert len(grouped["id-1"]) == 1
        assert len(grouped["id-2"]) == 1

    def test_group_requests_by_id_duplicate_ids(self):
        """Test grouping requests with duplicate IDs."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                request_id="duplicate",
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}], request_id="unique"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 3"}]}],
                request_id="duplicate",
            ),
        ]

        grouped = validator._group_requests_by_id(requests=requests)

        assert len(grouped) == 2
        assert "duplicate" in grouped
        assert "unique" in grouped
        assert len(grouped["duplicate"]) == 2
        assert len(grouped["unique"]) == 1

    def test_group_requests_by_id_with_none_ids(self):
        """Test grouping requests with None IDs."""
        validator = RequestValidator()

        request1 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello 1"}]}], request_id="valid-id"
        )
        request2 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello 2"}]}]
        )
        request2.request_id = None  # Manually set to None

        requests = [request1, request2]

        grouped = validator._group_requests_by_id(requests=requests)

        # Only valid-id should be in the result
        assert len(grouped) == 1
        assert "valid-id" in grouped
        assert len(grouped["valid-id"]) == 1


class TestFindDuplicateIds:
    """Test cases for _find_duplicate_ids method."""

    def test_find_duplicate_ids_no_duplicates(self):
        """Test finding duplicates when there are none."""
        validator = RequestValidator()

        req1 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hello"}]}])
        req2 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hi"}]}])
        req3 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hey"}]}])

        id_to_requests = {
            "id-1": [req1],
            "id-2": [req2],
            "id-3": [req3],
        }

        duplicates = validator._find_duplicate_ids(id_to_requests=id_to_requests)

        assert len(duplicates) == 0

    def test_find_duplicate_ids_with_duplicates(self):
        """Test finding duplicates when they exist."""
        validator = RequestValidator()

        req1 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hello"}]}])
        req2 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hi"}]}])
        req3 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hey"}]}])
        duplicate_requests = [req2, req3]

        id_to_requests = {
            "id-1": [req1],
            "duplicate-id": duplicate_requests,
            "id-3": [req1],
        }

        duplicates = validator._find_duplicate_ids(id_to_requests=id_to_requests)

        assert len(duplicates) == 1
        assert "duplicate-id" in duplicates
        assert duplicates["duplicate-id"] == duplicate_requests

    def test_find_duplicate_ids_multiple_duplicates(self):
        """Test finding multiple duplicate IDs."""
        validator = RequestValidator()

        req1 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hello"}]}])
        req2 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hi"}]}])
        req3 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Hey"}]}])
        req4 = BedrockConverseRequest(messages=[{"role": "user", "content": [{"text": "Howdy"}]}])

        duplicate_requests_1 = [req1, req2]
        duplicate_requests_2 = [req3, req4, req1]

        id_to_requests = {
            "id-1": [req1],
            "dup-1": duplicate_requests_1,
            "dup-2": duplicate_requests_2,
            "id-4": [req2],
        }

        duplicates = validator._find_duplicate_ids(id_to_requests=id_to_requests)

        assert len(duplicates) == 2
        assert "dup-1" in duplicates
        assert "dup-2" in duplicates
        assert duplicates["dup-1"] == duplicate_requests_1
        assert duplicates["dup-2"] == duplicate_requests_2


class TestLogCollisionDetails:
    """Test cases for _log_collision_details method."""

    def test_log_collision_details_single_collision(self):
        """Test logging collision details for single collision."""
        validator = RequestValidator()

        request_1 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello"}]}],
            system=None,
            inference_config=None,
        )

        request_2 = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hi"}]}],
            system=[{"text": "System message"}],
            inference_config={"maxTokens": 100},
        )

        duplicates = {"collision-id": [request_1, request_2]}

        with patch.object(validator._logger, "error") as mock_error:
            validator._log_collision_details(duplicates=duplicates)

            # Verify logging was called
            assert mock_error.call_count >= 2  # Main collision message + details

    def test_log_collision_details_multiple_collisions(self):
        """Test logging collision details for multiple collisions."""
        validator = RequestValidator()

        request_1 = BedrockConverseRequest(messages=[], system=None, inference_config=None)

        request_2 = BedrockConverseRequest(messages=[], system=None, inference_config=None)

        duplicates = {"collision-1": [request_1, request_2], "collision-2": [request_1, request_2]}

        with patch.object(validator._logger, "error") as mock_error:
            validator._log_collision_details(duplicates=duplicates)

            # Should log for both collision IDs
            assert mock_error.call_count >= 4


class TestValidateRequestStructure:
    """Test cases for validate_request_structure method."""

    def test_validate_request_structure_valid_request(self):
        """Test validation of valid request structure."""
        validator = RequestValidator()

        request = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello"}]}]
        )

        errors = validator.validate_request_structure(request=request)

        assert len(errors) == 0

    def test_validate_request_structure_empty_messages(self):
        """Test validation with empty messages."""
        validator = RequestValidator()

        request = BedrockConverseRequest(messages=[])

        errors = validator.validate_request_structure(request=request)

        assert len(errors) == 1
        assert "at least one message" in errors[0]

    def test_validate_request_structure_invalid_system_messages(self):
        """Test validation with invalid system messages."""
        validator = RequestValidator()

        request = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello"}]}],
            system=["not a dict", {"missing_text_field": "value"}],
        )

        errors = validator.validate_request_structure(request=request)

        assert len(errors) == 2
        assert "must be a dictionary" in errors[0]
        assert "must have 'text' field" in errors[1]

    def test_validate_request_structure_invalid_inference_config(self):
        """Test validation with invalid inference config."""
        validator = RequestValidator()

        request = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello"}]}],
            inference_config={
                "maxTokens": -1,  # Invalid
                "temperature": 2.0,  # Invalid
                "topP": 1.5,  # Invalid
            },
        )

        errors = validator.validate_request_structure(request=request)

        assert len(errors) == 3
        assert any("maxTokens must be a positive integer" in error for error in errors)
        assert any("temperature must be a number between 0.0 and 1.0" in error for error in errors)
        assert any("topP must be a number between 0.0 and 1.0" in error for error in errors)

    def test_validate_request_structure_with_valid_system_and_inference(self):
        """Test validation with valid system messages and inference config."""
        validator = RequestValidator()

        request = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello"}]}],
            system=[{"text": "You are a helpful assistant"}],
            inference_config={"maxTokens": 100, "temperature": 0.7, "topP": 0.9},
        )

        errors = validator.validate_request_structure(request=request)

        assert len(errors) == 0


class TestValidateMessageStructure:
    """Test cases for _validate_message_structure method."""

    def test_validate_message_structure_valid_message(self):
        """Test validation of valid message structure."""
        validator = RequestValidator()

        message = {"role": "user", "content": [{"text": "Hello"}]}

        errors = validator._validate_message_structure(message=message, index=0)

        assert len(errors) == 0

    def test_validate_message_structure_missing_role(self):
        """Test validation with missing role field."""
        validator = RequestValidator()

        message = {"content": [{"text": "Hello"}]}

        errors = validator._validate_message_structure(message=message, index=0)

        assert len(errors) == 1
        assert "missing required 'role' field" in errors[0]

    def test_validate_message_structure_invalid_role(self):
        """Test validation with invalid role."""
        validator = RequestValidator()

        message = {"role": "invalid_role", "content": [{"text": "Hello"}]}

        errors = validator._validate_message_structure(message=message, index=0)

        assert len(errors) == 1
        assert "invalid role" in errors[0]

    def test_validate_message_structure_missing_content(self):
        """Test validation with missing content field."""
        validator = RequestValidator()

        message = {"role": "user"}

        errors = validator._validate_message_structure(message=message, index=0)

        assert len(errors) == 1
        assert "missing required 'content' field" in errors[0]

    def test_validate_message_structure_invalid_content_type(self):
        """Test validation with invalid content type."""
        validator = RequestValidator()

        message = {"role": "user", "content": "not a list"}

        errors = validator._validate_message_structure(message=message, index=0)

        assert len(errors) == 1
        assert "content must be a list" in errors[0]

    def test_validate_message_structure_with_content_errors(self):
        """Test validation with content block errors."""
        validator = RequestValidator()

        message = {"role": "user", "content": []}  # Empty content

        errors = validator._validate_message_structure(message=message, index=0)

        assert len(errors) == 1
        assert "at least one content block" in errors[0]


class TestValidateContentBlocks:
    """Test cases for _validate_content_blocks method."""

    def test_validate_content_blocks_valid_blocks(self):
        """Test validation of valid content blocks."""
        validator = RequestValidator()

        content_blocks = [
            {"text": "Hello"},
            {"image": {"format": "jpeg", "source": {"bytes": b"image_data"}}},
            {"toolUse": {"toolUseId": "123", "name": "function", "input": {}}},
        ]

        errors = validator._validate_content_blocks(content_blocks=content_blocks, message_index=0)

        assert len(errors) == 0

    def test_validate_content_blocks_empty_blocks(self):
        """Test validation with empty content blocks."""
        validator = RequestValidator()

        content_blocks = []

        errors = validator._validate_content_blocks(content_blocks=content_blocks, message_index=0)

        assert len(errors) == 1
        assert "at least one content block" in errors[0]

    def test_validate_content_blocks_invalid_block_type(self):
        """Test validation with invalid block type."""
        validator = RequestValidator()

        content_blocks = ["not a dict", {"text": "Valid block"}]

        errors = validator._validate_content_blocks(content_blocks=content_blocks, message_index=0)

        assert len(errors) == 1
        assert "must be a dictionary" in errors[0]

    def test_validate_content_blocks_no_content_type(self):
        """Test validation with blocks that have no content type."""
        validator = RequestValidator()

        content_blocks = [{"invalid_field": "value"}, {"text": "Valid block"}]

        errors = validator._validate_content_blocks(content_blocks=content_blocks, message_index=0)

        assert len(errors) == 1
        assert "at least one content type" in errors[0]


class TestValidateInferenceConfig:
    """Test cases for _validate_inference_config method."""

    def test_validate_inference_config_valid_config(self):
        """Test validation of valid inference config."""
        validator = RequestValidator()

        config = {"maxTokens": 100, "temperature": 0.7, "topP": 0.9}

        errors = validator._validate_inference_config(config=config)

        assert len(errors) == 0

    def test_validate_inference_config_invalid_max_tokens(self):
        """Test validation with invalid maxTokens."""
        validator = RequestValidator()

        configs = [
            {"maxTokens": -1},
            {"maxTokens": 0},
            {"maxTokens": "not_an_int"},
            {"maxTokens": 1.5},
        ]

        for config in configs:
            errors = validator._validate_inference_config(config=config)
            assert len(errors) == 1
            assert "maxTokens must be a positive integer" in errors[0]

    def test_validate_inference_config_invalid_temperature(self):
        """Test validation with invalid temperature."""
        validator = RequestValidator()

        configs = [{"temperature": -0.1}, {"temperature": 1.1}, {"temperature": "not_a_number"}]

        for config in configs:
            errors = validator._validate_inference_config(config=config)
            assert len(errors) == 1
            assert "temperature must be a number between 0.0 and 1.0" in errors[0]

    def test_validate_inference_config_invalid_top_p(self):
        """Test validation with invalid topP."""
        validator = RequestValidator()

        configs = [{"topP": -0.1}, {"topP": 1.1}, {"topP": "not_a_number"}]

        for config in configs:
            errors = validator._validate_inference_config(config=config)
            assert len(errors) == 1
            assert "topP must be a number between 0.0 and 1.0" in errors[0]

    def test_validate_inference_config_edge_values(self):
        """Test validation with edge values."""
        validator = RequestValidator()

        config = {"maxTokens": 1, "temperature": 0.0, "topP": 1.0}

        errors = validator._validate_inference_config(config=config)

        assert len(errors) == 0

    def test_validate_inference_config_empty_config(self):
        """Test validation with empty config."""
        validator = RequestValidator()

        config = {}

        errors = validator._validate_inference_config(config=config)

        assert len(errors) == 0


class TestValidateBatchRequests:
    """Test cases for validate_batch_requests method."""

    def test_validate_batch_requests_valid_batch(self):
        """Test validation of valid request batch."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}], request_id="req-1"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}], request_id="req-2"
            ),
        ]

        # Should not raise any exception
        validator.validate_batch_requests(requests=requests)

    def test_validate_batch_requests_with_id_collision(self):
        """Test validation with request ID collision."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                request_id="duplicate-id",
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}],
                request_id="duplicate-id",
            ),
        ]

        with pytest.raises(RequestIdCollisionError):
            validator.validate_batch_requests(requests=requests)

    def test_validate_batch_requests_with_structure_errors(self):
        """Test validation with request structure errors."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Valid request"}]}],
                request_id="valid-req",
            ),
            BedrockConverseRequest(
                messages=[], request_id="invalid-req"  # Invalid: empty messages
            ),
        ]

        with pytest.raises(RequestValidationError) as exc_info:
            validator.validate_batch_requests(requests=requests)

        error = exc_info.value
        assert "structure validation failed" in str(error)
        assert hasattr(error, "validation_errors")
        assert len(error.validation_errors) > 0
        assert "invalid-req" in error.validation_errors[0]

    def test_validate_batch_requests_multiple_structure_errors(self):
        """Test validation with multiple structure errors."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(messages=[], request_id="invalid-1"),  # Invalid: empty messages
            BedrockConverseRequest(
                messages=[{"invalid": "message"}],  # Invalid: missing role and content
                request_id="invalid-2",
            ),
        ]

        with pytest.raises(RequestValidationError) as exc_info:
            validator.validate_batch_requests(requests=requests)

        error = exc_info.value
        assert hasattr(error, "validation_errors")
        assert len(error.validation_errors) > 0
        # Should have errors for both requests
        assert any("invalid-1" in err for err in error.validation_errors)
        assert any("invalid-2" in err for err in error.validation_errors)

    def test_validate_batch_requests_success_logging(self):
        """Test that successful validation logs completion."""
        validator = RequestValidator()

        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello"}]}], request_id="req-1"
            ),
        ]

        with patch.object(validator._logger, "info") as mock_info:
            validator.validate_batch_requests(requests=requests)

            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "Batch validation completed successfully" in call_args
            assert "1 requests" in call_args
