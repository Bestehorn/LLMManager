"""
Unit tests for ConverseMessageBuilder local file methods.
Tests the new path-based methods: add_local_image, add_local_document, add_local_video.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from src.bedrock.models.converse_message_builder import ConverseMessageBuilder
from src.bedrock.models.message_builder_enums import RolesEnum, ImageFormatEnum, DocumentFormatEnum, VideoFormatEnum
from src.bedrock.models.llm_manager_constants import ConverseAPIFields
from src.bedrock.exceptions.llm_manager_exceptions import RequestValidationError


class TestAddLocalImageMethod:
    """Test cases for add_local_image method."""
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'\xFF\xD8\xFF\xE0')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_image_success(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test successfully adding local image."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Mock file size (1MB)
        mock_stat_result = Mock()
        mock_stat_result.st_size = 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        result = builder.add_local_image(
            path_to_local_file="/test/image.jpg",
            format=ImageFormatEnum.JPEG,
            max_size_mb=5.0
        )
        
        assert result is builder
        assert builder.content_block_count == 1
        
        # Verify file was opened
        mock_file.assert_called_once_with(Path("/test/image.jpg"), "rb")
        
        message = builder.build()
        image_block = message[ConverseAPIFields.CONTENT][0]
        
        assert ConverseAPIFields.IMAGE in image_block
        assert image_block[ConverseAPIFields.IMAGE][ConverseAPIFields.FORMAT] == "jpeg"
    
    @patch('pathlib.Path.exists')
    def test_add_local_image_file_not_found(self, mock_exists):
        """Test adding local image with non-existent file."""
        mock_exists.return_value = False
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            builder.add_local_image(path_to_local_file="/nonexistent/image.jpg")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    def test_add_local_image_not_a_file(self, mock_is_file, mock_exists):
        """Test adding local image with directory path."""
        mock_exists.return_value = True
        mock_is_file.return_value = False
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(RequestValidationError, match="Path is not a file"):
            builder.add_local_image(path_to_local_file="/test/directory/")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_image_file_too_large(self, mock_stat, mock_is_file, mock_exists):
        """Test adding local image that exceeds size limit."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Mock file size (10MB)
        mock_stat_result = Mock()
        mock_stat_result.st_size = 10 * 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(RequestValidationError, match="exceeds limit"):
            builder.add_local_image(
                path_to_local_file="/test/large_image.jpg",
                max_size_mb=5.0
            )
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_image_read_error(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test adding local image with read error."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        mock_stat_result = Mock()
        mock_stat_result.st_size = 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(RequestValidationError, match="Failed to read image file"):
            builder.add_local_image(path_to_local_file="/test/image.jpg")
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'\xFF\xD8\xFF\xE0')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_image_auto_detection(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test adding local image with automatic format detection."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        mock_stat_result = Mock()
        mock_stat_result.st_size = 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        # Test without explicit format (should auto-detect)
        result = builder.add_local_image(path_to_local_file="/test/image.jpg")
        
        assert result is builder
        assert builder.content_block_count == 1


class TestAddLocalDocumentMethod:
    """Test cases for add_local_document method."""
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'%PDF-1.4')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_document_success(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test successfully adding local document."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Mock file size (2MB)
        mock_stat_result = Mock()
        mock_stat_result.st_size = 2 * 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        result = builder.add_local_document(
            path_to_local_file="/test/document.pdf",
            format=DocumentFormatEnum.PDF,
            name="Test Document",
            max_size_mb=5.0
        )
        
        assert result is builder
        assert builder.content_block_count == 1
        
        # Verify file was opened
        mock_file.assert_called_once_with(Path("/test/document.pdf"), "rb")
        
        message = builder.build()
        doc_block = message[ConverseAPIFields.CONTENT][0]
        
        assert ConverseAPIFields.DOCUMENT in doc_block
        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.FORMAT] == "pdf"
        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] == "Test Document"
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'%PDF-1.4')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_document_filename_as_name(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test adding local document uses filename as name when no explicit name."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        mock_stat_result = Mock()
        mock_stat_result.st_size = 2 * 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        builder.add_local_document(
            path_to_local_file="/test/report.pdf",
            format=DocumentFormatEnum.PDF
        )
        
        message = builder.build()
        doc_block = message[ConverseAPIFields.CONTENT][0]
        
        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] == "report.pdf"
    
    @patch('pathlib.Path.exists')
    def test_add_local_document_file_not_found(self, mock_exists):
        """Test adding local document with non-existent file."""
        mock_exists.return_value = False
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(FileNotFoundError, match="Document file not found"):
            builder.add_local_document(path_to_local_file="/nonexistent/document.pdf")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_document_file_too_large(self, mock_stat, mock_is_file, mock_exists):
        """Test adding local document that exceeds size limit."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Mock file size (10MB)
        mock_stat_result = Mock()
        mock_stat_result.st_size = 10 * 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(RequestValidationError, match="exceeds limit"):
            builder.add_local_document(
                path_to_local_file="/test/large_document.pdf",
                max_size_mb=5.0
            )


class TestAddLocalVideoMethod:
    """Test cases for add_local_video method."""
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'\x00\x00\x00\x20ftypmp4')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_video_success(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test successfully adding local video."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Mock file size (50MB)
        mock_stat_result = Mock()
        mock_stat_result.st_size = 50 * 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        result = builder.add_local_video(
            path_to_local_file="/test/video.mp4",
            format=VideoFormatEnum.MP4,
            max_size_mb=100.0
        )
        
        assert result is builder
        assert builder.content_block_count == 1
        
        # Verify file was opened
        mock_file.assert_called_once_with(Path("/test/video.mp4"), "rb")
        
        message = builder.build()
        video_block = message[ConverseAPIFields.CONTENT][0]
        
        assert ConverseAPIFields.VIDEO in video_block
        assert video_block[ConverseAPIFields.VIDEO][ConverseAPIFields.FORMAT] == "mp4"
    
    @patch('pathlib.Path.exists')
    def test_add_local_video_file_not_found(self, mock_exists):
        """Test adding local video with non-existent file."""
        mock_exists.return_value = False
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            builder.add_local_video(path_to_local_file="/nonexistent/video.mp4")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_add_local_video_file_too_large(self, mock_stat, mock_is_file, mock_exists):
        """Test adding local video that exceeds size limit."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Mock file size (200MB)
        mock_stat_result = Mock()
        mock_stat_result.st_size = 200 * 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        with pytest.raises(RequestValidationError, match="exceeds limit"):
            builder.add_local_video(
                path_to_local_file="/test/large_video.mp4",
                max_size_mb=100.0
            )


class TestLocalMethodsIntegration:
    """Integration test cases for local file methods."""
    
    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_mixed_local_and_bytes_methods(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test mixing local file methods with bytes methods."""        
        # Setup mocks for file operations
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        mock_stat_result = Mock()
        mock_stat_result.st_size = 1024 * 1024  # 1MB
        mock_stat.return_value = mock_stat_result
        
        # Mock file content
        mock_file.side_effect = [
            mock_open(read_data=b'\xFF\xD8\xFF\xE0').return_value,  # JPEG data
            mock_open(read_data=b'%PDF-1.4').return_value,  # PDF data
        ]
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        # Mix local and bytes methods
        result = builder.add_text(text="Analyze these files:")\
                        .add_local_image(
                            path_to_local_file="/test/image.jpg",
                            format=ImageFormatEnum.JPEG
                        )\
                        .add_document_bytes(
                            bytes=b'%PDF-1.4',
                            format=DocumentFormatEnum.PDF,
                            name="Manual Document"
                        )\
                        .add_local_document(
                            path_to_local_file="/test/document.pdf",
                            format=DocumentFormatEnum.PDF
                        )
        
        assert result is builder
        assert builder.content_block_count == 4
        
        message = builder.build()
        content_blocks = message[ConverseAPIFields.CONTENT]
        
        # Verify all content blocks
        assert content_blocks[0][ConverseAPIFields.TEXT] == "Analyze these files:"
        assert ConverseAPIFields.IMAGE in content_blocks[1]
        assert ConverseAPIFields.DOCUMENT in content_blocks[2]
        assert ConverseAPIFields.DOCUMENT in content_blocks[3]
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'\xFF\xD8\xFF\xE0')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_local_methods_chaining(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test chaining of local file methods."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        mock_stat_result = Mock()
        mock_stat_result.st_size = 1024 * 1024
        mock_stat.return_value = mock_stat_result
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        # Test chaining returns same instance
        result = builder.add_local_image(path_to_local_file="/test/image1.jpg")
        assert result is builder
        
        result = result.add_local_image(path_to_local_file="/test/image2.jpg")
        assert result is builder
        
        result = result.add_local_document(path_to_local_file="/test/doc.pdf")
        assert result is builder
        
        assert builder.content_block_count == 3
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'\xFF\xD8\xFF\xE0')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_local_methods_with_different_size_limits(self, mock_stat, mock_is_file, mock_exists, mock_file):
        """Test local methods with different size limits."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Test different file sizes
        mock_stat_results = [
            Mock(st_size=1024 * 1024),    # 1MB - should pass with 2MB limit
            Mock(st_size=3 * 1024 * 1024), # 3MB - should fail with 2MB limit
            Mock(st_size=3 * 1024 * 1024), # 3MB - should fail with 2MB limit (second call in error message)
        ]
        mock_stat.side_effect = mock_stat_results
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        # First image should succeed
        builder.add_local_image(
            path_to_local_file="/test/small_image.jpg",
            max_size_mb=2.0
        )
        assert builder.content_block_count == 1
        
        # Second image should fail due to size limit
        with pytest.raises(RequestValidationError):
            builder.add_local_image(
                path_to_local_file="/test/large_image.jpg",
                max_size_mb=2.0
            )


class TestLocalMethodsErrorScenarios:
    """Test error scenarios for local file methods."""
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    def test_path_validation_edge_cases(self, mock_is_file, mock_exists):
        """Test various path validation edge cases."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        # Test empty path
        mock_exists.return_value = False
        with pytest.raises(FileNotFoundError):
            builder.add_local_image(path_to_local_file="")
        
        # Test relative path handling
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Should work with relative paths
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = Mock()
            mock_stat_result.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_result
            
            with patch('builtins.open', mock_open(read_data=b'\xFF\xD8\xFF\xE0')):
                result = builder.add_local_image(path_to_local_file="./test_image.jpg")
                assert result is builder
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    def test_size_limit_boundary_conditions(self, mock_stat, mock_is_file, mock_exists):
        """Test size limit boundary conditions."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        
        # Test file exactly at limit
        mock_stat_result = Mock()
        mock_stat_result.st_size = 5 * 1024 * 1024  # Exactly 5MB
        mock_stat.return_value = mock_stat_result
        
        with patch('builtins.open', mock_open(read_data=b'\xFF\xD8\xFF\xE0')):
            builder.add_local_image(
                path_to_local_file="/test/image.jpg",
                max_size_mb=5.0
            )
            assert builder.content_block_count == 1
        
        # Test file just over limit
        mock_stat_result.st_size = 5 * 1024 * 1024 + 1  # 5MB + 1 byte
        
        with pytest.raises(RequestValidationError):
            builder.add_local_image(
                path_to_local_file="/test/large_image.jpg",
                max_size_mb=5.0
            )
