"""
Builder for constructing additionalModelRequestFields from various sources.
Handles priority merging and model-specific parameter compatibility.
"""

import copy
import logging
from typing import Any, Dict, List, Optional, Set

from ..models.model_specific_structures import ModelSpecificConfig

logger = logging.getLogger(__name__)


# JSON field constants
class ParameterFields:
    """JSON field name constants for additionalModelRequestFields."""

    ANTHROPIC_BETA: str = "anthropic_beta"


class ParameterBuilder:
    """
    Builds additionalModelRequestFields from various sources.

    This class handles the merging of parameters from multiple sources with
    a defined priority order, and applies model-specific transformations.
    """

    # Model compatibility mappings
    EXTENDED_CONTEXT_MODELS: Set[str] = {
        "Claude 3.5 Sonnet v2",
        "Claude Sonnet 4",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
    }

    EXTENDED_CONTEXT_BETA_HEADER: str = "context-1m-2025-08-07"

    def build_additional_fields(
        self,
        model_name: str,
        model_specific_config: Optional[ModelSpecificConfig] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build final additionalModelRequestFields dictionary.

        Priority order:
        1. Start with additional_model_request_fields (backward compatibility)
        2. Merge in model_specific_config.custom_fields
        3. Apply enable_extended_context if set

        Args:
            model_name: Name of the model
            model_specific_config: High-level configuration
            additional_model_request_fields: Direct fields (legacy)

        Returns:
            Merged additionalModelRequestFields or None if no parameters
        """
        # Start with a copy of direct fields (backward compatibility)
        result: Optional[Dict[str, Any]] = None
        if additional_model_request_fields is not None:
            result = copy.deepcopy(additional_model_request_fields)
            logger.debug(
                f"Starting with additional_model_request_fields: "
                f"{list(additional_model_request_fields.keys())}"
            )

        # Merge in model_specific_config if provided
        if model_specific_config is not None:
            # Merge custom_fields
            if model_specific_config.custom_fields is not None:
                if result is None:
                    result = {}

                # Special handling for anthropic_beta to avoid duplicates
                custom_fields_copy = copy.deepcopy(model_specific_config.custom_fields)
                if ParameterFields.ANTHROPIC_BETA in custom_fields_copy:
                    # Extract beta array from custom_fields
                    custom_beta = custom_fields_copy.pop(ParameterFields.ANTHROPIC_BETA)
                    # Merge other fields first
                    result.update(custom_fields_copy)
                    # Then merge beta array without duplicates
                    if isinstance(custom_beta, list):
                        result = self._merge_anthropic_beta(
                            existing_fields=result,
                            new_beta_values=custom_beta,
                        )
                    else:
                        # If not a list, just set it
                        result[ParameterFields.ANTHROPIC_BETA] = custom_beta
                else:
                    # No beta array, just merge normally
                    result.update(custom_fields_copy)

                logger.debug(
                    f"Merged custom_fields: {list(model_specific_config.custom_fields.keys())}"
                )

            # Apply enable_extended_context
            if model_specific_config.enable_extended_context:
                if self._is_extended_context_compatible(model_name=model_name):
                    if result is None:
                        result = {}
                    result = self._merge_anthropic_beta(
                        existing_fields=result,
                        new_beta_values=[self.EXTENDED_CONTEXT_BETA_HEADER],
                    )
                    logger.info(f"Extended context enabled for model: {model_name}")
                else:
                    logger.warning(
                        f"Extended context requested but model {model_name} "
                        f"is not compatible. Skipping extended context parameter."
                    )

        return result

    def _merge_anthropic_beta(
        self,
        existing_fields: Dict[str, Any],
        new_beta_values: List[str],
    ) -> Dict[str, Any]:
        """
        Merge anthropic_beta arrays without duplicates.

        Args:
            existing_fields: Existing additionalModelRequestFields
            new_beta_values: New beta values to add

        Returns:
            Merged fields with combined beta array
        """
        result = copy.deepcopy(existing_fields)

        # Get existing beta array or create new one
        existing_beta = result.get(ParameterFields.ANTHROPIC_BETA, [])
        if not isinstance(existing_beta, list):
            existing_beta = []

        # Merge without duplicates while preserving order
        # Use a set to track what we've seen for deduplication
        seen = set()
        merged_beta = []

        # Add existing values first
        for value in existing_beta:
            if value not in seen:
                seen.add(value)
                merged_beta.append(value)

        # Add new values
        for value in new_beta_values:
            if value not in seen:
                seen.add(value)
                merged_beta.append(value)

        result[ParameterFields.ANTHROPIC_BETA] = merged_beta
        return result

    def _is_extended_context_compatible(self, model_name: str) -> bool:
        """
        Check if model supports extended context.

        Args:
            model_name: Name of the model to check

        Returns:
            True if model supports extended context, False otherwise
        """
        return model_name in self.EXTENDED_CONTEXT_MODELS
