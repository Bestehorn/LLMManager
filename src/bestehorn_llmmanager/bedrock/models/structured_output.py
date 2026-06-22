"""
Helpers for the Bedrock Converse structured-output feature (issue #35).

Provides :func:`build_json_schema_output_config`, which wraps a JSON Schema into the
Converse ``outputConfig`` envelope (``{"textFormat": {"type": "json_schema",
"structure": <schema>}}``) accepted by :meth:`LLMManager.converse`'s ``output_config``
parameter. This is the API-native way to force schema-valid JSON output, distinct from
the library's response-validation-retry approach (which re-calls the model instead of
constraining generation).

Reference: Converse request ``outputConfig`` / ``OutputConfig`` / text format:
https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
"""

from typing import Any, Dict

from ..exceptions.llm_manager_exceptions import RequestValidationError
from .llm_manager_constants import ConverseAPIFields


def build_json_schema_output_config(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build an ``outputConfig`` for JSON-schema-constrained structured output.

    Args:
        schema: A JSON Schema object (a dict) describing the required output shape.

    Returns:
        An ``outputConfig`` dict ready to pass to ``converse(output_config=...)``::

            {"textFormat": {"type": "json_schema", "structure": <schema>}}

    Raises:
        RequestValidationError: If ``schema`` is not a non-empty dict.
    """
    if not isinstance(schema, dict) or not schema:
        raise RequestValidationError(
            f"output_config schema must be a non-empty JSON Schema dict, got {type(schema).__name__}"
        )
    return {
        ConverseAPIFields.TEXT_FORMAT: {
            ConverseAPIFields.OUTPUT_FORMAT_TYPE: ConverseAPIFields.OUTPUT_FORMAT_JSON_SCHEMA,
            ConverseAPIFields.OUTPUT_FORMAT_STRUCTURE: schema,
        }
    }
