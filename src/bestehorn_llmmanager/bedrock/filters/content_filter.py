"""
Content filtering and restoration system for LLM requests.

Handles the selective filtering of content blocks (images, documents, videos, etc.)
based on model capabilities and provides mechanisms to restore original content
when retrying with different models.
"""

import logging
from copy import deepcopy
from typing import Any, Dict, List, Set, Tuple

from ..models.llm_manager_constants import ConverseAPIFields, FeatureAvailability
from ..models.llm_manager_structures import ContentFilterState, FilteredContent


class ContentFilter:
    """
    Manages content filtering and restoration for LLM requests.

    This class provides functionality to:
    - Filter out unsupported content types from requests
    - Preserve original content for restoration
    - Restore filtered content when trying models that support it
    - Track which features have been disabled
    """

    def __init__(self) -> None:
        """Initialize the content filter."""
        self._logger = logging.getLogger(__name__)

        # Mapping of features to content block types
        self._feature_to_content_type = {
            "image_processing": ConverseAPIFields.IMAGE,
            "document_processing": ConverseAPIFields.DOCUMENT,
            "video_processing": ConverseAPIFields.VIDEO,
        }

        # Mapping of features to request fields
        self._feature_to_request_field = {
            "guardrails": ConverseAPIFields.GUARDRAIL_CONFIG,
            "tool_use": ConverseAPIFields.TOOL_CONFIG,
            "prompt_caching": ConverseAPIFields.CACHE_POINT,
        }

    def create_filter_state(self, original_request: Dict[str, Any]) -> ContentFilterState:
        """
        Create a filter state from the original request.

        Args:
            original_request: The original request arguments

        Returns:
            ContentFilterState containing original request and filtering metadata
        """
        return ContentFilterState(
            original_request=deepcopy(original_request),
            disabled_features=set(),
            filtered_content={},
        )

    def apply_filters(
        self, filter_state: ContentFilterState, disabled_features: Set[str]
    ) -> Dict[str, Any]:
        """
        Apply content filters to create a filtered request.

        Args:
            filter_state: The current filter state
            disabled_features: Set of features to disable

        Returns:
            Filtered request arguments
        """
        # Start with original request
        filtered_request = deepcopy(filter_state.original_request)

        # Track newly disabled features
        newly_disabled = disabled_features - filter_state.disabled_features

        # Apply content block filters
        if ConverseAPIFields.MESSAGES in filtered_request:
            filtered_messages, removed_content = self._filter_messages(
                messages=filtered_request[ConverseAPIFields.MESSAGES],
                disabled_features=disabled_features,
            )
            filtered_request[ConverseAPIFields.MESSAGES] = filtered_messages

            # Store removed content for potential restoration
            for feature in newly_disabled:
                if feature in self._feature_to_content_type:
                    if feature not in filter_state.filtered_content:
                        filter_state.filtered_content[feature] = []
                    filter_state.filtered_content[feature].extend(removed_content.get(feature, []))

        # Apply request field filters
        for feature in newly_disabled:
            if feature in self._feature_to_request_field:
                field_name = self._feature_to_request_field[feature]
                if field_name in filtered_request:
                    # Store original value for restoration
                    if feature not in filter_state.filtered_content:
                        filter_state.filtered_content[feature] = []
                    filter_state.filtered_content[feature] = deepcopy(filtered_request[field_name])
                    del filtered_request[field_name]

        # Update filter state
        filter_state.disabled_features.update(disabled_features)

        return filtered_request

    def restore_features(
        self, filter_state: ContentFilterState, features_to_restore: Set[str]
    ) -> Dict[str, Any]:
        """
        Restore previously filtered features to create a new request.

        Args:
            filter_state: The current filter state
            features_to_restore: Set of features to restore

        Returns:
            Request arguments with specified features restored
        """
        # Start with original request (unfiltered)
        restored_request = deepcopy(filter_state.original_request)

        # Determine which features should remain disabled
        remaining_disabled = filter_state.disabled_features - features_to_restore

        # Apply filtering only for features that should remain disabled
        if remaining_disabled:
            restored_request = self.apply_filters(
                filter_state=ContentFilterState(
                    original_request=filter_state.original_request,
                    disabled_features=set(),
                    filtered_content={},
                ),
                disabled_features=remaining_disabled,
            )

        return restored_request

    def _filter_messages(
        self, messages: List[Dict[str, Any]], disabled_features: Set[str]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[FilteredContent]]]:
        """
        Filter content blocks from messages based on disabled features.

        Args:
            messages: List of message dictionaries
            disabled_features: Set of features to disable

        Returns:
            Tuple of (filtered_messages, removed_content_by_feature)
        """
        filtered_messages = []
        removed_content: Dict[str, List[FilteredContent]] = {
            feature: [] for feature in disabled_features
        }

        for message_idx, message in enumerate(messages):
            if ConverseAPIFields.CONTENT not in message:
                filtered_messages.append(deepcopy(message))
                continue

            filtered_content_blocks = []

            for block_idx, content_block in enumerate(message[ConverseAPIFields.CONTENT]):
                if not isinstance(content_block, dict):
                    filtered_content_blocks.append(deepcopy(content_block))
                    continue

                # Check if this content block should be filtered
                should_filter = False
                filtered_feature = None

                for feature in disabled_features:
                    if feature in self._feature_to_content_type:
                        content_type = self._feature_to_content_type[feature]
                        if content_type in content_block:
                            should_filter = True
                            filtered_feature = feature
                            break

                if should_filter and filtered_feature:
                    # Store the filtered content for potential restoration
                    removed_content[filtered_feature].append(
                        FilteredContent(
                            message_index=message_idx,
                            block_index=block_idx,
                            content_block=deepcopy(content_block),
                        )
                    )

                    self._logger.debug(
                        f"Filtered {filtered_feature} content from message {message_idx}, "
                        f"block {block_idx}"
                    )
                else:
                    # Keep the content block
                    filtered_content_blocks.append(deepcopy(content_block))

            # Only include message if it has remaining content
            if filtered_content_blocks:
                filtered_message = deepcopy(message)
                filtered_message[ConverseAPIFields.CONTENT] = filtered_content_blocks
                filtered_messages.append(filtered_message)
            else:
                self._logger.warning(
                    f"Message {message_idx} has no remaining content after filtering"
                )

        return filtered_messages, removed_content

    def get_supported_features_for_model(self, model_name: str) -> Set[str]:
        """
        Determine which features are supported by a given model.

        Args:
            model_name: Name of the model to check

        Returns:
            Set of supported feature names
        """
        supported_features = set()

        # Convert model name to lowercase for pattern matching
        model_lower = model_name.lower()

        # Check if this is a text-only model first
        is_text_only = False
        for text_only_pattern in FeatureAvailability.TEXT_ONLY_MODELS:
            if text_only_pattern.lower() in model_lower:
                is_text_only = True
                self._logger.debug(f"Model {model_name} identified as text-only")
                break

        # If not explicitly text-only, check for multimodal capabilities
        if not is_text_only:
            for multimodal_pattern in FeatureAvailability.MULTIMODAL_MODELS:
                if multimodal_pattern.lower() in model_lower:
                    supported_features.update(
                        ["image_processing", "document_processing", "video_processing"]
                    )
                    self._logger.debug(f"Model {model_name} identified as multimodal")
                    break

        # Check tool use support
        for tool_pattern in FeatureAvailability.TOOL_USE_SUPPORTED_MODELS:
            if tool_pattern.lower() in model_lower:
                supported_features.add("tool_use")
                break

        # Most models support these features
        supported_features.update(["guardrails", "prompt_caching"])

        return supported_features

    def should_restore_features_for_model(
        self, filter_state: ContentFilterState, model_name: str
    ) -> Tuple[bool, Set[str]]:
        """
        Determine if features should be restored when trying a new model.

        Args:
            filter_state: Current filter state
            model_name: Name of the model to try

        Returns:
            Tuple of (should_restore, features_to_restore)
        """
        if not filter_state.disabled_features:
            return False, set()

        # Get features supported by this model
        supported_features = self.get_supported_features_for_model(model_name)

        # Find disabled features that this model supports
        restorable_features = filter_state.disabled_features & supported_features

        if restorable_features:
            self._logger.info(
                f"Model {model_name} supports {len(restorable_features)} "
                f"previously disabled features: {', '.join(restorable_features)}"
            )
            return True, restorable_features

        return False, set()

    def get_filter_summary(self, filter_state: ContentFilterState) -> Dict[str, Any]:
        """
        Get a summary of the current filtering state.

        Args:
            filter_state: The filter state to summarize

        Returns:
            Dictionary with filtering summary information
        """
        summary = {
            "disabled_features": list(filter_state.disabled_features),
            "filtered_content_types": list(filter_state.filtered_content.keys()),
            "total_filtered_items": sum(
                len(items) for items in filter_state.filtered_content.values()
            ),
        }

        # Count filtered items by type
        for feature, items in filter_state.filtered_content.items():
            if isinstance(items, list):
                summary[f"filtered_{feature}_count"] = len(items)

        return summary
