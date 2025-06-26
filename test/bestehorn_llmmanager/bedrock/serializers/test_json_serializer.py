"""
Unit tests for bedrock.serializers.json_serializer module.
Tests for JSONModelSerializer class.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, mock_open, patch

import pytest

from bestehorn_llmmanager.bedrock.models.constants import LogMessages
from bestehorn_llmmanager.bedrock.models.data_structures import ModelCatalog
from bestehorn_llmmanager.bedrock.serializers.json_serializer import JSONModelSerializer


class TestJSONModelSerializer:
    """Test cases for JSONModelSerializer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = JSONModelSerializer()
        self.custom_serializer = JSONModelSerializer(indent=4, ensure_ascii=True)

        # Mock model catalog
        self.mock_catalog = Mock(spec=ModelCatalog)
        self.mock_catalog_dict = {
            "retrieval_timestamp": "2024-01-01T12:00:00Z",
            "models": {
                "anthropic.claude-3-5-sonnet-20241022-v2:0": {
                    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "model_name": "Claude 3.5 Sonnet",
                    "provider_name": "Anthropic",
                }
            },
        }
        self.mock_catalog.to_dict.return_value = self.mock_catalog_dict

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        serializer = JSONModelSerializer()

        assert serializer._indent == 2
        assert serializer._ensure_ascii is False

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        serializer = JSONModelSerializer(indent=4, ensure_ascii=True)

        assert serializer._indent == 4
        assert serializer._ensure_ascii is True

    def test_serialize_to_file_success(self):
        """Test successful serialization to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_output.json"

            with patch(
                "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
            ) as mock_logger:
                mock_log_instance = Mock()
                mock_logger.return_value = mock_log_instance

                serializer = JSONModelSerializer()
                serializer._logger = mock_log_instance

                serializer.serialize_to_file(catalog=self.mock_catalog, output_path=output_path)

                # Verify file was created and contains expected data
                assert output_path.exists()

                with open(output_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)

                assert loaded_data == self.mock_catalog_dict

                # Verify logging calls
                mock_log_instance.info.assert_any_call(LogMessages.JSON_EXPORT_STARTED)
                mock_log_instance.info.assert_any_call(
                    LogMessages.JSON_EXPORT_COMPLETED.format(file_path=output_path)
                )

    def test_serialize_to_file_creates_parent_directory(self):
        """Test that serialization creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "subdir" / "nested" / "test_output.json"

            self.serializer.serialize_to_file(catalog=self.mock_catalog, output_path=output_path)

            # Verify nested directories were created
            assert output_path.exists()
            assert output_path.parent.exists()

    def test_serialize_to_file_custom_formatting(self):
        """Test serialization with custom formatting options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_formatted.json"

            self.custom_serializer.serialize_to_file(
                catalog=self.mock_catalog, output_path=output_path
            )

            # Read the file content as text to check formatting
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Should have 4-space indentation and sorted keys
            assert "    " in content  # 4-space indent
            lines = content.split("\n")
            # Should be pretty-printed (multiple lines)
            assert len(lines) > 1

    def test_serialize_to_file_os_error(self):
        """Test handling of OS errors during file serialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.json"

            # Mock open to raise OSError
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with patch(
                    "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
                ) as mock_logger:
                    mock_log_instance = Mock()
                    mock_logger.return_value = mock_log_instance

                    serializer = JSONModelSerializer()
                    serializer._logger = mock_log_instance

                    with pytest.raises(OSError):
                        serializer.serialize_to_file(
                            catalog=self.mock_catalog, output_path=output_path
                        )

                    # Verify error was logged
                    mock_log_instance.error.assert_called()

    def test_serialize_to_file_serialization_error(self):
        """Test handling of serialization errors during file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_error.json"

            # Mock catalog that raises TypeError on to_dict()
            error_catalog = Mock(spec=ModelCatalog)
            error_catalog.to_dict.side_effect = TypeError("Serialization error")

            with patch(
                "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
            ) as mock_logger:
                mock_log_instance = Mock()
                mock_logger.return_value = mock_log_instance

                serializer = JSONModelSerializer()
                serializer._logger = mock_log_instance

                with pytest.raises(TypeError, match="JSON serialization failed"):
                    serializer.serialize_to_file(catalog=error_catalog, output_path=output_path)

                # Verify error was logged
                mock_log_instance.error.assert_called()

    def test_serialize_to_string_success(self):
        """Test successful serialization to string."""
        result = self.serializer.serialize_to_string(catalog=self.mock_catalog)

        # Should be valid JSON
        parsed_result = json.loads(result)
        assert parsed_result == self.mock_catalog_dict

        # Should be formatted (contains newlines for indentation)
        assert "\n" in result

    def test_serialize_to_string_custom_formatting(self):
        """Test string serialization with custom formatting."""
        result = self.custom_serializer.serialize_to_string(catalog=self.mock_catalog)

        # Should use 4-space indentation
        lines = result.split("\n")
        indented_lines = [line for line in lines if line.startswith("    ")]
        assert len(indented_lines) > 0

        # Should contain 4 spaces for first level indentation
        assert any(line.startswith("    ") and not line.startswith("        ") for line in lines)

    def test_serialize_to_string_serialization_error(self):
        """Test handling of serialization errors in string serialization."""
        error_catalog = Mock(spec=ModelCatalog)
        error_catalog.to_dict.side_effect = TypeError("Serialization error")

        with patch(
            "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
        ) as mock_logger:
            mock_log_instance = Mock()
            mock_logger.return_value = mock_log_instance

            serializer = JSONModelSerializer()
            serializer._logger = mock_log_instance

            with pytest.raises(TypeError, match="JSON serialization failed"):
                serializer.serialize_to_string(catalog=error_catalog)

            # Verify error was logged
            mock_log_instance.error.assert_called()

    def test_serialize_dict_to_file_success(self):
        """Test successful dictionary serialization to file."""
        test_data = {"key1": "value1", "key2": {"nested": "value2"}, "key3": [1, 2, 3]}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_dict.json"

            self.serializer.serialize_dict_to_file(data=test_data, output_path=output_path)

            # Verify file was created and contains expected data
            assert output_path.exists()

            with open(output_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data

    def test_serialize_dict_to_file_creates_parent_directory(self):
        """Test that dict serialization creates parent directories."""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "dir" / "test.json"

            self.serializer.serialize_dict_to_file(data=test_data, output_path=output_path)

            assert output_path.exists()
            assert output_path.parent.exists()

    def test_serialize_dict_to_file_os_error(self):
        """Test handling of OS errors in dictionary serialization."""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.json"

            # Mock open to raise OSError
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with patch(
                    "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
                ) as mock_logger:
                    mock_log_instance = Mock()
                    mock_logger.return_value = mock_log_instance

                    serializer = JSONModelSerializer()
                    serializer._logger = mock_log_instance

                    with pytest.raises(OSError):
                        serializer.serialize_dict_to_file(data=test_data, output_path=output_path)

                    mock_log_instance.error.assert_called()

    def test_serialize_dict_to_file_serialization_error(self):
        """Test handling of serialization errors in dictionary serialization."""
        # Create unserializable data (e.g., containing a function)
        unserializable_data = {"func": lambda x: x}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_error.json"

            with patch(
                "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
            ) as mock_logger:
                mock_log_instance = Mock()
                mock_logger.return_value = mock_log_instance

                serializer = JSONModelSerializer()
                serializer._logger = mock_log_instance

                with pytest.raises(TypeError, match="JSON serialization failed"):
                    serializer.serialize_dict_to_file(
                        data=unserializable_data, output_path=output_path
                    )

                mock_log_instance.error.assert_called()

    def test_load_from_file_success(self):
        """Test successful loading from JSON file."""
        test_data = {"key1": "value1", "key2": {"nested": "value2"}, "key3": [1, 2, 3]}

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test_input.json"

            # Create test file
            with open(input_path, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            result = self.serializer.load_from_file(input_path=input_path)

            assert result == test_data

    def test_load_from_file_not_found(self):
        """Test loading from non-existent file."""
        nonexistent_path = Path("/nonexistent/file.json")

        with pytest.raises(FileNotFoundError, match="JSON file not found"):
            self.serializer.load_from_file(input_path=nonexistent_path)

    def test_load_from_file_os_error(self):
        """Test handling of OS errors during file loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test_input.json"

            # Create the file
            with open(input_path, "w", encoding="utf-8") as f:
                json.dump({"test": "data"}, f)

            # Mock open to raise OSError
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with patch(
                    "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
                ) as mock_logger:
                    mock_log_instance = Mock()
                    mock_logger.return_value = mock_log_instance

                    serializer = JSONModelSerializer()
                    serializer._logger = mock_log_instance

                    with pytest.raises(OSError):
                        serializer.load_from_file(input_path=input_path)

                    mock_log_instance.error.assert_called()

    def test_load_from_file_json_decode_error(self):
        """Test handling of JSON decode errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "invalid.json"

            # Create invalid JSON file
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{ invalid json content }")

            with patch(
                "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
            ) as mock_logger:
                mock_log_instance = Mock()
                mock_logger.return_value = mock_log_instance

                serializer = JSONModelSerializer()
                serializer._logger = mock_log_instance

                with pytest.raises(ValueError, match="JSON parsing failed"):
                    serializer.load_from_file(input_path=input_path)

                mock_log_instance.error.assert_called()

    def test_serialize_to_file_sorted_keys(self):
        """Test that serialization produces sorted keys."""
        # Create data with unsorted keys
        unsorted_catalog_dict = {"z_last": "value_z", "a_first": "value_a", "m_middle": "value_m"}

        mock_catalog = Mock(spec=ModelCatalog)
        mock_catalog.to_dict.return_value = unsorted_catalog_dict

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "sorted_test.json"

            self.serializer.serialize_to_file(catalog=mock_catalog, output_path=output_path)

            # Read file content as text to check key ordering
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Keys should appear in sorted order
            a_pos = content.find('"a_first"')
            m_pos = content.find('"m_middle"')
            z_pos = content.find('"z_last"')

            assert a_pos < m_pos < z_pos

    def test_serialize_to_string_sorted_keys(self):
        """Test that string serialization produces sorted keys."""
        unsorted_catalog_dict = {"z_last": "value_z", "a_first": "value_a", "m_middle": "value_m"}

        mock_catalog = Mock(spec=ModelCatalog)
        mock_catalog.to_dict.return_value = unsorted_catalog_dict

        result = self.serializer.serialize_to_string(catalog=mock_catalog)

        # Keys should appear in sorted order
        a_pos = result.find('"a_first"')
        m_pos = result.find('"m_middle"')
        z_pos = result.find('"z_last"')

        assert a_pos < m_pos < z_pos

    def test_serialize_dict_to_file_sorted_keys(self):
        """Test that dictionary serialization produces sorted keys."""
        unsorted_dict = {"z_last": "value_z", "a_first": "value_a", "m_middle": "value_m"}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "dict_sorted_test.json"

            self.serializer.serialize_dict_to_file(data=unsorted_dict, output_path=output_path)

            # Read file content as text to check key ordering
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Keys should appear in sorted order
            a_pos = content.find('"a_first"')
            m_pos = content.find('"m_middle"')
            z_pos = content.find('"z_last"')

            assert a_pos < m_pos < z_pos

    def test_ensure_ascii_false(self):
        """Test that non-ASCII characters are preserved when ensure_ascii=False."""
        unicode_data = {"message": "Hello 世界"}
        mock_catalog = Mock(spec=ModelCatalog)
        mock_catalog.to_dict.return_value = unicode_data

        serializer_ascii_false = JSONModelSerializer(ensure_ascii=False)
        result = serializer_ascii_false.serialize_to_string(catalog=mock_catalog)

        # Should contain actual Unicode characters
        assert "世界" in result

    def test_ensure_ascii_true(self):
        """Test that non-ASCII characters are escaped when ensure_ascii=True."""
        unicode_data = {"message": "Hello 世界"}
        mock_catalog = Mock(spec=ModelCatalog)
        mock_catalog.to_dict.return_value = unicode_data

        serializer_ascii_true = JSONModelSerializer(ensure_ascii=True)
        result = serializer_ascii_true.serialize_to_string(catalog=mock_catalog)

        # Should contain escaped Unicode sequences
        assert "\\u" in result
        assert "世界" not in result

    def test_logger_initialization(self):
        """Test that logger is properly initialized."""
        with patch(
            "bestehorn_llmmanager.bedrock.serializers.json_serializer.logging.getLogger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            serializer = JSONModelSerializer()

            mock_get_logger.assert_called_once_with(
                "bestehorn_llmmanager.bedrock.serializers.json_serializer"
            )
            assert serializer._logger == mock_logger

    def test_comprehensive_workflow(self):
        """Test a complete serialize-then-load workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "workflow_test.json"

            # Serialize catalog to file
            self.serializer.serialize_to_file(catalog=self.mock_catalog, output_path=file_path)

            # Load data back from file
            loaded_data = self.serializer.load_from_file(input_path=file_path)

            # Should match original catalog data
            assert loaded_data == self.mock_catalog_dict

            # Verify catalog's to_dict was called
            self.mock_catalog.to_dict.assert_called()
