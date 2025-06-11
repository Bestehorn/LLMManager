"""
Unit tests for message builder enums.
Tests all enumeration classes used in the ConverseMessageBuilder system.
"""

import pytest
from enum import Enum

from src.bedrock.models.message_builder_enums import (
    RolesEnum, ImageFormatEnum, DocumentFormatEnum, VideoFormatEnum, DetectionMethodEnum
)
from src.bedrock.models.llm_manager_constants import ConverseAPIFields


class TestRolesEnum:
    """Test cases for RolesEnum."""
    
    def test_roles_enum_values(self):
        """Test that RolesEnum has correct values."""
        assert RolesEnum.USER == ConverseAPIFields.ROLE_USER
        assert RolesEnum.ASSISTANT == ConverseAPIFields.ROLE_ASSISTANT
    
    def test_roles_enum_is_string_enum(self):
        """Test that RolesEnum extends str."""
        assert isinstance(RolesEnum.USER, str)
        assert isinstance(RolesEnum.ASSISTANT, str)
    
    def test_roles_enum_string_representation(self):
        """Test string representation of enum values."""
        assert str(RolesEnum.USER) == "user"
        assert str(RolesEnum.ASSISTANT) == "assistant"
    
    def test_roles_enum_comparison(self):
        """Test enum value comparison."""
        assert RolesEnum.USER != RolesEnum.ASSISTANT
        assert RolesEnum.USER == "user"
        assert RolesEnum.ASSISTANT == "assistant"


class TestImageFormatEnum:
    """Test cases for ImageFormatEnum."""
    
    def test_image_format_enum_values(self):
        """Test that ImageFormatEnum has expected values."""
        expected_formats = ["jpeg", "png", "gif", "webp"]
        actual_formats = [format.value for format in ImageFormatEnum]
        
        for expected in expected_formats:
            assert expected in actual_formats
    
    def test_image_format_enum_is_string_enum(self):
        """Test that ImageFormatEnum extends str."""
        for format_enum in ImageFormatEnum:
            assert isinstance(format_enum, str)
    
    def test_image_format_enum_specific_values(self):
        """Test specific enum values."""
        assert ImageFormatEnum.JPEG == "jpeg"
        assert ImageFormatEnum.PNG == "png"
        assert ImageFormatEnum.GIF == "gif"
        assert ImageFormatEnum.WEBP == "webp"


class TestDocumentFormatEnum:
    """Test cases for DocumentFormatEnum."""
    
    def test_document_format_enum_values(self):
        """Test that DocumentFormatEnum has expected values."""
        expected_formats = ["pdf", "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"]
        actual_formats = [format.value for format in DocumentFormatEnum]
        
        for expected in expected_formats:
            assert expected in actual_formats
    
    def test_document_format_enum_is_string_enum(self):
        """Test that DocumentFormatEnum extends str."""
        for format_enum in DocumentFormatEnum:
            assert isinstance(format_enum, str)
    
    def test_document_format_enum_specific_values(self):
        """Test specific enum values."""
        assert DocumentFormatEnum.PDF == "pdf"
        assert DocumentFormatEnum.DOCX == "docx"
        assert DocumentFormatEnum.HTML == "html"
        assert DocumentFormatEnum.TXT == "txt"


class TestVideoFormatEnum:
    """Test cases for VideoFormatEnum."""
    
    def test_video_format_enum_values(self):
        """Test that VideoFormatEnum has expected values."""
        expected_formats = ["mp4", "mov", "avi", "webm", "mkv"]
        actual_formats = [format.value for format in VideoFormatEnum]
        
        for expected in expected_formats:
            assert expected in actual_formats
    
    def test_video_format_enum_is_string_enum(self):
        """Test that VideoFormatEnum extends str."""
        for format_enum in VideoFormatEnum:
            assert isinstance(format_enum, str)
    
    def test_video_format_enum_specific_values(self):
        """Test specific enum values."""
        assert VideoFormatEnum.MP4 == "mp4"
        assert VideoFormatEnum.MOV == "mov"
        assert VideoFormatEnum.AVI == "avi"
        assert VideoFormatEnum.WEBM == "webm"
        assert VideoFormatEnum.MKV == "mkv"


class TestDetectionMethodEnum:
    """Test cases for DetectionMethodEnum."""
    
    def test_detection_method_enum_values(self):
        """Test that DetectionMethodEnum has expected values."""
        expected_methods = ["extension", "content", "combined", "manual"]
        actual_methods = [method.value for method in DetectionMethodEnum]
        
        for expected in expected_methods:
            assert expected in actual_methods
    
    def test_detection_method_enum_is_string_enum(self):
        """Test that DetectionMethodEnum extends str."""
        for method_enum in DetectionMethodEnum:
            assert isinstance(method_enum, str)
    
    def test_detection_method_enum_specific_values(self):
        """Test specific enum values."""
        assert DetectionMethodEnum.EXTENSION == "extension"
        assert DetectionMethodEnum.CONTENT == "content"
        assert DetectionMethodEnum.COMBINED == "combined"
        assert DetectionMethodEnum.MANUAL == "manual"


class TestEnumInteroperability:
    """Test interoperability between enums and other systems."""
    
    def test_enum_json_serialization(self):
        """Test that enums can be serialized to JSON-compatible values."""
        import json
        
        # Test that enum values can be JSON serialized
        test_data = {
            "role": RolesEnum.USER,
            "image_format": ImageFormatEnum.JPEG,
            "document_format": DocumentFormatEnum.PDF,
            "video_format": VideoFormatEnum.MP4,
            "detection_method": DetectionMethodEnum.CONTENT
        }
        
        # This should not raise an exception
        json_str = json.dumps(test_data, default=str)
        assert "user" in json_str
        assert "jpeg" in json_str
        assert "pdf" in json_str
        assert "mp4" in json_str
        assert "content" in json_str
    
    def test_enum_in_collections(self):
        """Test that enums work properly in collections."""
        roles = [RolesEnum.USER, RolesEnum.ASSISTANT]
        assert len(roles) == 2
        assert RolesEnum.USER in roles
        
        formats = {ImageFormatEnum.JPEG, ImageFormatEnum.PNG}
        assert len(formats) == 2
        assert ImageFormatEnum.JPEG in formats
    
    def test_enum_comparison_with_strings(self):
        """Test that enums can be compared with strings."""
        assert RolesEnum.USER == "user"
        assert ImageFormatEnum.JPEG == "jpeg"
        assert DocumentFormatEnum.PDF == "pdf"
        assert VideoFormatEnum.MP4 == "mp4"
        assert DetectionMethodEnum.CONTENT == "content"
        
        # Test inequality
        assert RolesEnum.USER != "assistant"
        assert ImageFormatEnum.JPEG != "png"


class TestEnumValidation:
    """Test enum validation and error cases."""
    
    def test_invalid_enum_creation(self):
        """Test that invalid enum values raise appropriate errors."""
        with pytest.raises(ValueError):
            ImageFormatEnum("invalid_format")
        
        with pytest.raises(ValueError):
            DocumentFormatEnum("invalid_document")
        
        with pytest.raises(ValueError):
            VideoFormatEnum("invalid_video")
        
        with pytest.raises(ValueError):
            DetectionMethodEnum("invalid_method")
    
    def test_enum_membership(self):
        """Test enum membership testing."""
        assert "jpeg" in [f.value for f in ImageFormatEnum]
        assert "invalid" not in [f.value for f in ImageFormatEnum]
        
        assert "pdf" in [f.value for f in DocumentFormatEnum]
        assert "invalid" not in [f.value for f in DocumentFormatEnum]
    
    def test_enum_iteration(self):
        """Test that enums can be iterated over."""
        role_values = []
        for role in RolesEnum:
            role_values.append(role.value)
        
        assert "user" in role_values
        assert "assistant" in role_values
        assert len(role_values) == 2
