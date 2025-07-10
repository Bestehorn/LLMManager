"""
Enums for the ConverseMessageBuilder system.
Contains all enumerated values used in message construction.
"""

from enum import Enum

from .bedrock.models.llm_manager_constants import ConverseAPIFields


class RolesEnum(str, Enum):
    """
    Enumeration of valid message roles for the Converse API.

    Values map directly to the ConverseAPIFields constants to ensure consistency.
    """

    USER = ConverseAPIFields.ROLE_USER
    ASSISTANT = ConverseAPIFields.ROLE_ASSISTANT

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


class ImageFormatEnum(str, Enum):
    """
    Enumeration of supported image formats for the Converse API.

    These formats are compatible with AWS Bedrock image processing capabilities.
    """

    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"


class DocumentFormatEnum(str, Enum):
    """
    Enumeration of supported document formats for the Converse API.

    These formats are compatible with AWS Bedrock document processing capabilities.
    """

    PDF = "pdf"
    CSV = "csv"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    HTML = "html"
    TXT = "txt"
    MD = "md"


class VideoFormatEnum(str, Enum):
    """
    Enumeration of supported video formats for the Converse API.

    These formats are compatible with AWS Bedrock video processing capabilities.
    """

    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"
    MKV = "mkv"


class DetectionMethodEnum(str, Enum):
    """
    Enumeration of file type detection methods used by FileTypeDetector.

    Used for logging and debugging purposes to indicate how format was determined.
    """

    EXTENSION = "extension"
    CONTENT = "content"
    COMBINED = "combined"
    MANUAL = "manual"
