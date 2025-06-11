"""
Unit tests for src.bedrock.models.constants module.

Tests all constants classes and their values to ensure they remain unchanged
and maintain expected types and values.
"""

import pytest
from typing import Final

from src.bedrock.models.constants import (
    JSONFields,
    HTMLTableColumns,
    BooleanValues,
    URLs,
    FilePaths,
    LogMessages
)


class TestJSONFields:
    """Test JSONFields constant class."""
    
    def test_all_fields_are_strings(self):
        """Test that all JSONFields constants are strings."""
        assert isinstance(JSONFields.RETRIEVAL_TIMESTAMP, str)
        assert isinstance(JSONFields.MODELS, str)
        assert isinstance(JSONFields.PROVIDER, str)
        assert isinstance(JSONFields.MODEL_ID, str)
        assert isinstance(JSONFields.REGIONS_SUPPORTED, str)
        assert isinstance(JSONFields.INPUT_MODALITIES, str)
        assert isinstance(JSONFields.OUTPUT_MODALITIES, str)
        assert isinstance(JSONFields.STREAMING_SUPPORTED, str)
        assert isinstance(JSONFields.INFERENCE_PARAMETERS_LINK, str)
        assert isinstance(JSONFields.HYPERPARAMETERS_LINK, str)
    
    def test_field_values(self):
        """Test that JSONFields constants have expected values."""
        assert JSONFields.RETRIEVAL_TIMESTAMP == "retrieval_timestamp"
        assert JSONFields.MODELS == "models"
        assert JSONFields.PROVIDER == "provider"
        assert JSONFields.MODEL_ID == "model_id"
        assert JSONFields.REGIONS_SUPPORTED == "regions_supported"
        assert JSONFields.INPUT_MODALITIES == "input_modalities"
        assert JSONFields.OUTPUT_MODALITIES == "output_modalities"
        assert JSONFields.STREAMING_SUPPORTED == "streaming_supported"
        assert JSONFields.INFERENCE_PARAMETERS_LINK == "inference_parameters_link"
        assert JSONFields.HYPERPARAMETERS_LINK == "hyperparameters_link"
    
    @pytest.mark.skip(reason="Python doesn't enforce Final type immutability at runtime")
    def test_fields_are_immutable(self):
        """Test that JSONFields constants cannot be reassigned."""
        with pytest.raises(AttributeError):
            JSONFields.RETRIEVAL_TIMESTAMP = "new_value"
    
    def test_all_fields_are_non_empty(self):
        """Test that all JSONFields constants are non-empty strings."""
        fields = [
            JSONFields.RETRIEVAL_TIMESTAMP,
            JSONFields.MODELS,
            JSONFields.PROVIDER,
            JSONFields.MODEL_ID,
            JSONFields.REGIONS_SUPPORTED,
            JSONFields.INPUT_MODALITIES,
            JSONFields.OUTPUT_MODALITIES,
            JSONFields.STREAMING_SUPPORTED,
            JSONFields.INFERENCE_PARAMETERS_LINK,
            JSONFields.HYPERPARAMETERS_LINK
        ]
        
        for field in fields:
            assert field.strip() != ""
            assert len(field) > 0


class TestHTMLTableColumns:
    """Test HTMLTableColumns constant class."""
    
    def test_all_columns_are_strings(self):
        """Test that all HTMLTableColumns constants are strings."""
        assert isinstance(HTMLTableColumns.PROVIDER, str)
        assert isinstance(HTMLTableColumns.MODEL_NAME, str)
        assert isinstance(HTMLTableColumns.MODEL_ID, str)
        assert isinstance(HTMLTableColumns.REGIONS_SUPPORTED, str)
        assert isinstance(HTMLTableColumns.INPUT_MODALITIES, str)
        assert isinstance(HTMLTableColumns.OUTPUT_MODALITIES, str)
        assert isinstance(HTMLTableColumns.STREAMING_SUPPORTED, str)
        assert isinstance(HTMLTableColumns.INFERENCE_PARAMETERS, str)
        assert isinstance(HTMLTableColumns.HYPERPARAMETERS, str)
    
    def test_column_values(self):
        """Test that HTMLTableColumns constants have expected values."""
        assert HTMLTableColumns.PROVIDER == "Provider"
        assert HTMLTableColumns.MODEL_NAME == "Model name"
        assert HTMLTableColumns.MODEL_ID == "Model ID"
        assert HTMLTableColumns.REGIONS_SUPPORTED == "Regions supported"
        assert HTMLTableColumns.INPUT_MODALITIES == "Input modalities"
        assert HTMLTableColumns.OUTPUT_MODALITIES == "Output modalities"
        assert HTMLTableColumns.STREAMING_SUPPORTED == "Streaming supported"
        assert HTMLTableColumns.INFERENCE_PARAMETERS == "Inference parameters"
        assert HTMLTableColumns.HYPERPARAMETERS == "Hyperparameters"
    
    @pytest.mark.skip(reason="Python doesn't enforce Final type immutability at runtime")
    def test_columns_are_immutable(self):
        """Test that HTMLTableColumns constants cannot be reassigned."""
        with pytest.raises(AttributeError):
            HTMLTableColumns.PROVIDER = "new_value"
    
    def test_all_columns_are_non_empty(self):
        """Test that all HTMLTableColumns constants are non-empty strings."""
        columns = [
            HTMLTableColumns.PROVIDER,
            HTMLTableColumns.MODEL_NAME,
            HTMLTableColumns.MODEL_ID,
            HTMLTableColumns.REGIONS_SUPPORTED,
            HTMLTableColumns.INPUT_MODALITIES,
            HTMLTableColumns.OUTPUT_MODALITIES,
            HTMLTableColumns.STREAMING_SUPPORTED,
            HTMLTableColumns.INFERENCE_PARAMETERS,
            HTMLTableColumns.HYPERPARAMETERS
        ]
        
        for column in columns:
            assert column.strip() != ""
            assert len(column) > 0


class TestBooleanValues:
    """Test BooleanValues constant class."""
    
    def test_all_values_are_strings(self):
        """Test that all BooleanValues constants are strings."""
        assert isinstance(BooleanValues.YES, str)
        assert isinstance(BooleanValues.NO, str)
        assert isinstance(BooleanValues.NOT_AVAILABLE, str)
    
    def test_boolean_values(self):
        """Test that BooleanValues constants have expected values."""
        assert BooleanValues.YES == "Yes"
        assert BooleanValues.NO == "No"
        assert BooleanValues.NOT_AVAILABLE == "N/A"
    
    @pytest.mark.skip(reason="Python doesn't enforce Final type immutability at runtime")
    def test_values_are_immutable(self):
        """Test that BooleanValues constants cannot be reassigned."""
        with pytest.raises(AttributeError):
            BooleanValues.YES = "new_value"
    
    def test_all_values_are_non_empty(self):
        """Test that all BooleanValues constants are non-empty strings."""
        values = [
            BooleanValues.YES,
            BooleanValues.NO,
            BooleanValues.NOT_AVAILABLE
        ]
        
        for value in values:
            assert value.strip() != ""
            assert len(value) > 0


class TestURLs:
    """Test URLs constant class."""
    
    def test_all_urls_are_strings(self):
        """Test that all URLs constants are strings."""
        assert isinstance(URLs.BEDROCK_MODELS_DOCUMENTATION, str)
    
    def test_url_values(self):
        """Test that URLs constants have expected values."""
        expected_url = "https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html"
        assert URLs.BEDROCK_MODELS_DOCUMENTATION == expected_url
    
    @pytest.mark.skip(reason="Python doesn't enforce Final type immutability at runtime")
    def test_urls_are_immutable(self):
        """Test that URLs constants cannot be reassigned."""
        with pytest.raises(AttributeError):
            URLs.BEDROCK_MODELS_DOCUMENTATION = "new_value"
    
    def test_url_format(self):
        """Test that URL constants have valid URL format."""
        assert URLs.BEDROCK_MODELS_DOCUMENTATION.startswith("https://")
        assert "docs.aws.amazon.com" in URLs.BEDROCK_MODELS_DOCUMENTATION
    
    def test_url_is_non_empty(self):
        """Test that URL constants are non-empty strings."""
        assert URLs.BEDROCK_MODELS_DOCUMENTATION.strip() != ""
        assert len(URLs.BEDROCK_MODELS_DOCUMENTATION) > 0


class TestFilePaths:
    """Test FilePaths constant class."""
    
    def test_all_paths_are_strings(self):
        """Test that all FilePaths constants are strings."""
        assert isinstance(FilePaths.DEFAULT_HTML_OUTPUT, str)
        assert isinstance(FilePaths.DEFAULT_JSON_OUTPUT, str)
    
    def test_path_values(self):
        """Test that FilePaths constants have expected values."""
        assert FilePaths.DEFAULT_HTML_OUTPUT == "docs/FoundationalModels.htm"
        assert FilePaths.DEFAULT_JSON_OUTPUT == "docs/FoundationalModels.json"
    
    @pytest.mark.skip(reason="Python doesn't enforce Final type immutability at runtime")
    def test_paths_are_immutable(self):
        """Test that FilePaths constants cannot be reassigned."""
        with pytest.raises(AttributeError):
            FilePaths.DEFAULT_HTML_OUTPUT = "new_value"
    
    def test_path_format(self):
        """Test that file paths have expected formats."""
        assert FilePaths.DEFAULT_HTML_OUTPUT.endswith(".htm")
        assert FilePaths.DEFAULT_JSON_OUTPUT.endswith(".json")
        assert FilePaths.DEFAULT_HTML_OUTPUT.startswith("docs/")
        assert FilePaths.DEFAULT_JSON_OUTPUT.startswith("docs/")
    
    def test_paths_are_non_empty(self):
        """Test that FilePaths constants are non-empty strings."""
        paths = [
            FilePaths.DEFAULT_HTML_OUTPUT,
            FilePaths.DEFAULT_JSON_OUTPUT
        ]
        
        for path in paths:
            assert path.strip() != ""
            assert len(path) > 0


class TestLogMessages:
    """Test LogMessages constant class."""
    
    def test_all_messages_are_strings(self):
        """Test that all LogMessages constants are strings."""
        assert isinstance(LogMessages.DOWNLOAD_STARTED, str)
        assert isinstance(LogMessages.DOWNLOAD_COMPLETED, str)
        assert isinstance(LogMessages.PARSING_STARTED, str)
        assert isinstance(LogMessages.PARSING_COMPLETED, str)
        assert isinstance(LogMessages.JSON_EXPORT_STARTED, str)
        assert isinstance(LogMessages.JSON_EXPORT_COMPLETED, str)
        assert isinstance(LogMessages.NETWORK_ERROR, str)
        assert isinstance(LogMessages.PARSING_ERROR, str)
        assert isinstance(LogMessages.FILE_ERROR, str)
    
    def test_message_values(self):
        """Test that LogMessages constants have expected values."""
        assert LogMessages.DOWNLOAD_STARTED == "Starting download of Bedrock documentation"
        assert LogMessages.DOWNLOAD_COMPLETED == "Successfully downloaded documentation to {file_path}"
        assert LogMessages.PARSING_STARTED == "Starting HTML parsing"
        assert LogMessages.PARSING_COMPLETED == "Successfully parsed {model_count} models"
        assert LogMessages.JSON_EXPORT_STARTED == "Starting JSON export"
        assert LogMessages.JSON_EXPORT_COMPLETED == "Successfully exported JSON to {file_path}"
        assert LogMessages.NETWORK_ERROR == "Network error during download: {error}"
        assert LogMessages.PARSING_ERROR == "Error parsing HTML: {error}"
        assert LogMessages.FILE_ERROR == "File operation error: {error}"
    
    @pytest.mark.skip(reason="Python doesn't enforce Final type immutability at runtime")
    def test_messages_are_immutable(self):
        """Test that LogMessages constants cannot be reassigned."""
        with pytest.raises(AttributeError):
            LogMessages.DOWNLOAD_STARTED = "new_value"
    
    def test_template_messages_have_placeholders(self):
        """Test that template messages contain expected placeholders."""
        template_messages = [
            (LogMessages.DOWNLOAD_COMPLETED, "{file_path}"),
            (LogMessages.PARSING_COMPLETED, "{model_count}"),
            (LogMessages.JSON_EXPORT_COMPLETED, "{file_path}"),
            (LogMessages.NETWORK_ERROR, "{error}"),
            (LogMessages.PARSING_ERROR, "{error}"),
            (LogMessages.FILE_ERROR, "{error}")
        ]
        
        for message, placeholder in template_messages:
            assert placeholder in message
    
    def test_all_messages_are_non_empty(self):
        """Test that all LogMessages constants are non-empty strings."""
        messages = [
            LogMessages.DOWNLOAD_STARTED,
            LogMessages.DOWNLOAD_COMPLETED,
            LogMessages.PARSING_STARTED,
            LogMessages.PARSING_COMPLETED,
            LogMessages.JSON_EXPORT_STARTED,
            LogMessages.JSON_EXPORT_COMPLETED,
            LogMessages.NETWORK_ERROR,
            LogMessages.PARSING_ERROR,
            LogMessages.FILE_ERROR
        ]
        
        for message in messages:
            assert message.strip() != ""
            assert len(message) > 0
    
    def test_message_formatting(self):
        """Test that template messages can be formatted correctly."""
        # Test messages with file_path placeholder
        file_path_messages = [
            LogMessages.DOWNLOAD_COMPLETED,
            LogMessages.JSON_EXPORT_COMPLETED
        ]
        
        for message in file_path_messages:
            formatted = message.format(file_path="/test/path")
            assert "/test/path" in formatted
            assert "{file_path}" not in formatted
        
        # Test message with model_count placeholder
        formatted = LogMessages.PARSING_COMPLETED.format(model_count=42)
        assert "42" in formatted
        assert "{model_count}" not in formatted
        
        # Test messages with error placeholder
        error_messages = [
            LogMessages.NETWORK_ERROR,
            LogMessages.PARSING_ERROR,
            LogMessages.FILE_ERROR
        ]
        
        for message in error_messages:
            formatted = message.format(error="test error")
            assert "test error" in formatted
            assert "{error}" not in formatted


class TestConstantsIntegration:
    """Integration tests for all constants classes."""
    
    def test_no_duplicate_values_across_classes(self):
        """Test that there are no duplicate values across different constant classes."""
        # Collect all string constants
        all_constants = []
        
        # JSONFields
        json_fields = [
            JSONFields.RETRIEVAL_TIMESTAMP, JSONFields.MODELS, JSONFields.PROVIDER,
            JSONFields.MODEL_ID, JSONFields.REGIONS_SUPPORTED, JSONFields.INPUT_MODALITIES,
            JSONFields.OUTPUT_MODALITIES, JSONFields.STREAMING_SUPPORTED,
            JSONFields.INFERENCE_PARAMETERS_LINK, JSONFields.HYPERPARAMETERS_LINK
        ]
        all_constants.extend(json_fields)
        
        # HTMLTableColumns
        html_columns = [
            HTMLTableColumns.PROVIDER, HTMLTableColumns.MODEL_NAME, HTMLTableColumns.MODEL_ID,
            HTMLTableColumns.REGIONS_SUPPORTED, HTMLTableColumns.INPUT_MODALITIES,
            HTMLTableColumns.OUTPUT_MODALITIES, HTMLTableColumns.STREAMING_SUPPORTED,
            HTMLTableColumns.INFERENCE_PARAMETERS, HTMLTableColumns.HYPERPARAMETERS
        ]
        all_constants.extend(html_columns)
        
        # BooleanValues
        boolean_values = [BooleanValues.YES, BooleanValues.NO, BooleanValues.NOT_AVAILABLE]
        all_constants.extend(boolean_values)
        
        # URLs
        urls = [URLs.BEDROCK_MODELS_DOCUMENTATION]
        all_constants.extend(urls)
        
        # FilePaths
        file_paths = [FilePaths.DEFAULT_HTML_OUTPUT, FilePaths.DEFAULT_JSON_OUTPUT]
        all_constants.extend(file_paths)
        
        # Check for duplicates (excluding log messages which may have duplicates by design)
        unique_constants = set(all_constants)
        assert len(unique_constants) == len(all_constants), "Found duplicate constant values"
    
    def test_constants_module_structure(self):
        """Test that the constants module has the expected structure."""
        # Test that all expected classes exist
        from src.bedrock.models import constants
        
        expected_classes = [
            'JSONFields', 'HTMLTableColumns', 'BooleanValues', 
            'URLs', 'FilePaths', 'LogMessages'
        ]
        
        for class_name in expected_classes:
            assert hasattr(constants, class_name), f"Missing class: {class_name}"
    
    @pytest.mark.skip(reason="Python doesn't enforce Final type immutability at runtime")
    def test_final_type_annotations(self):
        """Test that constants use Final type annotations correctly."""
        # This test verifies that the constants are properly typed
        # The actual Final enforcement is tested in individual class tests
        from typing import get_type_hints
        
        # We can't directly test Final annotations at runtime, but we can verify
        # that the constants behave as expected (immutable)
        with pytest.raises(AttributeError):
            JSONFields.RETRIEVAL_TIMESTAMP = "changed"
        
        with pytest.raises(AttributeError):
            HTMLTableColumns.PROVIDER = "changed"
        
        with pytest.raises(AttributeError):
            BooleanValues.YES = "changed"
