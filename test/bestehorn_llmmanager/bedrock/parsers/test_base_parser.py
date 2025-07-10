"""
Unit tests for base parser functionality.
Tests abstract base parser and protocol definitions.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from bestehorn_llmmanager.bedrock.models.data_structures import BedrockModelInfo
from bestehorn_llmmanager.bedrock.parsers.base_parser import (
    BaseDocumentationParser,
    DocumentationParser,
    ParsingError,
)


class TestDocumentationParserProtocol:
    """Test cases for DocumentationParser protocol."""

    def test_protocol_exists(self):
        """Test that the protocol is properly defined."""
        # Verify the protocol exists and has the expected method
        assert hasattr(DocumentationParser, "parse")

        # Verify the protocol is properly structured
        assert DocumentationParser.__name__ == "DocumentationParser"


class TestParsingError:
    """Test cases for ParsingError exception."""

    def test_parsing_error_creation(self):
        """Test ParsingError can be created and raised."""
        error_message = "Test parsing error"

        with pytest.raises(ParsingError) as exc_info:
            raise ParsingError(error_message)

        assert str(exc_info.value) == error_message

    def test_parsing_error_inheritance(self):
        """Test ParsingError inherits from Exception."""
        error = ParsingError("Test error")
        assert isinstance(error, Exception)

    def test_parsing_error_empty_message(self):
        """Test ParsingError with empty message."""
        with pytest.raises(ParsingError) as exc_info:
            raise ParsingError("")

        assert str(exc_info.value) == ""

    def test_parsing_error_with_cause(self):
        """Test ParsingError with exception chaining."""
        original_error = ValueError("Original error")

        with pytest.raises(ParsingError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise ParsingError("Parsing failed") from e

        assert exc_info.value.__cause__ == original_error


class ConcreteParser(BaseDocumentationParser):
    """Concrete implementation for testing abstract base class."""

    def parse(self, file_path: Path) -> dict:
        """Concrete implementation of parse method."""
        return {
            "test_model": BedrockModelInfo(
                provider="test-provider",
                model_id="test-model",
                regions_supported=["us-east-1"],
                input_modalities=["Text"],
                output_modalities=["Text"],
                streaming_supported=True,
            )
        }


class TestBaseDocumentationParser:
    """Test cases for BaseDocumentationParser abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseDocumentationParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDocumentationParser()

    def test_concrete_implementation_works(self):
        """Test that concrete implementation can be instantiated."""
        parser = ConcreteParser()
        assert isinstance(parser, BaseDocumentationParser)

    def test_concrete_implementation_parse_method(self):
        """Test that concrete implementation has working parse method."""
        parser = ConcreteParser()
        result = parser.parse(Path("dummy_path"))

        assert isinstance(result, dict)
        assert "test_model" in result
        assert isinstance(result["test_model"], BedrockModelInfo)


class TestValidateFileExists:
    """Test cases for _validate_file_exists method."""

    def test_validate_file_exists_success(self):
        """Test validation with existing readable file."""
        parser = ConcreteParser()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write("test content")
            tmp_file_path = Path(tmp_file.name)

        try:
            # Should not raise any exception
            parser._validate_file_exists(file_path=tmp_file_path)
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    def test_validate_file_exists_file_not_found(self):
        """Test validation with non-existent file."""
        parser = ConcreteParser()
        non_existent_path = Path("non_existent_file.txt")

        with pytest.raises(FileNotFoundError) as exc_info:
            parser._validate_file_exists(file_path=non_existent_path)

        assert "Documentation file not found" in str(exc_info.value)
        assert str(non_existent_path) in str(exc_info.value)

    def test_validate_file_exists_path_is_directory(self):
        """Test validation when path points to directory instead of file."""
        parser = ConcreteParser()

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)

            with pytest.raises(ValueError) as exc_info:
                parser._validate_file_exists(file_path=dir_path)

            assert "Path is not a file" in str(exc_info.value)
            assert str(dir_path) in str(exc_info.value)

    def test_validate_file_exists_permission_error(self):
        """Test validation with permission error."""
        parser = ConcreteParser()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write("test content")
            tmp_file_path = Path(tmp_file.name)

        try:
            # Mock open to raise PermissionError
            with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                with pytest.raises(PermissionError) as exc_info:
                    parser._validate_file_exists(file_path=tmp_file_path)

                assert "Cannot read file" in str(exc_info.value)
                assert str(tmp_file_path) in str(exc_info.value)
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    def test_validate_file_exists_unicode_decode_error(self):
        """Test validation with Unicode decode error."""
        parser = ConcreteParser()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write("test content")
            tmp_file_path = Path(tmp_file.name)

        try:
            # Mock open to raise UnicodeDecodeError
            unicode_error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
            with patch("builtins.open", side_effect=unicode_error):
                with pytest.raises(ValueError) as exc_info:
                    parser._validate_file_exists(file_path=tmp_file_path)

                assert "File is not valid UTF-8" in str(exc_info.value)
                assert str(tmp_file_path) in str(exc_info.value)
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    def test_validate_file_exists_with_actual_binary_file(self):
        """Test validation with actual binary file that would cause Unicode error."""
        parser = ConcreteParser()

        # Create a temporary binary file
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as tmp_file:
            # Write some binary data that's not valid UTF-8
            tmp_file.write(b"\xff\xfe\x00\x00invalid_utf8_content")
            tmp_file_path = Path(tmp_file.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                parser._validate_file_exists(file_path=tmp_file_path)

            assert "File is not valid UTF-8" in str(exc_info.value)
            assert str(tmp_file_path) in str(exc_info.value)
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    def test_validate_file_exists_with_empty_file(self):
        """Test validation with empty but valid file."""
        parser = ConcreteParser()

        # Create an empty temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp_file:
            # Write nothing, just create empty file
            tmp_file_path = Path(tmp_file.name)

        try:
            # Should not raise any exception
            parser._validate_file_exists(file_path=tmp_file_path)
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_validate_file_exists_path_operations(self, mock_is_file, mock_exists):
        """Test validation path operations are called correctly."""
        parser = ConcreteParser()
        test_path = Path("test_file.txt")

        # Test file not exists case
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError):
            parser._validate_file_exists(file_path=test_path)

        mock_exists.assert_called_once()

        # Reset mocks
        mock_exists.reset_mock()
        mock_is_file.reset_mock()

        # Test file exists but is not a file
        mock_exists.return_value = True
        mock_is_file.return_value = False

        with pytest.raises(ValueError):
            parser._validate_file_exists(file_path=test_path)

        mock_exists.assert_called_once()
        mock_is_file.assert_called_once()

    def test_validate_file_exists_with_utf8_file(self):
        """Test validation with valid UTF-8 file containing special characters."""
        parser = ConcreteParser()

        # Create a temporary file with UTF-8 content including special characters
        test_content = "Hello, World! 🌍 ñ é ü 中文"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write(test_content)
            tmp_file_path = Path(tmp_file.name)

        try:
            # Should not raise any exception
            parser._validate_file_exists(file_path=tmp_file_path)
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    def test_validate_file_exists_exception_chaining(self):
        """Test that exception chaining works correctly."""
        parser = ConcreteParser()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write("test content")
            tmp_file_path = Path(tmp_file.name)

        try:
            # Test PermissionError chaining
            original_permission_error = PermissionError("Original permission error")
            with patch("builtins.open", side_effect=original_permission_error):
                with pytest.raises(PermissionError) as exc_info:
                    parser._validate_file_exists(file_path=tmp_file_path)

                assert exc_info.value.__cause__ == original_permission_error

            # Test UnicodeDecodeError chaining
            original_unicode_error = UnicodeDecodeError(
                "utf-8", b"\xff", 0, 1, "invalid start byte"
            )
            with patch("builtins.open", side_effect=original_unicode_error):
                with pytest.raises(ValueError) as exc_info:
                    parser._validate_file_exists(file_path=tmp_file_path)

                assert exc_info.value.__cause__ == original_unicode_error
        finally:
            # Clean up
            os.unlink(tmp_file_path)
