"""
Request validation functionality for parallel processing in LLM Manager system.
Handles request ID collision detection and request structure validation.
"""

import logging
from typing import Dict, List

from ..exceptions.parallel_exceptions import RequestIdCollisionError, RequestValidationError
from ..models.parallel_constants import ParallelErrorMessages, ParallelLogMessages
from ..models.parallel_structures import BedrockConverseRequest


class RequestValidator:
    """
    Validates collections of BedrockConverseRequest objects.

    Provides functionality for:
    - Request ID uniqueness validation
    - Request structure validation
    - Batch request validation
    """

    def __init__(self) -> None:
        """Initialize the request validator."""
        self._logger = logging.getLogger(__name__)

    def validate_request_ids(self, requests: List[BedrockConverseRequest]) -> None:
        """
        Validate that all request IDs in the collection are unique.

        Args:
            requests: List of BedrockConverseRequest objects to validate

        Raises:
            RequestValidationError: If the request list is empty
            RequestIdCollisionError: If duplicate request IDs are found
        """
        if not requests:
            raise RequestValidationError(message=ParallelErrorMessages.EMPTY_REQUEST_LIST)

        # Group requests by ID to detect duplicates
        id_to_requests = self._group_requests_by_id(requests=requests)

        # Find duplicates
        duplicates = self._find_duplicate_ids(id_to_requests=id_to_requests)

        if duplicates:
            self._log_collision_details(duplicates=duplicates)
            raise RequestIdCollisionError(duplicated_ids=duplicates)

        self._logger.debug(f"Request ID validation passed for {len(requests)} requests")

    def _group_requests_by_id(
        self, requests: List[BedrockConverseRequest]
    ) -> Dict[str, List[BedrockConverseRequest]]:
        """
        Group requests by their request IDs.

        Args:
            requests: List of requests to group

        Returns:
            Dictionary mapping request_id to list of requests with that ID
        """
        id_to_requests: Dict[str, List[BedrockConverseRequest]] = {}

        for request in requests:
            req_id = request.request_id
            if req_id is None:
                # This shouldn't happen due to __post_init__, but handle gracefully
                continue

            if req_id in id_to_requests:
                id_to_requests[req_id].append(request)
            else:
                id_to_requests[req_id] = [request]

        return id_to_requests

    def _find_duplicate_ids(
        self, id_to_requests: Dict[str, List[BedrockConverseRequest]]
    ) -> Dict[str, List[BedrockConverseRequest]]:
        """
        Find request IDs that have duplicates.

        Args:
            id_to_requests: Dictionary mapping request_id to list of requests

        Returns:
            Dictionary containing only the duplicate IDs and their requests
        """
        return {
            req_id: requests for req_id, requests in id_to_requests.items() if len(requests) > 1
        }

    def _log_collision_details(self, duplicates: Dict[str, List[BedrockConverseRequest]]) -> None:
        """
        Log detailed information about request ID collisions.

        Args:
            duplicates: Dictionary of duplicate IDs and their requests
        """
        for req_id, duplicate_requests in duplicates.items():
            self._logger.error(
                ParallelLogMessages.REQUEST_ID_COLLISION_DETECTED.format(
                    request_id=req_id, collision_count=len(duplicate_requests)
                )
            )

            # Log details about each colliding request
            for i, request in enumerate(duplicate_requests):
                self._logger.error(
                    f"  Collision {i + 1}: {len(request.messages)} messages, "
                    f"system={request.system is not None}, "
                    f"inference_config={request.inference_config is not None}"
                )

    def validate_request_structure(self, request: BedrockConverseRequest) -> List[str]:
        """
        Validate the structure of a single request.

        Args:
            request: BedrockConverseRequest to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        validation_errors = []

        # Validate messages
        if not request.messages:
            validation_errors.append("Request must have at least one message")
        else:
            for i, message in enumerate(request.messages):
                message_errors = self._validate_message_structure(message=message, index=i)
                validation_errors.extend(message_errors)

        # Validate system messages if present
        if request.system is not None:
            for i, system_msg in enumerate(request.system):
                if not isinstance(system_msg, dict):
                    validation_errors.append(f"System message {i} must be a dictionary")
                elif "text" not in system_msg:
                    validation_errors.append(f"System message {i} must have 'text' field")

        # Validate inference config if present
        if request.inference_config is not None:
            inference_errors = self._validate_inference_config(config=request.inference_config)
            validation_errors.extend(inference_errors)

        return validation_errors

    def _validate_message_structure(self, message: Dict, index: int) -> List[str]:
        """
        Validate the structure of a single message.

        Args:
            message: Message dictionary to validate
            index: Index of the message for error reporting

        Returns:
            List of validation error messages
        """
        errors = []

        # Check required fields
        if "role" not in message:
            errors.append(f"Message {index} missing required 'role' field")
        elif message["role"] not in ["user", "assistant"]:
            errors.append(f"Message {index} has invalid role: {message['role']}")

        if "content" not in message:
            errors.append(f"Message {index} missing required 'content' field")
        elif not isinstance(message["content"], list):
            errors.append(f"Message {index} content must be a list")
        else:
            # Validate content blocks
            content_errors = self._validate_content_blocks(
                content_blocks=message["content"], message_index=index
            )
            errors.extend(content_errors)

        return errors

    def _validate_content_blocks(self, content_blocks: List, message_index: int) -> List[str]:
        """
        Validate content blocks within a message.

        Args:
            content_blocks: List of content blocks to validate
            message_index: Index of the parent message

        Returns:
            List of validation error messages
        """
        errors = []

        if not content_blocks:
            errors.append(f"Message {message_index} must have at least one content block")
            return errors

        for i, block in enumerate(content_blocks):
            if not isinstance(block, dict):
                errors.append(f"Message {message_index}, block {i} must be a dictionary")
                continue

            # Check that block has at least one content type
            content_types = ["text", "image", "document", "video", "toolUse", "toolResult"]
            if not any(content_type in block for content_type in content_types):
                errors.append(
                    f"Message {message_index}, block {i} must have at least one content type"
                )

        return errors

    def _validate_inference_config(self, config: Dict) -> List[str]:
        """
        Validate inference configuration parameters.

        Args:
            config: Inference configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate maxTokens if present
        if "maxTokens" in config:
            max_tokens = config["maxTokens"]
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                errors.append("maxTokens must be a positive integer")

        # Validate temperature if present
        if "temperature" in config:
            temperature = config["temperature"]
            if not isinstance(temperature, (int, float)) or not (0.0 <= temperature <= 1.0):
                errors.append("temperature must be a number between 0.0 and 1.0")

        # Validate topP if present
        if "topP" in config:
            top_p = config["topP"]
            if not isinstance(top_p, (int, float)) or not (0.0 <= top_p <= 1.0):
                errors.append("topP must be a number between 0.0 and 1.0")

        return errors

    def validate_batch_requests(self, requests: List[BedrockConverseRequest]) -> None:
        """
        Validate a complete batch of requests.

        Performs both ID collision detection and structure validation.

        Args:
            requests: List of BedrockConverseRequest objects to validate

        Raises:
            RequestValidationError: If any validation errors are found
            RequestIdCollisionError: If duplicate request IDs are found
        """
        # First validate request IDs for uniqueness
        self.validate_request_ids(requests=requests)

        # Then validate individual request structures
        all_validation_errors = []

        for request in requests:
            structure_errors = self.validate_request_structure(request=request)
            if structure_errors:
                for error in structure_errors:
                    all_validation_errors.append(f"Request {request.request_id}: {error}")

        if all_validation_errors:
            error_message = (
                f"Request structure validation failed: {len(all_validation_errors)} errors found"
            )
            raise RequestValidationError(
                message=error_message, validation_errors=all_validation_errors
            )

        self._logger.info(f"Batch validation completed successfully for {len(requests)} requests")
