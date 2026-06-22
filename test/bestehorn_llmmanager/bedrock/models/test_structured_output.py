"""
Tests for the structured-output helper (issue #35).
"""

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import RequestValidationError
from bestehorn_llmmanager.bedrock.models.structured_output import build_json_schema_output_config


class TestBuildJsonSchemaOutputConfig:
    """build_json_schema_output_config wraps a JSON Schema into outputConfig."""

    def test_wraps_schema(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        config = build_json_schema_output_config(schema=schema)
        assert config == {
            "textFormat": {
                "type": "json_schema",
                "structure": schema,
            }
        }

    def test_empty_schema_rejected(self):
        with pytest.raises(RequestValidationError):
            build_json_schema_output_config(schema={})

    def test_non_dict_schema_rejected(self):
        with pytest.raises(RequestValidationError):
            build_json_schema_output_config(schema="not-a-dict")  # type: ignore[arg-type]
